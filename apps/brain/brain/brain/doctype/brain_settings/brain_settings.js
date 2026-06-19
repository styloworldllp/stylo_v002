frappe.ui.form.on("Brain Settings", {
	refresh(frm) {
		_toggle_local_fields(frm);
	},

	provider(frm) {
		_toggle_local_fields(frm);
		// Default to Falcon engine when switching to Nuerix
		if ((frm.doc.provider || "").includes("Neurix") && !frm.doc.nuerix_engine) {
			frm.set_value("nuerix_engine", "Falcon");
		}
	},

	build_context_btn(frm) {
		frappe.show_alert({ message: "Building context… this may take 20–30 seconds.", indicator: "blue" });
		frappe.call({
			method: "brain.api.context.rebuild",
			callback(r) {
				if (r.message && r.message.ok) {
					frappe.show_alert({ message: "✓ Context built successfully!", indicator: "green" });
					frm.reload_doc();
				} else {
					frappe.show_alert({ message: "Context build failed — check error log.", indicator: "red" });
				}
			},
			error() {
				frappe.show_alert({ message: "Context build failed — check error log.", indicator: "red" });
			},
		});
	},
});

function _toggle_local_fields(frm) {
	const provider = frm.doc.provider || "";
	const is_local = provider.includes("Neurix") || provider.includes("Ollama");
	const is_compat = provider === "OpenAI Compatible";

	frm.toggle_display("nuerix_engine", is_local);
	frm.toggle_display("model", !is_local);
	frm.toggle_display("api_key", !is_local);
	frm.toggle_display("base_url", is_compat);

	if (is_local) {
		frm.set_df_property("api_key", "reqd", 0);
		if (frm.doc.nuerix_engine) {
			// Show a friendly label for what the engine maps to
			const ENGINE_LABELS = {
				"Falcon":     "qwen2.5:1.5b — fastest, ideal for quick queries",
				"Falcon Pro": "qwen2.5:3b — balanced speed and accuracy",
				"Kiwi":       "qwen2.5:7b — high accuracy, complex analysis",
				"Kiwi Pro":   "qwen2.5:14b — advanced reasoning",
				"Swift":      "llama3.2:1b — lightning fast lookups",
				"Swift Pro":  "llama3.2:3b — fast and capable",
				"Storm":      "mistral:7b — powerful general reasoning",
				"Atlas":      "llama3.1:8b — advanced analytics",
				"Mint":       "phi3.5:mini — compact and smart",
			};
			const hint = ENGINE_LABELS[frm.doc.nuerix_engine] || "";
			if (hint) {
				frm.set_df_property("nuerix_engine", "description", hint);
			}
		}
	}
}
