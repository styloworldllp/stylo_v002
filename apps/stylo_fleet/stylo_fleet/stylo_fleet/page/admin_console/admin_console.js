frappe.pages['admin-console'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Admin',
		single_column: true,
	});

	new AdminConsolePage(wrapper);
};

const ADMIN_DEMO_PASSWORD = 'Stylo@Demo123';

class AdminConsolePage {
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
					<h1>${__('Admin')}</h1>
					<div class="fd-sub">${__('Full fleet analytics and management — nhs.stylo.io')}</div>
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

		// ---- Manage section ----
		this.$body.append(`<div class="fd-section-title">${__('Manage Fleet')}</div>`);
		this.$manage_row = $('<div class="fd-grid-2">').appendTo(this.$body);
		this.$ambulances_card = $(`
			<div class="fd-card"><h3>${__('Ambulances')} <button class="fd-btn fd-btn-brand" id="add-ambulance-btn">+ ${__('Add')}</button></h3></div>
		`).appendTo(this.$manage_row);
		this.$stations_card = $(`
			<div class="fd-card"><h3>${__('Stations')} <button class="fd-btn fd-btn-brand" id="add-station-btn">+ ${__('Add')}</button></h3></div>
		`).appendTo(this.$manage_row);

		this.$body.append(`<div class="fd-section-title">${__('Manage People')}</div>`);
		this.$people_row = $('<div class="fd-grid-2">').appendTo(this.$body);
		this.$paramedics_card = $(`
			<div class="fd-card"><h3>${__('Paramedics')} <button class="fd-btn fd-btn-brand" id="add-paramedic-btn">+ ${__('Add')}</button></h3></div>
		`).appendTo(this.$people_row);
		this.$station_ops_card = $(`
			<div class="fd-card"><h3>${__('Station Operators')} <button class="fd-btn fd-btn-brand" id="add-station-op-btn">+ ${__('Add')}</button></h3></div>
		`).appendTo(this.$people_row);

		this.$ops_row = $('<div class="fd-grid-2">').appendTo(this.$body);
		this.$ops_card = $(`
			<div class="fd-card"><h3>${__('Operations Users')} <button class="fd-btn fd-btn-brand" id="add-ops-btn">+ ${__('Add')}</button></h3></div>
		`).appendTo(this.$ops_row);

