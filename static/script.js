const chat = document.getElementById("chat-box");
const input = document.getElementById("message");
const sendButton = document.getElementById("send-btn");
const typing = document.getElementById("typing");
const sessionKey = "nova_chat_session_id";

let sessionId = localStorage.getItem(sessionKey) || createId();
let currentHistory = [];
localStorage.setItem(sessionKey, sessionId);

function createId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function formatTime() {
    return new Intl.DateTimeFormat([], { hour: "numeric", minute: "2-digit" }).format(new Date());
}

function renderMarkdown(text) {
    if (window.marked) {
        const html = window.marked.parse(text, { breaks: true, gfm: true });
        return window.DOMPurify ? window.DOMPurify.sanitize(html) : html;
    }
    const escaped = document.createElement("div");
    escaped.textContent = text;
    return escaped.innerHTML.replace(/\n/g, "<br>");
}

function addMessage(role, text, showTime = true) {
    const row = document.createElement("article");
    row.className = `message-row ${role === "user" ? "user" : "assistant"}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "YOU" : "✦";

    const content = document.createElement("div");
    content.className = "bubble";
    if (role === "user") content.textContent = text;
    else content.innerHTML = renderMarkdown(text);

    row.append(avatar, content);
    if (showTime) {
        const meta = document.createElement("div");
        meta.className = "message-meta";
        meta.textContent = formatTime();
        content.append(meta);
    }
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
}

function showWelcome() {
    chat.innerHTML = `<div class="welcome"><div class="welcome-orb">✦</div><h1>How can I help you <span>today?</span></h1><p>Think of me as your intelligent work partner. Ask questions, explore ideas, analyze information, or get things done with a little help from AI.</p></div>`;
}

function setBusy(busy) {
    input.disabled = busy;
    sendButton.disabled = busy;
    typing.style.display = busy ? "flex" : "none";
}

async function sendMessage() {
    const message = input.value.trim();
    if (!message || sendButton.disabled) return;

    addMessage("user", message);
    currentHistory.push({ role: "user", message });
    input.value = "";
    resizeInput();
    setBusy(true);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 45000);
    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json", "Accept": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message }),
            signal: controller.signal,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
        const reply = typeof data.reply === "string" ? data.reply : "I received an invalid response.";
        addMessage("assistant", reply);
        currentHistory.push({ role: "assistant", message: reply });
        loadConversations();
    } catch (error) {
        const messageText = error.name === "AbortError" ? "That took longer than expected. Please try again." : (error.message || "I couldn't reach the assistant right now.");
        addMessage("assistant", `_${messageText}_`);
    } finally {
        clearTimeout(timeout);
        setBusy(false);
        input.focus();
    }
}

async function loadHistory() {
    try {
        const response = await fetch(`/history/${encodeURIComponent(sessionId)}`);
        if (!response.ok) throw new Error("history unavailable");
        const data = await response.json();
        currentHistory = data.history || [];
        chat.innerHTML = "";
        if (!currentHistory.length) showWelcome();
        currentHistory.forEach(item => addMessage(item.role, item.message, false));
    } catch (error) {
        showWelcome();
    }
}

function renderConversationList(items) {
    const list = document.getElementById("conversation-list");
    list.innerHTML = "";
    if (!items.length) {
        list.innerHTML = `<div class="conversation" style="color:var(--muted);cursor:default">No conversations yet</div>`;
        return;
    }
    items.slice(0, 15).forEach(item => {
        const button = document.createElement("button");
        button.className = `conversation ${item.session_id === sessionId ? "current" : ""}`;
        button.type = "button";
        button.textContent = item.title || "Untitled conversation";
        const date = document.createElement("time");
        date.textContent = item.created_at ? new Date(item.created_at.replace(" ", "T") + "Z").toLocaleDateString([], { month: "short", day: "numeric" }) : "";
        button.appendChild(date);
        button.addEventListener("click", () => switchSession(item.session_id));
        list.appendChild(button);
    });
}

async function loadConversations() {
    try {
        const response = await fetch("/conversations");
        const data = await response.json();
        renderConversationList(data.conversations || []);
    } catch (error) { /* The chat remains usable if the list endpoint is unavailable. */ }
}

function switchSession(id) {
    sessionId = id;
    localStorage.setItem(sessionKey, sessionId);
    loadHistory();
    loadConversations();
    document.getElementById("sidebar").classList.remove("open");
}

async function clearChat() {
    if (!currentHistory.length || !window.confirm("Clear this conversation?")) return;
    try {
        await fetch(`/history/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
        currentHistory = [];
        showWelcome();
        loadConversations();
    } catch (error) { window.alert("Could not clear the conversation."); }
}

function newChat() {
    sessionId = createId();
    localStorage.setItem(sessionKey, sessionId);
    currentHistory = [];
    showWelcome();
    loadConversations();
    input.focus();
    document.getElementById("sidebar").classList.remove("open");
}

function exportChat() {
    if (!currentHistory.length) return;
    const text = currentHistory.map(item => `${item.role === "user" ? "You" : "Nova"}: ${item.message}`).join("\n\n");
    const blob = new Blob([text], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `nova-conversation-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(link.href);
}

function resizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
}

async function loadHealth() {
    try {
        const response = await fetch("/health");
        const data = await response.json();
        const services = data.services || {};
        const ready = services.gemini;
        document.getElementById("provider-label").textContent = ready ? "AI systems ready" : "Demo mode active";
        document.getElementById("provider-detail").textContent = ready ? "Gemini connected" : "Add an API key for full AI";
    } catch (error) {
        document.getElementById("provider-label").textContent = "Offline mode";
        document.getElementById("provider-detail").textContent = "Backend unavailable";
    }
}

document.getElementById("send-btn").addEventListener("click", sendMessage);
document.getElementById("new-chat-btn").addEventListener("click", newChat);
document.getElementById("refresh-conversations").addEventListener("click", loadConversations);
document.getElementById("export-btn").addEventListener("click", exportChat);
document.getElementById("theme-btn").addEventListener("click", () => { document.body.classList.toggle("light"); localStorage.setItem("nova_theme", document.body.classList.contains("light") ? "light" : "dark"); });
document.getElementById("mobile-menu-btn").addEventListener("click", () => document.getElementById("sidebar").classList.toggle("open"));
document.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => { input.value = button.dataset.prompt; resizeInput(); input.focus(); }));
input.addEventListener("input", resizeInput);
input.addEventListener("keydown", event => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); } });
if (localStorage.getItem("nova_theme") === "light") document.body.classList.add("light");

loadHistory();
loadConversations();
loadHealth();
input.focus();
