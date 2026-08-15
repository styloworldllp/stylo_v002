frappe.pages['operations-console'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Operations',
		single_column: true,
	});

	new OperationsConsolePage(wrapper);
};

class OperationsConsolePage {
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
					<h1>${__('Operations')}</h1>
					<div class="fd-sub">${__('Service desk — open tickets across the fleet')}</div>
				</div>
			</div>
		`);
		this.$kpis = $('<div class="fd-kpi-grid">').appendTo(this.$body);

		this.$queue_card = $(`<div class="fd-card"><h3>${__('Ticket Queue')} <span id="op-queue-count" style="font-size:12px;font-weight:600;color:var(--text-muted)"></span></h3></div>`).appendTo(this.$body);

		this.$row2 = $('<div class="fd-grid-2" style="margin-top:16px">').appendTo(this.$body);
		this.$status_card = $('<div class="fd-card"><h3>' + __('Fleet Status') + '</h3></div>').appendTo(this.$row2);
		this.$kit_card = $('<div class="fd-card"><h3>' + __('Kit Readiness') + '</h3></div>').appendTo(this.$row2);
	}

	async load() {
		try {
			const [dash, tickets] = await Promise.all([
				frappe.call('stylo_fleet.api.analytics.get_dashboard_data'),
				frappe.call('stylo_fleet.api.ticketing.get_open_tickets'),
			]);
			this.data = dash.message;
			this.tickets = tickets.message;
			this.render();
		} catch (e) {
			frappe.msgprint({ message: e.message || 'Failed to load operations console', indicator: 'red' });
		}
	}

	render() {
		const k = this.data.kpis;
		const total_open = this.data.open_issues.length + this.data.pending_refills.length + this.tickets.length;
		fleet_render_kpis(this.$kpis, [
			{ label: __('Total Ambulances'), value: k.total_active, accent: 'var(--brand)' },
			{ label: __('Available Now'), value: k.available_now, accent: 'var(--status-good)' },
			{ label: __('On Call'), value: k.on_call, accent: 'var(--cat-1)' },
			{ label: __('Open Tickets'), value: total_open, accent: 'var(--status-serious)' },
		]);

		$('#op-queue-count').text(`${total_open} ${__('open')}`);
		this.render_queue();

		const status_entries = Object.entries(this.data.status_breakdown).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
		fleet_render_bar_chart(this.$status_card, status_entries, (l) => fleet_status_color(FLEET_OPERATIONAL_STATUS_GROUP[l] || 'muted'), __('No active ambulances yet.'), this.tooltip);

		const kit_entries = Object.entries(this.data.kit_breakdown).map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
		fleet_render_bar_chart(this.$kit_card, kit_entries, (l) => fleet_status_color(FLEET_KIT_STATUS_GROUP[l] || 'muted'), __('No kit data yet.'), this.tooltip);
	}

	render_queue() {
		this.$queue_card.find('.fd-list-item, .fd-empty').remove();
		const issues = this.data.open_issues || [];
		const refills = this.data.pending_refills || [];
		const tickets = this.tickets || [];

		if (!issues.length && !refills.length && !tickets.length) {
			this.$queue_card.append(`<div class="fd-empty">${__('No open tickets — fleet is clear.')}</div>`);
			return;
		}

		const PRIORITY_COLOR = { Low: 'var(--text-muted)', Medium: 'var(--cat-1)', High: 'var(--status-warning)', Urgent: 'var(--status-critical)' };
		tickets.forEach((t) => {
			const color = PRIORITY_COLOR[t.priority] || 'var(--text-muted)';
			const $item = $(`
				<div class="fd-list-item">
					<div>
						<span class="fd-status-badge" style="background:${color}1a;color:${color};margin-right:8px">
							<span class="fd-dot" style="background:${color}"></span>${frappe.utils.escape_html(t.category)} · ${frappe.utils.escape_html(t.priority)}
						</span>
						<span class="fd-li-main" style="display:inline">${frappe.utils.escape_html(t.subject)}</span>
						<div class="fd-li-sub">${frappe.utils.escape_html(t.raised_by)} — ${frappe.datetime.comment_when(t.raised_at)}</div>
					</div>
					<div class="fd-li-actions">
						<button class="fd-btn fd-btn-outline">${__('Close')}</button>
					</div>
				</div>
			`);
			$item.find('button').on('click', () => this.show_close_ticket_dialog(t));
			this.$queue_card.append($item);
		});

		issues.forEach((i) => {
			const color = i.issue_type === 'Mechanical' ? 'var(--status-critical)' : 'var(--status-warning)';
			const $item = $(`
				<div class="fd-list-item">
					<div>
						<span class="fd-status-badge" style="background:${color}1a;color:${color};margin-right:8px">
							<span class="fd-dot" style="background:${color}"></span>${frappe.utils.escape_html(i.issue_type)}
						</span>
						<span class="fd-li-main" style="display:inline">${frappe.utils.escape_html(i.ambulance)}</span>
						<div class="fd-li-sub">${frappe.utils.escape_html(i.description || i.severity || '')} — ${frappe.datetime.comment_when(i.reported_at)}</div>
					</div>
					<div class="fd-li-actions">
						<button class="fd-btn fd-btn-outline">${__('Resolve')}</button>
					</div>
				</div>
			`);
			$item.find('button').on('click', () => this.show_resolve_dialog(i));
			this.$queue_card.append($item);
		});

		refills.forEach((r) => {
			const $item = $(`
				<div class="fd-list-item">
					<div>
						<span class="fd-status-badge" style="background:var(--status-warning)1a;color:var(--status-warning);margin-right:8px">
							<span class="fd-dot" style="background:var(--status-warning)"></span>${__('Refill')}
						</span>
						<span class="fd-li-main" style="display:inline">${frappe.utils.escape_html(r.ambulance)}</span>
						<div class="fd-li-sub">${__('Needs')} ${r.expected_load_quantity} ${__('kits')} — ${frappe.utils.escape_html(r.station || '')} — ${frappe.datetime.comment_when(r.requested_at)}</div>
					</div>
					<div class="fd-li-actions">
						<button class="fd-btn fd-btn-brand">${__('Confirm Load')}</button>
					</div>
				</div>
			`);
			$item.find('button').on('click', () => this.show_confirm_refill_dialog(r));
			this.$queue_card.append($item);
		});
	}

	show_close_ticket_dialog(ticket) {
		const d = new frappe.ui.Dialog({
			title: __('Close Ticket — {0}', [ticket.subject]),
			fields: [
				{ fieldname: 'resolution_summary', fieldtype: 'Small Text', label: __('Resolution Summary'), reqd: 1 },
				{ fieldname: 'root_cause', fieldtype: 'Select', label: __('Root Cause'),
					options: ['', 'User Error', 'Equipment Failure', 'Process Gap', 'External', 'Other'] },
			],
			primary_action_label: __('Close Ticket'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.ticketing.close_ticket', {
						ticket: ticket.name,
						resolution_summary: values.resolution_summary,
						root_cause: values.root_cause,
					});
					frappe.show_alert({ message: __('Ticket closed'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to close ticket', indicator: 'red' });
				}
			},
		});
		d.show();
	}

	show_resolve_dialog(issue) {
		const d = new frappe.ui.Dialog({
			title: __('Resolve Issue — {0}', [issue.ambulance]),
			fields: [
				{ fieldname: 'resolution_remarks', fieldtype: 'Small Text', label: __('Resolution Remarks') },
			],
			primary_action_label: __('Resolve'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.issue.resolve_issue', {
						issue: issue.name,
						resolution_remarks: values.resolution_remarks,
					});
					frappe.show_alert({ message: __('Issue resolved'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to resolve issue', indicator: 'red' });
				}
			},
		});
		d.show();
	}

	show_confirm_refill_dialog(refill) {
		const d = new frappe.ui.Dialog({
			title: __('Confirm Refill — {0}', [refill.ambulance]),
			fields: [
				{ fieldname: 'actual_loaded_quantity', fieldtype: 'Int', label: __('Actual Loaded Quantity'), default: refill.expected_load_quantity, reqd: 1 },
				{ fieldname: 'exception_reason', fieldtype: 'Small Text', label: __('Exception Reason (required if less than expected)') },
			],
			primary_action_label: __('Confirm'),
			primary_action: async (values) => {
				d.hide();
				try {
					await frappe.call('stylo_fleet.api.refill.confirm_refill', {
						refill: refill.name,
						actual_loaded_quantity: values.actual_loaded_quantity,
						exception_reason: values.exception_reason,
					});
					frappe.show_alert({ message: __('Refill confirmed'), indicator: 'green' });
					this.load();
				} catch (e) {
					frappe.msgprint({ message: e.message || 'Failed to confirm refill', indicator: 'red' });
				}
			},
		});
		d.show();
	}
}
