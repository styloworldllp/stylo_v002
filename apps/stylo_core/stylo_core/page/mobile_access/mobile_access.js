frappe.pages['mobile-access'].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Mobile App Access',
		single_column: true,
	});

	new MobileAccessPage(wrapper);
};

class MobileAccessPage {
	constructor(wrapper) {
		this.wrapper = wrapper;
		this.page = wrapper.page;
		this.users = [];
		this.filtered = [];
		this.search = '';

		this.setup_toolbar();
		this.render_skeleton();
		this.load();
	}

	setup_toolbar() {
		// Search box in page header
		this.$search = $(`
			<div class="input-group" style="max-width:280px">
				<span class="input-group-text" style="background:transparent;border-right:none">
					<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
						viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
				</span>
				<input type="text" class="form-control" placeholder="Search users…"
					style="border-left:none;box-shadow:none">
			</div>
		`).appendTo(this.page.page_actions);

		this.$search.find('input').on('input', (e) => {
			this.search = e.target.value.toLowerCase();
			this.apply_filter();
		});

		// Refresh button
		this.page.add_inner_button(__('Refresh'), () => this.load());
	}

	render_skeleton() {
		this.$body = $('<div class="mobile-access-page" style="padding:20px 24px">').appendTo(
			$(this.wrapper).find('.layout-main-section')
		);

		// Stats strip
		this.$stats = $(`
			<div class="stats-row" style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap"></div>
		`).appendTo(this.$body);

		// Table container
		this.$table_wrap = $(`
			<div class="card" style="border-radius:12px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.08)">
				<div class="card-body p-0">
					<table class="table table-hover mb-0" style="font-size:13.5px">
						<thead style="background:var(--fg-color,#f8f8f8)">
							<tr>
								<th style="padding:12px 16px;font-weight:600;color:var(--text-muted)">User</th>
								<th style="padding:12px 16px;font-weight:600;color:var(--text-muted)">Email</th>
								<th style="padding:12px 16px;font-weight:600;color:var(--text-muted)">Last Login</th>
								<th style="padding:12px 16px;font-weight:600;color:var(--text-muted);text-align:center">Mobile Access</th>
							</tr>
						</thead>
						<tbody class="user-rows"></tbody>
					</table>
				</div>
			</div>
		`).appendTo(this.$body);

		this.$rows = this.$table_wrap.find('tbody.user-rows');
	}

	async load() {
		this.$rows.html(`
			<tr><td colspan="4" class="text-center text-muted" style="padding:40px">
				<div class="spinner-border spinner-border-sm me-2"></div> Loading…
			</td></tr>
		`);

		try {
			const r = await frappe.call('stylo_core.mobile_auth.get_mobile_users');
			this.users = r.message || [];
			this.apply_filter();
			this.render_stats();
		} catch (e) {
			this.$rows.html(`
				<tr><td colspan="4" class="text-center text-danger" style="padding:40px">
					Failed to load users
				</td></tr>
			`);
		}
	}

	apply_filter() {
		this.filtered = this.search
			? this.users.filter(u =>
				(u.full_name || '').toLowerCase().includes(this.search) ||
				(u.email || '').toLowerCase().includes(this.search)
			)
			: this.users;
		this.render_rows();
	}

	render_stats() {
		const total = this.users.length;
		const active = this.users.filter(u => u.has_mobile_access).length;

		this.$stats.html(`
			${this._stat_card('📱', active, 'Mobile Enabled', '#0FBF7F')}
			${this._stat_card('👥', total, 'Total Users', '#6366f1')}
			${this._stat_card('🚫', total - active, 'No Access', '#9ca3af')}
		`);
	}

	_stat_card(icon, value, label, color) {
		return `
			<div style="
				background:var(--card-bg,#fff);
				border-radius:12px;
				padding:14px 18px;
				min-width:130px;
				border:1px solid var(--border-color,rgba(0,0,0,.08));
				box-shadow:0 1px 4px rgba(0,0,0,.05);
			">
				<div style="font-size:22px;margin-bottom:4px">${icon}</div>
				<div style="font-size:26px;font-weight:800;color:${color};line-height:1">${value}</div>
				<div style="font-size:11px;color:var(--text-muted);font-weight:600;margin-top:4px;text-transform:uppercase;letter-spacing:.5px">${label}</div>
			</div>
		`;
	}

