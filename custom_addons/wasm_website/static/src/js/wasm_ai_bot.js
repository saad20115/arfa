/** @odoo-module **/

function initWasmAiBot() {
    const masterToggle = document.getElementById("wasmFloatingMasterToggle");
    const speedDialStack = document.getElementById("wasmFloatingStack");
    const botToggle = document.getElementById("wasmAiBotToggle");
    const chatWindow = document.getElementById("wasmAiChatWindow");
    const chatClose = document.getElementById("wasmAiChatClose");
    const chatBody = document.getElementById("wasmAiChatBody");
    const chatInput = document.getElementById("wasmAiInput");
    const sendBtn = document.getElementById("wasmAiSend");

    // Toggle Speed Dial Stack (Collapsed by default)
    if (masterToggle && speedDialStack) {
        masterToggle.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            const isCollapsed = speedDialStack.classList.contains("wasm-collapsed");
            const iconOpen = masterToggle.querySelector(".wasm-icon-open");
            const iconClose = masterToggle.querySelector(".wasm-icon-close");

            if (isCollapsed) {
                speedDialStack.classList.remove("wasm-collapsed");
                speedDialStack.classList.add("wasm-expanded");
                if (iconOpen && iconClose) {
                    iconOpen.classList.add("d-none");
                    iconClose.classList.remove("d-none");
                }
            } else {
                speedDialStack.classList.remove("wasm-expanded");
                speedDialStack.classList.add("wasm-collapsed");
                if (iconOpen && iconClose) {
                    iconOpen.classList.remove("d-none");
                    iconClose.classList.add("d-none");
                }
            }
        });
    }

    if (botToggle && chatWindow) {
        // Toggle Chat Window
        botToggle.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            chatWindow.classList.toggle("d-none");
            if (!chatWindow.classList.contains("d-none")) {
                chatInput && chatInput.focus();
            }
        });
    }

    chatClose && chatClose.addEventListener("click", function () {
        chatWindow.classList.add("d-none");
    });

    // Chip Clicks
    document.addEventListener("click", function (e) {
        const chip = e.target.closest(".wasm-chip-btn");
        if (chip) {
            const query = chip.getAttribute("data-query");
            if (query) {
                processUserQuery(query);
            }
        }
    });

    // Send Button Click
    sendBtn && sendBtn.addEventListener("click", function () {
        if (chatInput && chatInput.value.trim() !== "") {
            processUserQuery(chatInput.value.trim());
            chatInput.value = "";
        }
    });

    // Enter Key
    chatInput && chatInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter" && chatInput.value.trim() !== "") {
            processUserQuery(chatInput.value.trim());
            chatInput.value = "";
        }
    });

    // Answers, contact data and welcome text rendered by the template (all editable in the backend)
    const botData = readBotData();

    function readBotData() {
        const node = document.getElementById("arfa-bot-data");
        let data = {};
        if (node) {
            try { data = JSON.parse(node.textContent || "{}") || {}; } catch (err) { data = {}; }
        }
        data.contact = data.contact || {};
        data.replies = (data.replies || []).map(function (r) {
            return Object.assign({}, r, { kw: splitKeywords(r.keywords) });
        });
        return data;
    }

    function processUserQuery(text) {
        const isEn = (document.documentElement.lang && document.documentElement.lang.startsWith("en")) || window.location.pathname.startsWith("/en");

        // Append User Message
        appendMessage(text, "user");

        // Show Typing Indicator
        showTypingIndicator();

        // Simulate AI Thinking Delay
        setTimeout(function () {
            removeTypingIndicator();
            const responseHtml = generateAiResponse(text, isEn);
            appendMessage(responseHtml, "bot");
            if (chatBody) chatBody.scrollTop = chatBody.scrollHeight;
        }, 800);
    }

    function appendMessage(content, sender) {
        if (!chatBody) return;
        const msgDiv = document.createElement("div");
        msgDiv.className = `wasm-ai-message ${sender}`;
        
        const bubbleDiv = document.createElement("div");
        bubbleDiv.className = "wasm-ai-msg-bubble";

        if (sender === "user") {
            bubbleDiv.textContent = content;
        } else {
            // bot answers are built by renderReply(): every admin text is escaped there
            bubbleDiv.innerHTML = content;
        }

        msgDiv.appendChild(bubbleDiv);
        chatBody.appendChild(msgDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function showTypingIndicator() {
        if (!chatBody) return;
        const typingDiv = document.createElement("div");
        typingDiv.id = "wasmAiTyping";
        typingDiv.className = "wasm-ai-message bot";
        typingDiv.innerHTML = `
            <div class="wasm-ai-msg-bubble">
                <div class="wasm-typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        chatBody.appendChild(typingDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function removeTypingIndicator() {
        const typingDiv = document.getElementById("wasmAiTyping");
        if (typingDiv) {
            typingDiv.remove();
        }
    }

    function generateAiResponse(query, isEn) {
        const reply = findReply(botData.replies, query);
        if (reply) {
            return renderReply(reply, isEn, botData.contact);
        }
        return renderText(botData.welcome || "", botData.contact);
    }
}

/* ------------------------------------------------------------------
 * Pure helpers (no DOM) – also used by the keyword-matching check.
 * ------------------------------------------------------------------ */
const BOT_PLACEHOLDER_RE = /\{(phone|mobile|whatsapp|email)\}/g;

function escapeHtml(value) {
    return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function splitKeywords(text) {
    return String(text || "")
        .split(/[,،\n;]+/)
        .map(function (k) { return k.trim().toLowerCase(); })
        .filter(Boolean);
}

/** First answer (display order) with a keyword contained in the question, else the default answer
 *  (the first one without keywords), else null. */
function findReply(replies, query) {
    const q = String(query || "").toLowerCase();
    let fallback = null;
    for (const reply of replies || []) {
        const kw = reply.kw || splitKeywords(reply.keywords);
        if (!kw.length) {
            fallback = fallback || reply;
        } else if (kw.some(function (k) { return q.includes(k); })) {
            return reply;
        }
    }
    return fallback;
}

function pickLang(en, ar, isEn) {
    return (isEn ? (en || ar) : (ar || en)) || "";
}

function resolvePlaceholders(text, contact) {
    return String(text || "").replace(BOT_PLACEHOLDER_RE, function (m, key) { return contact[key] || ""; });
}

function isSafeUrl(url) {
    return /^(\/(?!\/)|#|https?:\/\/|mailto:|tel:)/i.test(url);
}

/** Escaped line with links: web addresses, e-mails and the contact placeholders. */
function formatInline(line, contact) {
    const tokens = [];
    const keep = function (html) { tokens.push(html); return "\u0000" + (tokens.length - 1) + "\u0000"; };
    let text = String(line).replace(BOT_PLACEHOLDER_RE, function (m, key) {
        const value = contact[key] || "";
        if (key === "whatsapp") {
            const shown = contact.mobile || value.replace(/^https?:\/\/(www\.)?/i, "");
            return keep(`<a href="${escapeHtml(value)}" target="_blank" rel="noopener noreferrer" class="dir-ltr d-inline-block">${escapeHtml(shown)}</a>`);
        }
        if (key === "email") {
            return keep(`<a href="mailto:${escapeHtml(value)}">${escapeHtml(value)}</a>`);
        }
        if (key === "phone" || key === "mobile") {
            const tel = value.replace(/[^\d+]/g, "");
            return keep(`<a href="tel:${escapeHtml(tel)}" class="dir-ltr d-inline-block">${escapeHtml(value)}</a>`);
        }
        return value;
    });
    text = text.replace(/https?:\/\/[^\s<>"']+[^\s<>"'.,;:!?)\]]/gi, function (url) {
        return keep(`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(url.replace(/^https?:\/\/(www\.)?/i, ""))}</a>`);
    });
    text = text.replace(/[\w.+-]+@[\w-]+(\.[\w-]+)+/g, function (mail) {
        return keep(`<a href="mailto:${escapeHtml(mail)}">${escapeHtml(mail)}</a>`);
    });
    return escapeHtml(text).replace(/\u0000(\d+)\u0000/g, function (m, i) { return tokens[Number(i)]; });
}

/** Plain admin text -> HTML: one <p> per line, "•"/"-" lines -> bullet list. */
function renderText(text, contact) {
    let html = "";
    let list = "";
    const flushList = function () {
        if (list) { html += `<ul class="mb-2 ps-3 small">${list}</ul>`; list = ""; }
    };
    for (const raw of String(text || "").split(/\r?\n/)) {
        const line = raw.trim();
        // a line whose contact placeholder is empty is skipped (e.g. no phone number set)
        const missing = (line.match(BOT_PLACEHOLDER_RE) || []).some(function (m) { return !contact[m.slice(1, -1)]; });
        if (!line || missing) { flushList(); continue; }
        const bullet = line.match(/^[•\-*·]\s*(.*)$/);
        if (bullet) {
            list += `<li>${formatInline(bullet[1], contact)}</li>`;
        } else {
            flushList();
            html += `<p class="mb-2">${formatInline(line, contact)}</p>`;
        }
    }
    flushList();
    return html;
}

function renderReply(reply, isEn, contact) {
    let html = renderText(pickLang(reply.en, reply.ar, isEn), contact);
    const url = resolvePlaceholders(reply.url, contact).trim();
    const label = pickLang(reply.label_en, reply.label_ar, isEn);
    if (url && label && isSafeUrl(url)) {
        const external = /^https?:\/\//i.test(url);
        const target = external ? ' target="_blank" rel="noopener noreferrer"' : "";
        if (/wa\.me\/|whatsapp\.com/i.test(url)) {
            html += `<a href="${escapeHtml(url)}"${target} class="btn btn-sm btn-success rounded-pill fw-bold text-white w-100"><i class="fa fa-whatsapp me-1"></i> ${escapeHtml(label)}</a>`;
        } else {
            const arrow = isEn ? "fa-arrow-right" : "fa-arrow-left";
            html += `<a href="${escapeHtml(url)}"${target} class="btn btn-sm btn-warning rounded-pill fw-bold text-dark w-100">${escapeHtml(label)} <i class="fa ${arrow} ms-1"></i></a>`;
        }
    }
    return html;
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initWasmAiBot);
} else {
    initWasmAiBot();
}
