frappe.pages["stylo-marketplace"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Stylo App Store"),
		single_column: true,
	});

	new StyloMarketplace(wrapper);
};

const CATALOG = [
	{
		key: "stylo_bms",
		title: "StyloBMS",
		tagline: "Complete ERP for growing businesses",
		description: "Full accounting, inventory, procurement, manufacturing, HR and compliance in one powerful platform.",
		icon: "/assets/stylo_core/images/workspace_icons/erp-core.png",
		color: "#0FBF7F",
		category: "Finance",
		apps: ["erpnext"],
		features: ["Accounting", "Inventory", "Manufacturing", "GST Compliance", "Procurement", "Projects"],
		highlight: true,
	},
	{
		key: "stylo_hr",
		title: "StyloHR",
		tagline: "HR & Payroll made simple",
		description: "Complete HR management — leave, attendance, payroll, appraisals, recruitment and more.",
		icon: "/assets/stylo_core/images/workspace_icons/hrms.png",
		color: "#3B82F6",
		category: "HR",
		apps: ["hrms"],
		features: ["Leave Management", "Payroll", "Attendance", "Appraisals", "Recruitment"],
	},
	{
		key: "stylo_crm",
		title: "StyloCRM",
		tagline: "Close deals faster",
		description: "Pipeline management, lead tracking, email integration and deal analytics in one clean interface.",
		icon: "/assets/stylo_core/images/workspace_icons/crm.png",
		color: "#8B5CF6",
		category: "CRM",
		apps: ["crm"],
		features: ["Pipeline", "Leads", "Email Integration", "Reports", "Territories"],
	},
	{
		key: "stylo_lms",
		title: "StyloLMS",
		tagline: "Train your team, delight your clients",
		description: "Build courses, assessments and certifications for employee onboarding and client training.",
		icon: "/assets/stylo_core/images/workspace_icons/documents.png",
		color: "#F59E0B",
		category: "Learning",
		apps: ["lms"],
		features: ["Courses", "Assessments", "Certifications", "Batches", "Progress Tracking"],
	},
	{
		key: "stylo_helpdesk",
		title: "StyloDesk",
		tagline: "Customer support that scales",
		description: "Ticketing system with SLA management, knowledge base, email integration and analytics.",
		icon: "/assets/stylo_core/images/workspace_icons/support.png",
		color: "#EF4444",
		category: "Productivity",
		apps: ["helpdesk"],
		features: ["Ticketing", "SLA Management", "Knowledge Base", "Email Integration", "Analytics"],
	},
	{
		key: "stylo_brain",
		title: "brAIn",
		tagline: "AI assistant for your business",
		description: "Conversational AI that understands your business data — create records, run reports, get insights by chat.",
		icon: "/assets/stylo_core/images/workspace_icons/ai-assistant.png",
		color: "#06B6D4",
		category: "AI",
		apps: ["brain"],
		features: ["Natural Language Queries", "Record Creation", "Dashboard Builder", "Data Insights"],
		highlight: true,
	},
	{
		key: "stylo_insights",
		title: "Stylo Insights",
		tagline: "BI dashboards in minutes",
		description: "Drag-and-drop analytics and dashboards. Connect your data, build charts, share with your team.",
		icon: "/assets/stylo_core/images/workspace_icons/reports.png",
		color: "#10B981",
		category: "AI",
		apps: ["insights"],
		features: ["Dashboards", "Charts", "Data Sources", "Workbooks", "Sharing"],
	},
	{
		key: "stylo_gameplan",
		title: "Gameplan",
		tagline: "Project collaboration for teams",
		description: "Projects, tasks, discussions and docs — everything your team needs to ship work together.",
		icon: "/assets/stylo_core/images/workspace_icons/projects.png",
		color: "#F97316",
		category: "Productivity",
		apps: ["gameplan"],
		features: ["Projects", "Tasks", "Team Discussions", "Docs", "Pages"],
	},
	{
		key: "stylo_telephony",
		title: "Telephony",
		tagline: "Calls integrated with your desk",
		description: "Click-to-call, call logs, auto-linking to customers and leads, call recordings.",
		icon: "/assets/stylo_core/images/workspace_icons/integration.png",
		color: "#6366F1",
		category: "Productivity",
		apps: ["telephony"],
		features: ["Click-to-Call", "Call Logs", "Customer Linking", "Recordings"],
	},
];

const CATEGORIES = ["All", "Finance", "HR", "CRM", "Learning", "AI", "Productivity"];

