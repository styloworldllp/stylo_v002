/* ── Stylo Migrator Dashboard ──────────────────────────────────────────────
   Mounts only on the /stylo-migrator page.
   Steps: 1 Connect → 2 Preview → 3 Migrate
   ──────────────────────────────────────────────────────────────────────── */
frappe.provide("stylo_migrator");

stylo_migrator.init = function () {
	const root = document.getElementById("stylo-migrator-root");
	if (!root) return;

	let state = {
		step:         1,    // 1=connect, 2=preview, 3=migrate
		job:          null,
		preview:      null,
		progress:     {},   // doctype → count
		pollTimer:    null,
		lastDoctype:  null, // track doctype changes to mark completed bars
	};

	/* ── Render skeleton ───────────────────────────────────────────────── */
	root.innerHTML = `
		<div class="smig-header">
			<div class="smig-header-icon">🗄️</div>
			<div>
				<h1>ERPNext v14 → v16 Migrator</h1>
				<p>Connect to your v14 database and migrate all data to this v16 site</p>
			</div>
		</div>
		<div class="smig-steps" id="smig-steps">
			<div class="smig-step active" data-step="1">1 · Connect</div>
			<div class="smig-step" data-step="2">2 · Preview</div>
			<div class="smig-step" data-step="3">3 · Migrate</div>
		</div>

		<div id="smig-step-1">
			<div class="smig-card">
				<h3>📡 v14 Database Connection</h3>
				<div class="smig-form-row">
					<div class="smig-field full">
						<label>v14 Site URL <span style="font-weight:400;opacity:.6">(auto-fills host &amp; port)</span></label>
						<input id="smig-site-url" placeholder="http://192.168.1.10:8000 or https://myoldsite.com"
							autocomplete="off" oninput="stylo_migrator.parseUrl(this.value)"/>
					</div>
				</div>
				<div class="smig-form-row">
					<div class="smig-field">
						<label>Host / IP</label>
						<input id="smig-host" placeholder="192.168.1.10" autocomplete="off"/>
					</div>
					<div class="smig-field">
						<label>DB Port</label>
						<input id="smig-port" type="number" value="3306"/>
					</div>
				</div>
				<div class="smig-form-row">
					<div class="smig-field">
						<label>DB User</label>
						<input id="smig-user" placeholder="root" autocomplete="off"/>
					</div>
					<div class="smig-field">
						<label>DB Password</label>
						<input id="smig-pass" type="password" autocomplete="off"/>
					</div>
				</div>
				<div class="smig-form-row">
					<div class="smig-field full">
						<label>Database Name</label>
						<input id="smig-db" placeholder="_5f3c2a... (Frappe DB name)" autocomplete="off"/>
					</div>
				</div>
				<div id="smig-conn-status" style="margin:8px 0;font-size:13px;min-height:20px;"></div>
				<div class="smig-btn-row">
					<button class="smig-btn smig-btn-secondary" onclick="stylo_migrator.testConn()">
						🔌 Test Connection
					</button>
					<button class="smig-btn smig-btn-primary" id="smig-goto-preview" disabled
						onclick="stylo_migrator.goPreview()">
						Preview Records →
					</button>
				</div>
			</div>
		</div>

		<div id="smig-step-2" class="smig-hidden">
			<div class="smig-card">
				<h3>📊 Record Counts in v14</h3>
				<p style="font-size:13px;opacity:.7;margin:-8px 0 16px">
					These records will be migrated. Review before starting.
				</p>
				<div id="smig-preview-body">
					<div class="smig-spinner"></div> Loading counts…
				</div>
			</div>

			<div class="smig-card" style="margin-top:16px;border:1.5px solid #6c5ce7;">
				<h3 style="color:#6c5ce7;">🤖 AI Schema Analysis <span style="font-size:13px;font-weight:400;opacity:.7">(Optional but Recommended)</span></h3>
				<p style="font-size:13px;opacity:.7;margin:-8px 0 16px">
					Claude compares v14 vs v16 field definitions for every DocType and generates intelligent field mappings.
					This helps auto-fix renames, dropped fields, and missing required fields before migration begins.
				</p>
				<div id="smig-ai-status" style="min-height:20px;font-size:13px;margin-bottom:10px;"></div>
				<div id="smig-ai-results" class="smig-hidden" style="max-height:320px;overflow-y:auto;margin-bottom:14px;font-size:12px;"></div>
				<button class="smig-btn" id="smig-ai-btn"
					style="background:#6c5ce7;color:#fff;border:none;"
					onclick="stylo_migrator.runAIAnalysis()">
					🤖 Run AI Schema Analysis
				</button>
			</div>

			<div class="smig-btn-row" style="margin-top:16px;">
				<button class="smig-btn smig-btn-secondary" onclick="stylo_migrator.goStep(1)">← Back</button>
				<button class="smig-btn smig-btn-primary" id="smig-start-btn"
					onclick="stylo_migrator.startMigration()">
					🚀 Start Migration
				</button>
			</div>
		</div>

		<div id="smig-step-3" class="smig-hidden">
			<div class="smig-stats" id="smig-stats">
				<div class="smig-stat">
					<div class="smig-stat-num" id="stat-migrated">0</div>
					<div class="smig-stat-label">Migrated</div>
				</div>
				<div class="smig-stat">
					<div class="smig-stat-num failed" id="stat-failed">0</div>
					<div class="smig-stat-label">Failed / Auto-fixed</div>
				</div>
				<div class="smig-stat">
					<div class="smig-stat-num" id="stat-phase" style="font-size:14px;">—</div>
					<div class="smig-stat-label">Current Phase</div>
				</div>
				<div class="smig-stat">
					<div class="smig-stat-num" id="stat-status" style="font-size:16px;">Queued</div>
					<div class="smig-stat-label">Status</div>
				</div>
			</div>

			<div class="smig-card smig-progress-section" id="smig-progress-card">
				<h3>⏳ Migration Progress</h3>
				<div id="smig-progress-body">Waiting to start…</div>
			</div>

			<div class="smig-btn-row">
				<button class="smig-btn smig-btn-danger" id="smig-abort-btn"
					onclick="stylo_migrator.abortMigration()">
					⛔ Abort
				</button>
				<button class="smig-btn smig-btn-secondary smig-hidden" id="smig-dl-btn"
					onclick="stylo_migrator.downloadFailures()">
					⬇️ Download Failures CSV
				</button>
			</div>

			<div class="smig-card smig-hidden" id="smig-log-card" style="margin-top:18px;">
				<h3>⚠️ Failures & Auto-Fixes</h3>
				<div id="smig-log-body"></div>
			</div>
		</div>
	`;

	/* Load saved config */
	frappe.call({
		method: "stylo_migrator.api.load_config",
		callback(r) {
			if (!r.message) return;
			const c = r.message;
			if (c.v14_host) {
				document.getElementById("smig-site-url").value = `http://${c.v14_host}`;
			}
			document.getElementById("smig-host").value = c.v14_host || "";
			document.getElementById("smig-port").value = c.v14_port || 3306;
			document.getElementById("smig-user").value = c.v14_db_user || "";
			document.getElementById("smig-db").value   = c.v14_database || "";
			if (c.connection_status && c.connection_status.includes("✓")) {
				_setConnStatus(c.connection_status, true);
				document.getElementById("smig-goto-preview").disabled = false;
			}
		},
	});

	/* ── Realtime progress ──────────────────────────────────────────────── */
	frappe.realtime.on("migration_progress", function (data) {
		if (data.job && data.job !== state.job) return;
		const isActive = data.doctype === state.lastDoctype;
		_renderProgressRow(data.doctype, data.count, isActive);
		if (data.phase === "Done") {
			_onMigrationDone();
		}
	});

	/* ── Step navigation ────────────────────────────────────────────────── */
	stylo_migrator.goStep = function (n) {
		state.step = n;
		[1, 2, 3].forEach(i => {
			document.getElementById(`smig-step-${i}`).classList.toggle("smig-hidden", i !== n);
			const stepEl = document.querySelector(`.smig-step[data-step="${i}"]`);
			stepEl.classList.remove("active", "done");
			if (i < n) stepEl.classList.add("done");
			else if (i === n) stepEl.classList.add("active");
		});
	};

	/* ── URL parser — fills host + port from a site URL ────────────────── */
	stylo_migrator.parseUrl = function (raw) {
		if (!raw || raw.length < 4) return;
		try {
			// Ensure there's a protocol so URL() can parse it
			const full = /^https?:\/\//i.test(raw) ? raw : "http://" + raw;
			const u    = new URL(full);
			const host = u.hostname;
			// DB port is always 3306 — never copy the HTTP port
			if (host) {
				document.getElementById("smig-host").value = host;
				document.getElementById("smig-port").value = "3306";
			}
		} catch (e) {
			// Not a valid URL yet — user is still typing, ignore
		}
	};

	// Mark port as user-edited if they touch it directly
	document.getElementById("smig-port").addEventListener("input", function () {
		this.dataset.userEdited = "1";
	});

	/* ── Step 1: Test connection ────────────────────────────────────────── */
	stylo_migrator.testConn = async function () {
		_setConnStatus("Testing…", null);
		document.getElementById("smig-goto-preview").disabled = true;

		await frappe.call({
			method: "stylo_migrator.api.save_config",
			args:   _getConnArgs(),
		});

		frappe.call({
			method: "stylo_migrator.api.test_connection",
			callback(r) {
				if (!r.message) return;
				const { success, message } = r.message;
				_setConnStatus(message, success);
				document.getElementById("smig-goto-preview").disabled = !success;
			},
		});
	};

	stylo_migrator.goPreview = function () {
		stylo_migrator.goStep(2);
		_loadPreview();
	};

	/* ── Step 2: Preview (phase-by-phase streaming) ────────────────────── */
	function _loadPreview() {
		const body = document.getElementById("smig-preview-body");
		body.innerHTML = "";
		state.preview = [];

		let currentIndex   = 0;
		let totalPhases    = 19;   // updated from first response
		let totalRecords   = 0;

		// Sticky loading indicator always at the bottom
		body.insertAdjacentHTML("beforeend", `
			<div id="smig-phase-loader" class="smig-phase-loader">
				<span class="smig-spinner smig-spinner-sm"></span>
				<span id="smig-phase-loader-text">Connecting to v14…</span>
			</div>
		`);

		function _loadNext() {
			const loaderText = document.getElementById("smig-phase-loader-text");
			if (loaderText) loaderText.textContent = `Loading phase ${currentIndex + 1} of ${totalPhases}…`;

			frappe.call({
				method: "stylo_migrator.api.preview_phase",
				args:   { phase_index: currentIndex },
				callback(r) {
					if (!r.message || !r.message.success) {
						const loader = document.getElementById("smig-phase-loader");
						if (loader) loader.innerHTML =
							`<span style="color:red">✗ ${_esc((r.message || {}).error || "Connection failed")}</span>`;
						return;
					}

					const { phase, has_more, total_phases, skipped, skip_reason } = r.message;
					if (total_phases) totalPhases = total_phases;

					if (phase && phase.doctypes && phase.doctypes.length) {
						state.preview.push(phase);
						const phaseTotal = phase.doctypes.reduce((s, d) => s + d.count, 0);
						totalRecords += phaseTotal;

						// Insert the phase card above the loader
						const loader = document.getElementById("smig-phase-loader");
						loader.insertAdjacentHTML("beforebegin", _renderPhase(phase, phaseTotal));
					} else if (skipped) {
						const loader = document.getElementById("smig-phase-loader");
						loader.insertAdjacentHTML("beforebegin", `
							<div class="smig-preview-phase smig-phase-skipped smig-fade-in">
								<h4>⏭ Skipped — ${skip_reason || ""}</h4>
							</div>
						`);
					}

					currentIndex++;

					if (has_more) {
						setTimeout(_loadNext, 80);
					} else {
						// All phases done
						const loader = document.getElementById("smig-phase-loader");
						if (loader) loader.remove();

						body.insertAdjacentHTML("beforeend", `
							<div class="smig-preview-summary smig-fade-in">
								✓ ${state.preview.length} phases loaded &nbsp;·&nbsp;
								<strong>${totalRecords.toLocaleString()}</strong> total records to migrate
							</div>
						`);
					}
				},
			});
		}

		_loadNext();
	}

	function _renderPhase(phase, phaseTotal) {
		const hasData = phase.doctypes.some(d => d.count > 0);
		return `
			<div class="smig-preview-phase smig-fade-in">
				<div class="smig-preview-phase-header">
					<h4>${_esc(phase.phase)}</h4>
					<span class="smig-phase-total">${(phaseTotal || 0).toLocaleString()} records</span>
				</div>
				<table class="smig-preview-table">
					<thead><tr><th>DocType</th><th>Records in v14</th></tr></thead>
					<tbody>
						${phase.doctypes.map(d => `
							<tr class="${d.count === 0 ? 'smig-row-empty' : ''}">
								<td>${_esc(d.doctype)}</td>
								<td>${d.count > 0
									? `<span class="smig-count-badge">${d.count.toLocaleString()}</span>`
									: `<span style="opacity:.35">0</span>`
								}</td>
							</tr>
						`).join("")}
					</tbody>
				</table>
			</div>
		`;
	}

	/* ── AI Schema Analysis ──────────────────────────────────────────── */
	stylo_migrator.runAIAnalysis = function () {
		const btn    = document.getElementById("smig-ai-btn");
		const status = document.getElementById("smig-ai-status");
		const results = document.getElementById("smig-ai-results");

		btn.disabled = true;
		btn.textContent = "⏳ Analysing schemas…";
		status.innerHTML = `<span style="color:#6c5ce7;">Claude is comparing v14 vs v16 fields for all DocTypes — this may take 1–2 minutes…</span>`;
		results.classList.add("smig-hidden");

		frappe.call({
			method: "stylo_migrator.api.generate_schema_map",
			timeout: 180,
			callback(r) {
				btn.disabled = false;
				btn.textContent = "🤖 Re-run AI Schema Analysis";

				if (!r.message || !r.message.success) {
					status.innerHTML = `<span style="color:red;">✗ ${_esc((r.message || {}).error || "Analysis failed")}</span>`;
					return;
				}

				const { analysed, with_changes, changes, errors } = r.message;
				status.innerHTML = `<span style="color:#00b894;">✓ Analysed ${analysed} DocTypes — ${with_changes} have AI-generated mappings applied.</span>`;

				if (!changes.length && !errors.length) {
					results.innerHTML = `<p style="opacity:.6;padding:8px 0;">No schema differences detected — v14 and v16 field structures match for all covered DocTypes.</p>`;
				} else {
					results.innerHTML = [
						changes.map(c => `
							<div style="margin-bottom:10px;padding:8px;background:#f0ecff;border-radius:6px;">
								<strong>${_esc(c.doctype)}</strong>
								${Object.keys(c.renames).length ? `<div style="margin-top:4px;">🔄 Renames: ${Object.entries(c.renames).map(([o,n]) => `<code>${_esc(o)} → ${_esc(n)}</code>`).join(", ")}</div>` : ""}
								${c.dropped.length ? `<div>🗑️ Dropped: ${c.dropped.map(f => `<code>${_esc(f)}</code>`).join(", ")}</div>` : ""}
								${c.new_defaults.length ? `<div>✨ New defaults: ${c.new_defaults.map(f => `<code>${_esc(f)}</code>`).join(", ")}</div>` : ""}
							</div>
						`).join(""),
						errors.length ? `<div style="margin-top:8px;color:#d63031;font-size:11px;">⚠️ ${errors.length} DocType(s) could not be analysed: ${errors.map(e => e.doctype).join(", ")}</div>` : "",
					].join("");
				}
				results.classList.remove("smig-hidden");
			},
		});
	};

	/* ── Step 3: Migrate ────────────────────────────────────────────────── */
	stylo_migrator.startMigration = function () {
		document.getElementById("smig-start-btn").disabled = true;

		frappe.call({
			method: "stylo_migrator.api.start_migration",
			callback(r) {
				if (!r.message || !r.message.success) {
					frappe.msgprint(r.message ? r.message.error : "Could not start migration.");
					document.getElementById("smig-start-btn").disabled = false;
					return;
				}
				state.job = r.message.job;
				stylo_migrator.goStep(3);
				_buildProgressUI();
				_startPolling();
			},
		});
	};

	function _buildProgressUI() {
		if (!state.preview) return;
		const body = document.getElementById("smig-progress-body");
		body.innerHTML = state.preview.map(phase => `
			<div class="smig-progress-phase" id="phase-${_slug(phase.phase)}">
				<h4>${phase.phase}</h4>
				${phase.doctypes.map(d => `
					<div class="smig-progress-row" id="row-${_slug(d.doctype)}">
						<div class="smig-progress-label">${d.doctype}</div>
						<div class="smig-progress-bar-wrap">
							<div class="smig-progress-bar" id="bar-${_slug(d.doctype)}" style="width:0%"></div>
						</div>
						<div class="smig-progress-count" id="cnt-${_slug(d.doctype)}">0 / ${d.count.toLocaleString()}</div>
					</div>
				`).join("")}
			</div>
		`).join("");
	}

	function _renderProgressRow(doctype, count, active) {
		const slug = _slug(doctype);
		const bar  = document.getElementById(`bar-${slug}`);
		const cnt  = document.getElementById(`cnt-${slug}`);
		const row  = document.getElementById(`row-${slug}`);
		if (!bar) return;

		state.progress[doctype] = count;

		const total = _getPreviewCount(doctype);
		const pct   = total > 0 ? Math.min(100, Math.round(count / total * 100)) : (count > 0 ? 100 : 0);
		bar.style.width = pct + "%";
		bar.style.transition = "width 0.4s ease";
		bar.style.background = pct >= 100 ? "#00b894" : active ? "#6c5ce7" : "#0984e3";

		if (cnt) {
			cnt.textContent = total > 0
				? `${count.toLocaleString()} / ${total.toLocaleString()} (${pct}%)`
				: `${count.toLocaleString()}`;
		}
		if (row) {
			row.classList.toggle("active", !!active && pct < 100);
			row.classList.toggle("done", pct >= 100);
		}
	}

	function _startPolling() {
		clearInterval(state.pollTimer);
		state.pollTimer = setInterval(() => {
			if (!state.job) return;
			frappe.call({
				method: "stylo_migrator.api.get_progress",
				args:   { job: state.job },
				callback(r) {
					if (!r.message || !r.message.success) return;
					const d = r.message;

					// Top stats
					document.getElementById("stat-migrated").textContent = (d.migrated || 0).toLocaleString();
					document.getElementById("stat-failed").textContent   = (d.failed || 0).toLocaleString();
					document.getElementById("stat-phase").textContent    = d.current_doctype || d.current_phase || "—";
					document.getElementById("stat-status").textContent   = d.status || "—";

					// When doctype changes, mark the previous one as complete
					if (state.lastDoctype && d.current_doctype && state.lastDoctype !== d.current_doctype) {
						const prev = state.lastDoctype;
						const prevTotal = _getPreviewCount(prev);
						_renderProgressRow(prev, prevTotal || (state.progress[prev] || 0), false);
					}
					state.lastDoctype = d.current_doctype || state.lastDoctype;

					// Apply all per-doctype counts from Redis (polling fallback for realtime)
					const perDoctype = d.per_doctype || {};
					Object.entries(perDoctype).forEach(([dt, count]) => {
						const isActive = dt === d.current_doctype;
						_renderProgressRow(dt, count, isActive);
					});

					// Ensure the current doctype row shows as active / pulsing
					if (d.current_doctype) {
						const row = document.getElementById(`row-${_slug(d.current_doctype)}`);
						if (row && !row.classList.contains("done")) {
							document.querySelectorAll(".smig-progress-row.active").forEach(el => el.classList.remove("active"));
							row.classList.add("active");
						}
					}

					if (["Completed", "Failed", "Aborted"].includes(d.status)) {
						clearInterval(state.pollTimer);
						_onMigrationDone(d.status);
					}
				},
			});
		}, 2000);
	}

	function _onMigrationDone(status) {
		clearInterval(state.pollTimer);
		document.getElementById("smig-abort-btn").classList.add("smig-hidden");
		document.getElementById("smig-dl-btn").classList.remove("smig-hidden");
		_loadFailures();
	}

	function _loadFailures() {
		frappe.call({
			method: "stylo_migrator.api.get_failures",
			args:   { job: state.job },
			callback(r) {
				if (!r.message || !r.message.success || !r.message.logs.length) return;
				const logs = r.message.logs;
				const card = document.getElementById("smig-log-card");
				const body = document.getElementById("smig-log-body");
				card.classList.remove("smig-hidden");
				body.innerHTML = `
					<table class="smig-log-table">
						<thead><tr>
							<th>DocType</th><th>v14 Name</th><th>Error</th><th>Auto-Fix</th>
						</tr></thead>
						<tbody>
							${logs.map(l => `
								<tr>
									<td>${l.doctype_name || ""}</td>
									<td>${l.v14_name || ""}</td>
									<td>${l.error
										? `<span class="smig-tag smig-tag-error">${_esc(l.error.slice(0, 80))}</span>`
										: ""}</td>
									<td>${l.auto_fix_applied
										? `<span class="smig-tag smig-tag-fix">${_esc(l.auto_fix_applied.slice(0, 80))}</span>`
										: l.skipped
										? `<span class="smig-tag smig-tag-skip">duplicate</span>`
										: ""}</td>
								</tr>
							`).join("")}
						</tbody>
					</table>
				`;
			},
		});
	}

	stylo_migrator.abortMigration = function () {
		if (!state.job) return;
		frappe.confirm("Abort the running migration?", () => {
			frappe.call({
				method: "stylo_migrator.api.abort_migration",
				args:   { job: state.job },
				callback() {
					frappe.show_alert({ message: "Migration aborted.", indicator: "orange" });
					clearInterval(state.pollTimer);
				},
			});
		});
	};

	stylo_migrator.downloadFailures = function () {
		if (!state.job) return;
		frappe.call({
			method: "stylo_migrator.api.get_failures",
			args:   { job: state.job, limit: 10000 },
			callback(r) {
				if (!r.message || !r.message.success) return;
				const rows = r.message.logs;
				const csv  = [
					["DocType", "v14 Name", "Error", "Auto-Fix Applied"].join(","),
					...rows.map(l => [l.doctype_name, l.v14_name, l.error, l.auto_fix_applied]
						.map(v => `"${(v || "").replace(/"/g, '""')}"`)
						.join(","))
				].join("\n");
				const a = document.createElement("a");
				a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(csv);
				a.download = `migration-failures-${state.job}.csv`;
				a.click();
			},
		});
	};

	/* ── Utilities ─────────────────────────────────────────────────────── */
	function _getConnArgs() {
		return {
			v14_host:        document.getElementById("smig-host").value.trim(),
			v14_port:        document.getElementById("smig-port").value.trim() || "3306",
			v14_db_user:     document.getElementById("smig-user").value.trim(),
			v14_db_password: document.getElementById("smig-pass").value,
			v14_database:    document.getElementById("smig-db").value.trim(),
		};
	}

	function _setConnStatus(msg, success) {
		const el = document.getElementById("smig-conn-status");
		if (success === null) {
			el.innerHTML = msg;
		} else if (success) {
			el.innerHTML = `<span class="smig-status-badge connected">✓ ${_esc(msg)}</span>`;
		} else {
			el.innerHTML = `<span class="smig-status-badge error">✗ ${_esc(msg)}</span>`;
		}
	}

	function _getPreviewCount(doctype) {
		if (!state.preview) return 0;
		for (const phase of state.preview) {
			const found = phase.doctypes.find(d => d.doctype === doctype);
			if (found) return found.count;
		}
		return 0;
	}

	function _slug(s) {
		return (s || "").toLowerCase().replace(/[^a-z0-9]/g, "-");
	}
	function _esc(s) {
		return (s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
	}
};

/* Auto-mount when the page is the migrator page */
frappe.ready(function () {
	if (document.getElementById("stylo-migrator-root")) {
		stylo_migrator.init();
	}
});
