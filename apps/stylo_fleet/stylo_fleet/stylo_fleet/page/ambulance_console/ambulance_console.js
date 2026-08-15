frappe.pages['ambulance-console'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Ambulance',
		single_column: true,
	});

	new AmbulanceConsolePage(wrapper);
};

const STATUS_COLOR = {
	Available: '#2e9e5b',
	'On Call': '#2f6fed',
	'Returning / Transit': '#2f6fed',
	'Going for Refill': '#c98a1c',
	'At Refill Station': '#c98a1c',
	'Under Cleaning': '#c98a1c',
	'Under Maintenance': '#c9401c',
	Breakdown: '#c9401c',
	Unavailable: '#c9401c',
	Inactive: '#8a8f98',
};

class AmbulanceConsolePage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.data = null;
		fleet_inject_styles();

		this.setup_toolbar();
		this.render_skeleton();
		this.load();
	}

	setup_toolbar() {
		this.page.add_inner_button(__('Refresh'), () => this.load());
	}

	render_skeleton() {
		this.$body = $('<div class="ambulance-console-page" style="padding:20px 24px;max-width:720px">').appendTo(
			$(this.wrapper).find('.layout-main-section')
		);
		this.$stats_wrap = $('<div class="fleet-dash" style="padding:0;background:transparent">').appendTo(this.$body);
		this.$stats_wrap.append(`<div class="fd-section-title" style="margin:0 0 10px">${__('My Stats')}</div>`);
		this.$stats = $('<div class="fd-kpi-grid" style="margin-bottom:20px">').appendTo(this.$stats_wrap);

		this.$status = $('<div>').appendTo(this.$body);
		this.$actions = $('<div style="margin-top:16px">').appendTo(this.$body);
		this.$log = $('<div style="margin-top:28px">').appendTo(this.$body);
	}

	async load_stats() {
		try {
			const r = await frappe.call('stylo_fleet.api.console.get_my_stats');
			const s = r.message;
			fleet_render_kpis(this.$stats, [
				{ label: __('Total Shifts'), value: s.total_shifts, accent: 'var(--brand)' },
				{ label: __('Calls Completed'), value: s.total_calls, accent: 'var(--cat-1)' },
				{ label: __('Kits Consumed'), value: s.kits_consumed, accent: 'var(--cat-5)' },
				{ label: __('Issues Reported'), value: s.issues_reported, accent: 'var(--status-warning)' },
			]);
		} catch (e) {
			// non-fatal — stats are a nice-to-have, don't block the operating controls
			console.error(e);
		}
	}

	async load() {
		this.load_stats();
		try {
			const r = await frappe.call('stylo_fleet.api.console.get_my_console');
			this.data = r.message;
			this.render();
		} catch (e) {
			frappe.msgprint({ message: e.message || 'Failed to load your ambulance console', indicator: 'red' });
		}
	}

	get_location() {
		return new Promise((resolve) => {
			if (!navigator.geolocation) {
				resolve({ latitude: null, longitude: null });
				return;
			}
			navigator.geolocation.getCurrentPosition(
				(pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
				() => resolve({ latitude: null, longitude: null }), // permission denied / unavailable — spec §21: don't block the workflow
				{ timeout: 5000 }
			);
		});
	}

	async call_action(method, args, success_message) {
		try {
			const location = await this.get_location();
			await frappe.call({ method, args: Object.assign({}, args, location) });
			frappe.show_alert({ message: success_message, indicator: 'green' });
			this.load();
		} catch (e) {
			frappe.msgprint({ message: e.message || 'Action failed', indicator: 'red' });
		}
	}

	render() {
		this.render_status();
		this.render_actions();
		this.render_log();
	}

	render_status() {
		this.$status.empty();
		const amb = this.data.ambulance;

		if (!amb) {
			this.$status.append(`
				<div class="card" style="border-radius:12px;padding:24px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.08)">
					<div style="font-size:15px;color:var(--text-muted)">You have no active shift.</div>
				</div>
			`);
			return;
		}

		const color = STATUS_COLOR[amb.operational_status] || '#8a8f98';
		this.$status.append(`
			<div class="card" style="border-radius:12px;padding:20px;box-shadow:0 1px 4px rgba(0,0,0,.08)">
				<div style="display:flex;justify-content:space-between;align-items:center">
					<div>
						<div style="font-size:20px;font-weight:600">${frappe.utils.escape_html(amb.ambulance_id)}</div>
						<div style="color:var(--text-muted);font-size:13px">${frappe.utils.escape_html(amb.vehicle_number || '')}</div>
					</div>
					<span style="background:${color}1a;color:${color};padding:5px 12px;border-radius:20px;font-size:12.5px;font-weight:600">
						${frappe.utils.escape_html(amb.operational_status)}
					</span>
				</div>
				<div style="display:flex;gap:24px;margin-top:16px;flex-wrap:wrap">
					<div><div style="font-size:11px;color:var(--text-muted)">KITS</div><div style="font-weight:600">${amb.available_kits}/${amb.kit_capacity} (${frappe.utils.escape_html(amb.kit_status || '')})</div></div>
					<div><div style="font-size:11px;color:var(--text-muted)">CLEANLINESS</div><div style="font-weight:600">${frappe.utils.escape_html(amb.cleanliness_status || '')}</div></div>
					<div><div style="font-size:11px;color:var(--text-muted)">MECHANICAL</div><div style="font-weight:600">${frappe.utils.escape_html(amb.mechanical_status || '')}</div></div>
				</div>
				${amb.availability_reason ? `<div style="margin-top:12px;font-size:12.5px;color:${color}">${frappe.utils.escape_html(amb.availability_reason)}</div>` : ''}
			</div>
		`);
	}

	render_actions() {
		this.$actions.empty();
		const amb = this.data.ambulance;
		const make_btn = (label, cls, handler) => {
			const $btn = $(`<button class="btn ${cls}" style="margin:0 8px 8px 0">${__(label)}</button>`);
			$btn.on('click', handler);
			return $btn;
		};

		if (!amb) {
			this.$actions.append(make_btn('Start Shift', 'btn-primary', () => this.show_start_shift_dialog()));
			return;
		}

		if (amb.operational_status === 'On Call') {
			this.$actions.append(make_btn('Complete Call', 'btn-primary', () => this.show_complete_call_dialog()));
		} else {
			this.$actions.append(make_btn('Attend Call', 'btn-primary', () => this.call_action(
				'stylo_fleet.api.call.attend_call', { ambulance: amb.name }, __('Call started')
			)));

			if (this.data.pending_refill && !['Going for Refill', 'At Refill Station'].includes(amb.operational_status)) {
				this.$actions.append(make_btn('Proceed to Refill', 'btn-default', () => this.call_action(
					'stylo_fleet.api.refill.proceed_to_refill', { ambulance: amb.name }, __('Heading to refill station')
				)));
			}

			this.$actions.append(make_btn('Report Issue', 'btn-default', () => this.show_report_issue_dialog()));

			this.$actions.append(make_btn('End Shift', 'btn-default', () => frappe.confirm(
				__('End your shift on {0}?', [amb.ambulance_id]),
				() => this.call_action('stylo_fleet.api.shift.end_shift', { shift: amb.current_shift }, __('Shift ended'))
			)));
		}
	}

	show_start_shift_dialog() {
		frappe.call('stylo_fleet.api.console.get_selectable_ambulances').then((r) => {
			const ambulances = r.message || [];
			if (!ambulances.length) {
				frappe.msgprint({ message: __('No ambulance is currently available to start a shift on.'), indicator: 'orange' });
				return;
			}
			const d = new frappe.ui.Dialog({
				title: __('Start Shift'),
				fields: [
					{
						fieldname: 'ambulance', fieldtype: 'Select', label: __('Ambulance'), reqd: 1,
						options: ambulances.map((a) => `${a.name} (${a.vehicle_number})`),
					},
					{ fieldname: 'start_check_result', fieldtype: 'Small Text', label: __('Quick Safety Check (optional)') },
				],
				primary_action_label: __('Start Shift'),
				primary_action: async (values) => {
					const ambulance_name = values.ambulance.split(' (')[0];
					d.hide();
					await this.call_action('stylo_fleet.api.shift.start_shift', {
						ambulance: ambulance_name,
						paramedic: this.data.paramedic.name,
						start_check_result: values.start_check_result,
					}, __('Shift started'));
				},
			});
			d.show();
		});
	}

	show_complete_call_dialog() {
		const amb = this.data.ambulance;
		const d = new frappe.ui.Dialog({
			title: __('Complete Call'),
			fields: [
				{ fieldname: 'kits_consumed', fieldtype: 'Int', label: __('Kits Consumed'), reqd: 1, default: 0 },
				{ fieldname: 'ambulance_clean', fieldtype: 'Check', label: __('Ambulance clean?'), default: 1 },
				{ fieldname: 'contamination_required', fieldtype: 'Check', label: __('Contamination / special cleaning required?') },
				{ fieldname: 'mechanical_issue', fieldtype: 'Check', label: __('Mechanical issue observed?') },
				{
					fieldname: 'issue_severity', fieldtype: 'Select', label: __('Issue Severity'),
					options: ['', 'Observation', 'Attention Required', 'Breakdown'],
					depends_on: 'eval:doc.mechanical_issue',
				},
				{ fieldname: 'remarks', fieldtype: 'Small Text', label: __('Remarks (optional)') },
			],
			primary_action_label: __('Complete Call'),
			primary_action: async (values) => {
				d.hide();
				await this.call_action('stylo_fleet.api.call.complete_call', {
					ambulance: amb.name,
					kits_consumed: values.kits_consumed,
					ambulance_clean: values.ambulance_clean ? 1 : 0,
					contamination_required: values.contamination_required ? 1 : 0,
					mechanical_issue: values.mechanical_issue ? 1 : 0,
					issue_severity: values.issue_severity,
					remarks: values.remarks,
				}, __('Call completed'));
			},
		});
		d.show();
	}

	show_report_issue_dialog() {
		const amb = this.data.ambulance;
		const d = new frappe.ui.Dialog({
			title: __('Report Issue'),
			fields: [
				{ fieldname: 'issue_type', fieldtype: 'Select', label: __('Issue Type'), reqd: 1, options: ['Cleaning', 'Mechanical'] },
				{
					fieldname: 'severity', fieldtype: 'Select', label: __('Severity'),
					options: ['', 'Observation', 'Attention Required', 'Breakdown'],
					depends_on: 'eval:doc.issue_type=="Mechanical"',
				},
				{ fieldname: 'description', fieldtype: 'Small Text', label: __('Description') },
			],
			primary_action_label: __('Report'),
			primary_action: async (values) => {
				d.hide();
				await this.call_action('stylo_fleet.api.issue.report_issue', {
					ambulance: amb.name,
					issue_type: values.issue_type,
					severity: values.severity,
					description: values.description,
				}, __('Issue reported'));
			},
		});
		d.show();
	}

	render_log() {
		this.$log.empty();
		this.$log.append(`<div style="font-size:13px;font-weight:600;color:var(--text-muted);margin-bottom:8px">${__('TODAY\'S LOG')}</div>`);

		const rows = this.data.today_activity || [];
		if (!rows.length) {
			this.$log.append(`<div style="color:var(--text-muted);font-size:13px">${__('No activity yet today.')}</div>`);
			return;
		}

		const $table = $(`
			<div class="card" style="border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">
				<table class="table table-hover mb-0" style="font-size:13px">
					<thead><tr>
						<th>${__('Time')}</th><th>${__('Activity')}</th><th>${__('Detail')}</th>
					</tr></thead>
					<tbody></tbody>
				</table>
			</div>
		`).appendTo(this.$log);

		const $tbody = $table.find('tbody');
		rows.forEach((row) => {
			let detail = row.remarks || '';
			if (row.kit_balance_before !== row.kit_balance_after && row.kit_balance_after !== null) {
				detail = `${__('Kits')}: ${row.kit_balance_before} → ${row.kit_balance_after}${detail ? ' — ' + detail : ''}`;
			}
			$tbody.append(`
				<tr>
					<td>${frappe.datetime.str_to_user(row.event_datetime)}</td>
					<td>${frappe.utils.escape_html(row.activity_type)}</td>
					<td>${frappe.utils.escape_html(detail)}</td>
				</tr>
			`);
		});
	}
}
