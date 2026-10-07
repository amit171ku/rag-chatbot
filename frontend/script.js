const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send");
const clearBtn = document.getElementById("clear");
const uploadBtn = document.getElementById("upload-btn");
const fileInput = document.getElementById("file-input");

let history = []; // [{ role: "user" | "model", content: string }]

function addMessage(text, cls) {
  const div = document.createElement("div");
  div.className = `msg ${cls}`;
  div.textContent = text; // textContent prevents XSS
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function renderMarkdown(el, text) {
  // marked: Markdown -> HTML. DOMPurify: strips anything unsafe (XSS protection).
  if (window.marked && window.DOMPurify) {
    el.innerHTML = DOMPurify.sanitize(marked.parse(text));
  } else {
    el.textContent = text; // fallback if the CDN scripts failed to load
  }
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function addSources(msgEl, sources) {
  const details = document.createElement("details");
  details.className = "sources";

  const summary = document.createElement("summary");
  summary.textContent = `Sources (${sources.length})`;
  details.appendChild(summary);

  sources.forEach((s, i) => {
    const p = document.createElement("p");
    p.textContent = `[${i + 1}] (score ${s.score}) ${s.text}`; // textContent prevents XSS
    details.appendChild(p);
  });

  msgEl.appendChild(details);
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  inputEl.disabled = busy;
  if (!busy) inputEl.focus();
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  addMessage(text, "msg--user");
  inputEl.value = "";
  inputEl.style.height = "auto";
  setBusy(true);
  const loading = addMessage("Thinking...", "msg--loading");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, history }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }

    const { reply, sources } = await res.json();
    loading.remove();
    const msgEl = addMessage("", "msg--model");
    renderMarkdown(msgEl, reply);
    if (sources && sources.length) addSources(msgEl, sources);
    history.push({ role: "user", content: text }, { role: "model", content: reply });
  } catch (e) {
    loading.remove();
    addMessage(`Error: ${e.message}`, "msg--error");
  } finally {
    setBusy(false);
  }
}

sendBtn.addEventListener("click", sendMessage);

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = inputEl.scrollHeight + "px";
});

clearBtn.addEventListener("click", () => {
  history = [];
  messagesEl.innerHTML = "";
});

uploadBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  uploadBtn.disabled = true;
  const status = addMessage(`Uploading ${file.name}...`, "msg--loading");

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("/api/upload", { method: "POST", body: formData });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Upload failed (${res.status})`);
    }

    const data = await res.json();
    status.remove();
    addMessage(
      `Uploaded ${data.filename}: ${data.chunk_count} chunks embedded. Ask me anything about it.`,
      "msg--model"
    );
  } catch (e) {
    status.remove();
    addMessage(`Error: ${e.message}`, "msg--error");
  } finally {
    uploadBtn.disabled = false;
    fileInput.value = "";
  }
});