class StyloMarketplace {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.requested = JSON.parse(localStorage.getItem("stylo_requested") || "{}");
		// frappe.boot.versions = {frappe: "2.1.3", erpnext: "2.0.7", ...}
		this.installed_apps = Object.keys(frappe.boot.versions || {});
		this.active_category = "All";
		this.search_term = "";
		this.render();
	}

	render() {
		this.page.set_secondary_action(__("Request a custom module"), () => {
			this.show_request_modal(null);
		});

		$(this.wrapper).find(".page-content").html(`
			<div class="sms-container">
				<div class="sms-header">
					<div class="sms-headline">
						<h2>${__("Discover the full Stylo platform")}</h2>
						<p>${__("See an app you want? Request it — our team will reach out, understand your needs and set it up.")}</p>
					</div>
					<div class="sms-search-wrap">
						<input id="sms-search" class="sms-search" type="text" placeholder="${__("Search apps...")}"/>
					</div>
				</div>

				<div class="sms-categories">
					${CATEGORIES.map(c => `
						<button class="sms-cat-btn${c === "All" ? " active" : ""}" data-cat="${c}">${__(c)}</button>
					`).join("")}
				</div>

				<div id="sms-grid" class="sms-grid"></div>
			</div>
		`);

		this.bind_events();
		this.render_cards();
	}

	bind_events() {
		const self = this;

		$(this.wrapper).find(".sms-cat-btn").on("click", function () {
			$(self.wrapper).find(".sms-cat-btn").removeClass("active");
			$(this).addClass("active");
			self.active_category = $(this).data("cat");
			self.render_cards();
		});

		$(this.wrapper).find("#sms-search").on("input", function () {
			self.search_term = $(this).val().toLowerCase();
			self.render_cards();
		});
	}

	get_filtered_catalog() {
		return CATALOG.filter(app => {
			const cat_match = this.active_category === "All" || app.category === this.active_category;
			const search_match = !this.search_term ||
				app.title.toLowerCase().includes(this.search_term) ||
				app.tagline.toLowerCase().includes(this.search_term) ||
				(app.features || []).some(f => f.toLowerCase().includes(this.search_term));
			return cat_match && search_match;
		});
	}

	is_installed(app) {
		return app.apps.some(a => this.installed_apps.includes(a));
	}

	render_cards() {
		const apps = this.get_filtered_catalog();
		const grid = $(this.wrapper).find("#sms-grid");

		if (!apps.length) {
			grid.html(`<div class="sms-empty">${__("No apps match your search.")}</div>`);
			return;
		}

		grid.html(apps.map(app => this.card_html(app)).join(""));

		const self = this;
		grid.find(".sms-request-btn").on("click", function () {
			self.show_request_modal($(this).data("key"));
		});
	}

	card_html(app) {
		const installed = this.is_installed(app);
		const requested = this.requested[app.key];

		let action_btn = "";
		if (installed) {
			action_btn = `<div class="sms-installed-badge">✓ ${__("Active")}</div>`;
		} else if (requested) {
			action_btn = `<button class="sms-request-btn sms-requested" disabled>${__("✓ Requested")}</button>`;
		} else {
			action_btn = `<button class="sms-request-btn" data-key="${app.key}">${__("Request Installation")}</button>`;
		}

		return `
		<div class="sms-card${app.highlight ? " sms-featured" : ""}${installed ? " sms-active" : ""}">
			${app.highlight ? `<div class="sms-featured-tag">${__("Featured")}</div>` : ""}
			${installed ? `<div class="sms-active-bar" style="background:${app.color}"></div>` : ""}
			<div class="sms-card-top">
				<div class="sms-icon" style="background:${app.color}22">
					<img src="${app.icon}" onerror="this.style.display='none'" />
					<div class="sms-icon-fallback" style="background:${app.color}">${app.title[0]}</div>
				</div>
				<div class="sms-card-info">
					<div class="sms-card-title">${app.title}</div>
					<div class="sms-card-tagline">${__(app.tagline)}</div>
				</div>
			</div>
			<p class="sms-card-desc">${__(app.description)}</p>
			<div class="sms-features">
				${(app.features || []).map(f => `<span class="sms-feature">${__(f)}</span>`).join("")}
			</div>
			<div class="sms-card-footer">
				${action_btn}
			</div>
		</div>`;
	}

	show_request_modal(app_key) {
		const app = app_key ? CATALOG.find(a => a.key === app_key) : null;
		const title = app ? `${__("Request")} ${app.title}` : __("Request a custom module");

		const d = new frappe.ui.Dialog({
			title: title,
			fields: [
				{
					fieldname: "message",
					fieldtype: "Small Text",
					label: __("Tell us what you need (optional)"),
					description: __("Our team will contact you within 24 hours to discuss implementation."),
				},
			],
			primary_action_label: __("Send Request"),
			primary_action: (values) => {
				frappe.call({
					method: "stylo_core.marketplace.request_app",
					args: {
						product_key: app_key || "custom",
						product_title: app ? app.title : "Custom Module",
						message: values.message || "",
					},
					callback: () => {
						d.hide();
						if (app_key) {
							this.requested[app_key] = true;
							localStorage.setItem("stylo_requested", JSON.stringify(this.requested));
						}
						frappe.show_alert({
							message: __("Request sent! Our team will contact you within 24 hours."),
							indicator: "green",
						}, 5);
						this.render_cards();
					},
				});
			},
		});

		d.show();
	}
}
