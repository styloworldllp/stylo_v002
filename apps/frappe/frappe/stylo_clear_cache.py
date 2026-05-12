import frappe

def run():
    # Clear desktop icons cache
    from frappe.desk.doctype.desktop_icon.desktop_icon import clear_desktop_icons_cache
    clear_desktop_icons_cache()
    print("Cleared desktop icons cache")

    # Clear bootinfo cache for all users
    frappe.cache.delete_value("bootinfo")
    print("Cleared bootinfo cache")

    # Clear all user-specific boot caches
    for user in frappe.db.sql("SELECT name FROM `tabUser` WHERE enabled=1", pluck="name"):
        frappe.cache.hdel("bootinfo", user)
        frappe.cache.hdel("desktop_icons", user)
    print("Cleared per-user bootinfo and desktop_icons caches")

    frappe.db.commit()
    print("\nDone.")
