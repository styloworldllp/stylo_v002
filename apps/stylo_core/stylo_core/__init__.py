__version__ = "2.0.2"


def _patch_server_script_sandbox():
    """Expose `stylo` as an alias for `frappe` inside server script / safe_exec contexts.

    Server scripts run inside a RestrictedPython sandbox built by
    frappe.utils.safe_exec.get_safe_globals(). By wrapping that function we
    inject `stylo = frappe` into every execution, so script authors can use
    either namespace interchangeably.
    """
    try:
        import frappe.utils.safe_exec as _se

        _orig_get_safe_globals = _se.get_safe_globals

        def _patched_get_safe_globals():
            g = _orig_get_safe_globals()
            g["stylo"] = g.get("frappe")
            return g

        _se.get_safe_globals = _patched_get_safe_globals
    except Exception:
        pass


_patch_server_script_sandbox()
