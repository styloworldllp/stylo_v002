/**
 * Stylo Mobile App
 * Bottom nav + full-screen panels: Home | Approvals | brAIn | Work | Me
 * Demo-only until stable — do not deploy to stangroup without explicit sign-off.
 */
(function () {
	"use strict";

	const BP = 768;
	let activePanel = null;
	let approvalBadgeCount = 0;

	const isMobile = () => window.innerWidth <= BP;
	const qs  = (s, ctx = document) => ctx.querySelector(s);
	const mk  = (tag, cls, html) => {
		const e = document.createElement(tag);
		if (cls) e.className = cls;
		if (html !== undefined) e.innerHTML = html;
		return e;
	};
	const today = () => frappe.datetime.get_today();
	const fmt   = (d) => d ? frappe.datetime.str_to_user(d) : "—";
	const currency = (n) => frappe.format(n || 0, { fieldtype: "Currency" });

	/* ═══════════════════════════════════════════════════════════
	   STYLES
	══════════════════════════════════════════════════════════════ */
	function injectStyles() {
		if (qs("#sbn-styles")) return;
		const s = mk("style");
		s.id = "sbn-styles";
		s.textContent = `
/* ── Bottom Nav ──────────────────────────────────── */
#stylo-bottom-nav {
	display: none;
	position: fixed; bottom: 0; left: 0; right: 0; z-index: 10000;
	height: 64px;
	padding-bottom: env(safe-area-inset-bottom, 0px);
	box-sizing: content-box;
	background: rgba(255,255,255,0.94);
	backdrop-filter: blur(24px) saturate(1.6);
	-webkit-backdrop-filter: blur(24px) saturate(1.6);
	border-top: 1px solid rgba(0,0,0,0.07);
	box-shadow: 0 -2px 20px rgba(0,0,0,0.07);
	align-items: stretch;
	justify-content: space-evenly;
}
[data-theme="dark"] #stylo-bottom-nav {
	background: rgba(18,18,22,0.94);
	border-top: 1px solid rgba(255,255,255,0.07);
}
@media (max-width: 768px) {
	#stylo-bottom-nav { display: flex; }
	#page-desktop .desktop-navbar,
	#page-desktop .navbar-container { display: none !important; }
	.desktop-wrapper > .desktop-container { padding-bottom: 88px !important; }
	#brain-bubble { display: none !important; }
	.page-container { padding-bottom: 72px !important; }
	#brain-panel { width:100vw !important; right:-100vw !important;
		height:100dvh !important; border-radius:0 !important; border-left:none !important; }
	#brain-panel.brain-panel-open { right:0 !important; }
}

/* ── Nav items ───────────────────────────────────── */
.sbn-item {
	flex: 1; display: flex; flex-direction: column;
	align-items: center; justify-content: center; gap: 3px;
	background: none; border: none; cursor: pointer; padding: 0;
	color: #6e6e73; transition: color .15s;
	-webkit-tap-highlight-color: transparent;
	min-width: 0; height: 100%; position: relative;
}
.sbn-item:active { opacity: .65; }
.sbn-item svg { width: 22px; height: 22px; stroke: currentColor; display: block; flex-shrink: 0; }
.sbn-label { font-size: 10px; font-weight: 600; letter-spacing: .01em; line-height: 1; white-space: nowrap; }
[data-theme="dark"] .sbn-item { color: #8e8e93; }
.sbn-item.sbn-active, .sbn-item:hover { color: #0FBF7F; }

/* brAIn centre pill */
.sbn-brain { flex: 1; display: flex; flex-direction: column; align-items: center;
	justify-content: flex-end; padding-bottom: 8px; min-width: 0; height: 100%; }
.sbn-brain-btn { display: flex; flex-direction: column; align-items: center; gap: 4px;
	background: none; border: none; cursor: pointer; padding: 0;
	-webkit-tap-highlight-color: transparent; transform: translateY(-16px); }
.sbn-brain-pill { width: 54px; height: 54px; border-radius: 50%;
	background: linear-gradient(135deg,#0FBF7F 0%,#0DA870 100%);
	box-shadow: 0 6px 24px rgba(15,191,127,.5);
	display: flex; align-items: center; justify-content: center;
	transition: transform .15s, box-shadow .15s; }
.sbn-brain-pill:active { transform: scale(.92); }
.sbn-brain-pill svg { width: 26px; height: 26px; stroke: #fff; }
.sbn-brain-btn .sbn-label { color: #0FBF7F; font-size: 10px; }

/* Badge */
.sbn-badge {
	position: absolute; top: 8px; right: calc(50% - 20px);
	min-width: 16px; height: 16px; border-radius: 8px; padding: 0 3px;
	background: #ef4444; border: 2px solid #fff;
	font-size: 9px; font-weight: 700; color: #fff;
	display: none; align-items: center; justify-content: center; line-height: 1;
}
.sbn-badge.visible { display: flex; }
[data-theme="dark"] .sbn-badge { border-color: #18181b; }

/* ── Full-screen panels ──────────────────────────── */
.sbn-panel {
	position: fixed; inset: 0; z-index: 9998;
	background: var(--bg-color, #f4f9f6);
	display: flex; flex-direction: column;
	transform: translateX(100%);
	transition: transform .28s cubic-bezier(.4,0,.2,1);
	padding-bottom: calc(64px + env(safe-area-inset-bottom, 0px));
}
.sbn-panel.sbn-panel-open { transform: translateX(0); }
[data-theme="dark"] .sbn-panel { background: #0f0f13; }

/* Panel header */
.sbn-panel-header {
	display: flex; align-items: center; gap: 12px;
	padding: 14px 16px 10px;
	padding-top: calc(14px + env(safe-area-inset-top, 0px));
	background: rgba(255,255,255,0.9);
	backdrop-filter: blur(16px);
	border-bottom: 1px solid rgba(0,0,0,0.07);
	position: sticky; top: 0; z-index: 2; flex-shrink: 0;
}
[data-theme="dark"] .sbn-panel-header {
	background: rgba(18,18,22,0.9); border-bottom-color: rgba(255,255,255,0.07); }
.sbn-panel-back {
	width: 34px; height: 34px; border-radius: 50%; border: none; cursor: pointer;
	background: rgba(0,0,0,0.06); display: flex; align-items: center; justify-content: center;
	flex-shrink: 0; -webkit-tap-highlight-color: transparent; color: inherit;
}
[data-theme="dark"] .sbn-panel-back { background: rgba(255,255,255,0.08); }
.sbn-panel-title { font-size: 17px; font-weight: 700; flex: 1; }
.sbn-panel-body { flex: 1; overflow-y: auto; padding: 14px; }

/* ── Cards & shared components ───────────────────── */
.sbn-card {
	background: #fff; border-radius: 16px;
	box-shadow: 0 2px 12px rgba(0,0,0,0.06);
	margin-bottom: 12px; overflow: hidden;
}
[data-theme="dark"] .sbn-card { background: #1c1c22; }
.sbn-card-body { padding: 14px 16px; }
.sbn-section-title {
	font-size: 11px; font-weight: 700; letter-spacing: .06em;
	text-transform: uppercase; color: #6e6e73; margin: 16px 0 8px;
}

/* Stat row */
.sbn-stats { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
.sbn-stat {
	background: #fff; border-radius: 16px; padding: 14px;
	box-shadow: 0 2px 10px rgba(0,0,0,0.05);
	display: flex; flex-direction: column; gap: 4px;
}
[data-theme="dark"] .sbn-stat { background: #1c1c22; }
.sbn-stat-val { font-size: 24px; font-weight: 700; color: #0FBF7F; }
.sbn-stat-lbl { font-size: 11px; color: #6e6e73; font-weight: 500; }

/* Approval card */
.sbn-appr-card {
	background: #fff; border-radius: 16px; padding: 14px 16px;
	box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 10px;
	border-left: 4px solid #0FBF7F;
}
[data-theme="dark"] .sbn-appr-card { background: #1c1c22; }
.sbn-appr-type { font-size: 9px; font-weight: 700; letter-spacing: .06em;
	text-transform: uppercase; color: #0FBF7F; margin-bottom: 4px; }
.sbn-appr-name { font-size: 14px; font-weight: 600; margin-bottom: 2px; }
.sbn-appr-meta { font-size: 12px; color: #6e6e73; margin-bottom: 10px; }
.sbn-appr-actions { display: flex; gap: 8px; }

/* Buttons */
.sbn-btn {
	flex: 1; padding: 9px; border-radius: 10px; border: none;
	font-size: 13px; font-weight: 600; cursor: pointer;
	-webkit-tap-highlight-color: transparent; transition: opacity .15s;
}
.sbn-btn:active { opacity: .7; }
.sbn-btn-approve { background: #0FBF7F; color: #fff; }
.sbn-btn-reject  { background: rgba(239,68,68,.1); color: #ef4444; }
.sbn-btn-primary { background: #0FBF7F; color: #fff; width: 100%; margin-top: 8px; }
.sbn-btn-outline {
	background: transparent; color: #0FBF7F;
	border: 1.5px solid #0FBF7F; width: 100%; margin-top: 8px;
}

/* Tabs */
.sbn-tabs { display: flex; background: rgba(0,0,0,0.04); border-radius: 12px;
	padding: 3px; margin-bottom: 14px; }
[data-theme="dark"] .sbn-tabs { background: rgba(255,255,255,0.06); }
.sbn-tab { flex: 1; padding: 7px; text-align: center; border: none; background: none;
	cursor: pointer; border-radius: 9px; font-size: 12px; font-weight: 600;
	color: #6e6e73; transition: all .18s; -webkit-tap-highlight-color: transparent; }
.sbn-tab.active { background: #fff; color: #0FBF7F;
	box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
[data-theme="dark"] .sbn-tab.active { background: #2a2a35; }

/* Leave balance pills */
.sbn-leave-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-bottom: 12px; }
.sbn-leave-pill { border-radius: 14px; padding: 12px 8px; text-align: center;
	background: rgba(15,191,127,0.08); }
.sbn-leave-pill-val { font-size: 20px; font-weight: 700; color: #0FBF7F; }
.sbn-leave-pill-lbl { font-size: 10px; color: #6e6e73; font-weight: 500; margin-top: 2px; }

/* Loading skeleton */
.sbn-skeleton { border-radius: 10px; background: linear-gradient(90deg,#f0f0f0 25%,#e0e0e0 50%,#f0f0f0 75%);
	background-size: 200% 100%; animation: sbn-shimmer 1.4s infinite; }
[data-theme="dark"] .sbn-skeleton { background: linear-gradient(90deg,#1e1e28 25%,#252530 50%,#1e1e28 75%);
	background-size: 200% 100%; }
@keyframes sbn-shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
.sbn-skel-row { height: 80px; margin-bottom: 10px; }

/* Empty state */
.sbn-empty { text-align: center; padding: 48px 20px; color: #6e6e73; }
.sbn-empty-icon { font-size: 48px; margin-bottom: 12px; }
.sbn-empty-msg { font-size: 14px; font-weight: 500; }

/* Work quick links */
.sbn-quick-links { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 14px; }
.sbn-quick-link {
	background: #fff; border-radius: 16px; padding: 16px 14px;
	box-shadow: 0 2px 10px rgba(0,0,0,0.05); border: none; cursor: pointer;
	text-align: left; display: flex; flex-direction: column; gap: 8px;
	-webkit-tap-highlight-color: transparent; transition: transform .15s;
	text-decoration: none; color: inherit;
}
[data-theme="dark"] .sbn-quick-link { background: #1c1c22; }
.sbn-quick-link:active { transform: scale(.97); }
.sbn-quick-link-icon { width: 40px; height: 40px; border-radius: 12px;
	background: rgba(15,191,127,0.12); display: flex; align-items: center; justify-content: center; }
.sbn-quick-link-icon svg { width: 20px; height: 20px; stroke: #0FBF7F; }
.sbn-quick-link-lbl { font-size: 13px; font-weight: 600; }
.sbn-quick-link-sub { font-size: 11px; color: #6e6e73; }

/* Greeting */
.sbn-greeting { background: linear-gradient(135deg,#0FBF7F 0%,#0DA870 100%);
	border-radius: 20px; padding: 18px; margin-bottom: 14px; color: #fff; }
.sbn-greeting-sub { font-size: 12px; opacity: .8; margin-bottom: 4px; }
.sbn-greeting-name { font-size: 20px; font-weight: 700; }

/* Attendance badge */
.sbn-att-badge { display: inline-flex; align-items: center; gap: 6px;
	padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.sbn-att-present { background: rgba(15,191,127,.12); color: #0FBF7F; }
.sbn-att-absent  { background: rgba(239,68,68,.1);  color: #ef4444; }
.sbn-att-none    { background: rgba(110,110,115,.1); color: #6e6e73; }
		`;
		document.head.appendChild(s);
	}

	/* ═══════════════════════════════════════════════════════════
	   BOTTOM NAV
	══════════════════════════════════════════════════════════════ */
	function buildNav() {
		if (qs("#stylo-bottom-nav")) return;
		const nav = mk("div");
		nav.id = "stylo-bottom-nav";
		nav.innerHTML = `
		<button class="sbn-item" id="sbn-home" title="Home">
			<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/>
				<path d="M9 21V12h6v9"/>
			</svg>
			<span class="sbn-label">Home</span>
		</button>

		<button class="sbn-item" id="sbn-approvals" title="Approvals" style="position:relative">
			<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
			</svg>
			<span class="sbn-badge" id="sbn-appr-badge"></span>
			<span class="sbn-label">Approvals</span>
		</button>

		<div class="sbn-brain">
			<button class="sbn-brain-btn" id="sbn-brain" title="brAIn">
				<div class="sbn-brain-pill">
					<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M12 5a3 3 0 10-5.997.125 4 4 0 00-2.526 5.77 4 4 0 00.556 6.588A4 4 0 1012 18Z"/>
						<path d="M12 5a3 3 0 115.997.125 4 4 0 012.526 5.77 4 4 0 01-.556 6.588A4 4 0 1112 18Z"/>
						<path d="M15 13a4.5 4.5 0 01-3-4 4.5 4.5 0 01-3 4"/>
					</svg>
				</div>
				<span class="sbn-label">brAIn</span>
			</button>
		</div>

		<button class="sbn-item" id="sbn-work" title="Work">
			<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/>
			</svg>
			<span class="sbn-label">Work</span>
		</button>

		<button class="sbn-item" id="sbn-me" title="Me">
			<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
			</svg>
			<span class="sbn-label">Me</span>
		</button>`;
		document.body.appendChild(nav);
		wireNav();
		refreshApprovalBadge();
	}

	function wireNav() {
		qs("#sbn-home").onclick     = () => { closePanel(); frappe.set_route("desktop"); };
		qs("#sbn-approvals").onclick = () => openPanel("approvals");
		qs("#sbn-brain").onclick    = () => {
			const b = qs("#brain-bubble");
			b ? b.click() : frappe.set_route("app/brain-settings");
		};
		qs("#sbn-work").onclick = () => openPanel("work");
		qs("#sbn-me").onclick   = () => openPanel("me");
	}

	function setActiveTab(id) {
		document.querySelectorAll(".sbn-item").forEach(b => b.classList.remove("sbn-active"));
		const btn = qs(`#sbn-${id}`);
		if (btn) btn.classList.add("sbn-active");
	}

	/* ═══════════════════════════════════════════════════════════
	   PANEL SYSTEM
	══════════════════════════════════════════════════════════════ */
	function openPanel(id) {
		closePanel(false);
		activePanel = id;
		setActiveTab(id);

		let panel = qs(`#sbn-panel-${id}`);
		if (!panel) {
			panel = mk("div", "sbn-panel");
			panel.id = `sbn-panel-${id}`;
			document.body.appendChild(panel);
		}

		const titles = { approvals: "Approvals", work: "Work", me: "Me" };
		panel.innerHTML = `
			<div class="sbn-panel-header">
				<button class="sbn-panel-back" id="sbn-back-${id}">
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
						<path d="M15 18l-6-6 6-6"/>
					</svg>
				</button>
				<div class="sbn-panel-title">${titles[id]}</div>
			</div>
			<div class="sbn-panel-body" id="sbn-body-${id}">
				${skelRows(3)}
			</div>`;

		qs(`#sbn-back-${id}`).onclick = () => closePanel();

		requestAnimationFrame(() => {
			panel.classList.add("sbn-panel-open");
		});

		// Load content
		const loaders = { approvals: loadApprovals, work: loadWork, me: loadMe };
		loaders[id]();
	}

	function closePanel(resetTab = true) {
		if (!activePanel) return;
		const panel = qs(`#sbn-panel-${activePanel}`);
		if (panel) panel.classList.remove("sbn-panel-open");
		if (resetTab) {
			const isDesk = qs("#page-desktop");
			if (isDesk && isDesk.style.display !== "none") setActiveTab("home");
			else document.querySelectorAll(".sbn-item").forEach(b => b.classList.remove("sbn-active"));
		}
		activePanel = null;
	}

	function skelRows(n) {
		return Array(n).fill('<div class="sbn-skeleton sbn-skel-row"></div>').join("");
	}

	/* ═══════════════════════════════════════════════════════════
	   APPROVALS
	══════════════════════════════════════════════════════════════ */
	const APPROVAL_TYPES = [
		{
			doctype: "Leave Application",
			label: "Leave",
			filters: () => ({ status: "Open", docstatus: 1, leave_approver: frappe.session.user }),
			fields: ["name","employee_name","leave_type","from_date","to_date","total_leave_days"],
			summary: r => `${r.employee_name} · ${r.leave_type} · ${fmt(r.from_date)} – ${fmt(r.to_date)} (${r.total_leave_days} day${r.total_leave_days > 1 ? "s" : ""})`,
			approve: async (name) => frappe.db.set_value("Leave Application", name, "status", "Approved"),
			reject:  async (name) => frappe.db.set_value("Leave Application", name, "status", "Rejected"),
		},
		{
			doctype: "Expense Claim",
			label: "Expense",
			filters: () => ({ approval_status: "Submitted", docstatus: 1, expense_approver: frappe.session.user }),
			fields: ["name","employee_name","total_claimed_amount","expense_date","remark"],
			summary: r => `${r.employee_name} · ${currency(r.total_claimed_amount)} · ${fmt(r.expense_date)}`,
			approve: async (name) => frappe.db.set_value("Expense Claim", name, "approval_status", "Approved"),
			reject:  async (name) => frappe.db.set_value("Expense Claim", name, "approval_status", "Rejected"),
		},
		{
			doctype: "Purchase Order",
			label: "Purchase Order",
			filters: () => ({ docstatus: 0, status: ["not in", ["Cancelled"]] }),
			fields: ["name","supplier","grand_total","transaction_date"],
			summary: r => `${r.supplier} · ${currency(r.grand_total)} · ${fmt(r.transaction_date)}`,
			approve: async (name) => {
				await frappe.call({ method: "frappe.client.submit", args: { doc: { doctype: "Purchase Order", name } } });
			},
			reject: null,
		},
		{
			doctype: "Purchase Invoice",
			label: "Purchase Invoice",
			filters: () => ({ docstatus: 0 }),
			fields: ["name","supplier","grand_total","posting_date"],
			summary: r => `${r.supplier} · ${currency(r.grand_total)} · ${fmt(r.posting_date)}`,
			approve: async (name) => {
				await frappe.call({ method: "frappe.client.submit", args: { doc: { doctype: "Purchase Invoice", name } } });
			},
			reject: null,
		},
		{
			doctype: "Sales Order",
			label: "Sales Order",
			filters: () => ({ docstatus: 0, status: ["not in", ["Cancelled"]] }),
			fields: ["name","customer","grand_total","transaction_date"],
			summary: r => `${r.customer} · ${currency(r.grand_total)} · ${fmt(r.transaction_date)}`,
			approve: async (name) => {
				await frappe.call({ method: "frappe.client.submit", args: { doc: { doctype: "Sales Order", name } } });
			},
			reject: null,
		},
	];

	async function loadApprovals(filterType = "all") {
		const body = qs("#sbn-body-approvals");
		if (!body) return;
		body.innerHTML = tabsHTML(["all","leave","expense","purchase"], filterType) + skelRows(3);

		// Wire tab clicks
		body.querySelectorAll(".sbn-tab").forEach(t => {
			t.onclick = () => loadApprovals(t.dataset.tab);
		});

		let allItems = [];
		const activeTypes = filterType === "all" ? APPROVAL_TYPES :
			APPROVAL_TYPES.filter(t => t.label.toLowerCase().startsWith(filterType === "purchase" ? "purchase" : filterType));

		for (const type of activeTypes) {
			try {
				const rows = await frappe.db.get_list(type.doctype, {
					filters: type.filters(),
					fields: type.fields,
					limit: 20,
					order_by: "modified desc",
				});
				rows.forEach(r => allItems.push({ ...r, _type: type }));
			} catch (_) { /* doctype may not be installed */ }
		}

		// Update badge
		approvalBadgeCount = allItems.length;
		const badge = qs("#sbn-appr-badge");
		if (badge) {
			badge.textContent = approvalBadgeCount > 9 ? "9+" : approvalBadgeCount;
			badge.classList.toggle("visible", approvalBadgeCount > 0);
		}

		const listEl = mk("div");
		if (!allItems.length) {
			listEl.innerHTML = `<div class="sbn-empty"><div class="sbn-empty-icon">✅</div>
				<div class="sbn-empty-msg">All caught up! No pending approvals.</div></div>`;
		} else {
			allItems.forEach(item => listEl.appendChild(apprCard(item)));
		}

		body.innerHTML = tabsHTML(["all","leave","expense","purchase"], filterType);
		body.appendChild(listEl);
		body.querySelectorAll(".sbn-tab").forEach(t => {
			t.onclick = () => loadApprovals(t.dataset.tab);
		});
	}

	function tabsHTML(tabs, active) {
		return `<div class="sbn-tabs">${tabs.map(t =>
			`<button class="sbn-tab${t === active ? " active" : ""}" data-tab="${t}">
				${t.charAt(0).toUpperCase() + t.slice(1)}</button>`
		).join("")}</div>`;
	}

	function apprCard(item) {
		const type = item._type;
		const card = mk("div", "sbn-appr-card");
		const hasReject = !!type.reject;
		card.innerHTML = `
			<div class="sbn-appr-type">${type.label}</div>
			<div class="sbn-appr-name">${item.name}</div>
			<div class="sbn-appr-meta">${type.summary(item)}</div>
			<div class="sbn-appr-actions">
				<button class="sbn-btn sbn-btn-approve" data-action="approve">✓ Approve</button>
				${hasReject ? `<button class="sbn-btn sbn-btn-reject" data-action="reject">✗ Reject</button>` : ""}
			</div>`;

		card.querySelector("[data-action='approve']").onclick = async (e) => {
			e.target.disabled = true;
			e.target.textContent = "…";
			try {
				await type.approve(item.name);
				card.style.opacity = ".4";
				card.style.pointerEvents = "none";
				frappe.show_alert({ message: "Approved", indicator: "green" });
				approvalBadgeCount = Math.max(0, approvalBadgeCount - 1);
				const b = qs("#sbn-appr-badge");
				if (b) {
					b.textContent = approvalBadgeCount > 9 ? "9+" : approvalBadgeCount;
					b.classList.toggle("visible", approvalBadgeCount > 0);
				}
			} catch (err) {
				frappe.show_alert({ message: "Failed: " + (err.message || err), indicator: "red" });
				e.target.disabled = false;
				e.target.textContent = "✓ Approve";
			}
		};

		if (hasReject) {
			card.querySelector("[data-action='reject']").onclick = async (e) => {
				e.target.disabled = true;
				e.target.textContent = "…";
				try {
					await type.reject(item.name);
					card.style.opacity = ".4";
					card.style.pointerEvents = "none";
					frappe.show_alert({ message: "Rejected", indicator: "orange" });
				} catch (err) {
					frappe.show_alert({ message: "Failed: " + (err.message || err), indicator: "red" });
					e.target.disabled = false;
					e.target.textContent = "✗ Reject";
				}
			};
		}
		return card;
	}

	async function refreshApprovalBadge() {
		try {
			let total = 0;
			for (const type of APPROVAL_TYPES.slice(0, 2)) { // leave + expense only for badge
				const rows = await frappe.db.get_list(type.doctype, {
					filters: type.filters(), fields: ["name"], limit: 20 });
				total += rows.length;
			}
			approvalBadgeCount = total;
			const b = qs("#sbn-appr-badge");
			if (b) {
				b.textContent = total > 9 ? "9+" : total;
				b.classList.toggle("visible", total > 0);
			}
		} catch (_) {}
	}

	/* ═══════════════════════════════════════════════════════════
	   WORK — CRM + EXPENSES
	══════════════════════════════════════════════════════════════ */
	async function loadWork(tab = "crm") {
		const body = qs("#sbn-body-work");
		if (!body) return;

		body.innerHTML = tabsHTML(["crm","expenses"], tab);
		body.querySelectorAll(".sbn-tab").forEach(t => {
			t.onclick = () => loadWork(t.dataset.tab);
		});

		if (tab === "crm") {
			await loadCRM(body);
		} else {
			await loadExpenses(body);
		}
	}

	async function loadCRM(body) {
		const wrap = mk("div");
		wrap.innerHTML = skelRows(2);
		body.appendChild(wrap);

		// Quick links
		const links = mk("div");
		links.innerHTML = `
			<div class="sbn-quick-links">
				<a class="sbn-quick-link" href="/crm" target="_self">
					<div class="sbn-quick-link-icon">
						<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round">
							<path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
							<circle cx="9" cy="7" r="4"/>
							<path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/>
						</svg>
					</div>
					<div class="sbn-quick-link-lbl">Open CRM</div>
					<div class="sbn-quick-link-sub">Leads & Deals</div>
				</a>
				<a class="sbn-quick-link" href="/crm/leads/new-lead-1" target="_self">
					<div class="sbn-quick-link-icon">
						<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round">
							<circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/>
						</svg>
					</div>
					<div class="sbn-quick-link-lbl">New Lead</div>
					<div class="sbn-quick-link-sub">Add quickly</div>
				</a>
			</div>`;

		// Fetch open leads count
		let leadsCount = "—", dealsCount = "—";
		try {
			const leads = await frappe.db.get_list("CRM Lead",
				{ filters: { status: ["not in", ["Qualified","Junk","Lost"]] }, fields: ["name"], limit: 99 });
			leadsCount = leads.length;
		} catch (_) {}
		try {
			const deals = await frappe.db.get_list("CRM Deal",
				{ filters: { status: ["not in", ["Won","Lost"]] }, fields: ["name"], limit: 99 });
			dealsCount = deals.length;
		} catch (_) {}

		links.innerHTML += `
			<div class="sbn-stats">
				<div class="sbn-stat"><div class="sbn-stat-val">${leadsCount}</div><div class="sbn-stat-lbl">Open Leads</div></div>
				<div class="sbn-stat"><div class="sbn-stat-val">${dealsCount}</div><div class="sbn-stat-lbl">Open Deals</div></div>
			</div>`;

		// Recent leads
		let recentLeads = [];
		try {
			recentLeads = await frappe.db.get_list("CRM Lead", {
				filters: { status: ["not in", ["Qualified","Junk","Lost"]] },
				fields: ["name","lead_name","status","lead_owner","mobile_no"],
				limit: 10, order_by: "modified desc",
			});
		} catch (_) {}

		if (recentLeads.length) {
			links.innerHTML += `<div class="sbn-section-title">Recent Leads</div>`;
			recentLeads.forEach(l => {
				links.innerHTML += `
					<div class="sbn-appr-card" style="border-left-color:#6366f1;cursor:pointer"
						onclick="window.location='/crm/leads/${l.name}'">
						<div class="sbn-appr-type" style="color:#6366f1">${l.status || "New"}</div>
						<div class="sbn-appr-name">${l.lead_name || l.name}</div>
						<div class="sbn-appr-meta">${l.mobile_no || "No phone"} · ${l.lead_owner || ""}</div>
					</div>`;
			});
		}

		wrap.replaceWith(links);
	}

	async function loadExpenses(body) {
		const wrap = mk("div");
		wrap.innerHTML = skelRows(2);
		body.appendChild(wrap);

		// Find current employee
		let empId = null;
		try {
			const emp = await frappe.db.get_list("Employee",
				{ filters: { user_id: frappe.session.user, status: "Active" }, fields: ["name"], limit: 1 });
			if (emp.length) empId = emp[0].name;
		} catch (_) {}

		const cont = mk("div");
		cont.innerHTML = `
			<button class="sbn-btn sbn-btn-primary" onclick="frappe.set_route('Form','Expense Claim','new-expense-claim-1')">
				+ New Expense Claim
			</button>`;

		// My open claims
		let claims = [];
		try {
			const filters = empId
				? { employee: empId, docstatus: ["<", 2] }
				: { owner: frappe.session.user, docstatus: ["<", 2] };
			claims = await frappe.db.get_list("Expense Claim", {
				filters, fields: ["name","total_claimed_amount","approval_status","posting_date","remark"],
				limit: 15, order_by: "modified desc",
			});
		} catch (_) {}

		if (claims.length) {
			cont.innerHTML += `<div class="sbn-section-title">My Claims</div>`;
			const statusColor = { Approved: "#0FBF7F", Rejected: "#ef4444", Submitted: "#f59e0b", Draft: "#6e6e73" };
			claims.forEach(c => {
				const col = statusColor[c.approval_status] || "#6e6e73";
				cont.innerHTML += `
					<div class="sbn-appr-card" style="border-left-color:${col};cursor:pointer"
						onclick="frappe.set_route('Form','Expense Claim','${c.name}')">
						<div class="sbn-appr-type" style="color:${col}">${c.approval_status}</div>
						<div class="sbn-appr-name">${c.name}</div>
						<div class="sbn-appr-meta">${currency(c.total_claimed_amount)} · ${fmt(c.posting_date)}</div>
					</div>`;
			});
		} else {
			cont.innerHTML += `<div class="sbn-empty"><div class="sbn-empty-icon">🧾</div>
				<div class="sbn-empty-msg">No expense claims yet.</div></div>`;
		}

		wrap.replaceWith(cont);
	}

	/* ═══════════════════════════════════════════════════════════
	   ME — HRMS
	══════════════════════════════════════════════════════════════ */
	async function loadMe() {
		const body = qs("#sbn-body-me");
		if (!body) return;

		// Find employee
		let emp = null;
		try {
			const rows = await frappe.db.get_list("Employee",
				{ filters: { user_id: frappe.session.user, status: "Active" },
				  fields: ["name","employee_name","designation","department","date_of_joining"],
				  limit: 1 });
			if (rows.length) emp = rows[0];
		} catch (_) {}

		const cont = mk("div");

		// Profile card
		const name = emp ? emp.employee_name : (frappe.session.user_fullname || frappe.session.user);
		const desig = emp ? (emp.designation || "") : "";
		cont.innerHTML = `
			<div class="sbn-greeting">
				<div class="sbn-greeting-sub">Signed in as</div>
				<div class="sbn-greeting-name">${name}</div>
				${desig ? `<div style="font-size:13px;opacity:.85;margin-top:2px">${desig}</div>` : ""}
			</div>`;

		// Attendance today
		let attStatus = null;
		if (emp) {
			try {
				const att = await frappe.db.get_list("Attendance", {
					filters: { employee: emp.name, attendance_date: today() },
					fields: ["status"], limit: 1 });
				if (att.length) attStatus = att[0].status;
			} catch (_) {}
		}

		const attCls = attStatus === "Present" ? "sbn-att-present" :
					   attStatus === "Absent"  ? "sbn-att-absent"  : "sbn-att-none";
		const attLabel = attStatus || "Not marked";
		cont.innerHTML += `
			<div class="sbn-section-title">Today's Attendance</div>
			<div class="sbn-card">
				<div class="sbn-card-body" style="display:flex;align-items:center;justify-content:space-between">
					<span class="sbn-att-badge ${attCls}">${attLabel}</span>
					${emp && !attStatus ? `<button class="sbn-btn sbn-btn-approve" style="flex:0;padding:8px 16px"
						id="sbn-mark-att">Mark Present</button>` : ""}
				</div>
			</div>`;

		body.innerHTML = "";
		body.appendChild(cont);

		if (emp && !attStatus) {
			const markBtn = qs("#sbn-mark-att");
			if (markBtn) markBtn.onclick = () => markAttendance(emp.name, body);
		}

		// Leave balance
		if (emp) {
			const leaveWrap = mk("div");
			leaveWrap.innerHTML = `<div class="sbn-section-title">Leave Balance</div>` + skelRows(1);
			body.appendChild(leaveWrap);
			loadLeaveBalance(emp.name, leaveWrap);
		}

		// Leave applications
		const leaveSection = mk("div");
		leaveSection.innerHTML = `<div class="sbn-section-title">My Leave Requests</div>`;
		if (emp) {
			try {
				const leaves = await frappe.db.get_list("Leave Application", {
					filters: { employee: emp.name, docstatus: ["<", 2] },
					fields: ["name","leave_type","from_date","to_date","status","total_leave_days"],
					limit: 10, order_by: "from_date desc",
				});
				if (leaves.length) {
					const colMap = { Approved: "#0FBF7F", Rejected: "#ef4444", Open: "#f59e0b" };
					leaves.forEach(l => {
						const col = colMap[l.status] || "#6e6e73";
						leaveSection.innerHTML += `
							<div class="sbn-appr-card" style="border-left-color:${col};cursor:pointer"
								onclick="frappe.set_route('Form','Leave Application','${l.name}')">
								<div class="sbn-appr-type" style="color:${col}">${l.status}</div>
								<div class="sbn-appr-name">${l.leave_type}</div>
								<div class="sbn-appr-meta">${fmt(l.from_date)} – ${fmt(l.to_date)} · ${l.total_leave_days} day(s)</div>
							</div>`;
					});
				} else {
					leaveSection.innerHTML += `<div class="sbn-empty"><div class="sbn-empty-icon">🌴</div>
						<div class="sbn-empty-msg">No leave requests.</div></div>`;
				}
			} catch (_) {}
		}

		leaveSection.innerHTML += `
			<button class="sbn-btn sbn-btn-primary"
				onclick="frappe.set_route('Form','Leave Application','new-leave-application-1')">
				+ Apply for Leave
			</button>`;
		body.appendChild(leaveSection);

		// Latest payslip
		if (emp) {
			const paySection = mk("div");
			paySection.innerHTML = `<div class="sbn-section-title">Latest Payslip</div>`;
			try {
				const slips = await frappe.db.get_list("Salary Slip", {
					filters: { employee: emp.name, docstatus: 1 },
					fields: ["name","start_date","end_date","net_pay"],
					limit: 1, order_by: "start_date desc",
				});
				if (slips.length) {
					const slip = slips[0];
					paySection.innerHTML += `
						<div class="sbn-appr-card" style="border-left-color:#0FBF7F;cursor:pointer"
							onclick="frappe.set_route('Form','Salary Slip','${slip.name}')">
							<div class="sbn-appr-type" style="color:#0FBF7F">Salary Slip</div>
							<div class="sbn-appr-name">${currency(slip.net_pay)}</div>
							<div class="sbn-appr-meta">${fmt(slip.start_date)} – ${fmt(slip.end_date)}</div>
						</div>`;
				} else {
					paySection.innerHTML += `<div class="sbn-empty" style="padding:20px 0">
						<div class="sbn-empty-msg">No payslips yet.</div></div>`;
				}
			} catch (_) {}
			body.appendChild(paySection);
		}

		// Profile link
		body.appendChild(mk("div")).innerHTML = `
			<button class="sbn-btn sbn-btn-outline"
				onclick="frappe.set_route('Form','User','${frappe.session.user}')">
				Edit Profile
			</button>`;
	}

	async function loadLeaveBalance(empId, container) {
		const leaveTypes = ["Casual Leave", "Sick Leave", "Earned Leave", "Privilege Leave"];
		const balances = [];
		for (const lt of leaveTypes) {
			try {
				const r = await frappe.call({
					method: "hrms.hr.doctype.leave_application.leave_application.get_leave_balance_on",
					args: { employee: empId, date: today(), leave_type: lt },
				});
				if (r.message !== undefined) balances.push({ type: lt, balance: r.message });
			} catch (_) {}
		}

		if (!balances.length) {
			container.innerHTML = `<div class="sbn-section-title">Leave Balance</div>
				<div style="color:#6e6e73;font-size:13px;padding:8px 0">No leave allocations found.</div>`;
			return;
		}

		const pills = balances.map(b => `
			<div class="sbn-leave-pill">
				<div class="sbn-leave-pill-val">${b.balance}</div>
				<div class="sbn-leave-pill-lbl">${b.type.replace(" Leave","")}</div>
			</div>`).join("");

		container.innerHTML = `<div class="sbn-section-title">Leave Balance</div>
			<div class="sbn-leave-grid">${pills}</div>`;
	}

	async function markAttendance(empId, body) {
		const btn = qs("#sbn-mark-att");
		if (btn) { btn.disabled = true; btn.textContent = "Marking…"; }
		try {
			await frappe.db.insert({
				doctype: "Attendance",
				employee: empId,
				attendance_date: today(),
				status: "Present",
				docstatus: 1,
			});
			frappe.show_alert({ message: "Attendance marked ✓", indicator: "green" });
			// Refresh Me panel
			loadMe();
		} catch (err) {
			frappe.show_alert({ message: "Could not mark: " + (err.message || err), indicator: "red" });
			if (btn) { btn.disabled = false; btn.textContent = "Mark Present"; }
		}
	}

	/* ═══════════════════════════════════════════════════════════
	   INIT
	══════════════════════════════════════════════════════════════ */
	function isDesktopPage() {
		const p = qs("#page-desktop");
		return p && p.style.display !== "none" && !p.classList.contains("hidden");
	}

	function syncActiveTab() {
		if (!activePanel && isDesktopPage()) setActiveTab("home");
	}

	function init() {
		injectStyles();
		if (!isMobile()) return;
		buildNav();
		syncActiveTab();
	}

	$(document).on("page-change", () => {
		if (!isMobile()) return;
		if (!qs("#stylo-bottom-nav")) { injectStyles(); buildNav(); }
		// Close panel when Frappe navigates internally
		if (activePanel) closePanel();
		syncActiveTab();
	});

	$(document).ready(() => setTimeout(init, 400));

	window.addEventListener("resize", () => {
		if (isMobile() && !qs("#stylo-bottom-nav")) init();
		else if (!isMobile() && qs("#stylo-bottom-nav")) {
			qs("#stylo-bottom-nav").remove();
			document.querySelectorAll(".sbn-panel").forEach(p => p.remove());
		}
	});

	// Refresh badge every 2 minutes
	setInterval(() => { if (isMobile()) refreshApprovalBadge(); }, 120000);
})();