	render_rows() {
		if (!this.filtered.length) {
			this.$rows.html(`
				<tr><td colspan="4" class="text-center text-muted" style="padding:40px">
					No users found
				</td></tr>
			`);
			return;
		}

		this.$rows.html('');
		this.filtered.forEach(u => this._render_row(u));
	}

	_render_row(u) {
		const initials = (u.full_name || u.name || 'U')
			.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();

		const last_login = u.last_login
			? frappe.datetime.prettyDate(u.last_login)
			: '<span class="text-muted">Never</span>';

		const $tr = $(`
			<tr data-user="${frappe.utils.escape_html(u.name)}" style="vertical-align:middle">
				<td style="padding:12px 16px">
					<div style="display:flex;align-items:center;gap:10px">
						<div style="
							width:36px;height:36px;border-radius:50%;
							background:${u.has_mobile_access ? '#0FBF7F22' : 'rgba(0,0,0,.06)'};
							color:${u.has_mobile_access ? '#0FBF7F' : 'var(--text-muted)'};
							display:flex;align-items:center;justify-content:center;
							font-weight:700;font-size:13px;flex-shrink:0
						">${initials}</div>
						<div>
							<div style="font-weight:600;color:var(--heading-color)">${frappe.utils.escape_html(u.full_name || u.name)}</div>
							${u.name !== u.email ? `<div style="font-size:11px;color:var(--text-muted)">${frappe.utils.escape_html(u.name)}</div>` : ''}
						</div>
					</div>
				</td>
				<td style="padding:12px 16px;color:var(--text-muted)">${frappe.utils.escape_html(u.email || u.name)}</td>
				<td style="padding:12px 16px;color:var(--text-muted)">${last_login}</td>
				<td style="padding:12px 16px;text-align:center">
					<div class="toggle-wrap" style="display:inline-flex;align-items:center;gap:8px">
						<div class="toggle-switch ${u.has_mobile_access ? 'active' : ''}" style="
							width:44px;height:24px;border-radius:12px;
							background:${u.has_mobile_access ? '#0FBF7F' : 'rgba(0,0,0,.15)'};
							cursor:pointer;position:relative;transition:background .2s;flex-shrink:0
						">
							<div style="
								position:absolute;top:3px;
								left:${u.has_mobile_access ? '23px' : '3px'};
								width:18px;height:18px;border-radius:50%;
								background:#fff;transition:left .2s;
								box-shadow:0 1px 3px rgba(0,0,0,.25)
							"></div>
						</div>
						<span class="status-label" style="font-size:12px;font-weight:600;color:${u.has_mobile_access ? '#0FBF7F' : 'var(--text-muted)'}">
							${u.has_mobile_access ? 'Enabled' : 'Disabled'}
						</span>
					</div>
				</td>
			</tr>
		`);

		$tr.find('.toggle-wrap').on('click', () => this._toggle(u, $tr));
		this.$rows.append($tr);
	}

	async _toggle(u, $tr) {
		const new_state = !u.has_mobile_access;
		const action = new_state ? 'Grant' : 'Revoke';

		frappe.confirm(
			`${action} mobile app access for <b>${frappe.utils.escape_html(u.full_name || u.name)}</b>?`,
			async () => {
				const $switch = $tr.find('.toggle-switch');
				const $dot = $switch.find('div');
				const $label = $tr.find('.status-label');

				// Optimistic UI update
				$switch.css('background', new_state ? '#0FBF7F' : 'rgba(0,0,0,.15)');
				$dot.css('left', new_state ? '23px' : '3px');
				$label.text(new_state ? 'Enabled' : 'Disabled').css('color', new_state ? '#0FBF7F' : 'var(--text-muted)');

				try {
					await frappe.call({
						method: 'stylo_core.mobile_auth.set_mobile_access',
						args: { user: u.name, grant: new_state },
					});

					u.has_mobile_access = new_state;
					frappe.show_alert({
						message: `Mobile access ${new_state ? 'granted' : 'revoked'} for ${u.full_name || u.name}`,
						indicator: new_state ? 'green' : 'orange',
					}, 4);
					this.render_stats();
				} catch (e) {
					// Roll back on error
					$switch.css('background', !new_state ? '#0FBF7F' : 'rgba(0,0,0,.15)');
					$dot.css('left', !new_state ? '23px' : '3px');
					$label.text(!new_state ? 'Enabled' : 'Disabled').css('color', !new_state ? '#0FBF7F' : 'var(--text-muted)');
					frappe.msgprint({ message: e.message || 'Failed to update access', indicator: 'red' });
				}
			}
		);
	}
}
