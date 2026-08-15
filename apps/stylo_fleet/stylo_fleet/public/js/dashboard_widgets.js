// Shared dashboard building blocks for stylo_fleet's role consoles
// (Fleet Analytics, Admin, Operations). Palette/marks per the validated
// Stylo brand palette — see nhs_tracking CHANGELOG for the validation run.

const FLEET_OPERATIONAL_STATUS_GROUP = {
	Available: 'good',
	'On Call': 'info',
	'Returning / Transit': 'info',
	'Going for Refill': 'info',
	'At Refill Station': 'info',
	'Under Cleaning': 'warning',
	'Under Maintenance': 'serious',
	Breakdown: 'critical',
	Unavailable: 'critical',
	Inactive: 'muted',
};

const FLEET_KIT_STATUS_GROUP = {
	Ready: 'good',
	'Refill Due': 'warning',
	Insufficient: 'serious',
	'No Kits': 'critical',
};

const FLEET_CAT_SLOTS = ['--cat-1', '--cat-2', '--cat-3', '--cat-4', '--cat-5', '--cat-6'];

function fleet_inject_styles() {
	if (document.getElementById('fleet-dashboard-styles')) return;
	$(`<style id="fleet-dashboard-styles">
		.fleet-dash {
			--surface-1:      #fcfcfb;
			--page-plane:     #f9f9f7;
			--text-primary:   #0b0b0b;
			--text-secondary: #52514e;
			--text-muted:     #898781;
			--gridline:       #e1e0d9;
			--baseline:       #c3c2b7;
			--border:         rgba(11,11,11,0.10);
			--brand:          #0FBF7F;
			--brand-hover:    #0DA870;
			--status-good:      #0ca30c;
			--status-warning:   #fab219;
			--status-serious:   #ec835a;
			--status-critical:  #d03b3b;
			--cat-1: #2a78d6; --cat-2: #eb6834; --cat-3: #1baf7a;
			--cat-4: #eda100; --cat-5: #e87ba4; --cat-6: #4a3aa7;
		}
		@media (prefers-color-scheme: dark) {
			:root:where(:not([data-theme="light"])) .fleet-dash {
				--surface-1: #1a1a19; --page-plane: #0d0d0d;
				--text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
				--gridline: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
				--cat-1: #3987e5; --cat-2: #d95926; --cat-3: #199e70;
				--cat-4: #c98500; --cat-5: #d55181; --cat-6: #9085e9;
			}
		}
		:root[data-theme="dark"] .fleet-dash {
			--surface-1: #1a1a19; --page-plane: #0d0d0d;
			--text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #898781;
			--gridline: #2c2c2a; --baseline: #383835; --border: rgba(255,255,255,0.10);
			--cat-1: #3987e5; --cat-2: #d95926; --cat-3: #199e70;
			--cat-4: #c98500; --cat-5: #d55181; --cat-6: #9085e9;
		}
		.fleet-dash { background: var(--page-plane); padding: 8px 4px 40px; font-variant-numeric: proportional-nums; }
		.fleet-dash * { box-sizing: border-box; }
		.fd-header { display:flex; justify-content:space-between; align-items:flex-end; margin-bottom:20px; flex-wrap:wrap; gap:8px; }
		.fd-header h1 { font-size:22px; font-weight:600; color:var(--text-primary); margin:0; }
		.fd-header .fd-sub { font-size:13px; color:var(--text-muted); margin-top:2px; }
		.fd-refreshed { font-size:12px; color:var(--text-muted); }

		.fd-section-title { font-size:15px; font-weight:600; color:var(--text-primary); margin:28px 0 12px; }

		.fd-kpi-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:12px; margin-bottom:24px; }
		.fd-kpi { background:var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:16px 18px; position:relative; overflow:hidden; box-shadow:0 1px 3px rgba(0,0,0,.05); }
		.fd-kpi::before { content:''; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--accent, var(--brand)); }
		.fd-kpi .fd-kpi-label { font-size:11.5px; color:var(--text-muted); text-transform:uppercase; letter-spacing:.03em; font-weight:600; }
		.fd-kpi .fd-kpi-value { font-size:30px; font-weight:600; color:var(--text-primary); margin-top:6px; line-height:1; }

		.fd-grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
		@media (max-width: 900px) { .fd-grid-2 { grid-template-columns:1fr; } }

		.fd-card { background:var(--surface-1); border:1px solid var(--border); border-radius:12px; padding:18px 20px; box-shadow:0 1px 3px rgba(0,0,0,.05); }
		.fd-card h3 { font-size:14px; font-weight:600; color:var(--text-primary); margin:0 0 14px; display:flex; justify-content:space-between; align-items:center; }
		.fd-card .fd-empty { color:var(--text-muted); font-size:13px; padding:12px 0; }

		.fd-bar-row { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
		.fd-bar-row:last-child { margin-bottom:0; }
		.fd-bar-label { width:132px; flex-shrink:0; font-size:12.5px; color:var(--text-secondary); text-align:right; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
		.fd-bar-track { flex:1; height:20px; background:var(--gridline); border-radius:4px; position:relative; overflow:hidden; }
		.fd-bar-fill { position:absolute; left:0; top:0; bottom:0; border-radius:4px 8px 8px 4px; transition:width .3s ease; cursor:default; }
		.fd-bar-value { width:34px; flex-shrink:0; font-size:12.5px; font-weight:600; color:var(--text-primary); text-align:left; font-variant-numeric: tabular-nums; }

		.fd-status-badge { display:inline-flex; align-items:center; gap:5px; padding:3px 9px; border-radius:20px; font-size:11.5px; font-weight:600; }
		.fd-status-badge .fd-dot { width:6px; height:6px; border-radius:50%; }

		.fd-list-item { display:flex; align-items:flex-start; justify-content:space-between; gap:10px; padding:10px 0; border-bottom:1px solid var(--gridline); }
		.fd-list-item:last-child { border-bottom:none; padding-bottom:0; }
		.fd-list-item .fd-li-main { font-size:13px; color:var(--text-primary); font-weight:500; }
		.fd-list-item .fd-li-sub { font-size:12px; color:var(--text-muted); margin-top:2px; }
		.fd-list-item .fd-li-actions { flex-shrink:0; }

		.fd-feed-item { display:flex; gap:10px; padding:9px 0; border-bottom:1px solid var(--gridline); }
		.fd-feed-item:last-child { border-bottom:none; padding-bottom:0; }
		.fd-feed-dot { width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0; }
		.fd-feed-text { font-size:13px; color:var(--text-primary); }
		.fd-feed-meta { font-size:11.5px; color:var(--text-muted); margin-top:1px; }

		.fd-tooltip { position:fixed; pointer-events:none; background:var(--text-primary,#0b0b0b); color:var(--surface-1,#fff); font-size:12px; font-weight:600; padding:5px 9px; border-radius:6px; opacity:0; transform:translate(-50%,-130%); transition:opacity .1s; z-index:9999; white-space:nowrap; }
		.fd-tooltip.show { opacity:1; }
		[data-theme="dark"] .fd-tooltip { background:#fff; color:#0b0b0b; }

		.fd-table { width:100%; border-collapse:collapse; font-size:13px; }
		.fd-table th { text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.03em; color:var(--text-muted); font-weight:600; padding:0 10px 8px; border-bottom:1px solid var(--gridline); }
		.fd-table td { padding:9px 10px; border-bottom:1px solid var(--gridline); color:var(--text-primary); }
		.fd-table tr:last-child td { border-bottom:none; }

		.fd-btn { border:none; border-radius:6px; padding:5px 12px; font-size:12px; font-weight:600; cursor:pointer; }
		.fd-btn-brand { background:var(--brand); color:#fff; }
		.fd-btn-brand:hover { background:var(--brand-hover); }
		.fd-btn-outline { background:transparent; border:1px solid var(--border); color:var(--text-primary); }
	</style>`).appendTo('head');
}

