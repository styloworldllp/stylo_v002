frappe.pages['station-console'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Station',
		single_column: true,
	});

	new StationConsolePage(wrapper);
};

class StationConsolePage {
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
					<h1>${__('Station Console')}</h1>
					<div class="fd-sub" id="station-console-sub"></div>
				</div>
			</div>
		`);
		this.$kpis = $('<div class="fd-kpi-grid">').appendTo(this.$body);
		this.$pending_card = $('<div class="fd-card"><h3>' + __('Pending Refills') + '</h3></div>').appendTo(this.$body);
		this.$body.append('<div style="margin-top:16px"></div>');
		this.$completed_card = $('<div class="fd-card" style="margin-top:16px"><h3>' + __("Completed Today") + '</h3></div>').appendTo(this.$body);
	}

	async load() {
		try {
			const r = await frappe.call('stylo_fleet.api.station_console.get_my_station_console');
			this.data = r.message;
			this.render();
		} catch (e) {
			frappe.msgprint({ message: e.message || 'Failed to load station console', indicator: 'red' });
		}
	}

	render() {
		const d = this.data;
		$('#station-console-sub').text(d.station ? __('Scoped to {0}', [d.station]) : __('All stations'));

		fleet_render_kpis(this.$kpis, [
			{ label: __('Pending Refills'), value: d.pending.length, accent: 'var(--status-warning)' },
			{ label: __('Completed Today'), value: d.completed_today.length, accent: 'var(--status-good)' },
			{ label: __('Kits Loaded Today'), value: d.kits_loaded_today, accent: 'var(--brand)' },
		]);

		this.render_pending();
		this.render_completed();
	}

	render_pending() {
		this.$pending_card.find('.fd-list-item, .fd-empty').remove();
		if (!this.data.pending.length) {
			this.$pending_card.append(`<div class="fd-empty">${__('No pending refills.')}</div>`);
			return;
		}
		this.data.pending.forEach((r) => {
			const $item = $(`
				<div class="fd-list-item">
					<div>
						<div class="fd-li-main">${frappe.utils.escape_html(r.ambulance)}</div>
						<div class="fd-li-sub">${__('Balance')} ${r.balance_before_refill} — ${__('needs')} ${r.expected_load_quantity} ${__('kits')} — ${frappe.datetime.comment_when(r.requested_at)}</div>
					</div>
					<div class="fd-li-actions">
						<button class="fd-btn fd-btn-brand">${__('Confirm Load')}</button>
					</div>
				</div>
			`);
			$item.find('button').on('click', () => this.show_confirm_dialog(r));
			this.$pending_card.append($item);
		});
	}

	render_completed() {
		this.$completed_card.find('.fd-list-item, .fd-empty').remove();
		if (!this.data.completed_today.length) {
			this.$completed_card.append(`<div class="fd-empty">${__('No refills completed yet today.')}</div>`);
			return;
		}
		this.data.completed_today.forEach((r) => {
			this.$completed_card.append(`
				<div class="fd-list-item">
					<div>
						<div class="fd-li-main">${frappe.utils.escape_html(r.ambulance)} — ${r.actual_loaded_quantity} ${__('kits loaded')}</div>
						<div class="fd-li-sub">${r.exception_reason ? __('Partial: ') + frappe.utils.escape_html(r.exception_reason) : __('Full load')} — ${frappe.datetime.comment_when(r.completed_at)}</div>
					</div>
				</div>
			`);
		});
	}

	show_confirm_dialog(refill) {
		const d = new frappe.ui.Dialog({
			title: __('Confirm Refill — {0}', [refill.ambulance]),
			fields: [
				{ fieldname: 'info', fieldtype: 'HTML', options: `<div style="margin-bottom:10px;color:var(--text-muted,#888)">${__('Expected load')}: <b>${refill.expected_load_quantity}</b> ${__('kits')}</div>` },
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
