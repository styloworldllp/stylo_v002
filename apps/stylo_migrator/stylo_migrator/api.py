"""
Whitelisted API endpoints called by the migration dashboard.
"""
import frappe
from .migrator.connection import test_connection as _test_conn
from .migrator.engine import get_preview_counts, run_all


@frappe.whitelist()
def test_connection():
    """Test the v14 DB connection. Returns {success, message, table_count}."""
    success, message, table_count = _test_conn()

    # Persist status on Migration Config
    cfg = frappe.get_single("Migration Config")
    cfg.connection_status = message
    cfg.save(ignore_permissions=True)
    frappe.db.commit()

    return {"success": success, "message": message, "table_count": table_count}


@frappe.whitelist()
def preview_counts():
    """Return per-phase record counts from v14. Used in the Preview step."""
    try:
        return {"success": True, "phases": get_preview_counts()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def preview_phase(phase_index):
    """
    Return counts for a single migration phase (zero-based index).
    Index == len(PHASES) triggers discovery of extra/custom tables.
    Called repeatedly by the dashboard to stream results phase-by-phase.
    """
    from .migrator.connection import get_v14_conn, table_exists, count_records
    from .migrator.dependency_order import PHASES, ALL_DOCTYPES

    idx = int(phase_index)

    try:
        conn = get_v14_conn()
    except Exception as e:
        return {"success": False, "error": str(e)}

    try:
        # Final pass — discover tables not in the predefined list
        if idx >= len(PHASES):
            covered = set(ALL_DOCTYPES)
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES")
                all_tables = [list(r.values())[0] for r in cur.fetchall()]
            extra = []
            for tbl in sorted(all_tables):
                if not tbl.startswith("tab"):
                    continue
                dt = tbl[3:]
                if dt in covered:
                    continue
                cnt = count_records(conn, dt)
                if cnt > 0:
                    extra.append({"doctype": dt, "count": cnt})
            return {
                "success":  True,
                "phase":    {"phase": "Phase ∞ — Other / Custom Tables", "doctypes": extra} if extra else None,
                "has_more": False,
                "total_phases": len(PHASES) + 1,
            }

        phase = PHASES[idx]
        requires_app = phase.get("requires_app")

        # Skip entire phase if required app is not installed
        if requires_app and requires_app not in frappe.get_installed_apps():
            return {
                "success":      True,
                "phase":        None,
                "skipped":      True,
                "skip_reason":  f"'{requires_app}' not installed",
                "has_more":     True,
                "total_phases": len(PHASES) + 1,
            }

        phase_counts = []
        for doctype in phase["doctypes"]:
            if not table_exists(conn, doctype):
                continue
            cnt = count_records(conn, doctype)
            phase_counts.append({"doctype": doctype, "count": cnt})

        return {
            "success":      True,
            "phase":        {"phase": phase["name"], "doctypes": phase_counts} if phase_counts else None,
            "has_more":     True,          # always true for defined phases (custom pass follows)
            "total_phases": len(PHASES) + 1,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


@frappe.whitelist()
def start_migration():
    """Create a Migration Job and enqueue the migration engine."""
    # Check no job is currently running
    running = frappe.db.exists("Migration Job", {"status": "Running"})
    if running:
        return {"success": False, "error": f"A migration is already running: {running}"}

    job = frappe.get_doc({
        "doctype": "Migration Job",
        "status":  "Queued",
    })
    job.insert(ignore_permissions=True)
    frappe.db.commit()

    site     = frappe.local.site
    job_name = job.name

    # Use subprocess so the engine gets its own clean Frappe + DB context.
    # This is more reliable than threads (no shared connection pool issues).
    import subprocess, sys, os

    bench_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    bench_bin  = os.path.join(bench_root, "env", "bin", "bench")
    cmd = f"frappe.get_module('stylo_migrator.migrator.engine').run_all('{job_name}')"

    subprocess.Popen(
        [bench_bin, "--site", site, "execute", cmd],
        cwd=bench_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,   # detach from parent process group
    )

    return {"success": True, "job": job_name}


@frappe.whitelist()
def get_progress(job):
    """Return current job status, counters, and per-doctype progress from Redis."""
    if not frappe.db.exists("Migration Job", job):
        return {"success": False, "error": "Job not found"}

    doc = frappe.get_doc("Migration Job", job)

    # Read per-doctype progress stored by _publish() in engine.py
    import json
    per_doctype = {}
    try:
        prefix = f"{job}:"
        # frappe.cache().hgetall returns {field: value} for all hash fields
        all_fields = frappe.cache().hgetall("migration_progress") or {}
        for field_bytes, val_bytes in all_fields.items():
            field = field_bytes.decode() if isinstance(field_bytes, bytes) else field_bytes
            if not field.startswith(prefix):
                continue
            dt = field[len(prefix):]
            payload = json.loads(val_bytes.decode() if isinstance(val_bytes, bytes) else val_bytes)
            per_doctype[dt] = payload.get("count", 0)
    except Exception:
        pass

    return {
        "success":         True,
        "status":          doc.status,
        "current_phase":   doc.current_phase,
        "current_doctype": doc.current_doctype,
        "migrated":        doc.migrated or 0,
        "failed":          doc.failed or 0,
        "total_records":   doc.total_records or 0,
        "started_at":      str(doc.started_at or ""),
        "completed_at":    str(doc.completed_at or ""),
        "per_doctype":     per_doctype,
    }


@frappe.whitelist()
def get_failures(job, limit=200):
    """Return Migration Log entries for a job."""
    logs = frappe.get_all(
        "Migration Log",
        filters={"job": job},
        fields=["doctype_name", "v14_name", "error", "auto_fix_applied", "skipped"],
        limit=int(limit),
        order_by="name asc",
    )
    return {"success": True, "logs": logs}


@frappe.whitelist()
def abort_migration(job):
    """Abort a running migration."""
    if not frappe.db.exists("Migration Job", job):
        return {"success": False, "error": "Job not found"}
    frappe.db.set_value("Migration Job", job, "status", "Aborted")
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def generate_schema_map():
    """
    AI Option A — analyse v14 vs v16 schemas for every DocType in the migration plan.
    Stores results in Redis cache so apply_schema_map() picks them up automatically.
    Returns a summary of what the AI found.
    """
    from .migrator.connection import get_v14_conn, table_exists
    from .migrator.ai_helper import ai_analyze_schema, clear_ai_schema_cache
    from .migrator.dependency_order import ALL_DOCTYPES

    try:
        conn = get_v14_conn()
    except Exception as e:
        return {"success": False, "error": f"Cannot connect to v14: {e}"}

    clear_ai_schema_cache()

    summary = []
    errors = []

    for doctype in ALL_DOCTYPES:
        if not table_exists(conn, doctype):
            continue
        try:
            result = ai_analyze_schema(conn, doctype)
            renames = result.get("renames", {})
            dropped = result.get("dropped", [])
            defaults = result.get("required_defaults", {})
            if renames or dropped or defaults:
                summary.append({
                    "doctype": doctype,
                    "renames": renames,
                    "dropped": dropped,
                    "new_defaults": list(defaults.keys()),
                })
        except Exception as e:
            errors.append({"doctype": doctype, "error": str(e)})

    conn.close()
    return {
        "success": True,
        "analysed": len(summary) + len(errors),
        "with_changes": len(summary),
        "changes": summary,
        "errors": errors,
    }


@frappe.whitelist()
def save_config(v14_host, v14_port, v14_db_user, v14_db_password, v14_database):
    """Save v14 connection details to Migration Config."""
    cfg = frappe.get_single("Migration Config")
    cfg.v14_host     = v14_host
    cfg.v14_port     = int(v14_port or 3306)
    cfg.v14_db_user  = v14_db_user
    cfg.v14_database = v14_database
    if v14_db_password:
        cfg.v14_db_password = v14_db_password
    cfg.save(ignore_permissions=True)
    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def load_config():
    """Load saved Migration Config for the form."""
    cfg = frappe.get_single("Migration Config")
    return {
        "v14_host":          cfg.v14_host or "",
        "v14_port":          cfg.v14_port or 3306,
        "v14_db_user":       cfg.v14_db_user or "",
        "v14_database":      cfg.v14_database or "",
        "connection_status": cfg.connection_status or "",
    }
