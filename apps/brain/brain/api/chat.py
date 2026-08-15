import hashlib
import json

import frappe
from werkzeug.wrappers import Response as WerkzeugResponse


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def _get_or_create_session(session_id: str, page_context: dict, provider: str, model: str) -> str:
    """Return an existing open session or create a new one. Returns session name."""
    if session_id:
        row = frappe.db.get_value(
            "Brain Chat Session", session_id, ["status", "user"], as_dict=True
        )
        if row and row.status == "Active" and row.user == frappe.session.user:
            frappe.db.set_value("Brain Chat Session", session_id, "last_active", frappe.utils.now_datetime())
            return session_id

    user = frappe.session.user
    user_doc = frappe.get_cached_doc("User", user)

    # Read settings via raw dict — avoids Document.onload and any password field loading
    s = frappe.db.get_singles_dict("Brain Settings")
    data_classification = s.get("data_classification") or "Regulated (21 CFR)"

    # Route may arrive as a list from the browser — convert to a readable string
    route = page_context.get("route", "")
    if isinstance(route, list):
        route = " > ".join(str(r) for r in route)

    session = frappe.get_doc({
        "doctype": "Brain Chat Session",
        "user": user,
        "user_fullname": user_doc.full_name,
        "status": "Active",
        "ip_address": _get_ip(),
        "initial_route": route,
        "provider_used": provider,
        "model_used": model,
        "data_classification": data_classification,
        "message_count": 0,
        "tool_call_count": 0,
    })
    session.insert(ignore_permissions=True)
    frappe.db.commit()

    from brain.ai.audit import write_audit_log
    write_audit_log(
        event_type="session_start",
        session=session.name,
        detail={"route": route, "provider": provider, "model": model},
    )

    return session.name


def _save_message(session_id: str, role: str, content: str, sequence: int,
                  tools_called: list = None, provider: str = "", model: str = "") -> str:
    """Persist a single message to Brain Chat Message. Returns the doc name."""
    now = frappe.utils.now_datetime()
    raw = f"{content}{now}{session_id}"
    content_hash = hashlib.sha256(raw.encode()).hexdigest()

    msg = frappe.get_doc({
        "doctype": "Brain Chat Message",
        "session": session_id,
        "sequence": sequence,
        "role": role,
        "content": content,
        "content_hash": content_hash,
        "timestamp": now,
        "provider_used": provider if role == "assistant" else "",
        "model_used": model if role == "assistant" else "",
        "tools_called": json.dumps(tools_called or [], default=str),
    })
    msg.insert(ignore_permissions=True)
    return msg.name


def _increment_session_count(session_id: str, messages: int = 0, tools: int = 0):
    if not session_id:
        return
    frappe.db.sql(
        """UPDATE `tabBrain Chat Session`
           SET message_count = message_count + %s,
               tool_call_count = tool_call_count + %s,
               last_active = NOW()
           WHERE name = %s""",
        (messages, tools, session_id),
    )


def _get_ip() -> str:
    try:
        return frappe.local.request.environ.get("REMOTE_ADDR", "")
    except Exception:
        return ""


def _provider_info():
    """Return (provider_name, model_name) from Brain Settings — no Document load, no password side effects."""
    try:
        s = frappe.db.get_singles_dict("Brain Settings")
        return (s.get("provider") or "Unknown"), (s.get("model") or "")
    except Exception:
        return "Unknown", ""


# ---------------------------------------------------------------------------
# Public whitelisted endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def send(message: str, history: str = "[]", context: str = "{}", session_id: str = ""):
    """
    Receives a chat message, runs the AI agent, persists the exchange,
    and returns the AI response.

    Returns:
        {message: str, actions: list, session_id: str}
    """
    if frappe.session.user == "Guest":
        frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

    try:
        history_list = json.loads(history) if isinstance(history, str) else history
    except Exception:
        history_list = []

    try:
        page_context = json.loads(context) if isinstance(context, str) else context
    except Exception:
        page_context = {}

    provider, model = _provider_info()

    # Resolve or create session
    sid = _get_or_create_session(session_id, page_context, provider, model)

    # Sequence = number of existing messages + 1
    seq_base = frappe.db.count("Brain Chat Message", {"session": sid})

    # Persist user message
    _save_message(sid, "user", message, seq_base + 1)

    from brain.ai.audit import write_audit_log
    write_audit_log(
        event_type="user_message",
        session=sid,
        detail={"sequence": seq_base + 1, "char_count": len(message)},
    )

    # If loading from server history, skip passing the client's stale copy
    if not history_list and sid:
        history_list = _load_server_history(sid, exclude_last=1)

    from brain.ai.agent import run
    result = run(
        user_message=message,
        conversation_history=history_list,
        page_context=page_context,
    )

    # Persist assistant response
    tool_count = len(result.get("actions", []))
    _save_message(sid, "assistant", result.get("message", ""), seq_base + 2,
                  tools_called=result.get("actions", []), provider=provider, model=model)
    _increment_session_count(sid, messages=2, tools=tool_count)

    write_audit_log(
        event_type="assistant_response",
        session=sid,
        detail={"sequence": seq_base + 2, "tool_count": tool_count, "char_count": len(result.get("message", ""))},
    )

    frappe.db.commit()
    result["session_id"] = sid
    return result


