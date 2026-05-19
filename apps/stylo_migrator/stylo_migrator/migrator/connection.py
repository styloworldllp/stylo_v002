"""
PyMySQL connection to the v14 MariaDB instance.
All reads are via this module — we never write to v14.
"""
import pymysql
import frappe


def get_v14_conn():
    cfg = frappe.get_single("Migration Config")
    return pymysql.connect(
        host=cfg.v14_host,
        port=int(cfg.v14_port or 3306),
        user=cfg.v14_db_user,
        password=cfg.get_password("v14_db_password"),
        database=cfg.v14_database,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        charset="utf8mb4",
    )


def test_connection():
    """Return (success: bool, message: str, table_count: int)."""
    try:
        conn = get_v14_conn()
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = cur.fetchall()
        conn.close()
        doc_tables = [list(t.values())[0] for t in tables if list(t.values())[0].startswith("tab")]
        return True, f"Connected ✓ — {len(doc_tables)} DocType tables found", len(doc_tables)
    except Exception as e:
        return False, str(e), 0


def read_batch(conn, doctype, offset=0, limit=500):
    """Fetch one page of raw rows from a v14 DocType table."""
    table = f"tab{doctype}"
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM `{table}` LIMIT %s OFFSET %s", (limit, offset))
        return cur.fetchall()


def count_records(conn, doctype):
    """Return total row count for a DocType in v14."""
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) as cnt FROM `tab{doctype}`")
            return (cur.fetchone() or {}).get("cnt", 0)
    except Exception:
        return 0


def table_exists(conn, doctype):
    """Check whether a table exists in v14."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) as cnt FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            (f"tab{doctype}",),
        )
        return bool((cur.fetchone() or {}).get("cnt", 0))


def get_child_batch(conn, child_doctype, parent_name, offset=0, limit=500):
    """Fetch child table rows for a given parent document."""
    table = f"tab{child_doctype}"
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT * FROM `{table}` WHERE parent = %s LIMIT %s OFFSET %s",
            (parent_name, limit, offset),
        )
        return cur.fetchall()


def list_custom_doctypes(conn):
    """Return names of custom (non-standard) DocTypes defined in v14."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT name FROM `tabDocType` WHERE custom = 1 AND issingle = 0 AND istable = 0"
            )
            return [r["name"] for r in cur.fetchall()]
    except Exception:
        return []


def get_doctype_fields_from_v14(conn, doctype):
    """Return field definitions for a custom doctype from v14."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fieldname, label, fieldtype, options, reqd, `default`, hidden "
            "FROM `tabDocField` WHERE parent = %s ORDER BY idx",
            (doctype,),
        )
        return cur.fetchall()
