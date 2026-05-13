/**
 * brAIn — AI intelligence layer for Styloworld
 * Two surfaces:
 *   1. Floating bubble (bottom-right) → slide-in chat panel
 *   2. Augmented search bar — detects natural-language queries and routes to brAIn
 */
(function () {
	"use strict";

	// ── State ─────────────────────────────────────────────────────────────────

	const STATE = {
		open: false,
		loading: false,
		history: [],         // [{role, content}] — plain text, sent to server
		configured: false,
	};

	// ── Init ──────────────────────────────────────────────────────────────────

	function init() {
		if (frappe.session.user === "Guest") return;

		frappe.call("brain.api.chat.get_settings_status").then((r) => {
			const s = r.message || {};
			if (!s.enabled) return;
			STATE.configured = s.configured;
			injectStyles();
			buildBubble();
			buildPanel();
			augmentSearchBar();
		}).catch(() => {
			// brAIn not installed or settings missing — silently skip
		});
	}

	// ── Styles ────────────────────────────────────────────────────────────────

	function injectStyles() {
		if (document.getElementById("brain-styles")) return;
		const style = document.createElement("style");
		style.id = "brain-styles";
		style.textContent = `
/* ── brAIn Bubble ──────────────────────────────────────────────── */
#brain-bubble {
	position: fixed;
	bottom: 24px;
	right: 24px;
	width: 52px;
	height: 52px;
	border-radius: 50%;
	background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
	box-shadow: 0 4px 20px rgba(99, 102, 241, 0.45);
	cursor: pointer;
	z-index: 9998;
	display: flex;
	align-items: center;
	justify-content: center;
	transition: transform 0.2s ease, box-shadow 0.2s ease;
	user-select: none;
}
#brain-bubble:hover {
	transform: scale(1.08);
	box-shadow: 0 6px 28px rgba(99, 102, 241, 0.6);
}
#brain-bubble.brain-active {
	background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
}
#brain-bubble svg {
	width: 26px;
	height: 26px;
	fill: none;
	stroke: white;
	stroke-width: 1.8;
}
#brain-bubble .brain-pulse {
	position: absolute;
	top: -3px; right: -3px;
	width: 12px; height: 12px;
	border-radius: 50%;
	background: #10b981;
	border: 2px solid white;
}

/* ── brAIn Panel ───────────────────────────────────────────────── */
#brain-panel {
	position: fixed;
	top: 0;
	right: -420px;
	width: 420px;
	height: 100vh;
	background: var(--bg-color, #fff);
	border-left: 1px solid var(--border-color, #e5e7eb);
	box-shadow: -8px 0 40px rgba(0,0,0,0.12);
	z-index: 9999;
	display: flex;
	flex-direction: column;
	transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
	font-family: var(--font-stack, system-ui, -apple-system, sans-serif);
}
#brain-panel.brain-panel-open {
	right: 0;
}

/* Header */
.brain-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: 16px 20px;
	border-bottom: 1px solid var(--border-color, #e5e7eb);
	background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
	color: white;
	flex-shrink: 0;
}
.brain-header-title {
	display: flex;
	align-items: center;
	gap: 10px;
	font-size: 16px;
	font-weight: 600;
	letter-spacing: 0.3px;
}
.brain-header-title svg {
	width: 20px; height: 20px;
	fill: none; stroke: white; stroke-width: 2;
}
.brain-header-subtitle {
	font-size: 11px;
	opacity: 0.8;
	font-weight: 400;
	margin-top: 1px;
}
.brain-header-actions {
	display: flex;
	gap: 8px;
}
.brain-btn-icon {
	background: rgba(255,255,255,0.15);
	border: none;
	border-radius: 6px;
	color: white;
	cursor: pointer;
	width: 30px; height: 30px;
	display: flex; align-items: center; justify-content: center;
	transition: background 0.15s;
}
.brain-btn-icon:hover { background: rgba(255,255,255,0.25); }
.brain-btn-icon svg { width: 15px; height: 15px; stroke: white; fill: none; stroke-width: 2; }

/* Context bar */
.brain-context {
	padding: 8px 16px;
	background: var(--bg-light-gray, #f9fafb);
	border-bottom: 1px solid var(--border-color, #e5e7eb);
	font-size: 11px;
	color: var(--text-muted, #6b7280);
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	flex-shrink: 0;
}

/* Messages */
.brain-messages {
	flex: 1;
	overflow-y: auto;
	padding: 20px 16px;
	display: flex;
	flex-direction: column;
	gap: 16px;
	scroll-behavior: smooth;
}
.brain-messages::-webkit-scrollbar { width: 4px; }
.brain-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 2px; }

/* Message bubbles */
.brain-msg {
	display: flex;
	gap: 10px;
	animation: brain-fadein 0.2s ease;
}
@keyframes brain-fadein { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

.brain-msg-user {
	flex-direction: row-reverse;
}
.brain-avatar {
	width: 30px; height: 30px;
	border-radius: 50%;
	flex-shrink: 0;
	display: flex; align-items: center; justify-content: center;
	font-size: 12px; font-weight: 600;
}
.brain-avatar-ai {
	background: linear-gradient(135deg, #6366f1, #8b5cf6);
	color: white;
	font-size: 13px;
}
.brain-avatar-user {
	background: var(--bg-light-gray, #f3f4f6);
	color: var(--text-color, #374151);
}
.brain-bubble-content {
	max-width: 82%;
	padding: 10px 14px;
	border-radius: 12px;
	font-size: 13.5px;
	line-height: 1.55;
	word-break: break-word;
}
.brain-msg-ai .brain-bubble-content {
	background: var(--bg-light-gray, #f3f4f6);
	color: var(--text-color, #111827);
	border-radius: 2px 12px 12px 12px;
}
.brain-msg-user .brain-bubble-content {
	background: linear-gradient(135deg, #6366f1, #8b5cf6);
	color: white;
	border-radius: 12px 2px 12px 12px;
}
.brain-bubble-content p { margin: 0 0 6px; }
.brain-bubble-content p:last-child { margin: 0; }
.brain-bubble-content ul, .brain-bubble-content ol { margin: 4px 0; padding-left: 18px; }
.brain-bubble-content code {
	background: rgba(0,0,0,0.07);
	padding: 1px 5px;
	border-radius: 3px;
	font-size: 12px;
}
.brain-msg-user .brain-bubble-content code { background: rgba(255,255,255,0.2); }
.brain-bubble-content table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 6px; }
.brain-bubble-content th, .brain-bubble-content td { padding: 5px 8px; border: 1px solid rgba(0,0,0,0.1); text-align: left; }
.brain-bubble-content th { background: rgba(0,0,0,0.05); font-weight: 600; }

/* Action chips */
.brain-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 6px;
	margin-top: 8px;
}
.brain-action-chip {
	display: inline-flex;
	align-items: center;
	gap: 5px;
	padding: 4px 10px;
	background: white;
	border: 1px solid #6366f1;
	color: #6366f1;
	border-radius: 20px;
	font-size: 11.5px;
	font-weight: 500;
	cursor: pointer;
	transition: all 0.15s;
}
.brain-action-chip:hover { background: #6366f1; color: white; }
.brain-action-chip svg { width: 12px; height: 12px; }

/* Typing indicator */
.brain-typing {
	display: flex;
	align-items: center;
	gap: 4px;
	padding: 10px 14px;
}
.brain-typing span {
	width: 7px; height: 7px;
	border-radius: 50%;
	background: #9ca3af;
	animation: brain-bounce 1.2s infinite;
}
.brain-typing span:nth-child(2) { animation-delay: 0.2s; }
.brain-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes brain-bounce {
	0%, 60%, 100% { transform: translateY(0); }
	30% { transform: translateY(-5px); }
}

/* Welcome / empty state */
.brain-welcome {
	text-align: center;
	padding: 40px 20px;
	color: var(--text-muted, #6b7280);
}
.brain-welcome-icon {
	font-size: 40px;
	margin-bottom: 12px;
}
.brain-welcome h3 {
	font-size: 16px;
	font-weight: 600;
	color: var(--text-color, #111827);
	margin: 0 0 6px;
}
.brain-welcome p { font-size: 13px; margin: 0 0 20px; }
.brain-suggestions {
	display: flex;
	flex-direction: column;
	gap: 8px;
	text-align: left;
}
.brain-suggestion {
	padding: 10px 14px;
	border: 1px solid var(--border-color, #e5e7eb);
	border-radius: 8px;
	cursor: pointer;
	font-size: 12.5px;
	color: var(--text-color, #374151);
	transition: all 0.15s;
	background: white;
}
.brain-suggestion:hover {
	border-color: #6366f1;
	background: #f5f3ff;
	color: #6366f1;
}
.brain-suggestion-icon { margin-right: 8px; }

/* Input area */
.brain-input-area {
	padding: 12px 16px;
	border-top: 1px solid var(--border-color, #e5e7eb);
	background: var(--bg-color, #fff);
	flex-shrink: 0;
}
.brain-input-row {
	display: flex;
	gap: 8px;
	align-items: flex-end;
	background: var(--bg-light-gray, #f3f4f6);
	border: 1.5px solid var(--border-color, #e5e7eb);
	border-radius: 12px;
	padding: 8px 12px;
	transition: border-color 0.15s;
}
.brain-input-row:focus-within {
	border-color: #6366f1;
	background: white;
}
.brain-input-row textarea {
	flex: 1;
	border: none;
	background: transparent;
	resize: none;
	outline: none;
	font-size: 13.5px;
	line-height: 1.5;
	color: var(--text-color, #111827);
	max-height: 120px;
	font-family: inherit;
}
.brain-input-row textarea::placeholder { color: #9ca3af; }
.brain-send-btn {
	background: linear-gradient(135deg, #6366f1, #8b5cf6);
	border: none;
	border-radius: 8px;
	color: white;
	cursor: pointer;
	width: 32px; height: 32px;
	display: flex; align-items: center; justify-content: center;
	flex-shrink: 0;
	transition: opacity 0.15s, transform 0.15s;
}
.brain-send-btn:hover { opacity: 0.9; transform: scale(1.05); }
.brain-send-btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
.brain-send-btn svg { width: 16px; height: 16px; fill: white; stroke: none; }

.brain-input-hint {
	font-size: 10.5px;
	color: var(--text-muted, #9ca3af);
	margin-top: 6px;
	text-align: center;
}

/* ── Augmented search ──────────────────────────────────────────── */
.brain-search-hint {
	display: flex;
	align-items: center;
	gap: 8px;
	padding: 8px 12px;
	cursor: pointer;
	font-size: 13px;
	color: #6366f1;
	border-top: 1px solid #f0f0f0;
	transition: background 0.1s;
}
.brain-search-hint:hover { background: #f5f3ff; }
.brain-search-hint-badge {
	background: linear-gradient(135deg, #6366f1, #8b5cf6);
	color: white;
	font-size: 10px;
	font-weight: 700;
	padding: 2px 6px;
	border-radius: 4px;
	letter-spacing: 0.5px;
}

/* Overlay */
#brain-overlay {
	display: none;
	position: fixed;
	inset: 0;
	background: rgba(0,0,0,0.15);
	z-index: 9997;
	backdrop-filter: blur(1px);
}
#brain-overlay.brain-overlay-show { display: block; }
`;
		document.head.appendChild(style);
	}

	// ── Bubble ────────────────────────────────────────────────────────────────

	function buildBubble() {
		const el = document.createElement("div");
		el.id = "brain-bubble";
		el.title = "Ask brAIn";
		el.innerHTML = `
			${brainIcon()}
			<div class="brain-pulse"></div>
		`;
		el.addEventListener("click", togglePanel);
		document.body.appendChild(el);

		const overlay = document.createElement("div");
		overlay.id = "brain-overlay";
		overlay.addEventListener("click", closePanel);
		document.body.appendChild(overlay);
	}

	function brainIcon() {
		// Spark/brain SVG icon
		return `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
			<path d="M12 2L9.5 8.5L3 9.27L7.5 13.97L6.18 20.9L12 17.77L17.82 20.9L16.5 13.97L21 9.27L14.5 8.5L12 2Z"
				fill="white" stroke="none"/>
		</svg>`;
	}

	// ── Panel ─────────────────────────────────────────────────────────────────

	function buildPanel() {
		const el = document.createElement("div");
		el.id = "brain-panel";
		el.innerHTML = `
			<div class="brain-header">
				<div>
					<div class="brain-header-title">
						${brainIcon()}
						brAIn
					</div>
					<div class="brain-header-subtitle">AI intelligence layer · Styloworld</div>
				</div>
				<div class="brain-header-actions">
					<button class="brain-btn-icon" id="brain-clear-btn" title="Clear conversation">
						<svg viewBox="0 0 24 24"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3"/></svg>
					</button>
					<button class="brain-btn-icon" id="brain-close-btn" title="Close">
						<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
					</button>
				</div>
			</div>
			<div class="brain-context" id="brain-context-bar">Ready</div>
			<div class="brain-messages" id="brain-messages">
				${renderWelcome()}
			</div>
			<div class="brain-input-area">
				<div class="brain-input-row">
					<textarea id="brain-input" placeholder="Ask anything… create invoices, find customers, run reports" rows="1"></textarea>
					<button class="brain-send-btn" id="brain-send-btn" title="Send">
						<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
							<path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
						</svg>
					</button>
				</div>
				<div class="brain-input-hint">Enter to send · Shift+Enter for new line</div>
			</div>
		`;
		document.body.appendChild(el);

		// Wire events
		document.getElementById("brain-close-btn").addEventListener("click", closePanel);
		document.getElementById("brain-clear-btn").addEventListener("click", clearConversation);
		document.getElementById("brain-send-btn").addEventListener("click", sendMessage);

		const textarea = document.getElementById("brain-input");
		textarea.addEventListener("keydown", (e) => {
			if (e.key === "Enter" && !e.shiftKey) {
				e.preventDefault();
				sendMessage();
			}
		});
		textarea.addEventListener("input", () => autoResizeTextarea(textarea));

		// Update context on page change
		$(document).on("page-change", updateContextBar);
	}

	function renderWelcome() {
		const suggestions = [
			{ icon: "🔍", text: "Show me all overdue invoices" },
			{ icon: "📊", text: "What is our revenue this month?" },
			{ icon: "➕", text: "Create a new customer named Acme Corp" },
			{ icon: "🗂️", text: "List all open purchase orders" },
			{ icon: "📈", text: "Who are our top 5 customers by sales?" },
		];
		return `
			<div class="brain-welcome">
				<div class="brain-welcome-icon">✦</div>
				<h3>How can I help?</h3>
				<p>I can create, find, update, and navigate anything in Styloworld.</p>
				<div class="brain-suggestions">
					${suggestions.map(s => `
						<div class="brain-suggestion" onclick="brainSendSuggestion('${s.text.replace(/'/g, "\\'")}')">
							<span class="brain-suggestion-icon">${s.icon}</span>${s.text}
						</div>
					`).join("")}
				</div>
			</div>
		`;
	}

	// ── Panel open/close ──────────────────────────────────────────────────────

	function togglePanel() {
		STATE.open ? closePanel() : openPanel();
	}

	function openPanel() {
		STATE.open = true;
		document.getElementById("brain-panel").classList.add("brain-panel-open");
		document.getElementById("brain-overlay").classList.add("brain-overlay-show");
		document.getElementById("brain-bubble").classList.add("brain-active");
		updateContextBar();
		setTimeout(() => document.getElementById("brain-input").focus(), 300);
	}

	function closePanel() {
		STATE.open = false;
		document.getElementById("brain-panel").classList.remove("brain-panel-open");
		document.getElementById("brain-overlay").classList.remove("brain-overlay-show");
		document.getElementById("brain-bubble").classList.remove("brain-active");
	}

	function clearConversation() {
		STATE.history = [];
		document.getElementById("brain-messages").innerHTML = renderWelcome();
	}

	// ── Context bar ───────────────────────────────────────────────────────────

	function updateContextBar() {
		const ctx = getPageContext();
		const bar = document.getElementById("brain-context-bar");
		if (!bar) return;
		const parts = [];
		if (ctx.route && ctx.route.length) parts.push(ctx.route.join(" › "));
		if (ctx.doctype) parts.push(`📄 ${ctx.doctype}`);
		if (ctx.doc_name) parts.push(ctx.doc_name);
		bar.textContent = parts.join(" · ") || "Styloworld";
	}

	function getPageContext() {
		const route = frappe.get_route ? frappe.get_route() : [];
		const ctx = { route: route || [] };
		if (route && route[0] === "Form" && route[1] && route[2]) {
			ctx.doctype = route[1];
			ctx.doc_name = route[2];
		} else if (route && route[0] === "List" && route[1]) {
			ctx.doctype = route[1];
		}
		return ctx;
	}

	// ── Send message ──────────────────────────────────────────────────────────

	function sendMessage() {
		const textarea = document.getElementById("brain-input");
		const msg = textarea.value.trim();
		if (!msg || STATE.loading) return;

		textarea.value = "";
		autoResizeTextarea(textarea);

		appendMessage("user", msg);

		STATE.loading = true;
		document.getElementById("brain-send-btn").disabled = true;
		showTypingIndicator();

		const pageCtx = getPageContext();
		const historyToSend = STATE.history.slice(-20); // Last 20 turns

		frappe.call({
			method: "brain.api.chat.send",
			args: {
				message: msg,
				history: JSON.stringify(historyToSend),
				context: JSON.stringify(pageCtx),
			},
			callback: (r) => {
				hideTypingIndicator();
				STATE.loading = false;
				document.getElementById("brain-send-btn").disabled = false;

				if (r.exc) {
					appendMessage("ai", "⚠️ An error occurred. Please check Brain Settings and try again.");
					return;
				}

				const result = r.message || {};
				const aiText = result.message || "Done.";
				const actions = result.actions || [];

				// Add to history (plain text only)
				STATE.history.push({ role: "user", content: msg });
				STATE.history.push({ role: "assistant", content: aiText });

				appendMessage("ai", aiText, actions);
				executeActions(actions);
			},
			error: () => {
				hideTypingIndicator();
				STATE.loading = false;
				document.getElementById("brain-send-btn").disabled = false;
				appendMessage("ai", "⚠️ brAIn encountered an error. Check the console for details.");
			},
		});
	}

	// Exposed globally for suggestion click
	window.brainSendSuggestion = function (text) {
		if (!STATE.open) openPanel();
		const ta = document.getElementById("brain-input");
		if (ta) { ta.value = text; ta.focus(); }
		setTimeout(sendMessage, 50);
	};

	// ── Render messages ───────────────────────────────────────────────────────

	function appendMessage(role, content, actions) {
		const container = document.getElementById("brain-messages");

		// Remove welcome screen on first message
		const welcome = container.querySelector(".brain-welcome");
		if (welcome) welcome.remove();

		const isUser = role === "user";
		const initials = isUser
			? (frappe.boot.user.full_name || "U").charAt(0).toUpperCase()
			: "✦";

		const formattedContent = isUser ? escapeHtml(content) : renderMarkdown(content);

		const actionChips = (!isUser && actions && actions.length)
			? `<div class="brain-actions">
				${actions.map(a => renderActionChip(a)).join("")}
			</div>`
			: "";

		const msgEl = document.createElement("div");
		msgEl.className = `brain-msg brain-msg-${isUser ? "user" : "ai"}`;
		msgEl.innerHTML = `
			<div class="brain-avatar brain-avatar-${isUser ? "user" : "ai"}">${initials}</div>
			<div class="brain-bubble-content">
				${formattedContent}
				${actionChips}
			</div>
		`;
		container.appendChild(msgEl);
		container.scrollTop = container.scrollHeight;
	}

	function renderActionChip(action) {
		const labels = {
			navigate: "→ Go there",
			open_form: "→ Open record",
		};
		const label = labels[action.type] || action.type;
		const onclick = `brainExecuteAction(${JSON.stringify(action).replace(/"/g, "&quot;")})`;
		return `<button class="brain-action-chip" onclick="${onclick}">
			<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M5 12h14M12 5l7 7-7 7"/>
			</svg>
			${label}
		</button>`;
	}

	window.brainExecuteAction = function (action) {
		executeActions([action]);
	};

	function showTypingIndicator() {
		const container = document.getElementById("brain-messages");
		const el = document.createElement("div");
		el.className = "brain-msg brain-msg-ai";
		el.id = "brain-typing-indicator";
		el.innerHTML = `
			<div class="brain-avatar brain-avatar-ai">✦</div>
			<div class="brain-bubble-content">
				<div class="brain-typing">
					<span></span><span></span><span></span>
				</div>
			</div>
		`;
		container.appendChild(el);
		container.scrollTop = container.scrollHeight;
	}

	function hideTypingIndicator() {
		const el = document.getElementById("brain-typing-indicator");
		if (el) el.remove();
	}

	// ── Execute browser-side actions ──────────────────────────────────────────

	function executeActions(actions) {
		(actions || []).forEach(action => {
			try {
				if (action.type === "navigate" && action.route) {
					setTimeout(() => {
						frappe.set_route(action.route);
						if (action.filters) {
							// Apply filters after navigation
							setTimeout(() => {
								try {
									frappe.route_flags.filters = action.filters;
								} catch (e) {}
							}, 500);
						}
					}, 400);
				} else if (action.type === "open_form" && action.doctype && action.name) {
					setTimeout(() => {
						frappe.set_route("Form", action.doctype, action.name);
					}, 400);
				}
			} catch (e) {
				console.warn("brAIn: action failed", action, e);
			}
		});
	}

	// ── Search bar augmentation ───────────────────────────────────────────────

	function augmentSearchBar() {
		// Hook into Frappe's awesomebar after it's rendered
		const checkInterval = setInterval(() => {
			const awesomebar = document.querySelector(".navbar .awesomebar, #navbar-search, .search-bar input");
			if (awesomebar) {
				clearInterval(checkInterval);
				_hookAwesomebar(awesomebar);
			}
		}, 500);
	}

	function _hookAwesomebar(input) {
		let hintInjected = false;

		input.addEventListener("keyup", (e) => {
			const val = (input.value || "").trim();

			// Detect natural language: contains spaces AND looks like a question/command
			const isNL = val.length > 10 && (
				val.split(" ").length >= 3 ||
				/^(show|find|create|update|list|how|what|who|give|delete|submit|cancel|make|get|run)\b/i.test(val)
			);

			const existing = document.querySelector(".brain-search-hint");

			if (isNL && !existing) {
				// Inject "Ask brAIn" option into search dropdown
				const dropdown = document.querySelector(".search-results, .awesomebar-container .results");
				if (dropdown && !hintInjected) {
					hintInjected = true;
					const hint = document.createElement("div");
					hint.className = "brain-search-hint";
					hint.innerHTML = `
						<span class="brain-search-hint-badge">brAIn</span>
						<span>Ask brAIn: "${val}"</span>
					`;
					hint.addEventListener("click", () => {
						input.blur();
						window.brainSendSuggestion(val);
						input.value = "";
					});
					dropdown.appendChild(hint);
				}
			} else if (!isNL && existing) {
				existing.remove();
				hintInjected = false;
			}

			if (e.key === "Escape" || val === "") {
				hintInjected = false;
			}
		});
	}

	// ── Markdown renderer (lightweight) ──────────────────────────────────────

	function renderMarkdown(text) {
		if (!text) return "";
		return text
			// Code blocks
			.replace(/```[\s\S]*?```/g, (m) => `<pre><code>${escapeHtml(m.slice(3, -3).trim())}</code></pre>`)
			// Bold
			.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
			// Italic
			.replace(/\*(.+?)\*/g, "<em>$1</em>")
			// Inline code
			.replace(/`(.+?)`/g, "<code>$1</code>")
			// Headers
			.replace(/^### (.+)$/gm, "<h4>$1</h4>")
			.replace(/^## (.+)$/gm, "<h3>$1</h3>")
			.replace(/^# (.+)$/gm, "<h2>$1</h2>")
			// Bullet lists
			.replace(/^[-*] (.+)$/gm, "<li>$1</li>")
			.replace(/(<li>[\s\S]+?<\/li>)/g, "<ul>$1</ul>")
			// Numbered lists
			.replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
			// Line breaks
			.replace(/\n\n/g, "</p><p>")
			.replace(/\n/g, "<br>")
			// Wrap in paragraph
			.replace(/^(?!<[h|u|o|p|pre])/, "<p>")
			.replace(/(?<![>])$/, "</p>")
			// Clean double-wrapped
			.replace(/<p><\/p>/g, "");
	}

	function escapeHtml(str) {
		return String(str)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;");
	}

	function autoResizeTextarea(el) {
		el.style.height = "auto";
		el.style.height = Math.min(el.scrollHeight, 120) + "px";
	}

	// ── Boot ──────────────────────────────────────────────────────────────────

	$(document).on("app_ready", init);
	if (document.readyState === "complete" && frappe && frappe.session && frappe.session.user !== "Guest") {
		init();
	}

})();
