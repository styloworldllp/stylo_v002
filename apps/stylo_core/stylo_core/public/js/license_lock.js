/**
 * license_lock.js — injected on every Frappe desk page.
 * If the site license has expired (past grace period), replaces the page
 * body with a lock screen. Administrator is exempt.
 */
frappe.ready(function () {
	if (frappe.session.user === "Administrator") return;

	frappe
		.call("stylo_core.user_license.get_site_license_info")
		.then(function (r) {
			const info = r.message || {};
			const status = info.status || "active";

			if (status === "expired" || status === "suspended") {
				_showLockScreen(status, info);
			} else if (status === "grace_period") {
				_showGraceBanner(info);
			}
		})
		.catch(function () {
			// Fail silently — never lock on API errors
		});
});

function _showLockScreen(status, info) {
	const msg =
		status === "suspended"
			? "This site has been suspended by Stylo."
			: "Your Stylo license has expired.";

	document.body.innerHTML = `
		<div style="
			display: flex;
			height: 100vh;
			align-items: center;
			justify-content: center;
			flex-direction: column;
			gap: 16px;
			background: #f4f5f7;
			font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
		">
			<img
				src="/assets/stylo_core/images/stylo-ring.png"
				style="width: 72px; opacity: 0.85;"
				alt="Stylo"
			/>
			<h2 style="margin: 0; color: #1a1a2e; font-size: 22px;">${msg}</h2>
			<p style="margin: 0; color: #6b7280; text-align: center; max-width: 380px;">
				Please contact your Stylo implementation consultant to renew your license
				and restore access.
			</p>
		</div>`;
}

function _showGraceBanner(info) {
	const graceEnd = info.grace_end_date || "";
	const banner = document.createElement("div");
	banner.id = "stylo-license-banner";
	banner.style.cssText = `
		position: fixed; top: 0; left: 0; right: 0; z-index: 9999;
		background: #f59e0b; color: #fff;
		padding: 8px 16px;
		display: flex; align-items: center; justify-content: center; gap: 8px;
		font-size: 13px; font-weight: 500;
	`;
	banner.innerHTML = `
		⚠ Your Stylo license has expired.
		${graceEnd ? `Grace period ends <b>${graceEnd}</b>.` : ""}
		Contact your consultant to renew.
		<button onclick="document.getElementById('stylo-license-banner').remove()"
			style="margin-left: 12px; background: rgba(255,255,255,0.25);
			border: none; color: #fff; padding: 2px 8px; border-radius: 4px; cursor: pointer;">
			✕
		</button>`;
	document.body.prepend(banner);
}
