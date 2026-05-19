"""
Main migration engine.
Called by api.py via frappe.enqueue so it runs in a background worker.
"""
import frappe

from .connection import get_v14_conn, count_records, table_exists, read_batch
from .schema_map import apply_schema_map
from .fixup import apply_fixup
from .submitted_docs import insert_record, record_exists
from .dependency_order import PHASES
from .migrate_hr import apply_hr_patch, should_skip as hr_should_skip
from .migrate_custom import run_custom_phase


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_job_aborted(job_name: str) -> bool:
    return frappe.db.get_value("Migration Job", job_name, "status") == "Aborted"


def _update_job(job_name: str, **kwargs):
    frappe.db.set_value("Migration Job", job_name, kwargs)
    frappe.db.commit()


def _log_failure(job_name: str, doctype: str, v14_name, error: str, fix_note: str = ""):
    frappe.get_doc({
        "doctype":         "Migration Log",
        "job":             job_name,
        "doctype_name":    doctype,
        "v14_name":        str(v14_name or ""),
        "error":           str(error)[:500],
        "auto_fix_applied": fix_note[:500],
    }).insert(ignore_permissions=True)
    frappe.db.commit()


_PROGRESS_CACHE_KEY = "migration_progress"


def _publish(job_name: str, phase: str, doctype: str, count: int):
    payload = {"job": job_name, "phase": phase, "doctype": doctype, "count": count}

    # Store per-doctype progress in Redis so polling can read it without realtime
    try:
        import json
        frappe.cache().hset(_PROGRESS_CACHE_KEY, f"{job_name}:{doctype}", json.dumps(payload))
    except Exception:
        pass

    # Broadcast to all site users — subprocess has no frappe.session.user
    try:
        frappe.publish_realtime("migration_progress", payload)
    except Exception:
        pass


# ── Per-doctype migration ─────────────────────────────────────────────────────

def migrate_doctype(conn, doctype: str, job_name: str, phase_name: str) -> tuple[int, int]:
    """
    Migrate all records for one DocType from v14 → v16.
    Returns (migrated_count, failed_count).
    """
    if not table_exists(conn, doctype):
        return 0, 0

    # HR/Payroll check
    skip, reason = hr_should_skip(doctype)
    if skip:
        _log_failure(job_name, doctype, "__phase__", reason)
        return 0, 0

    migrated = failed = 0
    offset = 0
    batch_size = 200

    while True:
        if _is_job_aborted(job_name):
            break

        rows = read_batch(conn, doctype, offset, batch_size)
        if not rows:
            break

        for row in rows:
            v14_name = row.get("name")
            try:
                # Skip duplicates
                if v14_name and record_exists(doctype, v14_name):
                    migrated += 1
                    continue

                # 1. Rename / drop fields per schema map (includes AI overrides)
                mapped = apply_schema_map(doctype, row)

                # 2. HR-specific patches
                mapped = apply_hr_patch(doctype, mapped)

                # 3. Auto-fix missing required fields / broken links
                fixed, fix_notes = apply_fixup(doctype, mapped)

                # 4. Insert into v16; on failure ask AI to patch the record
                try:
                    insert_record(doctype, fixed)
                except Exception as insert_err:
                    try:
                        from .ai_helper import ai_fix_record
                        ai_fixed, ai_note = ai_fix_record(doctype, fixed, str(insert_err))
                        if ai_note:
                            insert_record(doctype, ai_fixed)
                            fix_notes.append(f"AI fix: {ai_note}")
                        else:
                            raise insert_err
                    except Exception:
                        raise insert_err

                migrated += 1

                if fix_notes:
                    _log_failure(job_name, doctype, v14_name, "", "; ".join(fix_notes))

            except Exception as e:
                failed += 1
                _log_failure(job_name, doctype, v14_name, str(e))

        offset += len(rows)
        _publish(job_name, phase_name, doctype, migrated)

        # Update job counters
        frappe.db.sql(
            "UPDATE `tabMigration Job` SET migrated = migrated + %s, failed = failed + %s WHERE name = %s",
            (len(rows), failed - max(failed - len(rows), 0), job_name),
        )
        frappe.db.commit()

    return migrated, failed


# ── Full run ──────────────────────────────────────────────────────────────────

def run_all(job_name: str):
    """
    Entry point for the background job.
    Iterates all phases and doctypes, then runs custom phase.
    """
    _update_job(job_name, status="Running", started_at=frappe.utils.now())
    conn = get_v14_conn()

    total_migrated = total_failed = 0

    try:
        for phase in PHASES:
            phase_name = phase["name"]
            requires_app = phase.get("requires_app")

            if requires_app and requires_app not in frappe.get_installed_apps():
                _log_failure(job_name, phase_name, "__phase__",
                             f"Skipped — '{requires_app}' app not installed")
                continue

            for doctype in phase["doctypes"]:
                if _is_job_aborted(job_name):
                    break

                _update_job(job_name, current_phase=phase_name, current_doctype=doctype)
                _publish(job_name, phase_name, doctype, 0)

                m, f = migrate_doctype(conn, doctype, job_name, phase_name)
                total_migrated += m
                total_failed += f

            if _is_job_aborted(job_name):
                break

        # Phase 9 — Custom DocTypes
        if not _is_job_aborted(job_name):
            _update_job(job_name, current_phase="Phase 9 — Custom DocTypes", current_doctype="")
            cm, cf = run_custom_phase(conn, job_name, _log_failure, _publish)
            total_migrated += cm
            total_failed += cf

    except Exception as e:
        _update_job(job_name, status="Failed",
                    completed_at=frappe.utils.now(),
                    current_phase=f"Error: {e}")
        raise
    finally:
        conn.close()

    final_status = "Aborted" if _is_job_aborted(job_name) else "Completed"
    _update_job(
        job_name,
        status=final_status,
        completed_at=frappe.utils.now(),
        current_phase="Done",
        current_doctype="",
    )
    _publish(job_name, "Done", "", total_migrated)


# ── Preview counts ────────────────────────────────────────────────────────────

def get_preview_counts() -> list[dict]:
    """
    Return per-phase record counts from v14.
    Also adds a final phase for any v14 tables not covered by the predefined list.
    """
    from .dependency_order import ALL_DOCTYPES
    conn = get_v14_conn()
    result = []
    covered = set(ALL_DOCTYPES)

    for phase in PHASES:
        phase_counts = []
        for doctype in phase["doctypes"]:
            if not table_exists(conn, doctype):
                continue  # skip doctypes not in this v14 instance
            cnt = count_records(conn, doctype)
            phase_counts.append({"doctype": doctype, "count": cnt})
        if phase_counts:
            result.append({"phase": phase["name"], "doctypes": phase_counts})

    # Discover any extra tables in v14 not in our predefined list
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        all_tables = [list(r.values())[0] for r in cur.fetchall()]

    extra = []
    for tbl in sorted(all_tables):
        if not tbl.startswith("tab"):
            continue
        dt = tbl[3:]  # strip "tab" prefix
        if dt in covered:
            continue
        cnt = count_records(conn, dt)
        if cnt > 0:
            extra.append({"doctype": dt, "count": cnt})

    if extra:
        result.append({"phase": "Phase ∞ — Other / Custom Tables", "doctypes": extra})

    conn.close()
    return result