@frappe.whitelist()
def send_stream(message: str, history: str = "[]", context: str = "{}", session_id: str = ""):
    """Streaming SSE endpoint — yields tokens as they arrive so UI updates in real time."""
    if frappe.session.user == "Guest":
        frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

    try:
        history_list = json.loads(history) if isinstance(history, str) else history
    except Exception:
        history_list = []
    try:
        page_context = json.loads(context) if isinstance(context, str) else context
    except Exception:
        page_context = {}

    # Pre-flight: collect everything we need before opening the stream.
    # Any crash here returns an SSE error event instead of HTTP 500.
    setup_error = None
    sid = None
    seq_base = 0
    provider = "Unknown"
    model = ""
    write_audit_log = None

    try:
        provider, model = _provider_info()
        sid = _get_or_create_session(session_id, page_context, provider, model)
        seq_base = frappe.db.count("Brain Chat Message", {"session": sid}) or 0
        _save_message(sid, "user", message, seq_base + 1)

        from brain.ai.audit import write_audit_log as _wal
        write_audit_log = _wal
        write_audit_log(
            event_type="user_message",
            session=sid,
            detail={"sequence": seq_base + 1, "char_count": len(message)},
        )

        if not history_list and sid:
            history_list = _load_server_history(sid, exclude_last=1)

    except Exception as e:
        setup_error = str(e)
        frappe.log_error(frappe.get_traceback(), "Nuerix send_stream setup error")

    from brain.ai.agent import run_stream

    def _generate():
        # Always start with session_id (even if setup failed, so client clears state)
        yield f"data: {json.dumps({'type': 'session', 'session_id': sid or ''})}\n\n"

        if setup_error:
            yield f"data: {json.dumps({'type': 'error', 'message': setup_error})}\n\n"
            return

        # Fast-path: instant, non-AI answers for a known set of common data
        # questions on apps that register one (see brain_fast_answers docstring
        # for why this exists -- an LLM round trip has a multi-second floor that
        # no prompt tuning removes; this bypasses it for the high-frequency cases).
        fast_answer = None
        try:
            from stylo_fleet.api.brain_fast_answers import try_fast_answer
            fast_answer = try_fast_answer(message)
        except ImportError:
            pass
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Brain fast-path error")

        if fast_answer:
            yield f"data: {json.dumps({'type': 'chunk', 'text': fast_answer})}\n\n"
            try:
                _save_message(sid, "assistant", fast_answer, seq_base + 2,
                              tools_called=[], provider=provider, model=model)
                _increment_session_count(sid, messages=2, tools=0)
                if write_audit_log:
                    write_audit_log(
                        event_type="assistant_response",
                        session=sid,
                        detail={"sequence": seq_base + 2, "tool_count": 0, "fast_path": True},
                    )
                frappe.db.commit()
            except Exception:
                pass
            yield f"data: {json.dumps({'type': 'done', 'message': fast_answer, 'actions': []})}\n\n"
            return

        collected_text = []
        tool_events = []
        try:
            for event in run_stream(message, history_list, page_context, session_id=sid):
                if event.get("type") == "tool":
                    tool_events.append(event.get("label", ""))
                elif event.get("type") == "chunk":
                    collected_text.append(event.get("text", ""))
                elif event.get("type") == "done":
                    full_text = event.get("message", "".join(collected_text))
                    try:
                        _save_message(sid, "assistant", full_text, seq_base + 2,
                                      tools_called=event.get("actions", []), provider=provider, model=model)
                        _increment_session_count(sid, messages=2, tools=len(tool_events))
                        if write_audit_log:
                            write_audit_log(
                                event_type="assistant_response",
                                session=sid,
                                detail={"sequence": seq_base + 2, "tool_count": len(tool_events)},
                            )
                        frappe.db.commit()
                    except Exception:
                        pass  # persistence failure must not break the response

                yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Nuerix run_stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return WerkzeugResponse(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@frappe.whitelist()
def get_history(session_id: str):
    """
    Load message history for an existing session.
    Returns [{role, content, timestamp}] ordered by sequence ASC.
    Used on chat open to restore prior conversation.
    """
    if frappe.session.user == "Guest":
        frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

    if not session_id:
        return []

    # Verify the session belongs to this user
    owner = frappe.db.get_value("Brain Chat Session", session_id, "user")
    if owner != frappe.session.user and not frappe.has_permission("Brain Chat Session", "read"):
        frappe.throw("Not permitted.", frappe.PermissionError)

    messages = frappe.get_all(
        "Brain Chat Message",
        filters={"session": session_id, "is_anonymized": 0},
        fields=["role", "content", "timestamp", "sequence"],
        order_by="sequence asc",
    )
    return messages


@frappe.whitelist()
def close_session(session_id: str):
    """Mark a session as Closed."""
    if frappe.session.user == "Guest":
        frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

    if not session_id:
        return

    owner = frappe.db.get_value("Brain Chat Session", session_id, "user")
    if owner != frappe.session.user:
        frappe.throw("Not permitted.", frappe.PermissionError)

    frappe.db.set_value("Brain Chat Session", session_id, {
        "status": "Closed",
        "closed_at": frappe.utils.now_datetime(),
    })

    from brain.ai.audit import write_audit_log
    write_audit_log(event_type="session_end", session=session_id, detail={"closed_by": "user"})
    frappe.db.commit()


@frappe.whitelist()
def get_sessions(limit: int = 20):
    """Return recent chat sessions for the current user."""
    if frappe.session.user == "Guest":
        frappe.throw("brAIn requires authentication.", frappe.AuthenticationError)

    sessions = frappe.get_all(
        "Brain Chat Session",
        filters={"user": frappe.session.user},
        fields=["name", "session_title", "status", "started_at", "last_active", "message_count"],
        order_by="last_active desc",
        limit=limit,
    )
    return sessions


def _safe_pw(settings):
    """Return API key without ever calling frappe.throw() (which queues error messages to the browser)."""
    provider = settings.provider or ""
    # Local providers never need an API key
    if "Neurix" in provider or "Ollama" in provider:
        return ""
    try:
        # raise_exception=False means get_decrypted_password returns None instead of calling frappe.throw()
        return settings.get_password("api_key", raise_exception=False) or ""
    except Exception:
        return ""


@frappe.whitelist()
def health_check():
    """
    Diagnostic endpoint — tests Ollama connectivity and Python imports.
    Returns a plain dict so the UI can show specific error messages.
    """
    result = {"ok": True, "issues": [], "details": {}}

    # 1. Check Brain Settings readable
    try:
        s = frappe.db.get_singles_dict("Brain Settings")
        result["details"]["provider"] = s.get("provider", "not set")
        result["details"]["enabled"] = s.get("enabled", "0")
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"Brain Settings unreadable: {e}")

    # 2. Check Brain Chat Session table exists
    try:
        frappe.db.count("Brain Chat Session", {})
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"Brain Chat Session table missing — run bench migrate: {e}")

    # 3. Check Brain Chat Message table exists
    try:
        frappe.db.count("Brain Chat Message", {})
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"Brain Chat Message table missing — run bench migrate: {e}")

    # 4. Check Brain Audit Log table exists
    try:
        frappe.db.count("Brain Audit Log", {})
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"Brain Audit Log table missing — run bench migrate: {e}")

    # 5. Check Python imports
    try:
        from brain.ai.agent import get_settings, get_provider  # noqa
        from brain.ai.system_prompt import build_fast_system_prompt  # noqa
        from brain.ai.tools.executor import execute_tool  # noqa
    except Exception as e:
        result["ok"] = False
        result["issues"].append(f"Python import error: {e}")

    # 6. Check Ollama reachability (for Nuerix/Ollama providers)
    provider = result["details"].get("provider", "")
    if "Neurix" in provider or "Ollama" in provider:
        try:
            import urllib.request
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                headers={"User-Agent": "NuerixHealthCheck/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                import json as _json
                data = _json.loads(resp.read())
                models = [m.get("name", "") for m in data.get("models", [])]
                result["details"]["ollama_models"] = models
                result["details"]["ollama_ok"] = True
        except Exception as e:
            result["ok"] = False
            result["details"]["ollama_ok"] = False
            result["issues"].append(f"Ollama not reachable at localhost:11434 — is it running? Error: {e}")

    return result


@frappe.whitelist()
def get_settings_status():
    """Returns whether brAIn is configured and enabled (for the UI to show/hide the bubble)."""
    try:
        # Use db.get_singles_dict to avoid triggering Document.onload and password field logic
        values = frappe.db.get_singles_dict("Brain Settings")
        provider = values.get("provider") or ""
        is_local = "Ollama" in provider or "Neurix" in provider
        enabled = frappe.utils.cint(values.get("enabled", 0))
        display_name = values.get("display_name") or "brAIn"

        if is_local:
            configured = bool(provider)
        else:
            # Check API key exists in __Auth without triggering any exception messages
            has_key = bool(frappe.db.sql(
                "SELECT 1 FROM `__Auth` WHERE doctype=%s AND name=%s AND fieldname=%s LIMIT 1",
                ("Brain Settings", "Brain Settings", "api_key"),
            ))
            configured = bool(provider and has_key)

        return {
            "enabled": bool(enabled),
            "provider": provider,
            "display_name": display_name,
            "configured": configured,
        }
    except Exception:
        return {"enabled": False, "provider": None, "display_name": "brAIn", "configured": False}


# ---------------------------------------------------------------------------
# Internal utility
# ---------------------------------------------------------------------------

def _load_server_history(session_id: str, exclude_last: int = 0) -> list:
    """Load all non-anonymized messages as {role, content} for the agent."""
    messages = frappe.get_all(
        "Brain Chat Message",
        filters={"session": session_id, "is_anonymized": 0},
        fields=["role", "content", "sequence"],
        order_by="sequence asc",
    )
    if exclude_last and messages:
        messages = messages[:-exclude_last]
    return [{"role": m.role, "content": m.content} for m in messages]