		this.$body.find('#add-ambulance-btn').on('click', () => this.show_add_ambulance_dialog());
		this.$body.find('#add-station-btn').on('click', () => this.show_add_station_dialog());
		this.$body.find('#add-paramedic-btn').on('click', () => this.show_add_paramedic_dialog());
		this.$body.find('#add-station-op-btn').on('click', () => this.show_add_station_operator_dialog());
		this.$body.find('#add-ops-btn').on('click', () => this.show_add_ops_dialog());
	}

	async load() {
		try {
			const [dash, people, options] = await Promise.all([
				frappe.call('stylo_fleet.api.analytics.get_dashboard_data'),
				frappe.call('stylo_fleet.api.admin.get_people'),
				frappe.call('stylo_fleet.api.admin.get_master_options'),
			]);
			this.data = dash.message;
			this.people = people.message;
			this.options = options.message;
			this.render();
			this.$refreshed.text(__('Updated {0}', [frappe.datetime.now_time()]));
		} catch (e) {
			frappe.msgprint({ message: e.message || 'Failed to load admin console', indicator: 'red' });
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

		this.render_ambulances_table();
		this.render_stations_table();
		this.render_people_table(this.$paramedics_card, this.people.paramedics, ['paramedic_name', 'base_station'], [__('Name'), __('Station')]);
		this.render_people_table(this.$station_ops_card, this.people.station_operators, ['operator_name', 'station'], [__('Name'), __('Station')]);
		this.render_ops_table();
	}

	render_ambulances_table() {
		this.$ambulances_card.find('.fd-empty').remove();
		this.$ambulances_card.append(`<div class="fd-empty">${this.data.kpis.total_active} ${__('active ambulances')} — ${__('see Stylo Fleet workspace for full list')}</div>`);
	}

	render_stations_table() {
		this.$stations_card.find('.fd-empty').remove();
		const count = (this.options.stations || []).length;
		this.$stations_card.append(`<div class="fd-empty">${count} ${__('stations')}: ${(this.options.stations || []).map(frappe.utils.escape_html).join(', ')}</div>`);
	}

	render_people_table($card, rows, fields, headers) {
		$card.find('table').remove();
		if (!rows.length) {
			if (!$card.find('.fd-empty').length) $card.append(`<div class="fd-empty">${__('None yet.')}</div>`);
			return;
		}
		$card.find('.fd-empty').remove();
		const $table = $(`
			<table class="fd-table">
				<thead><tr>${headers.map((h) => `<th>${h}</th>`).join('')}<th>${__('Status')}</th></tr></thead>
				<tbody></tbody>
			</table>
		`).appendTo($card);
		const $tbody = $table.find('tbody');
		rows.forEach((row) => {
			const active = row.active ? __('Active') : __('Inactive');
			const color = row.active ? 'var(--status-good)' : 'var(--text-muted)';
			$tbody.append(`
				<tr>
					${fields.map((f) => `<td>${frappe.utils.escape_html(row[f] || '')}</td>`).join('')}
					<td><span class="fd-status-badge" style="background:${color}1a;color:${color}"><span class="fd-dot" style="background:${color}"></span>${active}</span></td>
				</tr>
			`);
		});
	}

	render_ops_table() {
		this.$ops_card.find('table, .fd-empty').remove();
		const rows = this.people.operations;
		if (!rows.length) {
			this.$ops_card.append(`<div class="fd-empty">${__('None yet.')}</div>`);
			return;
		}
		const $table = $(`
			<table class="fd-table">
				<thead><tr><th>${__('Name')}</th><th>${__('Email')}</th><th>${__('Status')}</th></tr></thead>
				<tbody></tbody>
			</table>
		`).appendTo(this.$ops_card);
		const $tbody = $table.find('tbody');
		rows.forEach((row) => {
			const color = row.enabled ? 'var(--status-good)' : 'var(--text-muted)';
			$tbody.append(`
				<tr>
					<td>${frappe.utils.escape_html(row.full_name || '')}</td>
					<td>${frappe.utils.escape_html(row.user)}</td>
					<td><span class="fd-status-badge" style="background:${color}1a;color:${color}"><span class="fd-dot" style="background:${color}"></span>${row.enabled ? __('Active') : __('Disabled')}</span></td>
				</tr>
			`);
		});
	}

	// ---- Add dialogs ----
	show_add_ambulance_dialog() {
		const d = new frappe.ui.Dialog({
			title: __('Add Ambulance'),
			fields: [
				{ fieldname: 'ambulance_id', fieldtype: 'Data', label: __('Ambulance ID'), reqd: 1 },
				{ fieldname: 'vehicle_number', fieldtype: 'Data', label: __('Vehicle Number'), reqd: 1 },
				{ fieldname: 'vehicle_type', fieldtype: 'Data', label: __('Vehicle Type') },
				{ fieldname: 'base_station', fieldtype: 'Select', label: __('Base Station'), options: this.options.stations, reqd: 1 },
				{ fieldname: 'kit_capacity', fieldtype: 'Int', label: __('Kit Capacity'), default: 10, reqd: 1 },
				{ fieldname: 'minimum_operational_kits', fieldtype: 'Int', label: __('Minimum Operational Kits'), default: 3, reqd: 1 },
				{ fieldname: 'refill_threshold', fieldtype: 'Int', label: __('Refill Threshold'), default: 5, reqd: 1 },
			],
			primary_action_label: __('Create'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.admin.create_ambulance', values);
					frappe.show_alert({ message: __('Ambulance created'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to create ambulance', indicator: 'red' });
				}
			},
		});
		d.show();
	}

	show_add_station_dialog() {
		const d = new frappe.ui.Dialog({
			title: __('Add Station'),
			fields: [
				{ fieldname: 'station_name', fieldtype: 'Data', label: __('Station Name'), reqd: 1 },
				{ fieldname: 'station_type', fieldtype: 'Select', label: __('Station Type'), reqd: 1,
					options: ['Base', 'Refill', 'Cleaning', 'Service', 'Multi-purpose'] },
			],
			primary_action_label: __('Create'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.admin.create_station', values);
					frappe.show_alert({ message: __('Station created'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to create station', indicator: 'red' });
				}
			},
		});
		d.show();
	}

	show_add_paramedic_dialog() {
		const d = new frappe.ui.Dialog({
			title: __('Add Paramedic'),
			fields: [
				{ fieldname: 'full_name', fieldtype: 'Data', label: __('Full Name'), reqd: 1 },
				{ fieldname: 'email', fieldtype: 'Data', label: __('Email'), reqd: 1 },
				{ fieldname: 'base_station', fieldtype: 'Select', label: __('Base Station'), options: this.options.stations, reqd: 1 },
				{ fieldname: 'password', fieldtype: 'Data', label: __('Password'), default: ADMIN_DEMO_PASSWORD, reqd: 1 },
			],
			primary_action_label: __('Create'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.admin.create_paramedic', values);
					frappe.show_alert({ message: __('Paramedic created'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to create paramedic', indicator: 'red' });
				}
			},
		});
		d.show();
	}

	show_add_station_operator_dialog() {
		const d = new frappe.ui.Dialog({
			title: __('Add Station Operator'),
			fields: [
				{ fieldname: 'full_name', fieldtype: 'Data', label: __('Full Name'), reqd: 1 },
				{ fieldname: 'email', fieldtype: 'Data', label: __('Email'), reqd: 1 },
				{ fieldname: 'station', fieldtype: 'Select', label: __('Station'), options: this.options.stations, reqd: 1 },
				{ fieldname: 'password', fieldtype: 'Data', label: __('Password'), default: ADMIN_DEMO_PASSWORD, reqd: 1 },
			],
			primary_action_label: __('Create'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.admin.create_station_operator', values);
					frappe.show_alert({ message: __('Station Operator created'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to create station operator', indicator: 'red' });
				}
			},
		});
		d.show();
	}

	show_add_ops_dialog() {
		const d = new frappe.ui.Dialog({
			title: __('Add Operations User'),
			fields: [
				{ fieldname: 'full_name', fieldtype: 'Data', label: __('Full Name'), reqd: 1 },
				{ fieldname: 'email', fieldtype: 'Data', label: __('Email'), reqd: 1 },
				{ fieldname: 'password', fieldtype: 'Data', label: __('Password'), default: ADMIN_DEMO_PASSWORD, reqd: 1 },
			],
			primary_action_label: __('Create'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.admin.create_operations_user', values);
					frappe.show_alert({ message: __('Operations user created'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to create operations user', indicator: 'red' });
				}
			},
		});
		d.show();
	}
}