function fleet_status_color(group) {
	return {
		good: 'var(--status-good)',
		warning: 'var(--status-warning)',
		serious: 'var(--status-serious)',
		critical: 'var(--status-critical)',
		info: 'var(--cat-1)',
		muted: 'var(--text-muted)',
	}[group] || 'var(--text-muted)';
}

function fleet_categorical_color_map(labels) {
	const sorted = [...new Set(labels)].sort();
	const map = {};
	sorted.forEach((l, i) => { map[l] = `var(${FLEET_CAT_SLOTS[i % FLEET_CAT_SLOTS.length]})`; });
	return map;
}

class FleetTooltip {
	constructor() {
		this.$el = $('<div class="fd-tooltip"></div>').appendTo('body');
	}
	show(ev, text) {
		this.$el.text(text).addClass('show');
		this.move(ev);
	}
	move(ev) {
		this.$el.css({ left: ev.clientX, top: ev.clientY });
	}
	hide() {
		this.$el.removeClass('show');
	}
}

function fleet_render_kpis($container, tiles) {
	$container.empty();
	tiles.forEach((t) => {
		$container.append(`
			<div class="fd-kpi" style="--accent:${t.accent}">
				<div class="fd-kpi-label">${t.label}</div>
				<div class="fd-kpi-value">${t.value}</div>
			</div>
		`);
	});
}

function fleet_render_bar_chart($card, entries, color_fn, empty_text, tooltip) {
	$card.find('.fd-bar-row, .fd-empty').remove();
	if (!entries.length) {
		$card.append(`<div class="fd-empty">${empty_text}</div>`);
		return;
	}
	const max = Math.max(...entries.map((e) => e.value), 1);
	entries.forEach((e) => {
		const pct = Math.max((e.value / max) * 100, 4);
		const color = color_fn(e.label);
		const $row = $(`
			<div class="fd-bar-row">
				<div class="fd-bar-label">${frappe.utils.escape_html(e.label)}</div>
				<div class="fd-bar-track">
					<div class="fd-bar-fill" style="width:${pct}%;background:${color}"></div>
				</div>
				<div class="fd-bar-value">${e.value}</div>
			</div>
		`);
		const $fill = $row.find('.fd-bar-fill');
		$fill.on('mouseenter', (ev) => tooltip.show(ev, `${e.label}: ${e.value}`));
		$fill.on('mousemove', (ev) => tooltip.move(ev));
		$fill.on('mouseleave', () => tooltip.hide());
		$card.append($row);
	});
}

function fleet_render_feed($card, rows, empty_text) {
	$card.find('.fd-feed-item, .fd-empty').remove();
	if (!rows.length) {
		$card.append(`<div class="fd-empty">${empty_text}</div>`);
		return;
	}
	rows.forEach((row) => {
		const color = fleet_status_color(FLEET_OPERATIONAL_STATUS_GROUP[row.new_status] || 'info');
		$card.append(`
			<div class="fd-feed-item">
				<div class="fd-feed-dot" style="background:${color}"></div>
				<div>
					<div class="fd-feed-text">
						<b>${frappe.utils.escape_html(row.ambulance)}</b> — ${frappe.utils.escape_html(row.activity_type)}
						${row.remarks ? ': ' + frappe.utils.escape_html(row.remarks) : ''}
					</div>
					<div class="fd-feed-meta">${frappe.datetime.comment_when(row.event_datetime)}</div>
				</div>
			</div>
		`);
	});
}
