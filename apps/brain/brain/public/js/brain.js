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

		frappe.call({
			method: "brain.api.chat.get_settings_status",
			error: () => { /* silently skip if brain not configured */ },
		}).then((r) => {
			const s = (r && r.message) || {};
			if (!s.enabled) return;
			STATE.configured = s.configured;
			injectStyles();
			buildBubble();
			buildPanel();
			augmentSearchBar();
		}).catch(() => {});
	}

	// ── Styles ────────────────────────────────────────────────────────────────

	function injectStyles() {
		if (document.getElementById("brain-styles")) return;
		const style = document.createElement("style");
		style.id = "brain-styles";
		style.textContent = `
/* ── brAIn Edge Tab ────────────────────────────────────────────── */
#brain-bubble {
	position: fixed;
	top: 50%;
	right: 0;
	transform: translateY(-50%);
	width: 36px;
	height: 96px;
	border-radius: 10px 0 0 10px;
	background: linear-gradient(180deg, #0FBF7F 0%, #0DA870 100%);
	box-shadow: -3px 0 18px rgba(15, 191, 127, 0.35);
	cursor: pointer;
	z-index: 9998;
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 6px;
	transition: width 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
	user-select: none;
}
#brain-bubble:hover {
	width: 42px;
	box-shadow: -5px 0 24px rgba(15, 191, 127, 0.5);
}
#brain-bubble.brain-active {
	background: linear-gradient(180deg, #0aa868 0%, #0aa868 100%);
	width: 42px;
}
#brain-bubble .brain-tab-icon {
	width: 20px;
	height: 20px;
	fill: white;
}
#brain-bubble .brain-tab-label {
	writing-mode: vertical-rl;
	text-orientation: mixed;
	transform: rotate(180deg);
	font-size: 10px;
	font-weight: 700;
	color: white;
	letter-spacing: 1px;
	opacity: 0.9;
}
#brain-bubble .brain-pulse {
	position: absolute;
	top: 8px; right: 8px;
	width: 8px; height: 8px;
	border-radius: 50%;
	background: #10b981;
	border: 1.5px solid white;
}
/* Guiding state — tab pulses to show brAIn is active */
#brain-bubble.brain-guiding {
	animation: brain-guide-tab-pulse 1.8s ease-in-out infinite !important;
}
@keyframes brain-guide-tab-pulse {
	0%, 100% { opacity: 1; box-shadow: -3px 0 18px rgba(15,191,127,0.4); }
	50%       { opacity: 0.75; box-shadow: -6px 0 28px rgba(15,191,127,0.8); }
}

/* ── brAIn Panel ───────────────────────────────────────────────── */
#brain-panel {
	position: fixed;
	top: 0;
	right: -440px;
	width: 400px;
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
	background: linear-gradient(135deg, #0FBF7F 0%, #0DA870 100%);
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
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
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
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
	color: white;
	border-radius: 12px 2px 12px 12px;
}
/* ── AI message content ─────────────────────────────────────── */
.brain-bubble-content p { margin: 0 0 8px; }
.brain-bubble-content p:last-child { margin: 0; }

/* Headings */
.brain-bubble-content h2 {
	font-size: 14px; font-weight: 700; margin: 12px 0 6px;
	color: var(--text-color, #111827); border-bottom: 1.5px solid rgba(15,191,127,0.25);
	padding-bottom: 4px;
}
.brain-bubble-content h3 {
	font-size: 13px; font-weight: 700; margin: 10px 0 4px;
	color: #0FBF7F;
}
.brain-bubble-content h4 {
	font-size: 12.5px; font-weight: 600; margin: 8px 0 4px;
	color: var(--text-color, #374151);
}

/* Lists */
.brain-bubble-content ul, .brain-bubble-content ol {
	margin: 6px 0 8px; padding-left: 20px;
}
.brain-bubble-content li { margin: 3px 0; line-height: 1.55; }
.brain-bubble-content ul li { list-style-type: disc; }
.brain-bubble-content ol li { list-style-type: decimal; }
.brain-bubble-content li + li { margin-top: 2px; }

/* Inline code */
.brain-bubble-content code {
	background: rgba(15,191,127,0.12);
	color: #0a8f5e;
	padding: 1px 6px;
	border-radius: 4px;
	font-size: 12px;
	font-family: ui-monospace, 'Cascadia Code', 'JetBrains Mono', monospace;
	border: 1px solid rgba(15,191,127,0.2);
}
.brain-msg-user .brain-bubble-content code {
	background: rgba(255,255,255,0.2);
	color: white;
	border-color: rgba(255,255,255,0.3);
}

/* Code blocks */
.brain-bubble-content pre {
	background: #0f172a;
	border-radius: 10px;
	padding: 14px 16px;
	margin: 10px 0;
	overflow-x: auto;
	position: relative;
	border: 1px solid rgba(255,255,255,0.06);
}
.brain-bubble-content pre code {
	background: none;
	color: #e2e8f0;
	border: none;
	padding: 0;
	font-size: 12px;
	line-height: 1.6;
	white-space: pre;
}
.brain-code-lang {
	position: absolute; top: 8px; right: 12px;
	font-size: 10px; color: rgba(255,255,255,0.3);
	font-family: ui-monospace, monospace; text-transform: uppercase; letter-spacing: 0.5px;
}

/* Horizontal rule */
.brain-bubble-content hr {
	border: none; border-top: 1px solid rgba(15,191,127,0.2);
	margin: 10px 0;
}

/* Blockquote / callout */
.brain-bubble-content blockquote {
	border-left: 3px solid #0FBF7F;
	background: rgba(15,191,127,0.06);
	margin: 8px 0;
	padding: 8px 12px;
	border-radius: 0 8px 8px 0;
	font-size: 13px;
	color: var(--text-muted, #4b5563);
}

/* ── Tables ───────────────────────────────────────────────────── */
.brain-table-wrap {
	width: 100%;
	overflow-x: auto;
	margin: 10px 0;
	border-radius: 10px;
	border: 1px solid rgba(15,191,127,0.2);
	box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
.brain-bubble-content table {
	width: 100%;
	border-collapse: collapse;
	font-size: 12.5px;
	min-width: 240px;
}
.brain-bubble-content thead {
	background: linear-gradient(135deg, rgba(15,191,127,0.14), rgba(13,168,112,0.1));
	position: sticky; top: 0;
}
.brain-bubble-content th {
	padding: 9px 12px;
	font-weight: 700;
	font-size: 11.5px;
	text-transform: uppercase;
	letter-spacing: 0.4px;
	color: #0a8f5e;
	text-align: left;
	border-bottom: 1.5px solid rgba(15,191,127,0.25);
	white-space: nowrap;
}
.brain-bubble-content td {
	padding: 8px 12px;
	text-align: left;
	border-bottom: 1px solid rgba(0,0,0,0.05);
	vertical-align: top;
	line-height: 1.5;
}
.brain-bubble-content tbody tr:hover td { background: rgba(15,191,127,0.04); }
.brain-bubble-content tbody tr:last-child td { border-bottom: none; }
.brain-bubble-content td strong { color: #0a8f5e; font-weight: 600; }

/* Highlight / badge inside AI messages */
.brain-highlight {
	background: rgba(15,191,127,0.15);
	color: #0a8f5e;
	border-radius: 4px;
	padding: 1px 5px;
	font-weight: 600;
	font-size: 12px;
}
.brain-badge {
	display: inline-block;
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
	color: white;
	border-radius: 6px;
	padding: 1px 8px;
	font-size: 11px;
	font-weight: 700;
	letter-spacing: 0.3px;
}

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
	border: 1px solid #0FBF7F;
	color: #0FBF7F;
	border-radius: 20px;
	font-size: 11.5px;
	font-weight: 500;
	cursor: pointer;
	transition: all 0.15s;
}
.brain-action-chip:hover { background: #0FBF7F; color: white; }
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

/* ── Action Choice Card ─────────────────────────────────────────────── */
.brain-choice-card {
	background: rgba(15,191,127,0.06);
	border: 1px solid rgba(15,191,127,0.22);
	border-radius: 14px;
	padding: 14px 16px 12px;
	margin-top: 10px;
}
.brain-choice-header {
	font-weight: 700; font-size: 13.5px; margin-bottom: 10px; color: #0FBF7F;
}
.brain-known-values {
	display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;
}
.brain-kv-chip {
	background: rgba(15,191,127,0.12); border: 1px solid rgba(15,191,127,0.3);
	border-radius: 8px; padding: 3px 9px; font-size: 11.5px;
	color: var(--text-color, #1f2937);
}
.brain-kv-chip b { color: #0FBF7F; }
.brain-field-count {
	font-size: 11px; font-weight: 600; color: #0FBF7F; opacity: 0.8;
	margin-bottom: 8px; letter-spacing: 0.2px;
}
.brain-required-inputs {
	margin-bottom: 12px;
	max-height: 320px;
	overflow-y: auto;
	padding-right: 4px;
}
.brain-required-inputs::-webkit-scrollbar { width: 3px; }
.brain-required-inputs::-webkit-scrollbar-thumb { background: rgba(15,191,127,0.3); border-radius: 2px; }
.brain-field-row { margin-bottom: 10px; }
.brain-field-row label {
	display: block; font-size: 11px; font-weight: 600; opacity: 0.7;
	margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.3px;
}
.brain-req-star { color: #ef4444; font-size: 10px; }
.brain-field-row input,
.brain-field-row select {
	width: 100%; box-sizing: border-box;
	border: 1px solid rgba(15,191,127,0.35);
	border-radius: 8px; padding: 7px 10px; font-size: 12.5px;
	background: var(--bg-color, white); color: var(--text-color, #1f2937);
	outline: none; transition: border-color 0.15s;
	font-family: inherit;
}
.brain-field-row input:focus,
.brain-field-row select:focus { border-color: #0FBF7F; box-shadow: 0 0 0 2px rgba(15,191,127,0.12); }
.brain-field-hint {
	display: block; font-size: 10.5px; color: #0FBF7F; opacity: 0.7;
	margin-top: 2px; padding-left: 2px;
}
.brain-check-label {
	display: flex; align-items: center; gap: 8px;
	cursor: pointer; font-size: 12.5px; color: var(--text-color, #1f2937);
	padding: 6px 0;
}
.brain-check-label input[type="checkbox"] { width: 15px; height: 15px; accent-color: #0FBF7F; cursor: pointer; }
.brain-choice-btns {
	display: flex; gap: 8px; margin-top: 2px;
}
.brain-choice-btn {
	flex: 1; padding: 8px 12px; border-radius: 10px;
	font-size: 12.5px; font-weight: 600; cursor: pointer;
	border: 1.5px solid rgba(15,191,127,0.4);
	background: transparent; color: #0FBF7F;
	transition: background 0.15s, color 0.15s;
}
.brain-choice-btn:hover { background: #0FBF7F; color: white; border-color: #0FBF7F; }
.brain-choice-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.brain-fill-btn { background: #0FBF7F; color: white; border-color: #0FBF7F; }
.brain-fill-btn:hover { background: #0DA870; border-color: #0DA870; }

/* Streaming tool pill */
.brain-tool-pill {
	display: inline-flex; align-items: center; gap: 5px;
	background: rgba(15,191,127,0.10); color: #0FBF7F;
	border: 1px solid rgba(15,191,127,0.25);
	border-radius: 20px; padding: 3px 10px;
	font-size: 11.5px; font-weight: 500; margin: 4px 0;
	animation: brain-pulse-subtle 1.2s ease-in-out infinite;
}
@keyframes brain-pulse-subtle {
	0%, 100% { opacity: 1; } 50% { opacity: 0.6; }
}
/* Blinking cursor while streaming */
.brain-msg-streaming .brain-stream-text::after {
	content: "▋"; animation: brain-blink 0.9s step-end infinite;
	color: #0FBF7F; margin-left: 1px;
}
@keyframes brain-blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }

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
	border-color: #0FBF7F;
	background: #e6fbf4;
	color: #0FBF7F;
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
	border-color: #0FBF7F;
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
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
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
	color: #0FBF7F;
	border-top: 1px solid #f0f0f0;
	transition: background 0.1s;
}
.brain-search-hint:hover { background: #e6fbf4; }
.brain-search-hint-badge {
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
	color: white;
	font-size: 10px;
	font-weight: 700;
	padding: 2px 6px;
	border-radius: 4px;
	letter-spacing: 0.5px;
}

/* ── AI Fill Animation ─────────────────────────────────────────── */
@keyframes brain-field-glow {
	0%, 100% { box-shadow: 0 0 0 2px rgba(15,191,127,0.35), 0 0 8px rgba(15,191,127,0.15); }
	50%       { box-shadow: 0 0 0 4px rgba(15,191,127,0.55), 0 0 20px rgba(15,191,127,0.25); }
}
.brain-filling .control-input-wrapper,
.brain-filling .frappe-control .control-input {
	animation: brain-field-glow 0.9s ease infinite !important;
	border-radius: 6px;
}
.brain-filling .control-input-wrapper input,
.brain-filling .control-input-wrapper textarea,
.brain-filling .control-input-wrapper .form-control,
.brain-filling .frappe-control input,
.brain-filling .frappe-control textarea {
	border-color: #0FBF7F !important;
	background: rgba(15,191,127,0.04) !important;
}
.brain-filling .control-label label,
.brain-filling > .control-label { color: #0FBF7F !important; font-weight: 600 !important; }
.brain-filled .control-input-wrapper input,
.brain-filled .frappe-control input { border-color: #0FBF7F !important; background: rgba(15,191,127,0.06) !important; }

#brain-fill-overlay {
	position: fixed;
	bottom: 32px;
	left: 50%;
	transform: translateX(-50%);
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
	color: white;
	padding: 11px 24px;
	border-radius: 28px;
	font-size: 13px;
	font-weight: 600;
	z-index: 99998;
	display: flex;
	align-items: center;
	gap: 10px;
	box-shadow: 0 6px 24px rgba(15,191,127,0.45);
	animation: brain-fadein 0.3s ease;
	white-space: nowrap;
}
.brain-fill-dots { display: flex; gap: 4px; }
.brain-fill-dot {
	width: 7px; height: 7px; border-radius: 50%; background: rgba(255,255,255,0.8);
	animation: brain-bounce 1s infinite;
}
.brain-fill-dot:nth-child(2) { animation-delay: 0.15s; }
.brain-fill-dot:nth-child(3) { animation-delay: 0.3s; }

/* ── AI Guide Cursor ───────────────────────────────────────────── */
#brain-guide-cursor {
	position: fixed;
	left: 0; top: 0;
	width: 16px; height: 20px;
	pointer-events: none;
	opacity: 1;
	/* drive movement via transform so GPU-accelerated, never silently fails */
	transition: transform 0.6s cubic-bezier(0.34,1.56,0.64,1), opacity 0.3s;
	filter: drop-shadow(0 2px 6px rgba(15,191,127,0.85));
	will-change: transform;
}
#brain-guide-cursor svg { width: 16px; height: 20px; display: block; }
.brain-guide-cursor-ring {
	position: absolute;
	top: -4px; left: -4px;
	width: 24px; height: 24px;
	border: 2px solid rgba(15,191,127,0.75);
	border-radius: 50%;
	animation: brain-ring-pulse 1.4s ease-out infinite;
	pointer-events: none;
}
@keyframes brain-ring-pulse {
	0%   { transform: scale(0.5); opacity: 1; }
	100% { transform: scale(2.0); opacity: 0; }
}
/* Click ripple effect */
.brain-click-ripple {
	position: fixed;
	width: 36px; height: 36px;
	margin-left: -18px; margin-top: -18px;
	border-radius: 50%;
	background: rgba(15,191,127,0.45);
	pointer-events: none;
	z-index: 2147483647;
	animation: brain-click-ripple 0.5s ease-out forwards;
}
@keyframes brain-click-ripple {
	0%   { transform: scale(0.3); opacity: 1; }
	100% { transform: scale(2.5); opacity: 0; }
}

#brain-guide-tooltip {
	position: fixed;
	background: #111827;
	color: white;
	padding: 12px 14px 10px;
	border-radius: 12px;
	font-size: 13px;
	min-width: 200px;
	max-width: 280px;
	z-index: 99999;
	pointer-events: all;
	opacity: 0;
	transition: left 0.6s cubic-bezier(0.34,1.56,0.64,1),
	            top  0.6s cubic-bezier(0.34,1.56,0.64,1),
	            opacity 0.25s;
	box-shadow: 0 10px 32px rgba(0,0,0,0.4);
}
.brain-guide-action-badge {
	display: inline-block;
	background: #0FBF7F;
	color: white;
	font-size: 10.5px;
	font-weight: 700;
	padding: 2px 8px;
	border-radius: 10px;
	margin-bottom: 7px;
	letter-spacing: 0.3px;
}
.brain-guide-msg { line-height: 1.55; margin-bottom: 10px; font-size: 13px; }
.brain-guide-nav { display: flex; gap: 7px; justify-content: flex-end; }
.brain-guide-nav button {
	background: rgba(255,255,255,0.1);
	border: 1px solid rgba(255,255,255,0.2);
	color: white; padding: 5px 12px;
	border-radius: 7px; font-size: 12px; cursor: pointer;
	transition: background 0.15s;
}
.brain-guide-nav button:hover { background: rgba(255,255,255,0.2); }
.brain-guide-next { background: #0FBF7F !important; border-color: #0FBF7F !important; }
.brain-guide-next:hover { background: #0DA870 !important; }

#brain-guide-progress {
	position: fixed;
	top: 58px;
	left: 50%;
	transform: translateX(-50%);
	background: rgba(17,24,39,0.94);
	color: white;
	padding: 8px 18px;
	border-radius: 24px;
	font-size: 12.5px;
	font-weight: 600;
	z-index: 99999;
	display: flex; align-items: center; gap: 12px;
	backdrop-filter: blur(14px);
	box-shadow: 0 4px 20px rgba(0,0,0,0.4);
	animation: brain-fadein 0.3s ease;
	white-space: nowrap;
}
.brain-guide-title { color: #0FBF7F; }
.brain-guide-step-label { color: rgba(255,255,255,0.75); font-weight: 500; font-size: 12px; flex: 1; }
.brain-guide-step-counter { opacity: 0.5; font-weight: 400; font-size: 11.5px; }
.brain-guide-exit {
	background: rgba(255,255,255,0.08);
	border: none; color: rgba(255,255,255,0.5);
	font-size: 11px; cursor: pointer;
	padding: 3px 8px; border-radius: 4px;
}
.brain-guide-exit:hover { color: white; background: rgba(255,255,255,0.15); }

.brain-guide-highlight {
	outline: 2.5px solid #0FBF7F !important;
	outline-offset: 5px !important;
	border-radius: 8px !important;
	animation: brain-highlight-pulse 1.6s ease infinite !important;
}
@keyframes brain-highlight-pulse {
	0%, 100% { outline-color: rgba(15,191,127,1); box-shadow: 0 0 0 0 rgba(15,191,127,0.3); }
	50%       { outline-color: rgba(15,191,127,0.4); box-shadow: 0 0 0 8px rgba(15,191,127,0); }
}

/* Overlay — transparent click-catcher so clicking outside closes panel */
#brain-overlay {
	display: none;
	position: fixed;
	inset: 0;
	background: transparent;
	z-index: 9997;
}
#brain-overlay.brain-overlay-show { display: block; }

/* ── Spotlight overlay (clicky-style dark mask with cutout) ──────── */
#brain-spotlight-mask {
	position: fixed;
	inset: 0;
	z-index: 2147483638;
	pointer-events: none;
	opacity: 0;
	transition: opacity 0.35s ease;
}
#brain-spotlight-mask.brain-spotlight-active { opacity: 1; }

/* The cutout element — positioned over the target, box-shadow darkens everything else */
#brain-spotlight-cutout {
	position: fixed;
	z-index: 2147483639;
	border-radius: 10px;
	box-shadow: 0 0 0 9999px rgba(0,0,0,0.62);
	outline: 2.5px solid rgba(15,191,127,0.85);
	outline-offset: 0;
	pointer-events: none;
	transition: left   0.45s cubic-bezier(0.34,1.2,0.64,1),
	            top    0.45s cubic-bezier(0.34,1.2,0.64,1),
	            width  0.35s cubic-bezier(0.34,1.2,0.64,1),
	            height 0.35s cubic-bezier(0.34,1.2,0.64,1),
	            opacity 0.3s;
	opacity: 0;
}
#brain-spotlight-cutout.brain-spotlight-active { opacity: 1; }

/* Guide start toast */
#brain-guide-toast {
	position: fixed;
	bottom: 36px;
	left: 50%;
	transform: translateX(-50%) translateY(20px);
	background: linear-gradient(135deg, #0FBF7F, #0DA870);
	color: white;
	padding: 12px 24px;
	border-radius: 30px;
	font-size: 13.5px;
	font-weight: 600;
	z-index: 2147483647;
	display: flex;
	align-items: center;
	gap: 10px;
	box-shadow: 0 8px 28px rgba(15,191,127,0.5);
	opacity: 0;
	transition: opacity 0.3s, transform 0.3s;
	white-space: nowrap;
	pointer-events: none;
}
#brain-guide-toast.brain-toast-show {
	opacity: 1;
	transform: translateX(-50%) translateY(0);
}
`;

		document.head.appendChild(style);
	}

	// ── Bubble ────────────────────────────────────────────────────────────────

	function buildBubble() {
		const el = document.createElement("div");
		el.id = "brain-bubble";
		el.title = "Ask brAIn";
		el.innerHTML = `
			<svg class="brain-tab-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
				<path d="M12 2L9.5 8.5L3 9.27L7.5 13.97L6.18 20.9L12 17.77L17.82 20.9L16.5 13.97L21 9.27L14.5 8.5L12 2Z"/>
			</svg>
			<span class="brain-tab-label"><span style="opacity:0.85">br</span><span style="opacity:1;color:#e6fbf4">AI</span><span style="opacity:0.85">n</span></span>
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
						<span>br<span style="color:#b2f5dc">AI</span>n</span>
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
			{ icon: "🧭", text: "Guide me through creating a Sales Invoice" },
			{ icon: "🧭", text: "How do I add a new employee?" },
			{ icon: "🔍", text: "Show me all overdue invoices" },
			{ icon: "📊", text: "What is our revenue this month?" },
			{ icon: "➕", text: "Create a new customer named Acme Corp" },
		];
		return `
			<div class="brain-welcome">
				<div class="brain-welcome-icon" style="font-size:28px;font-weight:800;letter-spacing:-1px;color:#111827">br<span style="color:#0FBF7F">AI</span>n</div>
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
			ctx.doctype  = route[1];
			ctx.doc_name = route[2];
		} else if (route && route[0] === "List" && route[1]) {
			ctx.doctype = route[1];
		}

		// ── Live UI state — gives the AI "eyes" on the current screen ────────────
		ctx.ui = _captureUIState();
		return ctx;
	}

	function _captureUIState() {
		const ui = {};

		// 1. Open dialog / modal
		const modal = document.querySelector(".modal.show");
		if (modal) {
			ui.modal_open   = true;
			ui.modal_title  = (modal.querySelector(".modal-title, .title-text") || {}).textContent?.trim() || "";
			ui.modal_type   = frappe.quick_entry ? "quick_entry" : "dialog";

			// Collect visible field values in the modal
			const fields = {};
			modal.querySelectorAll("[data-fieldname]").forEach(el => {
				const fn  = el.dataset.fieldname;
				const inp = el.querySelector("input, textarea, select");
				if (fn && inp) fields[fn] = inp.value || "";
			});
			if (Object.keys(fields).length) ui.modal_fields = fields;
		} else {
			ui.modal_open = false;
		}

		// 2. Current full form state (cur_frm)
		const frm = window.cur_frm;
		if (frm && frm.doctype) {
			ui.form_doctype  = frm.doctype;
			ui.form_name     = frm.docname;
			ui.form_is_new   = !!frm.is_new();
			ui.form_dirty    = !!frm.is_dirty();
			ui.form_docstatus = frm.doc ? frm.doc.docstatus : null;

			// Collect all non-empty field values (skip large text/attachment)
			const skip = new Set(["Text", "Text Editor", "HTML", "Attach", "Attach Image", "Long Text", "Code"]);
			const vals = {};
			Object.values(frm.fields_dict || {}).forEach(f => {
				if (!f.df || skip.has(f.df.fieldtype)) return;
				const v = frm.doc[f.df.fieldname];
				if (v !== null && v !== undefined && v !== "") vals[f.df.fieldname] = String(v);
			});
			if (Object.keys(vals).length) ui.form_values = vals;

			// Required fields that are still empty
			const missing = [];
			Object.values(frm.fields_dict || {}).forEach(f => {
				if (f.df && f.df.reqd && !frm.doc[f.df.fieldname]) {
					missing.push({ fieldname: f.df.fieldname, label: f.df.label, fieldtype: f.df.fieldtype });
				}
			});
			if (missing.length) ui.form_missing_required = missing;
		}

		// 3. List view — how many rows visible
		if (window.frappe && frappe.views && frappe.views.ListView && frappe.get_route()[0] === "List") {
			try {
				const lv = frappe.views.list_view;
				if (lv) {
					ui.list_doctype    = lv.doctype;
					ui.list_total      = lv.total_count;
					ui.list_page_count = lv.data ? lv.data.length : 0;
				}
			} catch (e) {}
		}

		// 4. Notifications / alerts visible on screen
		const alerts = [...document.querySelectorAll(".alert, .msgprint-dialog .modal-body")]
			.map(el => el.textContent.trim().slice(0, 120))
			.filter(Boolean);
		if (alerts.length) ui.visible_alerts = alerts.slice(0, 3);

		return ui;
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

		// Listen for real-time tool progress via Socket.io
		const onProgress = (data) => updateTypingStatus(data.label);
		frappe.realtime.on("brain_progress", onProgress);

		const pageCtx       = getPageContext();
		const historyToSend = STATE.history.slice(-20);

		frappe.call({
			method: "brain.api.chat.send",
			args: {
				message: msg,
				history: JSON.stringify(historyToSend),
				context: JSON.stringify(pageCtx),
			},
			callback: (r) => {
				frappe.realtime.off("brain_progress", onProgress);
				hideTypingIndicator();
				STATE.loading = false;
				document.getElementById("brain-send-btn").disabled = false;

				if (r.exc) {
					appendMessage("ai", "⚠️ An error occurred. Please check Brain Settings and try again.");
					return;
				}

				const result  = r.message || {};
				const aiText  = result.message || "Done.";
				const actions = result.actions || [];

				STATE.history.push({ role: "user",      content: msg });
				STATE.history.push({ role: "assistant", content: aiText });

				appendMessage("ai", aiText, actions);
				executeActions(actions);
			},
			error: () => {
				frappe.realtime.off("brain_progress", onProgress);
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

	function updateTypingStatus(label) {
		const el = document.getElementById("brain-typing-indicator");
		if (!el) return;
		el.querySelector(".brain-bubble-content").innerHTML = `
			<div class="brain-tool-pill">${label}</div>
		`;
	}

	// ── Execute browser-side actions ──────────────────────────────────────────

	const GUIDE_STATE = { active: false, steps: [], current: 0, title: "", listener: null, pendingTarget: null, pendingRect: null };

	function executeActions(actions) {
		(actions || []).forEach(action => {
			console.log("brAIn action:", action.type, action);
			try {
				if (action.type === "navigate" && action.route) {
					setTimeout(() => {
						frappe.set_route(action.route);
						if (action.filters) {
							setTimeout(() => {
								try { frappe.route_flags.filters = action.filters; } catch (e) {}
							}, 500);
						}
					}, 400);

				} else if (action.type === "open_form" && action.doctype && action.name) {
					setTimeout(() => frappe.set_route("Form", action.doctype, action.name), 400);

				} else if (action.type === "action_choice") {
					// Render choice card inside the last AI message bubble
					const msgs = document.getElementById("brain-messages");
					const lastBubble = msgs && msgs.querySelector(".brain-msg-ai:last-child .brain-bubble-content");
					if (lastBubble) renderActionChoiceCard(action, lastBubble);

				} else if (action.type === "fill_form") {
					setTimeout(() => executeFillForm(action), 400);

				} else if (action.type === "guide_user") {
					setTimeout(() => executeGuideUser(action), 400);
				}
			} catch (e) {
				console.warn("brAIn: action failed", action, e);
			}
		});
	}

	// ── Action Choice Card ────────────────────────────────────────────────────

	function renderActionChoiceCard(action, container) {
		const { doctype, title, name, known_values = {}, required_fields = [] } = action;

		// Known values chips
		const kvHtml = Object.entries(known_values).map(([k, v]) =>
			`<div class="brain-kv-chip"><b>${k.replace(/_/g, " ")}:</b> ${escapeHtml(String(v))}</div>`
		).join("");

		// Required field inputs — render appropriate control per fieldtype
		const rfHtml = required_fields.map(f => {
			const ft = f.fieldtype || "Data";
			const ph = escapeHtml(f.label);
			const fn = escapeHtml(f.fieldname);

			let input;
			if (ft === "Select" && f.options) {
				const opts = String(f.options).split("\n").filter(Boolean);
				const optHtml = opts.map(o => `<option value="${escapeHtml(o)}">${escapeHtml(o)}</option>`).join("");
				input = `<select data-fieldname="${fn}" data-fieldtype="${escapeHtml(ft)}">
					<option value="">— Select ${ph} —</option>${optHtml}
				</select>`;
			} else if (ft === "Check") {
				input = `<label class="brain-check-label">
					<input type="checkbox" data-fieldname="${fn}" data-fieldtype="${escapeHtml(ft)}" value="1"/>
					<span>${ph}</span>
				</label>`;
			} else if (ft === "Date") {
				input = `<input type="date" data-fieldname="${fn}" data-fieldtype="${escapeHtml(ft)}"/>`;
			} else if (["Int","Float","Currency","Percent"].includes(ft)) {
				input = `<input type="number" step="any" data-fieldname="${fn}"
					data-fieldtype="${escapeHtml(ft)}" placeholder="${ph}…" autocomplete="off"/>`;
			} else if (ft === "Link") {
				// Link field — text input with hint showing which doctype it links to
				input = `<input type="text" data-fieldname="${fn}" data-fieldtype="${escapeHtml(ft)}"
					placeholder="${ph}…" autocomplete="off"/>
					<span class="brain-field-hint">🔗 ${escapeHtml(f.options || "")}</span>`;
			} else {
				input = `<input type="text" data-fieldname="${fn}"
					data-fieldtype="${escapeHtml(ft)}" placeholder="${ph}…" autocomplete="off"/>`;
			}

			// Mark mandatory with asterisk
			return `<div class="brain-field-row">
				<label>${escapeHtml(f.label)} <span class="brain-req-star">*</span></label>
				${input}
			</div>`;
		}).join("");

		const card = document.createElement("div");
		card.className = "brain-choice-card";
		card.dataset.doctype  = doctype;
		card.dataset.title    = title;
		card.dataset.name     = name || "";
		card.dataset.known    = JSON.stringify(known_values);
		card.dataset.required = JSON.stringify(required_fields);

		const fieldCount = required_fields.length;
		const hint = fieldCount > 0
			? `<div class="brain-field-count">${fieldCount} required field${fieldCount > 1 ? "s" : ""}</div>`
			: "";

		card.innerHTML = `
			<div class="brain-choice-header">📋 ${escapeHtml(title)}</div>
			${kvHtml ? `<div class="brain-known-values">${kvHtml}</div>` : ""}
			${rfHtml ? `${hint}<div class="brain-required-inputs">${rfHtml}</div>` : ""}
			<div class="brain-choice-btns">
				<button class="brain-choice-btn brain-fill-btn" onclick="brainDoFillForm(this)">✨ Fill Form</button>
				<button class="brain-choice-btn brain-guide-btn" onclick="brainDoGuideForm(this)">🧭 Guide Me</button>
			</div>
		`;
		container.appendChild(card);
		container.closest(".brain-msg") && (container.closest(".brain-msg").scrollIntoView({ block: "end" }));
	}

	function _collectCardValues(card) {
		const known = JSON.parse(card.dataset.known || "{}");
		card.querySelectorAll(".brain-required-inputs [data-fieldname]").forEach(inp => {
			const fn = inp.dataset.fieldname;
			if (!fn) return;
			if (inp.type === "checkbox") {
				known[fn] = inp.checked ? 1 : 0;
			} else if (inp.value !== undefined && String(inp.value).trim() !== "") {
				known[fn] = inp.value.trim();
			}
		});
		return known;
	}

	function _disableCard(card) {
		card.querySelectorAll(".brain-choice-btn").forEach(b => b.disabled = true);
	}

	window.brainDoFillForm = function(btn) {
		const card = btn.closest(".brain-choice-card");
		const doctype = card.dataset.doctype;
		const name    = card.dataset.name || null;
		const values  = _collectCardValues(card);
		_disableCard(card);
		executeFillForm({ doctype, name, values });
	};

	window.brainDoGuideForm = function(btn) {
		const card   = btn.closest(".brain-choice-card");
		const doctype        = card.dataset.doctype;
		const title          = card.dataset.title;
		const name           = card.dataset.name || null;
		const known_values   = JSON.parse(card.dataset.known    || "{}");
		const required_fields = JSON.parse(card.dataset.required || "[]");
		_disableCard(card);

		// Build guide steps from required fields + save
		// Build guide steps — include value so brAIn auto-types it; omit for unknowns (user types)
		const isTextType = (ft) => ["Data","Small Text","Long Text","Text","Int","Float","Currency","Password","Email","Phone"].includes(ft);
		const fieldSteps = required_fields.map(f => {
			const knownVal = known_values[f.fieldname];
			return {
				target_type:       "form_field",
				target_name:       f.fieldname,
				frappe_fieldname:  f.fieldname,
				label:             f.label,
				message:           knownVal
					? `Filling <b>${f.label}</b>: ${String(knownVal)}`
					: `Enter the <b>${f.label}</b>`,
				action:            isTextType(f.fieldtype) ? "type" : "click",
				value:             knownVal || null,
			};
		});

		// Known-value fields that are NOT in required_fields (already known, pre-fill via guide too)
		const knownSteps = Object.entries(known_values)
			.filter(([k]) => !required_fields.some(f => f.fieldname === k))
			.map(([k, v]) => ({
				target_type:      "form_field",
				target_name:      k,
				frappe_fieldname: k,
				label:            k.replace(/_/g, " "),
				message:          `Filling <b>${k.replace(/_/g, " ")}</b>: ${String(v)}`,
				action:           "type",
				value:            v,
			}));

		const steps = [
			...knownSteps,
			...fieldSteps,
			{ target_type: "form_save_button", target_name: "", label: "Save", message: "Saving the record — click Save", action: "click" },
		];

		closePanel();

		try {
			openFullForm(doctype, name);
		} catch (e) {
			console.warn("brAIn: could not open form", e);
		}

		waitForForm(doctype, 12000).then(() => {
			executeGuideUser({ title, steps });
		}).catch(() => {
			executeGuideUser({ title, steps });
		});
	};

	// ── fill_form ─────────────────────────────────────────────────────────────

	function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

	// Auto-click: show ripple at (cx,cy) and dispatch a real click on el
	function _autoClick(cx, cy, el) {
		const ripple = document.createElement("div");
		ripple.className = "brain-click-ripple";
		ripple.style.left = cx + "px";
		ripple.style.top  = cy + "px";
		document.documentElement.appendChild(ripple);
		setTimeout(() => ripple && ripple.remove(), 600);
		if (el) {
			try {
				el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
			} catch (e) { try { el.click(); } catch (e2) {} }
		}
	}

	// Auto-type: type text into an input one character at a time
	async function _autoType(input, text) {
		if (!input || !text) return;
		input.focus();
		for (const char of String(text)) {
			input.value += char;
			input.dispatchEvent(new Event("input",  { bubbles: true }));
			input.dispatchEvent(new Event("change", { bubbles: true }));
			await sleep(40);
		}
	}

	// Auto-search-navigate: type in Frappe search bar, click first result
	async function _searchNavigate(query) {
		const searchInput = document.querySelector(
			"#navbar-search, .awesomebar, .search-bar input, input[placeholder='Search']"
		);
		if (!searchInput) return;
		searchInput.click();
		searchInput.focus();
		searchInput.value = "";
		await sleep(250);
		await _autoType(searchInput, query);
		// Wait for dropdown results
		let result = null;
		for (let i = 0; i < 12; i++) {
			await sleep(250);
			result = document.querySelector(
				".search-results .result, .search-results li, .awesomebar-container .result, " +
				".search-results .list-item, .awesomebar-results li"
			);
			if (result) break;
		}
		if (result) {
			result.click();
		} else {
			// Fallback: press Enter
			searchInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", keyCode: 13, bubbles: true }));
		}
	}

	// Open the full Frappe form — bypasses quick-entry dialogs for any doctype.
	// Strategy: temporarily patch frappe.ui.form.make_quick_entry so that when
	// frappe.new_doc() calls it, it navigates to the full form instead of showing
	// the modal dialog. The patch is restored immediately after via setTimeout(0).
	function openFullForm(doctype, name) {
		if (name) {
			frappe.set_route("Form", doctype, name);
			return;
		}
		// frappe.new_doc() calls make_quick_entry INSIDE frappe.model.with_doctype(),
		// which is async (may fetch doctype meta from server). We must restore the
		// original INSIDE our patch (not via setTimeout) so the restore happens only
		// after the async with_doctype callback fires, not before it.
		const orig = frappe.ui.form.make_quick_entry;
		frappe.ui.form.make_quick_entry = (dt, after_insert, init_cb, doc) => {
			// Restore first so any subsequent calls behave normally
			frappe.ui.form.make_quick_entry = orig;
			// Navigate to full form instead of showing dialog
			if (!doc) doc = frappe.model.get_new_doc(dt);
			frappe.set_route("Form", dt, doc.name);
			if (init_cb)      init_cb(doc);
			if (after_insert)  after_insert(doc);
			return Promise.resolve(doc);
		};
		frappe.new_doc(doctype);
	}

	// Wait for the full form (cur_frm) to be ready for a given doctype.
	function waitForForm(doctype, timeout) {
		timeout = timeout || 12000;
		return new Promise((resolve, reject) => {
			const start = Date.now();
			(function check() {
				const frm = window.cur_frm;
				if (frm && frm.doctype === doctype && frm.fields_dict
						&& Object.keys(frm.fields_dict).length > 0) {
					return setTimeout(resolve, 500);
				}
				if (Date.now() - start > timeout) {
					return reject(new Error("Form timeout: " + doctype));
				}
				setTimeout(check, 250);
			})();
		});
	}

	function showFillOverlay(text) {
		let el = document.getElementById("brain-fill-overlay");
		if (!el) {
			el = document.createElement("div");
			el.id = "brain-fill-overlay";
			document.body.appendChild(el);
		}
		el.innerHTML = `
			<div class="brain-fill-dots">
				<div class="brain-fill-dot"></div>
				<div class="brain-fill-dot"></div>
				<div class="brain-fill-dot"></div>
			</div>
			<span>${text}</span>
		`;
	}

	function hideFillOverlay() {
		const el = document.getElementById("brain-fill-overlay");
		if (el) el.remove();
	}

	// Fill a field in the full form (cur_frm)
	async function animateFillField(fieldname, value) {
		const frm = window.cur_frm;
		if (!frm || !frm.fields_dict) return;

		const field = frm.get_field(fieldname);
		if (!field || !field.$wrapper) return;

		const wrapper = field.$wrapper[0];
		if (!wrapper) return;

		wrapper.scrollIntoView({ behavior: "smooth", block: "center" });
		await sleep(300);
		wrapper.classList.add("brain-filling");

		const fieldtype = field.df ? field.df.fieldtype : "";
		const isText = ["Data", "Small Text", "Long Text", "Text", "Password", "Email", "Phone"].includes(fieldtype);

		if (isText && typeof value === "string" && value.length > 0) {
			await frm.set_value(fieldname, "");
			for (const char of String(value)) {
				await frm.set_value(fieldname, (frm.doc[fieldname] || "") + char);
				await sleep(38);
			}
		} else {
			await frm.set_value(fieldname, value);
			await sleep(300);
		}

		await sleep(120);
		wrapper.classList.remove("brain-filling");
		wrapper.classList.add("brain-filled");
		setTimeout(() => wrapper && wrapper.classList.remove("brain-filled"), 2500);
	}

	async function executeFillForm(action) {
		const { doctype, name, values } = action;
		closePanel();
		showFillOverlay("Opening form…");

		openFullForm(doctype, name);

		try {
			await waitForForm(doctype);
		} catch (e) {
			showFillOverlay("⚠️ Could not load form — please try again.");
			setTimeout(hideFillOverlay, 3000);
			return;
		}

		const entries = Object.entries(values || {})
			.filter(([, v]) => v !== null && v !== undefined && v !== "");

		let idx = 0;
		for (const [fieldname, value] of entries) {
			idx++;
			showFillOverlay(`Filling ${idx} of ${entries.length}…`);
			await animateFillField(fieldname, value);
			await sleep(160);
		}

		showFillOverlay("✓ All fields filled!");
		await sleep(1800);
		hideFillOverlay();
	}

	// ── guide_user ────────────────────────────────────────────────────────────

	// ── guide_user — real cursor that moves anywhere on screen ───────────────

	function executeGuideUser(action) {
		closePanel();
		GUIDE_STATE.steps   = action.steps || [];
		GUIDE_STATE.current = 0;
		GUIDE_STATE.title   = action.title || "AI Guide";
		GUIDE_STATE.listener = null;

		_showGuideToast(GUIDE_STATE.title);

		_buildGuideUI(GUIDE_STATE.title);  // calls _endGuide() internally — sets active=false
		GUIDE_STATE.active = true;          // re-set AFTER _buildGuideUI so it's not clobbered

		// Small delay so DOM is ready, then start
		setTimeout(() => _runGuideStep(0), 800);
	}

	function _showGuideToast(title) {
		let toast = document.getElementById("brain-guide-toast");
		if (!toast) {
			toast = document.createElement("div");
			toast.id = "brain-guide-toast";
			document.body.appendChild(toast);
		}
		toast.innerHTML = `✦ Starting guide: <b style="margin-left:4px">${escapeHtml(title)}</b>`;
		requestAnimationFrame(() => { toast.classList.add("brain-toast-show"); });
		setTimeout(() => {
			toast.classList.remove("brain-toast-show");
			setTimeout(() => toast && toast.remove(), 400);
		}, 2200);
	}

	function _positionSpotlight(rect) {
		const cutout = document.getElementById("brain-spotlight-cutout");
		const mask   = document.getElementById("brain-spotlight-mask");
		if (!cutout || !rect) return;
		const pad = 12;
		cutout.style.left   = (rect.left - pad) + "px";
		cutout.style.top    = (rect.top  - pad) + "px";
		cutout.style.width  = (rect.width  + pad * 2) + "px";
		cutout.style.height = (rect.height + pad * 2) + "px";
		if (!cutout.classList.contains("brain-spotlight-active")) {
			cutout.classList.add("brain-spotlight-active");
		}
		if (mask && !mask.classList.contains("brain-spotlight-active")) {
			mask.classList.add("brain-spotlight-active");
		}
	}

	function _buildGuideUI(title) {
		_endGuide();  // clear any previous

		// ── Spotlight mask + cutout ───────────────────────────────────────────
		const mask = document.createElement("div");
		mask.id = "brain-spotlight-mask";
		document.body.appendChild(mask);

		const cutout = document.createElement("div");
		cutout.id = "brain-spotlight-cutout";
		document.body.appendChild(cutout);

		// ── Isolated top-level layer appended to <html> (not body) ───────────
		// This escapes ALL Frappe stacking contexts (transforms, filters, z-index).
		const layer = document.createElement("div");
		layer.id = "brain-guide-layer";
		layer.style.cssText = [
			"position:fixed", "inset:0", "width:100vw", "height:100vh",
			"z-index:2147483647", "pointer-events:none",
			"overflow:visible", "margin:0", "padding:0",
		].join("!important;") + "!important";
		document.documentElement.appendChild(layer);

		// ── Ghost cursor arrow (absolute inside full-screen layer) ────────────
		const cursor = document.createElement("div");
		cursor.id = "brain-guide-cursor";
		// Park cursor at center via transform — left/top stay at 0,0 always
		const cx0 = Math.round(window.innerWidth  / 2);
		const cy0 = Math.round(window.innerHeight / 2);
		cursor.style.transform = `translate(${cx0}px, ${cy0}px)`;
		cursor.style.opacity   = "1";
		cursor.innerHTML = `
			<svg viewBox="0 0 20 26" fill="none" xmlns="http://www.w3.org/2000/svg">
				<path d="M2 1L2 20L7 15L10.5 22L13 21L9.5 14L16 14L2 1Z"
					fill="#0FBF7F" stroke="white" stroke-width="1.5" stroke-linejoin="round"/>
			</svg>
			<div class="brain-guide-cursor-ring"></div>
		`;
		layer.appendChild(cursor);
		void cursor.offsetWidth;  // commit initial transform before transition fires

		// ── Callout bubble ────────────────────────────────────────
		const bubble = document.createElement("div");
		bubble.id = "brain-guide-tooltip";
		bubble.style.opacity = "0";
		bubble.style.pointerEvents = "all";
		layer.appendChild(bubble);

		// ── Top progress bar (needs clicks — pointer-events enabled) ──────────
		const bar = document.createElement("div");
		bar.id = "brain-guide-progress";
		bar.style.pointerEvents = "all";
		bar.innerHTML = `
			<span class="brain-guide-title">✦ ${title}</span>
			<span class="brain-guide-step-label"></span>
			<span class="brain-guide-step-counter"></span>
			<button class="brain-guide-exit" onclick="brainGuideEnd()">✕ Stop</button>
		`;
		layer.appendChild(bar);

		// ── "brAIn is guiding" state on the edge tab ─────────────
		const bubble2 = document.getElementById("brain-bubble");
		if (bubble2) bubble2.classList.add("brain-guiding");
	}

	// Resolve a step's target_type + target_name to a DOM element
	function _resolveTarget(step) {
		const name = (step.target_name || "").trim();
		switch (step.target_type) {

			case "desktop_icon": {
				const nl = name.toLowerCase();
				// 1. Exact data-id match
				const byId = document.querySelector(`.desktop-icon[data-id="${name}"]`)
					|| [...document.querySelectorAll(".desktop-icon")]
						.find(el => (el.dataset.id || "").toLowerCase() === nl);
				if (byId) return byId;
				// 2. Title text exact match (handles translated labels)
				const byTitle = [...document.querySelectorAll(".desktop-icon .icon-title, .desktop-icon .icon-caption")]
					.find(el => el.textContent.trim().toLowerCase() === nl)
					?.closest(".desktop-icon");
				if (byTitle) return byTitle;
				// 3. Any icon containing the name text (partial match fallback)
				return [...document.querySelectorAll(".desktop-icon")]
					.find(el => el.textContent.trim().toLowerCase().includes(nl)) || null;
			}

			case "sidebar_item":
				// sidebar-item-container has data-id="{{ item.label }}" and item-name="{{ item.label }}"
				return document.querySelector(`.sidebar-item-container[data-id="${name}"]`) ||
					document.querySelector(`.sidebar-item-container[item-name="${name}"]`) ||
					[...document.querySelectorAll(".sidebar-item-label")]
						.find(el => el.textContent.trim().toLowerCase().includes(name.toLowerCase()))
						?.closest(".sidebar-item-container");

			case "list_new_button":
				// Frappe list view: .primary-action in page actions, or btn-new-doc
				return document.querySelector(".page-actions .primary-action") ||
					document.querySelector(".btn-primary.btn-new-doc") ||
					[...document.querySelectorAll(".btn-primary, .btn-primary-light")]
						.find(el => /^new$/i.test(el.textContent.trim()) && el.offsetParent);

			case "form_save_button":
				// Frappe form: .primary-action in .page-actions (Save/Submit button)
				return document.querySelector(".page-actions .primary-action") ||
					document.querySelector(".page-head .primary-action") ||
					[...document.querySelectorAll(".btn-primary")]
						.find(el => /^(save|submit)$/i.test(el.textContent.trim()) && el.offsetParent);

			case "form_field":
				if (window.cur_frm) {
					const f = cur_frm.get_field(name);
					if (f && f.$wrapper) return f.$wrapper[0];
				}
				return document.querySelector(`[data-fieldname="${name}"]`);

			case "nav_button":
				return [...document.querySelectorAll(".btn, button")]
					.find(el => el.textContent.trim().toLowerCase().includes(name.toLowerCase()) && el.offsetParent);

			case "search_bar":
			case "search_navigate":
				return document.querySelector(
					"#navbar-search, .awesomebar, .search-bar input, input[placeholder='Search']"
				);

			case "css_selector":
				return name ? document.querySelector(name) : null;

			default:
				return null;
		}
	}

	// Smart navigation for search_navigate steps — reliable Frappe routing, goes to desktop first
	async function _smartNavigate(targetName) {
		const name = (targetName || "").trim();

		// Always go to desktop (home) first so Frappe fully unmounts the current page
		// before navigating to the target. This prevents stale DOM from blocking field lookup.
		try { frappe.set_route(""); } catch (e) {}
		await sleep(600);

		// "New XYZ" → open new form
		const newMatch = name.match(/^new\s+(.+)$/i);
		if (newMatch) {
			const doctype = newMatch[1].trim();
			try { openFullForm(doctype, null); return; } catch (e) {}
		}
		// "XYZ list" → list view
		const listMatch = name.match(/^(.+?)\s+list$/i);
		if (listMatch) {
			try { frappe.set_route("List", listMatch[1].trim(), "List"); return; } catch (e) {}
		}
		// Workspace/module name
		const workspaceNames = ["BMS","HRMS","LMS","CRM","Stylo","Accounting","Buying","Selling",
			"Stock","Manufacturing","Projects","Support","Assets","Quality","Subcontracting",
			"India Compliance","HR Setup","Payroll","Leaves","Recruitment","Expenses"];
		if (workspaceNames.some(w => w.toLowerCase() === name.toLowerCase())) {
			try { frappe.set_route("Workspaces", name); return; } catch (e) {}
		}
		// Fallback: try typing in search bar
		await _searchNavigate(name);
	}

	async function _runGuideStep(index) {
		if (!GUIDE_STATE.active) return;
		const steps = GUIDE_STATE.steps;

		if (index >= steps.length) { _showGuideDone(); return; }

		GUIDE_STATE.current = index;
		const step = steps[index];

		// Cleanup previous state
		if (GUIDE_STATE.listener) { GUIDE_STATE.listener(); GUIDE_STATE.listener = null; }
		document.querySelectorAll(".brain-guide-highlight").forEach(el => el.classList.remove("brain-guide-highlight"));

		const isLast = index === steps.length - 1;
		const cursor    = document.getElementById("brain-guide-cursor");
		const tooltip   = document.getElementById("brain-guide-tooltip");
		const counter   = document.querySelector(".brain-guide-step-counter");
		const stepLabel = document.querySelector(".brain-guide-step-label");

		if (counter)   counter.textContent  = `${index + 1} / ${steps.length}`;
		if (stepLabel) stepLabel.textContent = step.label ? `→ ${step.label}` : "";
		if (cursor) cursor.style.opacity = "1";

		// ── Navigation steps (search_navigate, desktop_icon, sidebar_item) ────
		// Show a "Navigating…" tooltip at center screen, then navigate, then
		// proceed to the next step which will spotlight the result.
		if (step.target_type === "search_navigate" || step.target_type === "desktop_icon") {
			if (tooltip) {
				const cx = Math.round(window.innerWidth / 2);
				const cy = Math.round(window.innerHeight / 2);
				if (cursor) cursor.style.transform = `translate(${cx}px, ${cy}px)`;
				tooltip.innerHTML = `
					<div class="brain-guide-action-badge">🔍 Navigating…</div>
					<div class="brain-guide-msg">${step.message || "Opening page…"}</div>
				`;
				tooltip.style.left    = Math.round(cx - 130) + "px";
				tooltip.style.top     = Math.round(cy - 60)  + "px";
				tooltip.style.opacity = "1";
			}
			await sleep(600);
			await _smartNavigate(step.target_name || "");
			// Wait for page to fully load and render
			await sleep(3000);
			if (tooltip) tooltip.style.opacity = "0";
			_runGuideStep(index + 1);
			return;
		}

		// Try to find target element (retries up to 8s for form fields)
		let target = null;
		const maxRetries = step.target_type === "form_field" ? 32 : 8;
		for (let i = 0; i < maxRetries; i++) {
			target = _resolveTarget(step);
			if (target) break;
			await sleep(250);
		}

		// Still not found — show message and let user skip
		if (!target) {
			if (tooltip) {
				tooltip.innerHTML = `
					<div class="brain-guide-action-badge">⚠️ Not found</div>
					<div class="brain-guide-msg">${step.message}</div>
					<div class="brain-guide-nav">
						<button class="brain-guide-next" onclick="brainGuideNext()">Next →</button>
					</div>
				`;
				tooltip.style.left    = "50%";
				tooltip.style.top     = "50%";
				tooltip.style.opacity = "1";
			}
			// Wait for user click (brainGuideNext will call _runGuideStep(index+1))
			return;
		}

		// Scroll target into view
		target.scrollIntoView({ behavior: "smooth", block: "center" });
		await sleep(450);
		target.classList.add("brain-guide-highlight");

		// Spotlight + cursor
		const rect = target.getBoundingClientRect();
		_positionSpotlight(rect);
		const cx = Math.round(rect.left + 10);
		const cy = Math.round(rect.top  + 10);
		if (cursor) {
			cursor.style.transform = `translate(${cx}px, ${cy}px)`;
			cursor.style.opacity   = "1";
		}
		await sleep(650);  // wait for cursor animation

		// Build action badge label
		let actionBadge;
		if (step.action === "observe")      actionBadge = "👀 Look here";
		else if (step.action === "type" && step.value) actionBadge = "⚡ brAIn will type this";
		else if (step.action === "type")    actionBadge = "✏️ Your turn — type here";
		else if (step.action === "click")   actionBadge = "👆 Click here";
		else                                actionBadge = "→ Next";

		// ── Show tooltip and WAIT for user to click Next ──────────────────────
		// (exception: type-with-value steps auto-type then show "Next")
		if (step.action === "type" && step.value) {
			// Auto-type the value, then show "Next" button
			if (tooltip) {
				tooltip.innerHTML = `
					<div class="brain-guide-action-badge">${actionBadge}</div>
					<div class="brain-guide-msg">${step.message}</div>
				`;
				const tLeft = Math.min(Math.max(rect.left, 8), window.innerWidth - 290);
				const tTop  = rect.top > 140 ? rect.top - 116 : rect.bottom + 14;
				tooltip.style.left = tLeft + "px"; tooltip.style.top = tTop + "px";
				tooltip.style.opacity = "1";
			}
			await sleep(400);
			// Auto-type
			if (window.cur_frm && step.frappe_fieldname) {
				try { await animateFillField(step.frappe_fieldname, step.value); }
				catch (e) { try { await cur_frm.set_value(step.frappe_fieldname, step.value); } catch(e2){} }
			} else {
				const input = target.querySelector("input,textarea") || (["INPUT","TEXTAREA"].includes(target.tagName) ? target : null);
				if (input) { input.focus(); await _autoType(input, step.value); }
			}
			await sleep(300);
			// Update tooltip to show Next button
			if (tooltip) {
				tooltip.innerHTML = `
					<div class="brain-guide-action-badge">✓ Filled</div>
					<div class="brain-guide-msg">${step.message}</div>
					<div class="brain-guide-nav">
						${index > 0 ? `<button onclick="brainGuidePrev()">← Back</button>` : ""}
						<button class="brain-guide-next" onclick="brainGuideNext()">${isLast ? "Done ✓" : "Next →"}</button>
					</div>
				`;
			}
			// Wait for user to click Next (brainGuideNext → _runGuideStep(index+1))
			return;
		}

		if (step.action === "type" && !step.value) {
			// Focus input, wait for user to type, then show Next
			const input = target.querySelector("input,textarea") || (["INPUT","TEXTAREA"].includes(target.tagName) ? target : null);
			if (input) input.focus();
			if (tooltip) {
				tooltip.innerHTML = `
					<div class="brain-guide-action-badge">${actionBadge}</div>
					<div class="brain-guide-msg">${step.message}</div>
					<div class="brain-guide-nav">
						${index > 0 ? `<button onclick="brainGuidePrev()">← Back</button>` : ""}
						<button class="brain-guide-next" onclick="brainGuideNext()">${isLast ? "Done ✓" : "Next →"}</button>
					</div>
				`;
				const tLeft = Math.min(Math.max(rect.left, 8), window.innerWidth - 290);
				const tTop  = rect.top > 140 ? rect.top - 116 : rect.bottom + 14;
				tooltip.style.left = tLeft + "px"; tooltip.style.top = tTop + "px";
				tooltip.style.opacity = "1";
			}
			// Wait for user click Next OR input + auto-advance
			if (input) {
				let debounce;
				const onInput = () => {
					clearTimeout(debounce);
					debounce = setTimeout(() => {
						if ((input.value || "").length > 0) {
							input.removeEventListener("input", onInput);
							GUIDE_STATE.listener = null;
							if (tooltip) {
								tooltip.querySelector(".brain-guide-next") &&
									(tooltip.querySelector(".brain-guide-next").textContent = isLast ? "Done ✓" : "Next →");
							}
						}
					}, 600);
				};
				input.addEventListener("input", onInput);
				GUIDE_STATE.listener = () => { clearTimeout(debounce); input.removeEventListener("input", onInput); };
			}
			return;
		}

		// ── click or observe: show tooltip, user clicks Next, THEN brAIn acts ──
		if (tooltip) {
			tooltip.innerHTML = `
				<div class="brain-guide-action-badge">${actionBadge}</div>
				<div class="brain-guide-msg">${step.message}</div>
				<div class="brain-guide-nav">
					${index > 0 ? `<button onclick="brainGuidePrev()">← Back</button>` : ""}
					<button class="brain-guide-next" onclick="brainGuideNext()">${isLast ? "Done ✓" : "Next →"}</button>
				</div>
			`;
			const tLeft = Math.min(Math.max(rect.left, 8), window.innerWidth - 290);
			const tTop  = rect.top > 140 ? rect.top - 116 : rect.bottom + 14;
			tooltip.style.left = tLeft + "px"; tooltip.style.top = tTop + "px";
			tooltip.style.opacity = "1";
		}

		// Store click target for brainGuideNext to use
		GUIDE_STATE.pendingTarget = target;
		GUIDE_STATE.pendingRect   = rect;
		// User clicks Next → brainGuideNext() performs action then advances
	}

	function _showGuideDone() {
		const tooltip = document.getElementById("brain-guide-tooltip");
		if (tooltip) {
			tooltip.innerHTML = `
				<div style="text-align:center;padding:4px 0">
					<div style="font-size:22px;margin-bottom:6px">🎉</div>
					<div style="font-weight:600;color:#0FBF7F;margin-bottom:4px">All done!</div>
					<div style="font-size:12px;opacity:0.7;margin-bottom:10px">You completed the guide.</div>
					<button class="brain-guide-next" onclick="brainGuideEnd()">Close ✓</button>
				</div>
			`;
		}
		setTimeout(_endGuide, 3500);
	}

	function _endGuide() {
		GUIDE_STATE.active = false;
		if (GUIDE_STATE.listener) { GUIDE_STATE.listener(); GUIDE_STATE.listener = null; }
		["brain-guide-layer", "brain-guide-cursor", "brain-guide-tooltip", "brain-guide-progress",
		 "brain-spotlight-mask", "brain-spotlight-cutout"].forEach(id => {
			const el = document.getElementById(id);
			if (el) el.remove();
		});
		document.querySelectorAll(".brain-guide-highlight").forEach(el => el.classList.remove("brain-guide-highlight"));
		// Restore tab
		const tab = document.getElementById("brain-bubble");
		if (tab) tab.classList.remove("brain-guiding");
	}

	window.brainGuideNext = async () => {
		if (!GUIDE_STATE.active) return;
		if (GUIDE_STATE.listener) { GUIDE_STATE.listener(); GUIDE_STATE.listener = null; }

		const step   = GUIDE_STATE.steps[GUIDE_STATE.current];
		const target = GUIDE_STATE.pendingTarget;
		const rect   = GUIDE_STATE.pendingRect;
		GUIDE_STATE.pendingTarget = null;
		GUIDE_STATE.pendingRect   = null;

		// Perform the pending action (click/observe) before advancing
		if (step && step.action === "click" && target) {
			const tooltip = document.getElementById("brain-guide-tooltip");
			if (tooltip) {
				const nb = tooltip.querySelector(".brain-guide-next");
				if (nb) { nb.textContent = "⚡ Clicking…"; nb.disabled = true; }
			}
			const cx = Math.round(rect.left + rect.width  / 2);
			const cy = Math.round(rect.top  + rect.height / 2);
			_autoClick(cx, cy, target);
			await sleep(900);
		}

		_runGuideStep(GUIDE_STATE.current + 1);
	};
	window.brainGuidePrev = () => {
		if (GUIDE_STATE.listener) { GUIDE_STATE.listener(); GUIDE_STATE.listener = null; }
		GUIDE_STATE.pendingTarget = null;
		GUIDE_STATE.pendingRect   = null;
		_runGuideStep(Math.max(0, GUIDE_STATE.current - 1));
	};
	window.brainGuideEnd  = () => { _endGuide(); };

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

	// ── Markdown renderer ────────────────────────────────────────────────────

	function renderMarkdown(text) {
		if (!text) return "";

		const lines = text.split("\n");
		const out   = [];
		let i = 0;

		while (i < lines.length) {
			const raw = lines[i];
			const line = raw.trimEnd();

			// ── Fenced code block ─────────────────────────────────────────────
			if (/^```/.test(line)) {
				const lang = line.slice(3).trim();
				const body = [];
				i++;
				while (i < lines.length && !/^```/.test(lines[i])) {
					body.push(lines[i]);
					i++;
				}
				const langTag = lang
					? `<span class="brain-code-lang">${escapeHtml(lang)}</span>`
					: "";
				out.push(`<pre>${langTag}<code>${escapeHtml(body.join("\n"))}</code></pre>`);
				i++;
				continue;
			}

			// ── Table (lines that start/end with |) ───────────────────────────
			if (/^\s*\|/.test(line)) {
				const tableLines = [];
				while (i < lines.length && /^\s*\|/.test(lines[i])) {
					tableLines.push(lines[i]);
					i++;
				}
				out.push(_renderTable(tableLines));
				continue;
			}

			// ── Horizontal rule ───────────────────────────────────────────────
			if (/^[-*_]{3,}\s*$/.test(line)) {
				out.push("<hr>");
				i++;
				continue;
			}

			// ── Headings ──────────────────────────────────────────────────────
			const h4 = line.match(/^###\s+(.+)/);
			if (h4) { out.push(`<h4>${_inline(h4[1])}</h4>`); i++; continue; }
			const h3 = line.match(/^##\s+(.+)/);
			if (h3) { out.push(`<h3>${_inline(h3[1])}</h3>`); i++; continue; }
			const h2 = line.match(/^#\s+(.+)/);
			if (h2) { out.push(`<h2>${_inline(h2[1])}</h2>`); i++; continue; }

			// ── Blockquote ────────────────────────────────────────────────────
			if (/^>\s?/.test(line)) {
				const qLines = [];
				while (i < lines.length && /^>\s?/.test(lines[i])) {
					qLines.push(lines[i].replace(/^>\s?/, ""));
					i++;
				}
				out.push(`<blockquote>${_inline(qLines.join(" "))}</blockquote>`);
				continue;
			}

			// ── Unordered list ────────────────────────────────────────────────
			if (/^[-*+]\s/.test(line)) {
				const items = [];
				while (i < lines.length && /^[-*+]\s/.test(lines[i])) {
					items.push(`<li>${_inline(lines[i].replace(/^[-*+]\s/, ""))}</li>`);
					i++;
				}
				out.push(`<ul>${items.join("")}</ul>`);
				continue;
			}

			// ── Ordered list ──────────────────────────────────────────────────
			if (/^\d+\.\s/.test(line)) {
				const items = [];
				while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
					items.push(`<li>${_inline(lines[i].replace(/^\d+\.\s/, ""))}</li>`);
					i++;
				}
				out.push(`<ol>${items.join("")}</ol>`);
				continue;
			}

			// ── Blank line ────────────────────────────────────────────────────
			if (line.trim() === "") { i++; continue; }

			// ── Paragraph ─────────────────────────────────────────────────────
			const paraLines = [];
			while (
				i < lines.length &&
				lines[i].trim() !== "" &&
				!/^```/.test(lines[i]) &&
				!/^\s*\|/.test(lines[i]) &&
				!/^[-*_]{3,}\s*$/.test(lines[i]) &&
				!/^#{1,4}\s/.test(lines[i]) &&
				!/^[-*+]\s/.test(lines[i]) &&
				!/^\d+\.\s/.test(lines[i]) &&
				!/^>\s?/.test(lines[i])
			) {
				paraLines.push(lines[i].trimEnd());
				i++;
			}
			if (paraLines.length) {
				out.push(`<p>${_inline(paraLines.join(" "))}</p>`);
			}
		}

		return out.join("\n");
	}

	// Process a block of lines as a markdown table
	function _renderTable(rows) {
		const cells = (row) =>
			row.replace(/^\s*\|/, "").replace(/\|\s*$/, "").split("|").map(c => c.trim());

		const isSep = (row) => /^\s*\|?\s*[-:]+[-| :]*\s*$/.test(row);

		let headerRow = null, bodyRows = [];
		let sepFound = false;

		for (const row of rows) {
			if (isSep(row)) { sepFound = true; continue; }
			if (!sepFound && headerRow === null) { headerRow = row; continue; }
			bodyRows.push(row);
		}

		let thead = "";
		if (headerRow) {
			const ths = cells(headerRow).map(c => `<th>${_inline(c)}</th>`).join("");
			thead = `<thead><tr>${ths}</tr></thead>`;
		}

		const tbody = bodyRows
			.filter(r => r.trim() && !/^\s*\|?\s*[-:]+[-| :]*\s*$/.test(r))
			.map(r => {
				const tds = cells(r).map(c => `<td>${_inline(c)}</td>`).join("");
				return `<tr>${tds}</tr>`;
			}).join("");

		return `<div class="brain-table-wrap"><table>${thead}<tbody>${tbody}</tbody></table></div>`;
	}

	// Inline formatting: bold, italic, code, strikethrough
	function _inline(text) {
		return text
			.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
			// Bold+italic
			.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>")
			// Bold
			.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
			// Italic
			.replace(/\*(.+?)\*/g, "<em>$1</em>")
			// Strikethrough
			.replace(/~~(.+?)~~/g, "<del>$1</del>")
			// Inline code
			.replace(/`(.+?)`/g, "<code>$1</code>")
			// ==highlight==
			.replace(/==(.+?)==/g, `<mark class="brain-highlight">$1</mark>`);
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
