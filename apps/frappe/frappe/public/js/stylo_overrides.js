// Stylo brand overrides — replace "frappe" with "Stylo" in all user-facing messages
// and expose `stylo` as a global alias so scripts work with either namespace.

(function () {
	// ── Global alias: window.stylo === frappe ──────────────────────────────────
	window.stylo = frappe;

	// ── Full width by default ─────────────────────────────────────────────────
	// Always force full width — set localStorage so toolbar.set_fullwidth_if_enabled
	// also knows, and apply the class directly once the app is ready.
	localStorage.setItem("container_fullwidth", "true");

	$(document).on("app_ready", function () {
		$(document.body).addClass("full-width");
		// Keep toolbar's own state in sync so its toggle button works correctly
		if (frappe.ui.toolbar && frappe.ui.toolbar.set_fullwidth_if_enabled) {
			frappe.ui.toolbar.set_fullwidth_if_enabled();
		}
	});

	// ── Helpers ────────────────────────────────────────────────────────────────
	function sanitize(text) {
		if (typeof text !== "string") return text;
		// Replace "frappe" (any case) with "Stylo" in user-visible strings,
		// but keep internal Python paths readable by lowercasing "frappe" → "stylo"
		return text
			.replace(/\bFrappe\b/g, "Stylo")
			.replace(/\bfrappe\b/g, "stylo");
	}

	function sanitize_html(html) {
		if (typeof html !== "string") return html;
		// Only replace text content — not attributes or code paths inside <code>/<pre>
		return html.replace(/(<(?!code|pre)[^>]+>|^)([^<]*)(<\/(?!code|pre))/g, function (m, open, text, close) {
			return open + sanitize(text) + close;
		}).replace(/\bFrappe\b(?=[^<]*(?:<|$))/g, "Stylo")
		  .replace(/\bfrappe\b(?=[^<]*(?:<|$))/g, "stylo");
	}

	// ── Patch frappe.throw ─────────────────────────────────────────────────────
	const _orig_throw = frappe.throw.bind(frappe);
	frappe.throw = function (msg) {
		if (typeof msg === "string") msg = sanitize(msg);
		_orig_throw(msg);
	};

	// ── Patch frappe.msgprint ──────────────────────────────────────────────────
	const _orig_msgprint = frappe.msgprint.bind(frappe);
	frappe.msgprint = function (opts) {
		if (typeof opts === "string") {
			opts = sanitize(opts);
		} else if (opts && typeof opts === "object") {
			if (opts.message) opts.message = sanitize(opts.message);
			if (opts.title) opts.title = sanitize(opts.title);
		}
		_orig_msgprint(opts);
	};

	// ── Patch frappe.show_alert ────────────────────────────────────────────────
	const _orig_alert = frappe.show_alert.bind(frappe);
	frappe.show_alert = function (opts, seconds) {
		if (typeof opts === "string") {
			opts = sanitize(opts);
		} else if (opts && typeof opts === "object") {
			if (opts.message) opts.message = sanitize(opts.message);
		}
		_orig_alert(opts, seconds);
	};

	// ── Patch frappe.show_progress ─────────────────────────────────────────────
	const _orig_progress = frappe.show_progress.bind(frappe);
	frappe.show_progress = function (title, ...args) {
		_orig_progress(sanitize(title), ...args);
	};

	// ── Patch call error handler to sanitize server error messages ─────────────
	const _orig_call = frappe.call.bind(frappe);
	frappe.call = function (opts, ...rest) {
		// frappe.call supports two signatures:
		// 1. frappe.call({ method, args, ... })
		// 2. frappe.call("method.name", { args })  ← rest[0] is the args object
		if (opts && typeof opts === "object") {
			const orig_error = opts.error;
			opts.error = function (r) {
				if (r && r.exc) r.exc = sanitize(r.exc);
				if (r && r._server_messages) {
					try {
						const msgs = JSON.parse(r._server_messages);
						r._server_messages = JSON.stringify(
							msgs.map((m) => {
								try {
									const parsed = JSON.parse(m);
									if (parsed.message) parsed.message = sanitize(parsed.message);
									return JSON.stringify(parsed);
								} catch (e) {
									return sanitize(m);
								}
							})
						);
					} catch (e) {}
				}
				if (orig_error) orig_error(r);
			};
		}
		return _orig_call(opts, ...rest);
	};

	// ── Redirect all external frappe/erpnext doc links → styloworld.io ─────────
	const EXTERNAL_DOMAINS = [
		"docs.erpnext.com",
		"docs.frappe.io",
		"frappe.io",
		"frappe.school",
		"discuss.frappe.io",
		"frappecloud.com",
		"erpnext.com",
	];

	function is_external_frappe_url(href) {
		if (!href) return false;
		return EXTERNAL_DOMAINS.some((d) => href.includes(d));
	}

	function redirect_link(href) {
		return "https://styloworld.io";
	}

	// Intercept window.open for programmatic link opens
	const _orig_open = window.open.bind(window);
	window.open = function (url, ...args) {
		if (is_external_frappe_url(url)) url = redirect_link(url);
		return _orig_open(url, ...args);
	};

	// Patch any <a> links rendered into the DOM
	function patch_links(root) {
		(root || document).querySelectorAll("a[href]").forEach((a) => {
			if (is_external_frappe_url(a.href)) {
				a.href = redirect_link(a.href);
				a.textContent = a.textContent
					.replace(/https?:\/\/(www\.)?(docs\.)?(erpnext|frappe)\.[a-z.]+\/?[^\s]*/gi, "styloworld.io")
					.replace(/\bFrappe\b/g, "Stylo")
					.replace(/\bERPNext\b/g, "StyloBMS");
			}
		});
	}

	// Also patch the help_links array at boot time
	document.addEventListener("DOMContentLoaded", function () {
		if (frappe.utils && frappe.utils.help_links) {
			Object.keys(frappe.utils.help_links).forEach((key) => {
				frappe.utils.help_links[key].forEach((item) => {
					if (is_external_frappe_url(item.url)) item.url = redirect_link(item.url);
				});
			});
		}
		patch_links(document);
	});

	// ── DOM observer: catch any remaining "frappe" text in toasts/dialogs ──────
	function patch_node(node) {
		if (node.nodeType === Node.TEXT_NODE) {
			const t = node.textContent;
			if (t && (t.includes("frappe") || t.includes("Frappe"))) {
				node.textContent = sanitize(t);
			}
		}
	}

	const observer = new MutationObserver(function (mutations) {
		mutations.forEach(function (m) {
			m.addedNodes.forEach(function (node) {
				// Only patch inside alert/dialog areas to avoid touching code editors
				const parents = [
					".frappe-toast", ".msgprint-dialog", ".modal-dialog",
					".alert", "#page-desktop"
				];
				const inTarget = parents.some((sel) => node.closest && node.closest(sel));
				if (!inTarget) return;
				if (node.nodeType === Node.TEXT_NODE) {
					patch_node(node);
				} else if (node.nodeType === Node.ELEMENT_NODE) {
					const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
					while (walker.nextNode()) patch_node(walker.currentNode);
					patch_links(node);
				}
			});
		});
	});

	document.addEventListener("DOMContentLoaded", function () {
		observer.observe(document.body, { childList: true, subtree: true });
	});

	// ── Theme toggle button (sun = light, moon = dark) ────────────────────────
	function apply_theme(next) {
		document.documentElement.setAttribute("data-theme-mode", next);
		document.documentElement.setAttribute("data-theme", next);
		frappe.xcall("frappe.core.doctype.user.user.switch_theme", {
			theme: next.charAt(0).toUpperCase() + next.slice(1),
		});
	}

	function create_theme_toggle() {
		const btn = document.createElement("button");
		btn.className = "btn-reset stylo-theme-toggle";
		btn.title = "Toggle Theme";
		btn.innerHTML = `
			<svg class="icon icon-md theme-icon-sun"  aria-hidden="true"><use href="#icon-sun"></use></svg>
			<svg class="icon icon-md theme-icon-moon" aria-hidden="true"><use href="#icon-moon"></use></svg>`;
		btn.addEventListener("click", function () {
			const current = document.documentElement.getAttribute("data-theme") || "light";
			apply_theme(current === "dark" ? "light" : "dark");
		});
		return btn;
	}

	// ── Inject into standard Frappe toolbar (all non-desktop pages) ────────────
	$(document).on("toolbar_setup", function () {
		const navRight = document.querySelector(".navbar-right");
		if (!navRight || navRight.querySelector(".stylo-theme-toggle")) return;
		const li = document.createElement("li");
		li.style.cssText = "display:flex;align-items:center;list-style:none;margin:auto;margin-left:var(--margin-md);";
		li.appendChild(create_theme_toggle());
		navRight.insertBefore(li, navRight.firstChild);
	});

	// ── Inject into desktop page custom navbar ─────────────────────────────────
	function inject_desktop_toggle() {
		const desktop = document.querySelector("#page-desktop");
		if (!desktop || desktop.querySelector(".stylo-theme-toggle")) return;
		const notif = desktop.querySelector(".desktop-notifications");
		if (!notif) return;
		notif.parentElement.insertBefore(create_theme_toggle(), notif);
	}

	const desktop_observer = new MutationObserver(function () {
		if (document.querySelector("#page-desktop .desktop-notifications")) {
			inject_desktop_toggle();
			inject_desktop_widgets();
		}
	});
	document.addEventListener("DOMContentLoaded", function () {
		desktop_observer.observe(document.body, { childList: true, subtree: true });
		inject_desktop_toggle();
		inject_desktop_widgets();
	});

	// ── Daily quote + live clock ───────────────────────────────────────────────
	const DAILY_QUOTES = [
		{ q: "The secret of getting ahead is getting started.", a: "Mark Twain" },
		{ q: "It always seems impossible until it's done.", a: "Nelson Mandela" },
		{ q: "Don't watch the clock; do what it does. Keep going.", a: "Sam Levenson" },
		{ q: "Quality means doing it right when no one is looking.", a: "Henry Ford" },
		{ q: "Success is not final, failure is not fatal: it is the courage to continue that counts.", a: "Winston Churchill" },
		{ q: "Strive not to be a success, but rather to be of value.", a: "Albert Einstein" },
		{ q: "The only way to do great work is to love what you do.", a: "Steve Jobs" },
		{ q: "Believe you can and you're halfway there.", a: "Theodore Roosevelt" },
		{ q: "Your limitation — it's only your imagination.", a: "Unknown" },
		{ q: "Push yourself, because no one else is going to do it for you.", a: "Unknown" },
		{ q: "Great things never come from comfort zones.", a: "Unknown" },
		{ q: "Dream it. Wish it. Do it.", a: "Unknown" },
		{ q: "Work hard in silence; let success make the noise.", a: "Frank Ocean" },
		{ q: "Little things make big days.", a: "Unknown" },
		{ q: "It's going to be hard, but hard is not impossible.", a: "Unknown" },
		{ q: "Don't stop when you're tired. Stop when you're done.", a: "Unknown" },
		{ q: "Wake up with determination. Go to bed with satisfaction.", a: "Unknown" },
		{ q: "Do something today that your future self will thank you for.", a: "Sean Patrick Flanery" },
		{ q: "The harder you work for something, the greater you'll feel when you achieve it.", a: "Unknown" },
		{ q: "Dream bigger. Do bigger.", a: "Unknown" },
		{ q: "Don't wait for opportunity. Create it.", a: "Unknown" },
		{ q: "Sometimes we're tested not to show our weaknesses, but to discover our strengths.", a: "Unknown" },
		{ q: "The key to success is to focus on goals, not obstacles.", a: "Unknown" },
		{ q: "Dream it. Believe it. Build it.", a: "Unknown" },
		{ q: "Teamwork makes the dream work.", a: "John C. Maxwell" },
		{ q: "Alone we can do so little; together we can do so much.", a: "Helen Keller" },
		{ q: "Coming together is a beginning, staying together is progress, and working together is success.", a: "Henry Ford" },
		{ q: "None of us is as smart as all of us.", a: "Ken Blanchard" },
		{ q: "Talent wins games, but teamwork and intelligence win championships.", a: "Michael Jordan" },
		{ q: "The strength of the team is each individual member. The strength of each member is the team.", a: "Phil Jackson" },
		{ q: "If everyone is moving forward together, then success takes care of itself.", a: "Henry Ford" },
		{ q: "Find a group of people who challenge and inspire you; spend a lot of time with them.", a: "Amy Poehler" },
		{ q: "Great vision without great people is irrelevant.", a: "Jim Collins" },
		{ q: "You don't build a business — you build people — and then people build the business.", a: "Zig Ziglar" },
		{ q: "An investment in knowledge pays the best interest.", a: "Benjamin Franklin" },
		{ q: "The more you learn, the more you earn.", a: "Warren Buffett" },
		{ q: "Education is the most powerful weapon you can use to change the world.", a: "Nelson Mandela" },
		{ q: "Live as if you were to die tomorrow. Learn as if you were to live forever.", a: "Mahatma Gandhi" },
		{ q: "The beautiful thing about learning is that no one can take it away from you.", a: "B.B. King" },
		{ q: "The expert in anything was once a beginner.", a: "Helen Hayes" },
		{ q: "Opportunities don't happen. You create them.", a: "Chris Grosser" },
		{ q: "The way to get started is to quit talking and begin doing.", a: "Walt Disney" },
		{ q: "I find that the harder I work, the more luck I seem to have.", a: "Thomas Jefferson" },
		{ q: "Success usually comes to those who are too busy to be looking for it.", a: "Henry David Thoreau" },
		{ q: "Successful people do what unsuccessful people are not willing to do.", a: "Jeff Olson" },
		{ q: "I never dreamed about success. I worked for it.", a: "Estée Lauder" },
		{ q: "Motivation is what gets you started. Habit is what keeps you going.", a: "Jim Ryun" },
		{ q: "You are never too old to set another goal or to dream a new dream.", a: "C.S. Lewis" },
		{ q: "If you can dream it, you can do it.", a: "Walt Disney" },
		{ q: "Act as if what you do makes a difference. It does.", a: "William James" },
		{ q: "What you do today can improve all your tomorrows.", a: "Ralph Marston" },
		{ q: "You miss 100% of the shots you don't take.", a: "Wayne Gretzky" },
		{ q: "I attribute my success to this: I never gave or took any excuse.", a: "Florence Nightingale" },
		{ q: "Either you run the day or the day runs you.", a: "Jim Rohn" },
		{ q: "Happiness is not something ready-made. It comes from your own actions.", a: "Dalai Lama" },
		{ q: "Be the change that you wish to see in the world.", a: "Mahatma Gandhi" },
		{ q: "In the middle of every difficulty lies opportunity.", a: "Albert Einstein" },
		{ q: "The best time to plant a tree was 20 years ago. The second best time is now.", a: "Chinese Proverb" },
		{ q: "The journey of a thousand miles begins with one step.", a: "Lao Tzu" },
		{ q: "Fall seven times, stand up eight.", a: "Japanese Proverb" },
		{ q: "A smooth sea never made a skilled sailor.", a: "English Proverb" },
		{ q: "The harder the conflict, the greater the triumph.", a: "George Washington" },
		{ q: "Perseverance is not a long race; it is many short races one after the other.", a: "Walter Elliot" },
		{ q: "Even the darkest night will end and the sun will rise.", a: "Victor Hugo" },
		{ q: "Keep your eyes on the stars, and your feet on the ground.", a: "Theodore Roosevelt" },
		{ q: "Excellence is not a destination but a continuous journey that never ends.", a: "Brian Tracy" },
	];

	function get_daily_quote() {
		const day_index = Math.floor(Date.now() / 86400000);
		return DAILY_QUOTES[day_index % DAILY_QUOTES.length];
	}

	function inject_desktop_widgets() {
		const wrapper = document.querySelector("#page-desktop .desktop-wrapper");
		if (!wrapper) return;

		// ── Clock ──────────────────────────────────────────────────────────────
		if (!wrapper.querySelector(".stylo-clock")) {
			const clock = document.createElement("div");
			clock.className = "stylo-clock";
			clock.innerHTML = `<div class="stylo-clock-time"></div><div class="stylo-clock-date"></div>`;
			wrapper.appendChild(clock);

			function tick() {
				const now = new Date();
				const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
				const date = now.toLocaleDateString([], { weekday: "long", year: "numeric", month: "long", day: "numeric" });
				clock.querySelector(".stylo-clock-time").textContent = time;
				clock.querySelector(".stylo-clock-date").textContent = date;
			}
			tick();
			setInterval(tick, 1000);
		}

		// ── Daily quote ────────────────────────────────────────────────────────
		if (!wrapper.querySelector(".stylo-daily-quote")) {
			const { q, a } = get_daily_quote();
			const el = document.createElement("div");
			el.className = "stylo-daily-quote";
			el.innerHTML = `<span class="sdq-text">&ldquo;${q}&rdquo;</span><span class="sdq-author">&mdash; ${a}</span>`;
			wrapper.appendChild(el);
		}

		// ── Tasks / Reminders widget ───────────────────────────────────────────
		if (!wrapper.querySelector(".stylo-tasks-widget")) {
			const widget = document.createElement("div");
			widget.className = "stylo-tasks-widget";
			widget.innerHTML = `
				<div class="stw-header">
					<span class="stw-title">
						<svg class="icon icon-sm" style="margin-right:5px;vertical-align:-2px"><use href="#icon-check-circle"></use></svg>
						My Tasks
					</span>
					<a class="stw-add" href="/app/todo/new-todo-1" title="New task">
						<svg class="icon icon-sm"><use href="#icon-add"></use></svg>
					</a>
				</div>
				<div class="stw-body"></div>`;
			wrapper.appendChild(widget);
			refresh_tasks_widget(widget);
		}
	}

	function refresh_tasks_widget(widget) {
		const body = widget.querySelector(".stw-body");
		body.innerHTML = `<div class="stw-loading">Loading…</div>`;

		frappe.call({
			method: "frappe.client.get_list",
			args: {
				doctype: "ToDo",
				filters: [
					["allocated_to", "=", frappe.session.user],
					["status", "=", "Open"],
				],
				fields: ["name", "description", "date", "priority", "reference_type", "reference_name"],
				order_by: "date asc, priority desc",
				limit: 8,
			},
			callback: function (r) {
				const tasks = r.message || [];
				if (!tasks.length) {
					body.innerHTML = `
						<div class="stw-empty">
							<svg class="icon icon-md" style="opacity:0.4;margin-bottom:6px"><use href="#icon-check-circle"></use></svg>
							<div>All clear &mdash; no open tasks!</div>
							<a href="/app/todo" class="stw-link">View Tasks module</a>
						</div>`;
					return;
				}
				const today = frappe.datetime.get_today();
				body.innerHTML = tasks.map(function (t) {
					const overdue = t.date && t.date < today;
					const due_label = t.date
						? (overdue ? `<span class="stw-overdue">${frappe.datetime.str_to_user(t.date)}</span>`
							: `<span class="stw-due">${frappe.datetime.str_to_user(t.date)}</span>`)
						: "";
					const prio_class = (t.priority || "Medium").toLowerCase();
					const desc = t.description
						? t.description.replace(/<[^>]+>/g, "").substring(0, 55) + (t.description.length > 55 ? "…" : "")
						: "(no description)";
					const ref = t.reference_type && t.reference_name
						? `<a class="stw-ref" href="/app/${frappe.router.slug(t.reference_type)}/${t.reference_name}">${t.reference_type}: ${t.reference_name}</a>`
						: "";
					return `
						<div class="stw-item" data-name="${t.name}">
							<button class="stw-done" title="Mark done" data-name="${t.name}">
								<svg class="icon icon-sm"><use href="#icon-check"></use></svg>
							</button>
							<div class="stw-item-body">
								<div class="stw-desc">${desc}</div>
								<div class="stw-meta">
									<span class="stw-prio stw-prio-${prio_class}">${t.priority || "Medium"}</span>
									${due_label}${ref}
								</div>
							</div>
						</div>`;
				}).join("") + `<a href="/app/todo" class="stw-view-all">View all tasks →</a>`;

				// Mark-done buttons
				body.querySelectorAll(".stw-done").forEach(function (btn) {
					btn.addEventListener("click", function (e) {
						e.stopPropagation();
						const name = btn.dataset.name;
						frappe.call({
							method: "frappe.client.set_value",
							args: { doctype: "ToDo", name: name, fieldname: "status", value: "Closed" },
							callback: function () {
								const item = body.querySelector(`.stw-item[data-name="${name}"]`);
								if (item) {
									item.classList.add("stw-done-anim");
									setTimeout(() => refresh_tasks_widget(widget), 600);
								}
							},
						});
					});
				});
			},
		});
	}
})();
