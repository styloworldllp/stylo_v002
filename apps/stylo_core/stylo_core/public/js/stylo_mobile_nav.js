/**
 * stylo_mobile_nav.js
 * Bottom navigation bar for mobile — only injected on the desktop home page.
 * Layout: Stylo | Notifications | brAIn | Theme | Profile
 */

(function () {
	"use strict";

	const MOBILE_BP = 768;

	function isMobile() {
		return window.innerWidth <= MOBILE_BP;
	}

	// SVG icons (inline, no external request)
	const ICONS = {
		home: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/>
			<path d="M9 21V12h6v9"/>
		</svg>`,
		bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
			<path d="M13.73 21a2 2 0 01-3.46 0"/>
		</svg>`,
		brain: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d="M12 5a3 3 0 10-5.997.125 4 4 0 00-2.526 5.77 4 4 0 00.556 6.588A4 4 0 1012 18Z"/>
			<path d="M12 5a3 3 0 115.997.125 4 4 0 012.526 5.77 4 4 0 01-.556 6.588A4 4 0 1112 18Z"/>
			<path d="M15 13a4.5 4.5 0 01-3-4 4.5 4.5 0 01-3 4"/>
			<path d="M17.599 6.5a3 3 0 00.399-1.375"/>
			<path d="M6.003 5.125A3 3 0 006.401 6.5"/>
			<path d="M3.477 10.896a4 4 0 01.585-.396"/>
			<path d="M19.938 10.5a4 4 0 01.585.396"/>
			<path d="M6 18a4 4 0 01-1.967-.516"/>
			<path d="M19.967 17.484A4 4 0 0118 18"/>
		</svg>`,
		sun: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<circle cx="12" cy="12" r="4"/>
			<path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>
		</svg>`,
		moon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
		</svg>`,
		user: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<circle cx="12" cy="8" r="4"/>
			<path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
		</svg>`,
	};

	function getThemeIcon() {
		const isDark = document.documentElement.getAttribute("data-theme") === "dark";
		return isDark ? ICONS.moon : ICONS.sun;
	}

	function injectStyles() {
		if (document.getElementById("sbn-styles")) return;
		const style = document.createElement("style");
		style.id = "sbn-styles";
		style.textContent = `
/* ── Stylo Mobile Bottom Nav ─────────────────────────────── */
#stylo-bottom-nav {
	display: none;
	position: fixed;
	bottom: 0;
	left: 0;
	right: 0;
	z-index: 10000;
	height: 60px;
	padding-bottom: env(safe-area-inset-bottom, 0px);
	background: rgba(255, 255, 255, 0.88);
	backdrop-filter: blur(20px) saturate(1.5);
	-webkit-backdrop-filter: blur(20px) saturate(1.5);
	border-top: 1px solid rgba(0, 0, 0, 0.08);
	box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.08);
	align-items: center;
	justify-content: space-around;
}
[data-theme="dark"] #stylo-bottom-nav {
	background: rgba(18, 18, 22, 0.90);
	border-top: 1px solid rgba(255, 255, 255, 0.08);
	box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.4);
}
@media (max-width: 768px) {
	#stylo-bottom-nav { display: flex; }
	/* Hide top navbar on desktop home page */
	#page-desktop .desktop-navbar,
	#page-desktop .navbar-container { display: none !important; }
	/* Give the icon grid room above the bottom nav */
	#page-desktop .desktop-container,
	.desktop-wrapper > .desktop-container { padding-bottom: 80px !important; }
	/* Move brAIn floating bubble away — bottom nav handles it */
	#brain-bubble { display: none !important; }
}

/* ── Nav items ─────────────────────────────────────────────── */
.sbn-item {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 3px;
	flex: 1;
	background: none;
	border: none;
	cursor: pointer;
	padding: 6px 4px;
	color: #6e6e73;
	transition: color 0.15s;
	-webkit-tap-highlight-color: transparent;
	text-decoration: none;
}
.sbn-item:active { opacity: 0.7; }
.sbn-item svg {
	width: 22px;
	height: 22px;
	stroke: currentColor;
	display: block;
}
.sbn-label {
	font-size: 9px;
	font-weight: 600;
	letter-spacing: 0.02em;
	line-height: 1;
}
[data-theme="dark"] .sbn-item { color: #8e8e93; }
.sbn-item:hover,
.sbn-item.active { color: #0FBF7F; }
[data-theme="dark"] .sbn-item:hover,
[data-theme="dark"] .sbn-item.active { color: #0FBF7F; }

/* ── brAIn center button ───────────────────────────────────── */
.sbn-brain {
	flex: 1.2;
	position: relative;
	top: -10px;
}
.sbn-brain-btn {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 3px;
	background: none;
	border: none;
	cursor: pointer;
	padding: 0;
	-webkit-tap-highlight-color: transparent;
}
.sbn-brain-pill {
	width: 52px;
	height: 52px;
	border-radius: 50%;
	background: linear-gradient(135deg, #0FBF7F 0%, #0DA870 100%);
	box-shadow: 0 4px 20px rgba(15, 191, 127, 0.45);
	display: flex;
	align-items: center;
	justify-content: center;
	transition: transform 0.15s, box-shadow 0.15s;
}
.sbn-brain-pill:active {
	transform: scale(0.94);
	box-shadow: 0 2px 10px rgba(15, 191, 127, 0.35);
}
.sbn-brain-pill svg {
	width: 24px;
	height: 24px;
	stroke: #fff;
}
.sbn-brain-btn .sbn-label {
	color: #0FBF7F;
	margin-top: 2px;
}
/* Notification badge on bell */
.sbn-badge {
	position: absolute;
	top: 2px;
	right: calc(50% - 18px);
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: #ef4444;
	border: 1.5px solid #fff;
	display: none;
}
[data-theme="dark"] .sbn-badge { border-color: #18181b; }
.sbn-badge.visible { display: block; }
		`;
		document.head.appendChild(style);
	}

	function buildNav() {
		if (document.getElementById("stylo-bottom-nav")) return;

		const nav = document.createElement("div");
		nav.id = "stylo-bottom-nav";

		nav.innerHTML = `
			<button class="sbn-item" id="sbn-home" title="Home">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1H4a1 1 0 01-1-1V9.5z"/>
					<path d="M9 21V12h6v9"/>
				</svg>
				<span class="sbn-label">Home</span>
			</button>

			<button class="sbn-item sbn-notif-item" id="sbn-notif" title="Notifications" style="position:relative">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
					<path d="M13.73 21a2 2 0 01-3.46 0"/>
				</svg>
				<span class="sbn-badge" id="sbn-notif-badge"></span>
				<span class="sbn-label">Alerts</span>
			</button>

			<div class="sbn-brain">
				<button class="sbn-brain-btn" id="sbn-brain" title="brAIn">
					<div class="sbn-brain-pill">
						<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
							<path d="M12 5a3 3 0 10-5.997.125 4 4 0 00-2.526 5.77 4 4 0 00.556 6.588A4 4 0 1012 18Z"/>
							<path d="M12 5a3 3 0 115.997.125 4 4 0 012.526 5.77 4 4 0 01-.556 6.588A4 4 0 1112 18Z"/>
							<path d="M15 13a4.5 4.5 0 01-3-4 4.5 4.5 0 01-3 4"/>
						</svg>
					</div>
					<span class="sbn-label">brAIn</span>
				</button>
			</div>

			<button class="sbn-item" id="sbn-theme" title="Toggle theme">
				<span id="sbn-theme-icon">${getThemeIcon()}</span>
				<span class="sbn-label" id="sbn-theme-label">${document.documentElement.getAttribute("data-theme") === "dark" ? "Dark" : "Light"}</span>
			</button>

			<button class="sbn-item" id="sbn-profile" title="Profile">
				<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
					<circle cx="12" cy="8" r="4"/>
					<path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
				</svg>
				<span class="sbn-label">Profile</span>
			</button>
		`;

		document.body.appendChild(nav);
		wireHandlers();
		pollNotifications();
	}

	function wireHandlers() {
		// Home — go to desktop
		document.getElementById("sbn-home").addEventListener("click", () => {
			frappe.set_route("desktop");
		});

		// Notifications — trigger the bell in the real navbar
		document.getElementById("sbn-notif").addEventListener("click", () => {
			const bell = document.querySelector(
				".navbar .notifications-icon, .navbar [data-toggle='dropdown'] .icon-bell, #navbar-notifications"
			);
			if (bell) {
				bell.click();
			} else {
				frappe.set_route("notifications");
			}
		});

		// brAIn — open brain panel
		document.getElementById("sbn-brain").addEventListener("click", () => {
			const bubble = document.getElementById("brain-bubble");
			if (bubble) {
				bubble.click();
			} else {
				frappe.set_route("app/brain-settings");
			}
		});

		// Theme toggle
		document.getElementById("sbn-theme").addEventListener("click", () => {
			const current = document.documentElement.getAttribute("data-theme") || "light";
			const next = current === "dark" ? "light" : "dark";
			// Trigger Frappe's theme toggle if available
			if (frappe.ui && frappe.ui.set_theme) {
				frappe.ui.set_theme(next);
			} else {
				document.documentElement.setAttribute("data-theme", next);
				localStorage.setItem("theme", next);
			}
			// Update icon + label
			setTimeout(() => {
				const isDark = document.documentElement.getAttribute("data-theme") === "dark";
				document.getElementById("sbn-theme-icon").innerHTML = isDark ? ICONS.moon : ICONS.sun;
				document.getElementById("sbn-theme-label").textContent = isDark ? "Dark" : "Light";
			}, 50);
		});

		// Profile — open user dropdown or navigate to profile
		document.getElementById("sbn-profile").addEventListener("click", () => {
			const dropdown = document.querySelector(
				".navbar .user-avatar, .navbar .navbar-user, #navbar-user .dropdown-toggle, .avatar.avatar-small"
			);
			if (dropdown) {
				dropdown.closest("[data-toggle='dropdown'], .dropdown")
					? dropdown.closest("[data-toggle='dropdown'], .dropdown").querySelector("[data-toggle='dropdown']")?.click()
					: dropdown.click();
			} else {
				frappe.set_route("Form/User/" + frappe.session.user);
			}
		});
	}

	function pollNotifications() {
		function checkBadge() {
			const badge = document.getElementById("sbn-notif-badge");
			if (!badge) return;
			// Check if Frappe's notification count is >0
			const count =
				frappe.notification_count ||
				parseInt(document.querySelector(".notifications-count, .badge-notifications")?.textContent || "0");
			badge.classList.toggle("visible", count > 0);
		}
		checkBadge();
		setInterval(checkBadge, 10000);
	}

	function init() {
		// Only run on the desktop home page
		if (!document.getElementById("page-desktop")) return;
		injectStyles();
		if (isMobile()) buildNav();
	}

	// Run on page load and when Frappe navigates
	$(document).on("page-change", function () {
		// Remove old nav when leaving desktop page
		if (!document.getElementById("page-desktop")) {
			const nav = document.getElementById("stylo-bottom-nav");
			if (nav) nav.remove();
			return;
		}
		init();
	});

	// Also run on initial load
	$(document).ready(function () {
		setTimeout(init, 300);
	});

	// Re-check on resize
	window.addEventListener("resize", () => {
		if (!document.getElementById("page-desktop")) return;
		if (isMobile() && !document.getElementById("stylo-bottom-nav")) {
			injectStyles();
			buildNav();
		} else if (!isMobile()) {
			const nav = document.getElementById("stylo-bottom-nav");
			if (nav) nav.remove();
		}
	});
})();
