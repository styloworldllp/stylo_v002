frappe.provide("frappe.views");

frappe.views.GanttView = class GanttView extends frappe.views.ListView {
	get view_name() {
		return "Gantt";
	}

	before_refresh() {
		// Don't carry over filters from other list views (Calendar, List, etc.).
		// The Gantt view manages its own filter state.
		frappe.route_options = null;
		return super.before_refresh();
	}

	setup_defaults() {
		return super.setup_defaults().then(() => {
			this.page_title = this.page_title + " " + __("Gantt");
			this.calendar_settings = frappe.views.calendar[this.doctype] || {};

			if (typeof this.calendar_settings.gantt == "object") {
				Object.assign(this.calendar_settings, this.calendar_settings.gantt);
			}

			// Always sort by lft (nested set pre-order) so tasks appear in proper
			// parent→child tree order instead of flat date order.
			// Fall back to creation if lft field doesn't exist on the doctype.
			if (frappe.meta.get_field(this.doctype, "lft")) {
				this.sort_by = "lft";
				this.sort_order = "asc";
			} else if (this.calendar_settings.order_by) {
				this.sort_by = this.calendar_settings.order_by;
				this.sort_order = "asc";
			} else {
				this.sort_by =
					this.view_user_settings.sort_by ||
					(this.calendar_settings.field_map && this.calendar_settings.field_map.start) ||
					"creation";
				this.sort_order = this.view_user_settings.sort_order || "asc";
			}
		});
	}

	// ── CRITICAL FIX: include Gantt date/progress fields in the list query ───────
	// super.get_fields() returns `tabDoctype`.`fieldname` strings — we must push
	// the same format so the server-side get_list query includes these columns.
	get_fields() {
		const fields = super.get_fields();
		const field_map = (this.calendar_settings && this.calendar_settings.field_map) || {};
		const added = new Set(fields);

		const _add = (fn) => {
			const full = frappe.model.get_full_column_name(fn, this.doctype);
			if (!added.has(full)) {
				fields.push(full);
				added.add(full);
			}
		};

		["start", "end", "id", "title", "progress", "color"].forEach((key) => {
			const fn = typeof field_map[key] === "string" ? field_map[key] : null;
			if (fn) _add(fn);
		});

		if (frappe.meta.get_field(this.doctype, "depends_on_tasks")) _add("depends_on_tasks");
		if (frappe.meta.get_field(this.doctype, "is_milestone"))    _add("is_milestone");
		if (frappe.meta.get_field(this.doctype, "is_group"))        _add("is_group");
		if (frappe.meta.get_field(this.doctype, "parent_task"))     _add("parent_task");
		if (frappe.meta.get_field(this.doctype, "lft"))             _add("lft");

		// Actual dates for planned vs actual comparison
		if (frappe.meta.get_field(this.doctype, "act_start_date")) _add("act_start_date");
		if (frappe.meta.get_field(this.doctype, "act_end_date"))   _add("act_end_date");

		return fields;
	}

	setup_view() {
		// Load all tasks so the summary/detail toggle works without extra DB round-trips.
		this.page_length = 2000;
		// Default: summary mode — show only group tasks and milestones so all 76 WTGs
		// are visible at once. User can toggle to "Full Detail" to see leaf tasks.
		this._summary_mode = true;
		// Track collapsed group IDs — persisted across re-renders within this session.
		if (!this._collapsed) this._collapsed = new Set();
	}

	prepare_data(data) {
		super.prepare_data(data);
		this.prepare_tasks();
		this.compute_critical_path();
	}

	prepare_tasks() {
		var me = this;
		var meta = this.meta;
		var field_map = (this.calendar_settings && this.calendar_settings.field_map) || {};

		// If calendar settings not loaded yet, tasks array stays empty and empty-state shows
		if (!field_map.start || !field_map.end) {
			this.tasks = [];
			return;
		}

		// Build full parent→child map from ALL data (needed for collapse detection).
		const _all_child_of = {};
		this.data.forEach(function(d) {
			if (d.parent_task) _all_child_of[d.name] = d.parent_task;
		});

		// Returns true if any ancestor of `name` is in the collapsed set.
		const _has_collapsed_ancestor = (name) => {
			let p = _all_child_of[name];
			while (p) {
				if (me._collapsed.has(p)) return true;
				p = _all_child_of[p];
			}
			return false;
		};

		// Summary mode: only render group tasks and milestones so all WTG groups fit.
		// Leaf tasks are still in this.data (loaded from DB) but hidden from the Gantt.
		const _summary_filtered = this._summary_mode
			? this.data.filter((d) => d.is_group || d.is_milestone)
			: this.data;

		// Collapse filter: hide children of collapsed group tasks.
		const _render_data = _summary_filtered.filter((d) => !_has_collapsed_ancestor(d.name));

		// Build child→parent map and a set of all visible task IDs.
		// We use these to:
		//  1. Strip child IDs that ERPNext's populate_depends_on() auto-adds to
		//     the parent's depends_on_tasks (parent "depends on" its children is
		//     wrong for Gantt arrows / CPM).
		//  2. Strip dependency targets that aren't in the current view — these
		//     would cause "hanging" arrows that point to empty space.
		const _child_of = {};
		const _visible_ids = new Set();
		_render_data.forEach(function(d) {
			_visible_ids.add(d.name);
			if (d.parent_task) _child_of[d.name] = d.parent_task;
		});

		// Compute depth of each task from _child_of so we can indent task names.
		const _depth = {};
		const _get_depth = (name) => {
			if (_depth[name] !== undefined) return _depth[name];
			const parent = _child_of[name];
			_depth[name] = parent ? (_get_depth(parent) + 1) : 0;
			return _depth[name];
		};
		_render_data.forEach(function(d) { _get_depth(d.name); });

		this.tasks = _render_data
			.map(function (item) {
				if (!item[field_map.start] || !item[field_map.end]) {
					return null;
				}

				// progress
				var progress = 0;
				if (field_map.progress && $.isFunction(field_map.progress)) {
					progress = field_map.progress(item);
				} else if (field_map.progress) {
					progress = parseFloat(item[field_map.progress]) || 0;
				}
				progress = Math.min(100, Math.max(0, progress));

				// title — add visual indentation based on tree depth
				const depth  = _depth[item.name] || 0;
				const indent = depth > 0 ? ("  ".repeat(Math.min(depth, 4))) : "";
				// ▼ = expanded (has children visible), ▶ = collapsed
				const is_collapsed = item.is_group && me._collapsed.has(item.name);
				const prefix = item.is_group ? (is_collapsed ? "▶ " : "▼ ") : item.is_milestone ? "◆ " : "  ";
				var label;
				if (meta.title_field && item[meta.title_field]) {
					label = progress
						? __("{0} ({1}) - {2}%", [indent + prefix + item[meta.title_field], item.name, Math.round(progress)])
						: __("{0} ({1})", [indent + prefix + item[meta.title_field], item.name]);
				} else if (field_map.title) {
					label = indent + prefix + (item[field_map.title] || item.name);
				} else {
					label = indent + prefix + item.name;
				}

				var r = {
					start: item[field_map.start],
					end: item[field_map.end],
					name: label,
					id: item[field_map.id || "name"],
					doctype: me.doctype,
					progress: progress,
					dependencies: (item.depends_on_tasks || "").split(",").map(function(d){ return d.trim(); }).filter(function(d){
					// Strip: empty, child IDs auto-added by ERPNext, targets not visible in current page
					return d && _child_of[d] !== item.name && _visible_ids.has(d);
				}).join(","),
				};

				if (item.color && frappe.ui.color.validate_hex(item.color)) {
					r["custom_class"] = "color-" + item.color.substr(1);
				}

				if (item.is_milestone) {
					r["custom_class"] = "bar-milestone";
				}

				// Attach raw item so we can build the actual row below
				r._raw = item;

				return r;
			})
			.filter(Boolean);

		// Interleave "actual" rows directly below each planned row
		const today = frappe.datetime.now_date();
		const with_actuals = [];
		this.tasks.forEach((planned) => {
			with_actuals.push(planned);

			const raw = planned._raw || {};
			const act_start = raw.act_start_date;
			if (!act_start) return;

			// In-progress tasks end "today"; completed tasks use act_end_date
			const act_end   = raw.act_end_date || today;
			const is_late   = act_end > (planned._planned_end || planned.end);
			const delay_days = is_late
				? Math.floor((new Date(act_end) - new Date(planned._planned_end || planned.end)) / 86400000)
				: 0;

			with_actuals.push({
				id:           planned.id + "__actual",
				name:         "↳ actual",   // ↳ actual
				start:        act_start,
				end:          act_end,
				custom_class: "bar-actual " + (is_late ? "bar-actual-late" : "bar-actual-ontime"),
				progress:     0,
				dependencies: "",
				_is_actual:   true,
				_parent_id:   planned.id,
				_is_late:     is_late,
				_delay_days:  delay_days,
				_act_start:   act_start,
				_act_end:     act_end,
				_planned_start: planned.start,
				_planned_end:   planned.end,
				doctype:      me.doctype,
			});
		});
		this.tasks = with_actuals;
	}

	// ── Critical Path Method (CPM) — full forward/backward pass ─────────────
	// Proper CPM algorithm:
	//   Forward pass  → Earliest Start (ES) and Earliest Finish (EF) per task
	//   Backward pass → Latest Finish (LF) and Latest Start (LS) per task
	//   Float = LF - EF  (zero float = on the critical path)
	//
	// Then traces back the SINGLE longest chain from the project-end anchor
	// through the best critical predecessor at each step, so the highlighted
	// path is one clean spine instead of multiple scattered parallel branches.
	compute_critical_path() {
		// Only leaf tasks carry real work — group/summary tasks are containers.
		// Including group tasks distorts CPM because after stripping child-IDs from
		// their dependencies they become isolated nodes that inherit project_end as
		// their LF, giving them float = 0 and falsely landing on the critical path.
		const all_non_actual = (this.tasks || []).filter((t) => !t._is_actual);
		const tasks = all_non_actual.filter((t) => !(t._raw && t._raw.is_group));
		if (!tasks.length) return;

		const to_days = (s) => s ? Math.floor(new Date(s).getTime() / 86400000) : 0;
		const today   = to_days(frappe.datetime.now_date());

		// Index by id (leaf tasks only — for edge resolution)
		const by_id = {};
		tasks.forEach((t) => { by_id[t.id] = t; });

		// Build predecessor / successor maps (only edges between leaf tasks)
		const pred = {}, succ = {};
		tasks.forEach((t) => { pred[t.id] = []; succ[t.id] = []; });
		tasks.forEach((t) => {
			(t.dependencies || "").split(",").map((d) => d.trim()).filter(Boolean)
				.forEach((dep_id) => {
					if (by_id[dep_id]) {
						pred[t.id].push(dep_id);
						succ[dep_id].push(t.id);
					}
				});
		});

		// Topological sort (DFS post-order — predecessors before successors)
		const visited = new Set(), topo = [];
		const visit = (id) => {
			if (visited.has(id)) return;
			visited.add(id);
			pred[id].forEach((d) => visit(d));
			topo.push(id);
		};
		tasks.forEach((t) => visit(t.id));

		// ── Forward pass — ES / EF ────────────────────────────────────────────
		// Root tasks (no predecessors) use their planned start date as ES.
		// All others: ES = max(EF of all predecessors).
		const ES = {}, EF = {};
		topo.forEach((id) => {
			const t   = by_id[id];
			const dur = Math.max(1, to_days(t.end) - to_days(t.start)); // min 1 day
			const es  = pred[id].length === 0
				? to_days(t.start)
				: Math.max(...pred[id].map((d) => EF[d] ?? to_days(by_id[d].end)));
			ES[id] = es;
			EF[id] = es + dur;
		});

		const project_end = Math.max(...Object.values(EF));

		// ── Backward pass — LF / LS ───────────────────────────────────────────
		// Terminal tasks (no successors) use project_end as LF.
		// All others: LF = min(LS of all successors).
		const LF = {}, LS = {};
		[...topo].reverse().forEach((id) => {
			const t   = by_id[id];
			const dur = Math.max(1, to_days(t.end) - to_days(t.start));
			const lf  = succ[id].length === 0
				? project_end
				: Math.min(...succ[id].map((s) => LS[s] ?? ES[s]));
			LF[id] = lf;
			LS[id] = lf - dur;
		});

		// ── Float ─────────────────────────────────────────────────────────────
		// Float = LF - EF.  Zero float = on critical path.
		// Use tolerance of 1 day to absorb weekend/calendar rounding.
		tasks.forEach((t) => {
			t.float       = LF[t.id] - EF[t.id];
			t.buffer_days = Math.max(0, t.float);
		});

		// ── Mark ALL zero-float tasks as critical (standard CPM) ────────────
		// Standard CPM: every task with total float ≤ tolerance is on the
		// critical path. A single-spine trace only finds one chain and misses
		// parallel critical paths (common in projects with many similar WTG chains).
		const cp_set = new Set();
		const FLOAT_TOLERANCE = 1; // 1-day grace for weekend/calendar rounding
		tasks.forEach((t) => {
			if (t.float <= FLOAT_TOLERANCE) cp_set.add(t.id);
		});

		// ── Apply flags and CSS classes ───────────────────────────────────────
		// Group tasks never get critical-path styling (they're containers, not work).
		all_non_actual.forEach((t) => {
			if (t._raw && t._raw.is_group) return;

			const on_chain    = cp_set.has(t.id);
			const end_days    = to_days(t.end);
			const start_days  = to_days(t.start);
			const pct         = t.progress || 0;
			const overdue     = today > end_days && pct < 100;
			const not_started = today > start_days && pct === 0;

			t.is_critical  = on_chain;
			t.is_delayed   = overdue || not_started;
			t.days_overdue = overdue     ? today - end_days   :
			                 not_started ? today - start_days : 0;

			const base = t.custom_class || "";
			if (on_chain && t.is_delayed) {
				t.custom_class = (base + " bar-critical bar-critical-delayed").trim();
			} else if (on_chain) {
				t.custom_class = (base + " bar-critical").trim();
			} else if (t.is_delayed) {
				t.custom_class = (base + " bar-delayed").trim();
			}
		});
	}

	// ── Project delay from actual vs planned dates ────────────────────────────
	// Compares actual end dates (act_end_date) against planned end dates on the
	// critical path to determine overall project slippage.
	compute_project_delay() {
		const to_days = (s) => s ? Math.floor(new Date(s).getTime() / 86400000) : 0;
		const from_days = (n) => {
			const d = new Date(n * 86400000);
			return [d.getUTCFullYear(), String(d.getUTCMonth()+1).padStart(2,"0"), String(d.getUTCDate()).padStart(2,"0")].join("-");
		};

		const planned = (this.tasks || []).filter((t) => !t._is_actual);
		const actuals  = (this.tasks || []).filter((t) => t._is_actual);

		if (!planned.length) return null;

		const planned_end_days = Math.max(...planned.map((t) => to_days(t.end)));
		const planned_end      = from_days(planned_end_days);

		// Critical path task IDs
		const cp_ids = new Set(planned.filter((t) => t.is_critical).map((t) => t.id));

		// Actual rows for critical path tasks
		const cp_actuals = actuals.filter((t) => cp_ids.has(t._parent_id));

		if (!cp_actuals.length) {
			return { planned_end, projected_end: null, delay_days: 0, has_actuals: false };
		}

		const projected_end_days = Math.max(...cp_actuals.map((t) => to_days(t._act_end || t.end)));
		const projected_end      = from_days(projected_end_days);
		const delay_days         = projected_end_days - planned_end_days;

		return { planned_end, projected_end, delay_days, has_actuals: true };
	}

	setup_project_delay_banner(delay_info) {
		this.$result.find(".project-delay-banner").remove();
		if (!delay_info || !delay_info.has_actuals) return;

		const { planned_end, projected_end, delay_days } = delay_info;

		let color, icon, msg;
		if (delay_days > 0) {
			color = "#fdecea"; icon = "⚠";
			msg = `<strong style="color:#c0392b;">Project delayed by ${delay_days} day${delay_days !== 1 ? "s" : ""}</strong>
				&nbsp;&middot;&nbsp; Planned end: <strong>${planned_end}</strong>
				&nbsp;&middot;&nbsp; Projected end: <strong style="color:#c0392b;">${projected_end}</strong>`;
		} else if (delay_days < 0) {
			color = "#eafaf1"; icon = "✓";
			msg = `<strong style="color:#1e8449;">Project ${Math.abs(delay_days)} day${Math.abs(delay_days) !== 1 ? "s" : ""} ahead of schedule</strong>
				&nbsp;&middot;&nbsp; Planned end: <strong>${planned_end}</strong>
				&nbsp;&middot;&nbsp; Projected end: <strong style="color:#1e8449;">${projected_end}</strong>`;
		} else {
			color = "#eafaf1"; icon = "✓";
			msg = `<strong style="color:#1e8449;">Project on schedule</strong>
				&nbsp;&middot;&nbsp; Planned end: <strong>${planned_end}</strong>`;
		}

		const $banner = $(`<div class="project-delay-banner" style="
			display:flex;align-items:center;gap:8px;padding:7px 14px;
			margin-bottom:4px;border-radius:6px;font-size:0.88em;
			background:${color};border:1px solid ${delay_days > 0 ? "#e74c3c" : "#27ae60"};">
			<span style="font-size:1.1em;">${icon}</span>
			<span>${msg}</span>
		</div>`);

		this.$result.find("svg").length
			? this.$result.find("svg").before($banner)
			: this.$result.prepend($banner);
	}

	// ── Cascade schedule propagation (planned rows only) ─────────────────────
	cascade_schedule() {
		// Only cascade planned rows; actual rows reflect reality, not the forecast
		const tasks = (this.tasks || []).filter((t) => !t._is_actual);
		if (!tasks.length) return 0;

		// Convert "YYYY-MM-DD" ↔ integer day number (UTC to avoid tz issues)
		const to_days = (s) => s ? Math.floor(new Date(s).getTime() / 86400000) : 0;
		const from_days = (n) => {
			const d = new Date(n * 86400000);
			return [
				d.getUTCFullYear(),
				String(d.getUTCMonth() + 1).padStart(2, "0"),
				String(d.getUTCDate()).padStart(2, "0"),
			].join("-");
		};

		const by_id = {};
		tasks.forEach((t) => {
			t._orig_start = t.start;
			t._orig_end   = t.end;
			// Delayed tasks: their adjusted end = original end + days_overdue
			t._adj_end  = to_days(t.end) + (t.is_delayed ? (t.days_overdue || 0) : 0);
			t._adj_start= to_days(t.start);
			by_id[t.id] = t;
		});

		// Build predecessor map
		const predecessors = {};
		tasks.forEach((t) => {
			predecessors[t.id] = (t.dependencies || "")
				.split(",").map((d) => d.trim()).filter(Boolean);
		});

		// Topological sort (DFS post-order)
		const visited = new Set();
		const topo    = [];
		const visit = (id) => {
			if (visited.has(id)) return;
			visited.add(id);
			(predecessors[id] || []).forEach((dep) => { if (by_id[dep]) visit(dep); });
			topo.push(id);
		};
		tasks.forEach((t) => visit(t.id));

		// Forward pass: push each task to start no earlier than when all its
		// predecessors have finished (using their adjusted end dates).
		topo.forEach((id) => {
			const t = by_id[id];
			if (!t) return;
			const orig_start = to_days(t._orig_start);
			const duration   = to_days(t._orig_end) - orig_start;

			let min_start = orig_start;
			(predecessors[id] || []).forEach((dep_id) => {
				const dep = by_id[dep_id];
				if (dep) min_start = Math.max(min_start, dep._adj_end);
			});

			if (min_start > orig_start) {
				t._adj_start = min_start;
				t._adj_end   = min_start + duration;
				if (!t.is_delayed) {
					t.is_adjusted     = true;
					t.adjustment_days = min_start - orig_start;
					t.custom_class    = ((t.custom_class || "") + " bar-adjusted").trim();
				}
			}
		});

		// Apply adjusted dates to task objects used by frappe-gantt
		let total_adjusted = 0;
		tasks.forEach((t) => {
			const adj_s = from_days(t._adj_start);
			const adj_e = from_days(t._adj_end);
			if (adj_s !== t._orig_start || adj_e !== t._orig_end) {
				t._planned_start = t._orig_start;
				t._planned_end   = t._orig_end;
				t.start = adj_s;
				t.end   = adj_e;
				if (t.is_adjusted) total_adjusted++;
			}
		});

		return total_adjusted;
	}

	// Persist cascade-adjusted dates to the Frappe database.
	apply_cascade_to_db() {
		const field_map   = (this.calendar_settings && this.calendar_settings.field_map) || {};
		const start_field = field_map.start || "exp_start_date";
		const end_field   = field_map.end   || "exp_end_date";

		const adjustments = this.tasks.filter((t) => t.is_adjusted && t._planned_start);
		if (adjustments.length === 0) return;

		frappe.confirm(
			__("Update {0} task date(s) in the database to reflect the cascaded schedule?",
			   [adjustments.length]),
			() => {
				const calls = adjustments.map((t) =>
					frappe.db.set_value(this.doctype, t.id, {
						[start_field]: t.start,
						[end_field]:   t.end,
					})
				);
				Promise.all(calls).then(() => {
					frappe.show_alert({ message: __("Schedule saved"), indicator: "green" });
					// Mark as no longer just adjusted — they are now the planned dates
					adjustments.forEach((t) => {
						t._planned_start = t.start;
						t._planned_end   = t.end;
						t.is_adjusted    = false;
					});
					this.$result.find(".cascade-banner").remove();
				});
			}
		);
	}

	setup_cascade_banner(adjusted_count) {
		// Remove any previous banner from this render cycle
		this.$result.find(".cascade-banner").remove();
		if (adjusted_count === 0) return;

		const $banner = $(`
			<div class="cascade-banner" style="
				display:flex;align-items:center;gap:10px;flex-wrap:wrap;
				padding:8px 14px;margin-bottom:6px;border-radius:6px;
				background:#fff3cd;border:1px solid #ffc107;font-size:0.88em;">
				<span style="flex:1;min-width:200px;">
					&#9889; <strong>${adjusted_count} task${adjusted_count !== 1 ? "s" : ""}</strong>
					auto-rescheduled due to critical path delay — dates shown are projected.
				</span>
				<button class="btn btn-sm btn-primary cascade-save-btn" style="white-space:nowrap;">
					${__("Save to database")}
				</button>
				<button class="btn btn-sm btn-default cascade-discard-btn" style="white-space:nowrap;">
					${__("Discard")}
				</button>
			</div>`);

		// Insert above the SVG (inside $result, before the gantt svg)
		this.$result.find("svg").before($banner);
		if (!this.$result.find("svg").length) this.$result.append($banner);

		$banner.on("click", ".cascade-save-btn",    () => this.apply_cascade_to_db());
		$banner.on("click", ".cascade-discard-btn", () => {
			// Restore original dates and re-render
			this.tasks.forEach((t) => {
				if (t._planned_start) {
					t.start       = t._planned_start;
					t.end         = t._planned_end;
					t.is_adjusted = false;
					t.custom_class= (t.custom_class || "").replace(/bar-adjusted/g, "").trim();
				}
			});
			this.render_gantt();
		});
	}

	render() {
		this.load_lib.then(() => {
			this.render_gantt();
		});
	}

	render_header() {}

	render_gantt() {
		const me = this;
		const gantt_view_mode = this.view_user_settings.gantt_view_mode || "Day";
		const field_map = (this.calendar_settings && this.calendar_settings.field_map) || {};
		const date_format = "YYYY-MM-DD";

		this.$result.empty();
		this.$result.addClass("gantt-modern");

		// Inject critical-path + planned/actual colour rules once per render
		this.$result.prepend(`<style>
			/* ── Bar label text — always readable ── */
			.gantt .bar-wrapper .bar-label          { fill: #fff !important; font-size: 12px; font-weight: 500; }
			.gantt .bar-wrapper.bar-milestone .bar-label { fill: #333 !important; }
			/* ── Group task bars — wider, darker ── */
			.gantt .bar-wrapper.bar-group .bar      { rx: 2; }
			/* ── List row text visibility ── */
			.list-row .list-row-col, .list-row-col  { color: var(--text-color, #333) !important; }
			/* ── Popup overrides ── */
			.gantt .popup-wrapper                     { background: #fff !important; border: 1px solid #e0e0e0; border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,0.12) !important; padding: 0 !important; }
			.gantt .popup-wrapper .title              { color: #1a1a1a !important; font-weight: 600; font-size: 0.92em; }
			.gantt .popup-wrapper .subtitle           { color: #555 !important; font-size: 0.82em; margin-top: 2px; }
			.gantt .popup-wrapper p                   { color: #444 !important; }
			.gantt .details-container                 { background: #fff !important; color: #333 !important; border-radius: 6px; padding: 10px 14px; min-width: 220px; }
			.gantt .pointer                           { border-top-color: #e0e0e0 !important; }
		</style>
		<style>
			/* Critical path — light blue when on schedule */
			.gantt .bar-wrapper.bar-critical .bar            { fill: #2e86c1 !important; }
			.gantt .bar-wrapper.bar-critical .bar-progress   { fill: #1a5276 !important; }
			.gantt .bar-wrapper.bar-critical .bar-label      { fill: #fff    !important; }
			/* Critical path — red only when delayed */
			.gantt .bar-wrapper.bar-critical-delayed .bar    { fill: #e74c3c !important; stroke: #c0392b; stroke-width: 2; }
			.gantt .bar-wrapper.bar-critical-delayed .bar-progress { fill: #c0392b !important; }
			.gantt .bar-wrapper.bar-critical-delayed .bar-label   { fill: #fff !important; }
			/* Non-critical delayed */
			.gantt .bar-wrapper.bar-delayed .bar             { fill: #e67e22 !important; }
			.gantt .bar-wrapper.bar-delayed .bar-progress    { fill: #d35400 !important; }
			.gantt .bar-wrapper.bar-delayed .bar-label       { fill: #fff    !important; }
			/* Actual rows — on time */
			.gantt .bar-wrapper.bar-actual-ontime .bar       { fill: #27ae60 !important; opacity: 0.85; }
			.gantt .bar-wrapper.bar-actual-ontime .bar-progress { fill: #1e8449 !important; }
			.gantt .bar-wrapper.bar-actual-ontime .bar-label { fill: #fff    !important; font-size: 11px; }
			/* Actual rows — late */
			.gantt .bar-wrapper.bar-actual-late .bar         { fill: #e74c3c !important; opacity: 0.85; stroke: #922b21; stroke-width: 1.5; }
			.gantt .bar-wrapper.bar-actual-late .bar-progress{ fill: #c0392b !important; }
			.gantt .bar-wrapper.bar-actual-late .bar-label   { fill: #fff    !important; font-size: 11px; }
			/* Actual row label styling */
			.gantt .bar-wrapper.bar-actual .bar-label        { font-style: italic; opacity: 0.9; }
			/* Cascade-rescheduled tasks */
			.gantt .bar-wrapper.bar-adjusted .bar            { fill: #3498db !important; stroke: #1a6fa8; stroke-width: 1.5; stroke-dasharray: 4 2; }
			.gantt .bar-wrapper.bar-adjusted .bar-progress   { fill: #1a6fa8 !important; }
			.gantt .bar-wrapper.bar-adjusted .bar-label      { fill: #fff    !important; }
			/* Group / summary task rows (slightly muted) */
			.gantt .bar-wrapper.bar-group .bar               { fill: #78909c !important; opacity: 0.75; }
		</style>`);

		if (!this.tasks || this.tasks.length === 0) {
			this.$result.html(
				`<div style="padding: 40px; text-align: center; color: var(--text-muted);">
					<p style="font-size:1.1em;">${__("No tasks with start and end dates found.")}</p>
					<p style="font-size:0.9em; margin-top:8px;">${__("Set Exp. Start Date and Exp. End Date on tasks to see them here.")}</p>
				</div>`
			);
			this.setup_view_mode_buttons_empty();
			this.setup_export_button();
			return;
		}

		// Compute actual vs planned project delay for the banner
		const delay_info = this.compute_project_delay();

		this.gantt = new Gantt(this.$result[0], this.tasks, {
			bar_height: 28,
			bar_corner_radius: 4,
			resize_handle_width: 8,
			resize_handle_height: 20,
			resize_handle_corner_radius: 3,
			resize_handle_offset: 4,
			view_mode: gantt_view_mode,
			date_format: "YYYY-MM-DD",
			on_click: (task) => {
				// Group tasks: toggle collapse/expand instead of opening the form
				if (task._raw && task._raw.is_group) {
					if (me._collapsed.has(task.id)) {
						me._collapsed.delete(task.id);
					} else {
						me._collapsed.add(task.id);
					}
					me.prepare_data(me.data);
					me.render_gantt();
					return;
				}
				// Both planned and actual rows navigate to the same form
				const form_id = task._is_actual ? task._parent_id : task.id;
				if (form_id) frappe.set_route("Form", me.doctype, form_id);
			},
			on_date_change: (task, start, end) => {
				if (!me.can_write || task._is_actual) return;
				frappe.db.set_value(task.doctype, task.id, {
					[field_map.start]: moment(start).format(date_format),
					[field_map.end]: moment(end).format(date_format),
				});
			},
			on_progress_change: (task, progress) => {
				if (!me.can_write || task._is_actual) return;
				var progress_fieldname = "progress";

				if ($.isFunction(field_map.progress)) {
					progress_fieldname = null;
				} else if (field_map.progress) {
					progress_fieldname = field_map.progress;
				}

				if (progress_fieldname) {
					frappe.db.set_value(task.doctype, task.id, {
						[progress_fieldname]: parseInt(progress),
					});
				}
			},
			on_view_change: (mode) => {
				me.save_view_user_settings({ gantt_view_mode: mode });
			},
			custom_popup_html: (task) => {
				// ── Actual row popup ──────────────────────────────────────────────
				if (task._is_actual) {
					const status_color = task._is_late ? "#c0392b" : "#1e8449";
					const status_icon  = task._is_late ? "⚠" : "✓";
					const delay_txt    = task._is_late
						? `<span style="color:${status_color};font-weight:600;">${task._delay_days} day${task._delay_days !== 1 ? "s" : ""} late</span>`
						: `<span style="color:${status_color};font-weight:600;">On time</span>`;

					return `<div class="details-container" style="background:#fff;color:#333;border-radius:6px;padding:10px 14px;min-width:220px;">
						<div class="title" style="font-style:italic;color:#1a1a1a;font-weight:600;">${status_icon} Actual Progress</div>
						<div class="subtitle" style="color:#555;font-size:0.82em;">${task._act_start} → ${task._act_end}</div>
						<div style="margin-top:6px;font-size:0.88em;color:#444;">
							<strong>Planned:</strong> ${task._planned_start} → ${task._planned_end}<br>
							<strong>Status:</strong> ${delay_txt}
							${task._is_late ? `<br><small style="color:#888;">This delay impacts downstream tasks</small>` : ""}
						</div>
					</div>`;
				}

				// ── Planned row popup ─────────────────────────────────────────────
				var item = me.get_item(task.id);
				var html = `<div class="title">${task.name}</div>
					<div class="subtitle">${moment(task._start).format("MMM D")} - ${moment(task._end).format("MMM D")}</div>`;

				var custom = me.settings.gantt_custom_popup_html;
				if (custom && $.isFunction(custom)) {
					html = custom(task, item);
				}

				let badge_html = "";
				if (task.is_critical && task.is_delayed) {
					badge_html = `
						<div style="margin-top:8px;padding:6px 8px;background:#fdecea;border-left:3px solid #e74c3c;border-radius:3px;">
							<span style="color:#c0392b;font-weight:600;">&#9888; Critical &amp; Delayed</span>
							<div style="color:#c0392b;font-size:0.85em;margin-top:2px;">
								${task.days_overdue} day${task.days_overdue !== 1 ? "s" : ""} overdue — impacts project end date
							</div>
						</div>`;
				} else if (task.is_critical) {
					badge_html = `
						<div style="margin-top:8px;padding:6px 8px;background:#fdecea;border-left:3px solid #e74c3c;border-radius:3px;">
							<span style="color:#c0392b;font-weight:600;">&#128308; On Critical Path</span>
							<div style="color:#888;font-size:0.85em;margin-top:2px;">Any slip delays the project end date</div>
						</div>`;
				} else if (task.is_delayed) {
					badge_html = `
						<div style="margin-top:8px;padding:6px 8px;background:#fef5e7;border-left:3px solid #e67e22;border-radius:3px;">
							<span style="color:#d35400;font-weight:600;">&#9651; Delayed — not critical</span>
							<div style="color:#666;font-size:0.85em;margin-top:2px;">
								${task.days_overdue} day${task.days_overdue !== 1 ? "s" : ""} overdue
								&nbsp;&middot;&nbsp; Buffer: <strong>${task.buffer_days}</strong> day${task.buffer_days !== 1 ? "s" : ""} remaining
							</div>
						</div>`;
				} else if (task.buffer_days > 0) {
					badge_html = `
						<div style="margin-top:8px;padding:6px 8px;background:#eafaf1;border-left:3px solid #27ae60;border-radius:3px;">
							<span style="color:#1e8449;font-weight:600;">&#9989; On Track</span>
							<div style="color:#666;font-size:0.85em;margin-top:2px;">
								Buffer: <strong>${task.buffer_days}</strong> day${task.buffer_days !== 1 ? "s" : ""} of slack
							</div>
						</div>`;
				}

				return `<div class="details-container" style="background:#fff;color:#333;border-radius:6px;padding:10px 14px;min-width:220px;">${html}${badge_html}</div>`;
			},
		});

		this.setup_view_mode_buttons();
		this.setup_summary_toggle();
		this.setup_export_button();
		this.setup_critical_path_legend();
		this.setup_project_delay_banner(delay_info);
		this.set_colors();
		this.setup_gantt_legend();
		this._setup_sticky_date_header();
		this._setup_v6_enhancements();
	}

	_setup_sticky_date_header() {
		const container = this.$result.find(".gantt-container")[0];
		if (!container) return;
		const svg = container.querySelector("svg");
		if (!svg) return;
		const dateG = svg.querySelector(".date");
		if (!dateG) return;

		// frappe-gantt default header height is 50px
		const headerH = (this.gantt && this.gantt.options && this.gantt.options.header_height) || 50;
		const svgTotalW = parseFloat(svg.getAttribute("width")) || container.scrollWidth || 2000;

		// Clone the date header group
		const clone = dateG.cloneNode(true);

		// Build a sticky SVG that shows the header
		const stickySvg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
		stickySvg.setAttribute("height", headerH);
		stickySvg.setAttribute("viewBox", `0 0 ${container.clientWidth || 1000} ${headerH}`);
		stickySvg.style.cssText = "display:block;width:100%;";
		stickySvg.appendChild(clone);

		const stickyDiv = document.createElement("div");
		stickyDiv.className = "gantt-sticky-header";
		stickyDiv.style.cssText = `
			position: sticky;
			top: 0;
			z-index: 300;
			background: var(--fg-color, #fff);
			border-bottom: 2px solid var(--border-color, #dde3ee);
			box-shadow: 0 3px 10px rgba(0,0,0,0.10);
			overflow: hidden;
			margin-bottom: -${headerH}px;
		`;
		stickyDiv.appendChild(stickySvg);

		// Insert the sticky header before the gantt container
		this.$result.find(".gantt-container").before(stickyDiv);

		// Sync horizontal scroll: update viewBox when gantt scrolls left/right
		container.addEventListener("scroll", () => {
			const sl = container.scrollLeft;
			const cw = container.clientWidth;
			stickySvg.setAttribute("viewBox", `${sl} 0 ${cw} ${headerH}`);
		}, { passive: true });
	}

	// ── v6 Interactive Enhancements ──────────────────────────────────────────────
	// All overlay interactivity runs on the live SVG after each render:
	//   • Double-click empty area  → new task dialog
	//   • Drag blue dot on bar end → link dependency
	//   • Click dependency arrow   → unlink dependency
	//   • Right-click bar          → assign / status / priority context menu
	_setup_v6_enhancements() {
		const me = this;
		const container = this.$result.find(".gantt-container")[0];
		if (!container) return;
		const svg = container.querySelector("svg.gantt");
		if (!svg) return;

		// Inject CSS once per page
		if (!document.getElementById("g-enh-v6-css")) {
			const s = document.createElement("style");
			s.id = "g-enh-v6-css";
			s.textContent = `
.g-handle-overlay circle{fill:#5e72e4;stroke:#fff;stroke-width:1.5;cursor:crosshair;opacity:0.7;transition:opacity .15s}
.g-handle-overlay circle:hover{opacity:1}
svg.gantt.linking-mode .bar-wrapper .bar,
svg.gantt.linking-mode .bar-wrapper .bar-progress,
svg.gantt.linking-mode .bar-wrapper .bar-label{pointer-events:none!important}
svg.gantt.linking-mode{cursor:crosshair!important}
svg.gantt .arrow{cursor:pointer;pointer-events:stroke}
svg.gantt .arrow:hover{stroke:#e74c3c!important;stroke-width:3!important}
.gantt-drag-line{stroke:#5e72e4;stroke-width:2;stroke-dasharray:6 3;pointer-events:none}
.gantt-ctx-menu{position:fixed;z-index:9999;background:#fff;border:1px solid #d1d8dd;border-radius:6px;
  box-shadow:0 4px 16px rgba(0,0,0,.12);min-width:180px;padding:4px 0;font-size:13px}
.gantt-ctx-menu .ctx-item{padding:8px 14px;cursor:pointer;color:#333}
.gantt-ctx-menu .ctx-item:hover{background:#f4f5f7}
.gantt-ctx-menu .ctx-sep{height:1px;background:#eee;margin:4px 0}
.gantt-helper-bar{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
  background:#1b2a4a;color:#fff;padding:7px 16px;border-radius:8px;font-size:11px;
  z-index:9998;box-shadow:0 2px 12px rgba(0,0,0,.2);pointer-events:none;opacity:.9}
`;
			document.head.appendChild(s);
		}

		// Helper bar (shown once)
		if (!document.getElementById("gantt-helper-bar-v6")) {
			const el = document.createElement("div");
			el.id = "gantt-helper-bar-v6";
			el.className = "gantt-helper-bar";
			el.innerHTML = "<b>Click group</b> = expand/collapse &nbsp;|&nbsp; <b>Double-click</b> empty = new task &nbsp;|&nbsp; <b>Drag</b> blue dot = link &nbsp;|&nbsp; <b>Click arrow</b> = unlink &nbsp;|&nbsp; <b>Right-click</b> bar = assign/status";
			document.body.appendChild(el);
		}

		// Utility: SVG x-coord → calendar date
		const _x_to_date = (x) => {
			const g = this.gantt;
			const s = g && g.gantt_start;
			if (!s) return new Date();
			const cw = (g.options && g.options.column_width) || 30;
			const d = new Date(s);
			d.setDate(d.getDate() + Math.floor(x / cw));
			return d;
		};
		const _fmt = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
		const _proj = () => new URLSearchParams(window.location.search).get("project") || "";
		const _ctx_close = () => { const m = document.getElementById("gantt-ctx-v6"); if (m) m.remove(); };
		const _svgpt = (e) => {
			const pt = svg.createSVGPoint();
			pt.x = e.clientX; pt.y = e.clientY;
			return pt.matrixTransform(svg.getScreenCTM().inverse());
		};

		// ── Double-click empty area → new task dialog ─────────────────────────
		svg.addEventListener("dblclick", (e) => {
			if (e.target.closest(".bar-wrapper") || e.target.closest(".arrow") || e.target.closest(".g-handle-overlay")) return;
			const sp = _svgpt(e);
			const cd = _x_to_date(sp.x);
			const ed = new Date(cd); ed.setDate(ed.getDate() + 3);
			const dlg = new frappe.ui.Dialog({
				title: __("New Task"),
				fields: [
					{fieldname:"subject", fieldtype:"Data", label:__("Subject"), reqd:1},
					{fieldname:"project", fieldtype:"Link", label:__("Project"), options:"Project", default:_proj()},
					{fieldname:"col1", fieldtype:"Column Break"},
					{fieldname:"status", fieldtype:"Select", label:__("Status"), options:"Open\nWorking\nPending Review\nOverdue\nCompleted\nCancelled", default:"Open"},
					{fieldname:"sec1", fieldtype:"Section Break"},
					{fieldname:"exp_start_date", fieldtype:"Date", label:__("Start Date"), default:_fmt(cd)},
					{fieldname:"exp_end_date",   fieldtype:"Date", label:__("End Date"),   default:_fmt(ed)},
					{fieldname:"col2", fieldtype:"Column Break"},
					{fieldname:"priority", fieldtype:"Select", label:__("Priority"), options:"Low\nMedium\nHigh\nUrgent", default:"Medium"},
					{fieldname:"sec2", fieldtype:"Section Break"},
					{fieldname:"description", fieldtype:"Small Text", label:__("Description")},
				],
				primary_action_label: __("Create Task"),
				primary_action: (v) => {
					frappe.call({
						method: "frappe.client.insert",
						args: {doc: {doctype:"Task", subject:v.subject, project:v.project,
							status:v.status, exp_start_date:v.exp_start_date,
							exp_end_date:v.exp_end_date, priority:v.priority,
							description:v.description||""}},
						callback: (r) => {
							if (r && r.message) {
								frappe.show_alert({message:__("Task {0} created",[r.message.name]), indicator:"green"}, 5);
								dlg.hide();
								me.refresh();
							}
						},
					});
				},
			});
			dlg.show();
		});

		// ── Blue dot handles on bar end → drag to link dependency ────────────
		const overlay = document.createElementNS("http://www.w3.org/2000/svg", "g");
		overlay.classList.add("g-handle-overlay");
		svg.appendChild(overlay);

		const _sync_handles = () => {
			while (overlay.firstChild) overlay.removeChild(overlay.firstChild);
			svg.querySelectorAll(".bar-wrapper").forEach((w) => {
				const b = w.querySelector(".bar");
				if (!b) return;
				const bx = parseFloat(b.getAttribute("x")) || 0;
				const by = parseFloat(b.getAttribute("y")) || 0;
				const bw = parseFloat(b.getAttribute("width")) || 100;
				const bh = parseFloat(b.getAttribute("height")) || 20;
				const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
				c.setAttribute("cx", bx + bw + 10);
				c.setAttribute("cy", by + bh / 2);
				c.setAttribute("r", 7);
				c.setAttribute("data-task", w.getAttribute("data-id") || "");
				overlay.appendChild(c);
			});
		};
		_sync_handles();
		// Re-sync handles every 2 s to stay in sync with Gantt re-renders
		this._v6_handle_timer = setInterval(_sync_handles, 2000);

		let _drag = null, _drag_line = null;

		svg.addEventListener("mousedown", (e) => {
			if (!e.target.closest(".g-handle-overlay") || e.target.tagName !== "circle") return;
			e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
			svg.classList.add("linking-mode");
			const sp = _svgpt(e);
			_drag_line = document.createElementNS("http://www.w3.org/2000/svg", "line");
			_drag_line.classList.add("gantt-drag-line");
			_drag_line.setAttribute("x1", sp.x); _drag_line.setAttribute("y1", sp.y);
			_drag_line.setAttribute("x2", sp.x); _drag_line.setAttribute("y2", sp.y);
			svg.appendChild(_drag_line);
			_drag = {from: e.target.getAttribute("data-task")};
		}, true);

		document.addEventListener("mousemove", (e) => {
			if (!_drag || !_drag_line) return;
			const sp = _svgpt(e);
			_drag_line.setAttribute("x2", sp.x);
			_drag_line.setAttribute("y2", sp.y);
		});

		document.addEventListener("mouseup", (e) => {
			if (!_drag) return;
			svg.classList.remove("linking-mode");
			if (_drag_line) { _drag_line.remove(); _drag_line = null; }

			// Find which bar the mouse was released over
			const sp = _svgpt(e);
			let tgt_wrapper = null;
			svg.querySelectorAll(".bar-wrapper").forEach((w) => {
				const b = w.querySelector(".bar");
				if (!b) return;
				const bx = parseFloat(b.getAttribute("x")) || 0;
				const by = parseFloat(b.getAttribute("y")) || 0;
				const bw = parseFloat(b.getAttribute("width")) || 0;
				const bh = parseFloat(b.getAttribute("height")) || 0;
				if (sp.x >= bx && sp.x <= bx + bw + 20 && sp.y >= by - 5 && sp.y <= by + bh + 5) {
					tgt_wrapper = w;
				}
			});

			const from_id = _drag.from;
			_drag = null;

			if (!tgt_wrapper) return;
			const to_id = tgt_wrapper.getAttribute("data-id");
			if (!to_id || to_id === from_id) return;

			frappe.confirm(
				__("Create dependency?<br><br><b>{0}</b> depends on <b>{1}</b>", [to_id, from_id]),
				() => {
					frappe.call({
						method: "frappe.client.get",
						args: {doctype: "Task", name: to_id},
						callback: (r) => {
							if (!r || !r.message) return;
							const task = r.message;
							const deps = task.depends_on || [];
							if (deps.some((d) => d.task === from_id)) {
								frappe.show_alert({message: __("Already linked"), indicator: "orange"}, 3);
								return;
							}
							deps.push({doctype:"Task Depends On", task:from_id, parenttype:"Task", parentfield:"depends_on"});
							task.depends_on = deps;
							frappe.call({
								method: "frappe.client.save",
								args: {doc: task},
								callback: (res) => {
									frappe.show_alert({
										message: res && !res.exc ? __("Dependency linked") : __("Failed to save"),
										indicator: res && !res.exc ? "green" : "red",
									}, 3);
									me.refresh();
								},
							});
						},
					});
				}
			);
		});

		// ── Click dependency arrow → unlink ───────────────────────────────────
		svg.addEventListener("click", (e) => {
			const ar = e.target.closest(".arrow");
			if (!ar) return;
			e.stopPropagation();

			let fi = ar.getAttribute("data-from");
			let ti = ar.getAttribute("data-to");

			// Fallback: look up by arrow index in the frappe-gantt arrows array
			if ((!fi || !ti) && this.gantt) {
				const all_arrows = Array.from(svg.querySelectorAll(".arrow"));
				const idx = all_arrows.indexOf(ar);
				const ga  = this.gantt.arrows || [];
				if (idx >= 0 && ga[idx]) {
					fi = fi || (ga[idx].from_task && ga[idx].from_task.task_id);
					ti = ti || (ga[idx].to_task  && ga[idx].to_task.task_id);
				}
			}

			if (!fi || !ti) {
				// Manual fallback: show a dialog to pick which dependency to remove
				const ids = [];
				svg.querySelectorAll(".bar-wrapper").forEach((w) => {
					const id = w.getAttribute("data-id");
					if (id) ids.push(id);
				});
				const dlg = new frappe.ui.Dialog({
					title: __("Remove Dependency"),
					fields: [
						{fieldname:"dep_task", fieldtype:"Select", label:__("Task (depends on)"), options:ids.join("\n"), reqd:1},
						{fieldname:"prereq",   fieldtype:"Select", label:__("Depends on"),        options:ids.join("\n"), reqd:1},
					],
					primary_action_label: __("Remove"),
					primary_action: (v) => { _rem_dep(v.dep_task, v.prereq); dlg.hide(); },
				});
				dlg.show();
				return;
			}

			frappe.confirm(
				__("Remove dependency?<br><br><b>{0}</b> depends on <b>{1}</b>", [ti, fi]),
				() => _rem_dep(ti, fi)
			);
		});

		const _rem_dep = (tn, pn) => {
			frappe.call({
				method: "frappe.client.get",
				args: {doctype:"Task", name:tn},
				callback: (r) => {
					if (!r || !r.message) return;
					const task = r.message;
					task.depends_on = (task.depends_on || []).filter((row) => row.task !== pn);
					frappe.call({
						method: "frappe.client.save",
						args: {doc: task},
						callback: () => {
							frappe.show_alert({message:__("Dependency removed"), indicator:"green"}, 3);
							me.refresh();
						},
					});
				},
			});
		};

		// ── Right-click bar → context menu ────────────────────────────────────
		svg.addEventListener("contextmenu", (e) => {
			const w = e.target.closest(".bar-wrapper");
			if (!w) return;
			e.preventDefault(); e.stopPropagation();
			const tn = w.getAttribute("data-id");
			if (!tn) return;
			_ctx_close();

			const m = document.createElement("div");
			m.className = "gantt-ctx-menu"; m.id = "gantt-ctx-v6";
			m.style.left = e.clientX + "px"; m.style.top = e.clientY + "px";
			m.innerHTML = `
				<div class="ctx-item" data-action="assign">${__("Assign To")}</div>
				<div class="ctx-item" data-action="open">${__("Open Task")}</div>
				<div class="ctx-sep"></div>
				<div class="ctx-item" data-action="status">${__("Change Status")}</div>
				<div class="ctx-item" data-action="priority">${__("Change Priority")}</div>`;
			document.body.appendChild(m);

			m.addEventListener("click", (ev) => {
				const it = ev.target.closest(".ctx-item");
				if (!it) return;
				const a = it.getAttribute("data-action");
				_ctx_close();
				if (a === "assign")   _dlg_assign(tn);
				if (a === "open")     frappe.set_route("Form", me.doctype, tn);
				if (a === "status")   _dlg_status(tn);
				if (a === "priority") _dlg_priority(tn);
			});
		});
		document.addEventListener("click", _ctx_close);

		const _dlg_assign = (tn) => {
			const dlg = new frappe.ui.Dialog({
				title: __("Assign — {0}", [tn]),
				fields: [{fieldname:"assign_to", fieldtype:"Link", label:__("Assign To"), options:"User", reqd:1}],
				primary_action_label: __("Assign"),
				primary_action: (v) => {
					frappe.call({
						method: "frappe.desk.form.utils.add_assignment",
						args: {doctype:"Task", name:tn, assign_to:[v.assign_to]},
						callback: (r) => {
							if (!r.exc) { frappe.show_alert({message:__("Assigned"), indicator:"green"}, 3); dlg.hide(); me.refresh(); }
						},
					});
				},
			});
			dlg.show();
		};

		const _dlg_status = (tn) => {
			const dlg = new frappe.ui.Dialog({
				title: __("Status — {0}", [tn]),
				fields: [{fieldname:"status", fieldtype:"Select", label:__("Status"),
					options:"Open\nWorking\nPending Review\nOverdue\nCompleted\nCancelled", reqd:1}],
				primary_action_label: __("Update"),
				primary_action: (v) => {
					frappe.call({
						method: "frappe.client.set_value",
						args: {doctype:"Task", name:tn, fieldname:"status", value:v.status},
						callback: () => { frappe.show_alert({message:__("Status updated"), indicator:"green"}, 3); dlg.hide(); me.refresh(); },
					});
				},
			});
			dlg.show();
		};

		const _dlg_priority = (tn) => {
			const dlg = new frappe.ui.Dialog({
				title: __("Priority — {0}", [tn]),
				fields: [{fieldname:"priority", fieldtype:"Select", label:__("Priority"),
					options:"Low\nMedium\nHigh\nUrgent", reqd:1}],
				primary_action_label: __("Update"),
				primary_action: (v) => {
					frappe.call({
						method: "frappe.client.set_value",
						args: {doctype:"Task", name:tn, fieldname:"priority", value:v.priority},
						callback: () => { frappe.show_alert({message:__("Priority updated"), indicator:"green"}, 3); dlg.hide(); me.refresh(); },
					});
				},
			});
			dlg.show();
		};
	}

	setup_critical_path_legend() {
		this.$paging_area.find(".gantt-cp-legend").remove();

		const tasks = (this.tasks || []).filter((t) => !t._is_actual);
		const critical_count       = tasks.filter((t) => t.is_critical).length;
		const delayed_critical     = tasks.filter((t) => t.is_critical && t.is_delayed).length;
		const delayed_non_critical = tasks.filter((t) => !t.is_critical && t.is_delayed).length;

		if (critical_count === 0) return;

		let badges = `<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 7px;background:#fdecea;color:#c0392b;border-radius:10px;font-size:0.8em;font-weight:600;">
				&#128308; ${critical_count} critical
			</span>`;

		if (delayed_critical > 0) {
			badges += `&nbsp;<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 7px;background:#c0392b;color:#fff;border-radius:10px;font-size:0.8em;font-weight:600;">
				&#9888; ${delayed_critical} delayed on CP
			</span>`;
		}
		if (delayed_non_critical > 0) {
			badges += `&nbsp;<span style="display:inline-flex;align-items:center;gap:4px;padding:2px 7px;background:#fef5e7;color:#d35400;border-radius:10px;font-size:0.8em;font-weight:600;">
				&#9651; ${delayed_non_critical} delayed (buffered)
			</span>`;
		}

		const $legend = $(`<div class="gantt-cp-legend mx-2" style="display:inline-flex;align-items:center;gap:4px;">${badges}</div>`);
		this.$paging_area.find(".level-left").append($legend);
	}

	setup_gantt_legend() {
		this.$wrapper.find(".gantt-legend-bar").remove();

		const swatch = (color, opts = {}) => {
			const border   = opts.border   ? `border: 2px solid ${opts.border};` : "";
			const dash     = opts.dash     ? `background: repeating-linear-gradient(90deg, ${color} 0px, ${color} 6px, transparent 6px, transparent 9px) !important;` : `background: ${color};`;
			const opacity  = opts.actual   ? "opacity: 0.85;" : "";
			const radius   = opts.diamond  ? "border-radius:2px;transform:rotate(45deg);" : "border-radius:3px;";
			const width    = opts.diamond  ? "13px" : "30px";
			return `<span style="display:inline-block;width:${width};height:13px;${dash}${border}${opacity}${radius}flex-shrink:0;"></span>`;
		};

		const item = (sw, label) =>
			`<div style="display:flex;align-items:center;gap:5px;white-space:nowrap;">
				${sw}
				<span>${label}</span>
			</div>`;

		const todayLine = `<span style="display:inline-flex;align-items:center;gap:2px;flex-shrink:0;">
			<span style="display:inline-block;width:2px;height:18px;background:#e74c3c;border-left:2px dashed #e74c3c;flex-shrink:0;"></span>
		</span>`;
		const milestoneDiamond = `<span style="display:inline-block;width:13px;height:13px;background:#ff6b6b;transform:rotate(45deg);border-radius:2px;flex-shrink:0;"></span>`;
		const adjustedSwatch = `<span style="display:inline-block;width:30px;height:13px;border-radius:3px;flex-shrink:0;
			background:#3498db;border:1.5px dashed #1a6fa8;"></span>`;

		const items = [
			item(swatch("#b0bec5"),                                      "Normal task"),
			item(swatch("#78909c"),                                      "Group / summary task"),
			item(swatch("#2e86c1"),                                      "Critical path — on schedule"),
			item(swatch("#e74c3c", { border: "#c0392b" }),              "Critical & delayed — impacts end date"),
			item(swatch("#e67e22"),                                      "Delayed — has buffer (not critical)"),
			item(adjustedSwatch,                                        "Rescheduled by cascade"),
			item(swatch("#27ae60", { actual: true }),                    "Actual progress — on time"),
			item(swatch("#e74c3c", { border: "#922b21", actual: true }), "Actual progress — late"),
			item(milestoneDiamond,                                      "Milestone"),
			item(todayLine,                                             "Today"),
		];

		const $legend = $(`
			<div class="gantt-legend-bar" style="
				display: flex;
				flex-wrap: wrap;
				align-items: center;
				gap: 14px 20px;
				padding: 10px 16px;
				margin: 10px 4px 4px;
				background: var(--fg-color, #fff);
				border: 1px solid var(--border-color, #e0e0e0);
				border-radius: 6px;
				font-size: 0.78em;
				color: #555;
				font-family: var(--font-stack);
				box-shadow: 0 1px 4px rgba(0,0,0,0.05);
			">
				<span style="font-weight:700;color:#333;margin-right:2px;font-size:0.95em;">Legend</span>
				<span style="width:1px;height:18px;background:var(--border-color,#e0e0e0);flex-shrink:0;"></span>
				${items.join("")}
			</div>
		`);

		this.$result.after($legend);
	}

	setup_summary_toggle() {
		this.$paging_area.find(".gantt-summary-toggle").remove();
		this.$paging_area.find(".gantt-collapse-controls").remove();

		const is_summary = this._summary_mode !== false;

		// ── Summary / Full Detail toggle ──────────────────────────────────────
		const $btn = $(`
			<div class="mx-2 gantt-summary-toggle">
				<button class="btn btn-sm ${is_summary ? "btn-primary" : "btn-default"}"
					title="${is_summary ? __("Showing groups & milestones only — click for full detail") : __("Showing all tasks — click for summary view")}">
					${is_summary ? "&#9781; " + __("Summary") : "&#9783; " + __("Full Detail")}
				</button>
			</div>
		`);
		this.$paging_area.find(".level-left").prepend($btn);
		$btn.on("click", "button", () => {
			this._summary_mode = !this._summary_mode;
			this._collapsed.clear();  // reset collapse state when toggling view
			this.prepare_data(this.data);
			this.render_gantt();
		});

		// ── Expand All / Collapse All ─────────────────────────────────────────
		// Collect IDs of all group tasks currently visible
		const group_ids = (this.data || [])
			.filter((d) => d.is_group)
			.map((d) => d.name);

		if (group_ids.length === 0) return;

		const all_collapsed = this._collapsed.size >= group_ids.length;
		const $cc = $(`
			<div class="mx-1 gantt-collapse-controls" style="display:inline-flex;gap:4px;">
				<button class="btn btn-xs btn-default gantt-expand-all" title="${__("Expand all groups")}">&#9783; ${__("Expand All")}</button>
				<button class="btn btn-xs btn-default gantt-collapse-all" title="${__("Collapse all groups")}">&#9781; ${__("Collapse All")}</button>
			</div>
		`);
		this.$paging_area.find(".level-left").prepend($cc);

		$cc.on("click", ".gantt-expand-all", () => {
			this._collapsed.clear();
			this.prepare_data(this.data);
			this.render_gantt();
		});
		$cc.on("click", ".gantt-collapse-all", () => {
			group_ids.forEach((id) => this._collapsed.add(id));
			this.prepare_data(this.data);
			this.render_gantt();
		});
	}

	setup_view_mode_buttons() {
		// view modes (for translation) __("Day"), __("Week"), __("Month"),
		//__("Half Day"), __("Quarter Day")

		let $btn_group = this.$paging_area.find(".gantt-view-mode");
		if ($btn_group.length > 0) return;

		const view_modes = (this.gantt && this.gantt.options && this.gantt.options.view_modes) || [];
		const active_class = (view_mode) =>
			this.gantt && this.gantt.view_is(view_mode) ? "btn-info" : "";
		const html = `<div class="btn-group gantt-view-mode mx-2">
				${view_modes
					.map(
						(value) => `<button type="button"
						class="btn btn-default btn-sm btn-view-mode ${active_class(value)}"
						data-value="${value}">
						${__(value)}
					</button>`
					)
					.join("")}
			</div>`;

		this.$paging_area.find(".level-left").append(html);

		const change_view_mode = (value) =>
			setTimeout(() => this.gantt && this.gantt.change_view_mode(value), 0);

		this.$paging_area.on("click", ".btn-view-mode", (e) => {
			const $btn = $(e.currentTarget);
			this.$paging_area.find(".btn-view-mode").removeClass("btn-info");
			$btn.addClass("btn-info");
			change_view_mode($btn.data().value);
		});
	}

	setup_view_mode_buttons_empty() {
		// placeholder when no tasks — just show disabled view mode group so layout stays consistent
		let $btn_group = this.$paging_area.find(".gantt-view-mode");
		if ($btn_group.length > 0) return;
		this.$paging_area.find(".level-left").append(
			`<div class="btn-group gantt-view-mode mx-2">
				<button class="btn btn-default btn-sm" disabled>${__("Day")}</button>
				<button class="btn btn-default btn-sm" disabled>${__("Week")}</button>
				<button class="btn btn-default btn-sm" disabled>${__("Month")}</button>
			</div>`
		);
	}

	// ── Microsoft Project Export ─────────────────────────────────────────────────
	setup_export_button() {
		if (this.$paging_area.find(".gantt-export-btn").length > 0) return;

		const $export_btn = $(`
			<div class="mx-2">
				<div class="dropdown gantt-export-btn">
					<button class="btn btn-default btn-sm dropdown-toggle" data-toggle="dropdown">
						<svg viewBox="0 0 24 24" style="width:14px;height:14px;vertical-align:-2px;fill:none;stroke:currentColor;stroke-width:2">
							<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
							<polyline points="7 10 12 15 17 10"/>
							<line x1="12" y1="15" x2="12" y2="3"/>
						</svg>
						${__("Export")}
					</button>
					<ul class="dropdown-menu dropdown-menu-right">
						<li><a class="dropdown-item gantt-export-pdf" href="#">
							🖨 ${__("PDF (print)")}
						</a></li>
						<li><a class="dropdown-item gantt-export-msproject" href="#">
							📊 ${__("Microsoft Project (.xml)")}
						</a></li>
						<li><a class="dropdown-item gantt-export-csv" href="#">
							📄 ${__("CSV")}
						</a></li>
						<li><a class="dropdown-item gantt-export-json" href="#">
							🗂 ${__("JSON")}
						</a></li>
					</ul>
				</div>
			</div>
		`);

		this.$paging_area.find(".level-left").append($export_btn);

		$export_btn.on("click", ".gantt-export-pdf", (e) => {
			e.preventDefault();
			this.export_pdf();
		});
		$export_btn.on("click", ".gantt-export-msproject", (e) => {
			e.preventDefault();
			this.export_ms_project();
		});
		$export_btn.on("click", ".gantt-export-csv", (e) => {
			e.preventDefault();
			this.export_csv();
		});
		$export_btn.on("click", ".gantt-export-json", (e) => {
			e.preventDefault();
			this.export_json();
		});
	}

	export_pdf() {
		const tasks = (this.tasks || []).filter((t) => !t._is_actual);
		if (!tasks.length) {
			frappe.show_alert({ message: __("No tasks to export."), indicator: "orange" });
			return;
		}

		const project_name = this.page_title.replace(" Gantt", "").trim() || this.doctype;
		const to_ms  = (s) => new Date(s).getTime();
		const fmt_dt = (s) => s; // already YYYY-MM-DD

		// ── Date range ────────────────────────────────────────────────────────
		const all_ms    = tasks.flatMap((t) => [to_ms(t.start), to_ms(t.end)]);
		const r_start   = new Date(Math.min(...all_ms));
		const r_end     = new Date(Math.max(...all_ms));
		r_start.setUTCDate(r_start.getUTCDate() - 2);
		r_end.setUTCDate(r_end.getUTCDate() + 5);

		const total_days = Math.ceil((r_end - r_start) / 86400000);
		const PX         = 22;         // pixels per day
		const ROW_H      = 26;         // task row height px
		const HDR_H      = 40;         // two-row date header height
		const chart_w    = total_days * PX;
		const chart_h    = HDR_H + tasks.length * ROW_H + 2;

		const x_of  = (s) => Math.round((new Date(s) - r_start) / 86400000) * PX;
		const w_of  = (s, e) => Math.max(4, Math.round((new Date(e) - new Date(s)) / 86400000) * PX);

		// ── SVG: row backgrounds + grid ───────────────────────────────────────
		let svg_bg = "", svg_bars = "", svg_hdr = "";

		tasks.forEach((t, i) => {
			const y = HDR_H + i * ROW_H;
			svg_bg += `<rect x="0" y="${y}" width="${chart_w}" height="${ROW_H}" fill="${i % 2 === 0 ? "#fff" : "#f4f7fb"}"/>`;
			svg_bg += `<line x1="0" y1="${y + ROW_H}" x2="${chart_w}" y2="${y + ROW_H}" stroke="#dde3ee" stroke-width="0.5"/>`;
		});

		// ── SVG: date headers ─────────────────────────────────────────────────
		// Month band (top row)
		svg_hdr += `<rect x="0" y="0" width="${chart_w}" height="${HDR_H}" fill="#4472C4"/>`;
		{
			let cur = new Date(Date.UTC(r_start.getUTCFullYear(), r_start.getUTCMonth(), 1));
			while (cur < r_end) {
				const mx = Math.max(0, x_of(cur.toISOString().slice(0, 10)));
				const nxt = new Date(Date.UTC(cur.getUTCFullYear(), cur.getUTCMonth() + 1, 1));
				const label = cur.toLocaleDateString("en", { month: "short", year: "numeric", timeZone: "UTC" });
				svg_hdr += `<text x="${mx + 4}" y="15" fill="#fff" font-size="10" font-family="Arial" font-weight="bold">${label}</text>`;
				if (mx > 0) svg_hdr += `<line x1="${mx}" y1="0" x2="${mx}" y2="${HDR_H}" stroke="#2E5395" stroke-width="1"/>`;
				cur = nxt;
			}
		}
		// Day numbers (bottom row of header)
		{
			let cur = new Date(r_start);
			while (cur < r_end) {
				const dx      = x_of(cur.toISOString().slice(0, 10));
				const day_num = cur.getUTCDate();
				const is_wkd  = cur.getUTCDay() === 0 || cur.getUTCDay() === 6;
				svg_hdr += `<rect x="${dx}" y="22" width="${PX}" height="${HDR_H - 22}" fill="${is_wkd ? "#8EA9D0" : "#4472C4"}"/>`;
				svg_hdr += `<text x="${dx + PX / 2}" y="35" text-anchor="middle" fill="#fff" font-size="8" font-family="Arial">${day_num}</text>`;
				svg_hdr += `<line x1="${dx}" y1="22" x2="${dx}" y2="${chart_h}" stroke="#9BBCD6" stroke-width="0.3"/>`;
				cur.setUTCDate(cur.getUTCDate() + 1);
			}
		}

		// ── SVG: bars ─────────────────────────────────────────────────────────
		tasks.forEach((t, i) => {
			const y  = HDR_H + i * ROW_H;
			const bx = x_of(t.start);
			const bw = w_of(t.start, t.end);
			const by = y + 5;
			const bh = ROW_H - 10;
			const pct = t.progress || 0;

			let fill = "#4472C4";
			if (t.is_critical && t.is_delayed)  fill = "#C0392B";
			else if (t.is_critical)              fill = "#E74C3C";
			else if (t.is_delayed)               fill = "#E67E22";
			else if (t.is_adjusted)              fill = "#3498DB";

			svg_bars += `<rect x="${bx}" y="${by}" width="${bw}" height="${bh}" rx="2" fill="${fill}"/>`;
			if (pct > 0 && pct < 100) {
				svg_bars += `<rect x="${bx}" y="${by}" width="${Math.round(bw * pct / 100)}" height="${bh}" rx="2" fill="rgba(0,0,0,0.28)"/>`;
			}

			// Dependency arrows (simple elbow from predecessor bar end to this bar start)
			const deps = (t.dependencies || "").split(",").map((d) => d.trim()).filter(Boolean);
			deps.forEach((dep_id) => {
				const pred = tasks.find((p) => p.id === dep_id || p.id === dep_id.replaceAll("_", " "));
				if (!pred) return;
				const pred_i = tasks.indexOf(pred);
				const px_end = x_of(pred.end);
				const py_mid = HDR_H + pred_i * ROW_H + ROW_H / 2;
				const ty_mid = y + ROW_H / 2;
				svg_bars += `<polyline points="${px_end},${py_mid} ${bx - 4},${py_mid} ${bx - 4},${ty_mid} ${bx},${ty_mid}"
					fill="none" stroke="#555" stroke-width="1" marker-end="url(#arrow)"/>`;
			});
		});

		// Today line
		const today_x = x_of(frappe.datetime.now_date());
		if (today_x > 0 && today_x < chart_w) {
			svg_bars += `<line x1="${today_x}" y1="${HDR_H}" x2="${today_x}" y2="${chart_h}" stroke="#E74C3C" stroke-width="1.5" stroke-dasharray="5,3"/>`;
			svg_bars += `<text x="${today_x + 2}" y="${HDR_H - 3}" fill="#E74C3C" font-size="8" font-family="Arial">Today</text>`;
		}

		const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${chart_w}" height="${chart_h}">
			<defs>
				<marker id="arrow" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
					<path d="M0,0 L0,6 L6,3 z" fill="#555"/>
				</marker>
			</defs>
			${svg_bg}${svg_hdr}${svg_bars}
		</svg>`;

		// ── Task table (left panel) ───────────────────────────────────────────
		const table_rows = tasks.map((t, i) => {
			const pct  = Math.round(t.progress || 0);
			const name = t.name.replace(/<[^>]+>/g, "");
			const bg   = i % 2 === 0 ? "#fff" : "#f4f7fb";
			return `<tr style="height:${ROW_H}px;background:${bg};">
				<td style="text-align:center;">${i + 1}</td>
				<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-left:6px;" title="${name}">${name}</td>
				<td style="text-align:center;white-space:nowrap;">${t.start}</td>
				<td style="text-align:center;white-space:nowrap;">${t.end}</td>
				<td style="text-align:center;">${pct}%</td>
			</tr>`;
		}).join("");

		// ── Full HTML document ────────────────────────────────────────────────
		const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>${project_name} — Gantt Chart</title>
<style>
	* { margin:0; padding:0; box-sizing:border-box; }
	body { font-family: Arial, sans-serif; font-size: 10px; padding: 12px; background:#fff; }
	@page { size: A3 landscape; margin: 10mm; }
	h1 { font-size: 14px; color: #2E5395; margin-bottom: 3px; }
	.meta { font-size: 9px; color: #777; margin-bottom: 10px; }
	.gantt-wrap { display: flex; align-items: flex-start; border: 1px solid #9BBCD6; border-radius: 4px; overflow: hidden; }
	.left-panel table { border-collapse: collapse; border-right: 2px solid #4472C4; }
	.left-panel th { background: #4472C4; color: #fff; padding: 2px 6px; border: 1px solid #2E5395; height: ${HDR_H}px; vertical-align: middle; }
	.left-panel td { padding: 2px 4px; border: 1px solid #d0d8e8; }
	.right-panel { overflow-x: auto; flex: 1; }
	.legend { display: flex; gap: 14px; margin-top: 10px; font-size: 9px; flex-wrap: wrap; }
	.legend-item { display: flex; align-items: center; gap: 5px; }
	.legend-dot { width: 16px; height: 10px; border-radius: 2px; flex-shrink: 0; }
	@media print { body { padding: 0; } }
</style>
</head>
<body>
<h1>${project_name} — Gantt Chart</h1>
<div class="meta">Generated: ${new Date().toLocaleString()} &nbsp;·&nbsp; ${tasks.length} tasks &nbsp;·&nbsp; Styloworld ERP</div>

<div class="gantt-wrap">
	<div class="left-panel">
		<table>
			<thead>
				<tr style="height:${HDR_H}px;">
					<th style="width:28px;text-align:center;">ID</th>
					<th style="width:200px;">Task Name</th>
					<th style="width:80px;text-align:center;">Start</th>
					<th style="width:80px;text-align:center;">Finish</th>
					<th style="width:42px;text-align:center;">Done</th>
				</tr>
			</thead>
			<tbody>${table_rows}</tbody>
		</table>
	</div>
	<div class="right-panel">${svg}</div>
</div>

<div class="legend">
	<div class="legend-item"><div class="legend-dot" style="background:#4472C4;"></div>Normal</div>
	<div class="legend-item"><div class="legend-dot" style="background:#E74C3C;"></div>Critical path</div>
	<div class="legend-item"><div class="legend-dot" style="background:#E67E22;"></div>Delayed (buffered)</div>
	<div class="legend-item"><div class="legend-dot" style="background:#C0392B;"></div>Critical + Delayed</div>
	<div class="legend-item"><div class="legend-dot" style="background:#3498DB;border:1px dashed #1A6FA8;"></div>Rescheduled</div>
	<div class="legend-item"><div style="width:2px;height:14px;background:#E74C3C;border-left:2px dashed #E74C3C;margin-right:3px;"></div>Today</div>
</div>

<script>window.onload = function() { setTimeout(window.print, 400); };</script>
</body>
</html>`;

		const win = window.open("", "_blank");
		if (!win) {
			frappe.show_alert({ message: __("Popup blocked — please allow popups for this site."), indicator: "orange" });
			return;
		}
		win.document.write(html);
		win.document.close();
	}

	export_ms_project() {
		const tasks = (this.tasks || []).filter((t) => !t._is_actual);
		if (!tasks || tasks.length === 0) {
			frappe.show_alert({ message: __("No tasks to export."), indicator: "orange" });
			return;
		}

		const project_name = this.page_title.replace(" Gantt", "").trim() || this.doctype;
		const now_iso = new Date().toISOString().slice(0, 19);

		// Find overall project start and end
		const all_starts = tasks.map((t) => new Date(t.start)).filter((d) => !isNaN(d));
		const all_ends   = tasks.map((t) => new Date(t.end)).filter((d) => !isNaN(d));
		const proj_start = all_starts.length ? new Date(Math.min(...all_starts)) : new Date();
		const proj_end   = all_ends.length   ? new Date(Math.max(...all_ends))   : new Date();

		const fmt_dt = (d) => {
			// MS Project expects ISO 8601 datetime: 2024-01-15T08:00:00
			const dt = new Date(d);
			return dt.toISOString().slice(0, 19);
		};

		const calc_duration_days = (start, end) => {
			const ms = new Date(end) - new Date(start);
			return Math.max(1, Math.round(ms / 86400000));
		};

		const fmt_duration = (days) => {
			// MS Project duration: PT8H0M0S = 1 day, P5DT0H0M0S = 5 days
			const hours = days * 8; // 8-hour working day
			if (hours < 8) return `PT${hours}H0M0S`;
			return `P${days}DT0H0M0S`;
		};

		// Build a UID map so dependencies can reference predecessor UIDs
		const uid_map = {};
		tasks.forEach((t, i) => { uid_map[t.id] = i + 1; });

		let tasks_xml = "";

		// Task UID 0 = project summary row (required by MS Project)
		tasks_xml += `
		<Task>
			<UID>0</UID>
			<ID>0</ID>
			<Name>${_xml_escape(project_name)}</Name>
			<Milestone>0</Milestone>
			<Summary>1</Summary>
			<Start>${fmt_dt(proj_start)}</Start>
			<Finish>${fmt_dt(proj_end)}</Finish>
			<Duration>${fmt_duration(calc_duration_days(proj_start, proj_end))}</Duration>
		</Task>`;

		tasks.forEach((task, i) => {
			const uid = i + 1;
			const days = calc_duration_days(task.start, task.end);
			const pct = Math.round(task.progress || 0);
			const is_milestone = task.custom_class === "bar-milestone" ? 1 : 0;

			// Build predecessor links
			const dep_ids = Array.isArray(task.dependencies)
				? task.dependencies
				: (task.dependencies || "").split(",").map((s) => s.trim()).filter(Boolean);

			const pred_xml = dep_ids
				.map((dep_id) => {
					const dep_uid = uid_map[dep_id] || uid_map[dep_id.replaceAll("_", " ")];
					if (!dep_uid) return "";
					return `\t\t\t<PredecessorLink>
					<PredecessorUID>${dep_uid}</PredecessorUID>
					<Type>1</Type>
				</PredecessorLink>`;
				})
				.filter(Boolean)
				.join("\n");

			tasks_xml += `
		<Task>
			<UID>${uid}</UID>
			<ID>${uid}</ID>
			<Name>${_xml_escape(task.name)}</Name>
			<Milestone>${is_milestone}</Milestone>
			<Summary>0</Summary>
			<Start>${fmt_dt(task.start)}</Start>
			<Finish>${fmt_dt(task.end)}</Finish>
			<Duration>${fmt_duration(days)}</Duration>
			<PercentComplete>${pct}</PercentComplete>
			${pred_xml}
		</Task>`;
		});

		const xml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Project xmlns="http://schemas.microsoft.com/project">
	<Name>${_xml_escape(project_name)}</Name>
	<Title>${_xml_escape(project_name)}</Title>
	<Author>Styloworld ERP</Author>
	<CreationDate>${now_iso}</CreationDate>
	<StartDate>${fmt_dt(proj_start)}</StartDate>
	<FinishDate>${fmt_dt(proj_end)}</FinishDate>
	<DefaultStartTime>08:00:00</DefaultStartTime>
	<DefaultFinishTime>17:00:00</DefaultFinishTime>
	<HoursPerDay>8</HoursPerDay>
	<DaysPerMonth>20</DaysPerMonth>
	<Tasks>${tasks_xml}
	</Tasks>
</Project>`;

		_download_file(
			xml,
			`${project_name.replace(/\s+/g, "_")}_gantt.xml`,
			"application/xml"
		);

		frappe.show_alert({
			message: __("Exported {0} tasks as Microsoft Project XML", [tasks.length]),
			indicator: "green",
		});
	}

	export_csv() {
		const tasks = (this.tasks || []).filter((t) => !t._is_actual);
		if (!tasks || tasks.length === 0) {
			frappe.show_alert({ message: __("No tasks to export."), indicator: "orange" });
			return;
		}
		const headers = ["ID", "Name", "Start", "End", "Progress (%)", "Dependencies"];
		const rows = tasks.map((t) => [
			_csv_escape(t.id),
			_csv_escape(t.name),
			t.start,
			t.end,
			Math.round(t.progress || 0),
			_csv_escape(Array.isArray(t.dependencies) ? t.dependencies.join(", ") : (t.dependencies || "")),
		]);
		const csv = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
		const project_name = this.page_title.replace(" Gantt", "").trim() || this.doctype;
		_download_file(csv, `${project_name.replace(/\s+/g, "_")}_gantt.csv`, "text/csv");
		frappe.show_alert({ message: __("CSV exported"), indicator: "green" });
	}

	export_json() {
		const tasks = (this.tasks || []).filter((t) => !t._is_actual);
		if (!tasks || tasks.length === 0) {
			frappe.show_alert({ message: __("No tasks to export."), indicator: "orange" });
			return;
		}
		const project_name = this.page_title.replace(" Gantt", "").trim() || this.doctype;
		const payload = tasks.map((t) => ({
			id: t.id,
			name: t.name,
			start: t.start,
			end: t.end,
			progress: Math.round(t.progress || 0),
			dependencies: Array.isArray(t.dependencies) ? t.dependencies : [],
		}));
		_download_file(
			JSON.stringify({ project: project_name, tasks: payload }, null, 2),
			`${project_name.replace(/\s+/g, "_")}_gantt.json`,
			"application/json"
		);
		frappe.show_alert({ message: __("JSON exported"), indicator: "green" });
	}

	set_colors() {
		const classes = this.tasks
			.map((t) => t.custom_class)
			.filter((c) => c && c.startsWith("color-"));

		let style = classes
			.map((c) => {
				const class_name = c.replace("#", "");
				const bar_color = "#" + c.substr(6);
				const progress_color = frappe.ui.color.get_contrast_color(bar_color);
				return `
				.gantt .bar-wrapper.${class_name} .bar {
					fill: ${bar_color};
				}
				.gantt .bar-wrapper.${class_name} .bar-progress {
					fill: ${progress_color};
				}
			`;
			})
			.join("");

		this.$result.prepend(`<style>${style}</style>`);
	}

	get_item(name) {
		// The gantt library replaces spaces with underscores in task IDs — match both
		return (
			this.data.find((item) => item.name === name) ||
			this.data.find((item) => (item.name || "").replaceAll(" ", "_") === name)
		);
	}

	get required_libs() {
		return [
			"assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.css",
			"assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.min.js",
		];
	}
};

// ── Helpers (file-private) ────────────────────────────────────────────────────

function _xml_escape(str) {
	return String(str || "")
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;")
		.replace(/'/g, "&apos;");
}

function _csv_escape(val) {
	const s = String(val || "");
	if (s.includes(",") || s.includes('"') || s.includes("\n")) {
		return '"' + s.replace(/"/g, '""') + '"';
	}
	return s;
}

function _download_file(content, filename, mime) {
	const blob = new Blob([content], { type: mime });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = filename;
	document.body.appendChild(a);
	a.click();
	setTimeout(() => {
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}, 100);
}
// build: 1781258376
