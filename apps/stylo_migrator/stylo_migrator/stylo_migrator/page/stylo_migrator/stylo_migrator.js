frappe.pages["stylo-migrator"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title:  "v14 → v16 Migrator",
		single_column: true,
	});

	// Mount the dashboard div
	$(page.body).html('<div id="stylo-migrator-root"></div>');

	// Init the dashboard logic (defined in public/js/migrator.js)
	stylo_migrator.init();
};
