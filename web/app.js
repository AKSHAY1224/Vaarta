// Vaarta web UI. Plain JavaScript, no libraries, no internet.
//
// THE MEMORY: the same idea as the `messages` list in main.py. Every user
// message and every reply is pushed here, and the WHOLE array is sent to the
// server on each turn. The server puts the system prompt in front of it.
// Open the browser console (F12) and type `messages` to watch it grow.
const messages = [];

const LABELS = { user: "You", assistant: "Vaarta", error: "Problem" };

const chat = document.getElementById("chat");
const empty = document.getElementById("empty");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const newChatBtn = document.getElementById("new-chat");
const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

// Add one message block to the page and return its text bubble.
function addMessage(role, text) {
  empty.hidden = true;
  const block = document.createElement("div");
  block.className = `msg ${role}`;

  const who = document.createElement("div");
  who.className = "who";
  who.textContent = LABELS[role];

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  // textContent, never innerHTML: the model's words are shown as text,
  // never run as HTML.
  bubble.textContent = text;

  block.append(who, bubble);
  chat.append(block);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

// While a reply is streaming, nothing may send or clear the memory.
function setBusy(busy) {
  input.disabled = busy;
  sendBtn.disabled = busy;
  newChatBtn.disabled = busy;
  sendBtn.textContent = busy ? "Thinking" : "Send";
}

async function send(text) {
  messages.push({ role: "user", content: text });
  addMessage("user", text);
  setBusy(true);

  // An empty Vaarta bubble that fills up as the reply streams in.
  const bubble = addMessage("assistant", "");
  bubble.classList.add("thinking");
  let reply = "";
  let res;

  try {
    res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    if (!res.ok) {
      // The server is up but could not get a reply. It sends the reason as JSON.
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }

    // Read the reply piece by piece instead of waiting for all of it.
    // {stream: true} keeps multi-byte characters (Hindi, emoji) intact when
    // one character is split across two chunks.
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      reply += decoder.decode(value, { stream: true });
      bubble.classList.remove("thinking");
      bubble.textContent = reply;
      chat.scrollTop = chat.scrollHeight;
    }
    if (!reply) {
      reply = "(no reply)"; // rare, but the model can end a turn with nothing
      bubble.textContent = reply;
    }
    messages.push({ role: "assistant", content: reply });
  } catch (err) {
    bubble.parentElement.className = "msg error";
    bubble.previousElementSibling.textContent = LABELS.error;
    bubble.textContent = res === undefined
      ? `Could not reach the server (${err.message}). Is server.py running?`
      : `Could not get a reply: ${err.message}`;
    // No reply was stored for this turn, so remove the question as well. The
    // array must stay in user/reply pairs or the model gets confused next turn.
    messages.pop();
  } finally {
    bubble.classList.remove("thinking");
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || sendBtn.disabled) return;
  input.value = "";
  input.style.height = "auto";
  send(text);
});

// Enter sends, Shift+Enter makes a new line.
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

// Let the box grow with the text, up to the limit set in style.css.
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${input.scrollHeight}px`;
});

// Clicking a suggestion sends it.
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    if (!sendBtn.disabled) send(chip.textContent);
  });
});

// New chat: empty the memory and the screen. There is nothing to delete
// anywhere else, because nothing was ever stored outside this array.
newChatBtn.addEventListener("click", () => {
  if (newChatBtn.disabled) return;
  messages.length = 0;
  chat.querySelectorAll(".msg").forEach((m) => m.remove());
  empty.hidden = false;
  input.focus();
});

// On load: ask the server which model is running and whether Ollama is up.
fetch("/status")
  .then((res) => res.json())
  .then((s) => {
    statusDot.className = `dot ${s.ok ? "ok" : "bad"}`;
    statusText.textContent = s.ok ? `${s.model} ready` : "Ollama not ready";
    statusText.title = s.problem || ""; // hover shows the exact reason
  })
  .catch(() => {
    statusDot.className = "dot bad";
    statusText.textContent = "server not reachable";
  });

input.focus();
