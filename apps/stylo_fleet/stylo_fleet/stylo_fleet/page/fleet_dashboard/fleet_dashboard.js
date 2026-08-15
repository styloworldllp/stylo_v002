frappe.pages['fleet-dashboard'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Fleet Analytics',
		single_column: true,
	});

	new FleetDashboardPage(wrapper);
};

class FleetDashboardPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		fleet_inject_styles();
		this.tooltip = new FleetTooltip();
		this.setup_toolbar();
		this.render_skeleton();
		this.load();
	}

	setup_toolbar() {
		this.page.add_inner_button(__('Refresh'), () => this.load());
	}

	render_skeleton() {
		this.$body = $('<div class="fleet-dash">').appendTo($(this.wrapper).find('.layout-main-section'));

		this.$body.append(`
			<div class="fd-header">
				<div>
					<h1>${__('Fleet Analytics')}</h1>
					<div class="fd-sub">${__('Live operational overview — nhs.stylo.io')}</div>
				</div>
				<div class="fd-refreshed"></div>
			</div>
		`);
		this.$refreshed = this.$body.find('.fd-refreshed');

		this.$kpis = $('<div class="fd-kpi-grid">').appendTo(this.$body);
		this.$row1 = $('<div class="fd-grid-2">').appendTo(this.$body);
		this.$status_card = $('<div class="fd-card"><h3>' + __('Fleet Status') + '</h3></div>').appendTo(this.$row1);
		this.$kit_card = $('<div class="fd-card"><h3>' + __('Kit Readiness') + '</h3></div>').appendTo(this.$row1);

		this.$row2 = $('<div class="fd-grid-2">').appendTo(this.$body);
		this.$station_card = $('<div class="fd-card"><h3>' + __('Fleet by Station') + '</h3></div>').appendTo(this.$row2);
		this.$activity_card = $('<div class="fd-card"><h3>' + __("Today's Activity") + '</h3></div>').appendTo(this.$row2);

		this.$row3 = $('<div class="fd-grid-2">').appendTo(this.$body);
		this.$attention_card = $('<div class="fd-card"><h3>' + __('Needs Attention') + '</h3></div>').appendTo(this.$row3);
		this.$feed_card = $('<div class="fd-card"><h3>' + __('Recent Activity') + '</h3></div>').appendTo(this.$row3);
	}

	async load() {
		try {
			const r = await frappe.call('stylo_fleet.api.analytics.get_dashboard_data');
			this.data = r.message;
			this.render();
			this.$refreshed.text(__('Updated {0}', [frappe.datetime.now_time()]));
		} catch (e) {
			frappe.msgprint({ message: e.message || 'Failed to load dashboard data', indicator: 'red' });
		}
	}

	render() {
		const k = this.data.kpis;
		fleet_render_kpis(this.$kpis, [
			{ label: __('Total Ambulances'), value: k.total_active, accent: 'var(--brand)' },
			{ label: __('Available Now'), value: k.available_now, accent: 'var(--status-good)' },
			{ label: __('On Call'), value: k.on_call, accent: 'var(--cat-1)' },
			{ label: __('Refill Due'), value: k.refill_due_or_insufficient, accent: 'var(--status-warning)' },
			{ label: __('Maintenance Issues'), value: k.maintenance_or_breakdown, accent: 'var(--status-critical)' },
			{ label: __('Open Issues'), value: k.open_issues, accent: 'var(--status-serious)' },
			{ label: __('Shifts Today'), value: k.shifts_today, accent: 'var(--cat-3)' },
			{ label: __('Kits Consumed Today'), value: k.kits_consumed_today, accent: 'var(--cat-5)' },
		]);

		const status_entries = Object.entries(this.data.status_breakdown).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
		fleet_render_bar_chart(this.$status_card, status_entries, (l) => fleet_status_color(FLEET_OPERATIONAL_STATUS_GROUP[l] || 'muted'), __('No active ambulances yet.'), this.tooltip);

		const kit_entries = Object.entries(this.data.kit_breakdown).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
		fleet_render_bar_chart(this.$kit_card, kit_entries, (l) => fleet_status_color(FLEET_KIT_STATUS_GROUP[l] || 'muted'), __('No kit data yet.'), this.tooltip);

		const station_entries = Object.entries(this.data.station_breakdown).map(([label, value]) => ({ label, value }));
		const station_colors = fleet_categorical_color_map(station_entries.map((e) => e.label));
		station_entries.sort((a, b) => b.value - a.value);
		fleet_render_bar_chart(this.$station_card, station_entries, (l) => station_colors[l], __('No stations yet.'), this.tooltip);

		const activity_entries = Object.entries(this.data.activity_today_breakdown).map(([label, value]) => ({ label, value }));
		const activity_colors = fleet_categorical_color_map(activity_entries.map((e) => e.label));
		activity_entries.sort((a, b) => b.value - a.value);
		fleet_render_bar_chart(this.$activity_card, activity_entries, (l) => activity_colors[l], __('No activity recorded today yet.'), this.tooltip);

		this.render_attention();
		fleet_render_feed(this.$feed_card, this.data.recent_activity || [], __('No activity yet.'));
	}

	render_attention() {
		this.$attention_card.find('.fd-list-item, .fd-empty').remove();
		const issues = this.data.open_issues || [];
		const refills = this.data.pending_refills || [];

		if (!issues.length && !refills.length) {
			this.$attention_card.append(`<div class="fd-empty">${__('Nothing needs attention right now.')}</div>`);
			return;
		}

		issues.forEach((i) => {
			const color = i.issue_type === 'Mechanical' ? 'var(--status-critical)' : 'var(--status-warning)';
			this.$attention_card.append(`
				<div class="fd-list-item">
					<div>
						<div class="fd-li-main">${frappe.utils.escape_html(i.ambulance)} — ${frappe.utils.escape_html(i.issue_type)} Issue</div>
						<div class="fd-li-sub">${frappe.utils.escape_html(i.description || i.severity || '')}</div>
					</div>
					<span class="fd-status-badge" style="background:${color}1a;color:${color}">
						<span class="fd-dot" style="background:${color}"></span>${frappe.utils.escape_html(i.severity || i.issue_type)}
					</span>
				</div>
			`);
		});

		refills.forEach((r) => {
			this.$attention_card.append(`
				<div class="fd-list-item">
					<div>
						<div class="fd-li-main">${frappe.utils.escape_html(r.ambulance)} — ${__('Refill Pending')}</div>
						<div class="fd-li-sub">${__('Needs')} ${r.expected_load_quantity} ${__('kits')} — ${frappe.utils.escape_html(r.station || '')}</div>
					</div>
					<span class="fd-status-badge" style="background:var(--status-warning)1a;color:var(--status-warning)">
						<span class="fd-dot" style="background:var(--status-warning)"></span>${__('Refill')}
					</span>
				</div>
			`);
		});
	}
}
