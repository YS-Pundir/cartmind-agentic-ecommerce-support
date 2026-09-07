// Point this at wherever `uvicorn main:app` is running.
const API_BASE = "http://localhost:8000";

const els = {
  drawerToggle: document.getElementById("drawerToggle"),
  sidebar: document.getElementById("sidebar"),
  backdrop: document.getElementById("backdrop"),
  newThreadBtn: document.getElementById("newThreadBtn"),
  threadList: document.getElementById("threadList"),
  threadEmpty: document.getElementById("threadEmpty"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("fileInput"),
  kbStatus: document.getElementById("kbStatus"),
  chatTitle: document.getElementById("chatTitle"),
  chatSubtitle: document.getElementById("chatSubtitle"),
  statusDot: document.getElementById("statusDot"),
  statusText: document.getElementById("statusText"),
  messages: document.getElementById("messages"),
  emptyState: document.getElementById("emptyState"),
  composerForm: document.getElementById("composerForm"),
  messageInput: document.getElementById("messageInput"),
  sendBtn: document.getElementById("sendBtn"),
};

let currentThreadId = null;

// ---------------- Backend status ----------------

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error();
    els.statusDot.className = "status-dot online";
    els.statusText.textContent = "backend online";
  } catch {
    els.statusDot.className = "status-dot offline";
    els.statusText.textContent = "backend unreachable";
  }
}

// ---------------- Threads sidebar ----------------

async function loadThreads() {
  try {
    const res = await fetch(`${API_BASE}/api/threads`);
    if (!res.ok) throw new Error("Failed to load threads");
    const threads = await res.json();
    renderThreadList(threads);
  } catch (err) {
    console.error(err);
  }
}

function renderThreadList(threads) {
  els.threadList.innerHTML = "";
  els.threadEmpty.style.display = threads.length === 0 ? "block" : "none";

  for (const t of threads) {
    const stub = document.createElement("div");
    stub.className = "thread-stub" + (t.thread_id === currentThreadId ? " active" : "");
    stub.setAttribute("role", "listitem");
    stub.tabIndex = 0;

    stub.innerHTML = `
      <div class="thread-stub-row">
        <span class="thread-id">#${escapeHtml(t.thread_id)}</span>
        <span class="thread-count">${t.message_count} msg${t.message_count === 1 ? "" : "s"}</span>
      </div>
      <div class="thread-preview">${escapeHtml(t.last_message || "No messages yet")}</div>
      <button class="thread-delete" aria-label="Delete thread ${escapeHtml(t.thread_id)}" title="Delete thread">×</button>
    `;

    stub.addEventListener("click", (e) => {
      if (e.target.closest(".thread-delete")) return;
      resumeThread(t.thread_id);
      closeDrawer();
    });

    stub.querySelector(".thread-delete").addEventListener("click", (e) => {
      e.stopPropagation();
      deleteThread(t.thread_id);
    });

    els.threadList.appendChild(stub);
  }
}

async function resumeThread(threadId) {
  currentThreadId = threadId;
  els.chatTitle.textContent = `Thread #${threadId}`;
  els.chatSubtitle.textContent = "Resumed — new messages continue this thread";
  els.messages.innerHTML = "";

  try {
    const res = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}/messages`);
    if (!res.ok) throw new Error("Failed to load thread history");
    const data = await res.json();

    if (data.messages.length === 0) {
      showEmptyState();
    } else {
      for (const m of data.messages) {
        addBubble(m.role === "user" ? "user" : "agent", m.content);
      }
    }
  } catch (err) {
    console.error(err);
    addBubble("error", "Couldn't load this thread's history. Check that the backend is running.");
  }

  // Was this thread's agent run left mid-graph by an earlier error? If so,
  // offer to continue it from its exact checkpoint instead of resending.
  checkInterruptedState(threadId);

  loadThreads(); // refresh active-state highlighting
}

async function checkInterruptedState(threadId) {
  try {
    const res = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}/state`);
    if (!res.ok) return;
    const state = await res.json();
    if (state.interrupted) {
      showResumeBanner(threadId, state.next_nodes);
    }
  } catch (err) {
    console.error(err);
  }
}

function showResumeBanner(threadId, nextNodes) {
  const row = document.createElement("div");
  row.className = "bubble-row error";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = `This session was interrupted before finishing (stopped before: ${nextNodes.join(", ")}). `;

  const btn = document.createElement("button");
  btn.textContent = "Resume from where it stopped";
  btn.className = "resume-btn";
  btn.addEventListener("click", () => {
    btn.disabled = true;
    row.remove();
    resumeInterrupted(threadId);
  });

  bubble.appendChild(btn);
  row.appendChild(bubble);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function resumeInterrupted(threadId) {
  const pendingRow = addBubble("pending", "Resuming from where it stopped…");
  els.sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}/resume`, {
      method: "POST",
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Could not resume this thread.");
    }

    const data = await res.json();
    pendingRow.remove();
    addBubble("agent", data.answer);
    loadThreads();
  } catch (err) {
    console.error(err);
    pendingRow.remove();
    addBubble("error", err.message || "Something went wrong resuming the agent.");
  } finally {
    els.sendBtn.disabled = false;
  }
}

async function deleteThread(threadId) {
  const confirmed = confirm(`Delete thread #${threadId}? This can't be undone.`);
  if (!confirmed) return;

  try {
    const res = await fetch(`${API_BASE}/api/threads/${encodeURIComponent(threadId)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Delete failed");

    if (threadId === currentThreadId) {
      startNewThread();
    }
    loadThreads();
  } catch (err) {
    console.error(err);
    alert("Couldn't delete that thread. Check that the backend is running.");
  }
}

function startNewThread() {
  currentThreadId = null;
  els.chatTitle.textContent = "New thread";
  els.chatSubtitle.textContent = "Not saved yet — send a message to open a ticket";
  els.messages.innerHTML = "";
  showEmptyState();
  loadThreads();
}

// ---------------- Chat ----------------

function showEmptyState() {
  const el = document.createElement("div");
  el.className = "empty-state";
  el.innerHTML = "<p>Ask about an order, a return, or a policy. Cartmind pulls the answer from your order records or the knowledge base.</p>";
  els.messages.appendChild(el);
}

function addBubble(role, text) {
  const row = document.createElement("div");
  row.className = `bubble-row ${role}`;
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  row.appendChild(bubble);
  els.messages.appendChild(row);
  els.messages.scrollTop = els.messages.scrollHeight;
  return row;
}

async function sendMessage(message) {
  els.messages.querySelector(".empty-state")?.remove();
  addBubble("user", message);

  const pendingRow = addBubble("pending", "Thinking…");
  els.sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        thread_id: currentThreadId, // null starts a new thread
      }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      // The backend still returns the thread_id it created/used even on
      // failure (see main.py). That matters most on a brand-new thread:
      // currentThreadId is still null at this point, so without it we'd
      // have no id to ask /state about and could never offer resume.
      throw Object.assign(
        new Error(data.detail || "The agent could not process that message."),
        { thread_id: data.thread_id }
      );
    }

    pendingRow.remove();
    addBubble("agent", data.answer);

    currentThreadId = data.thread_id;
    els.chatTitle.textContent = `Thread #${data.thread_id}`;
    els.chatSubtitle.textContent = "Resumed — new messages continue this thread";
    loadThreads();
  } catch (err) {
    console.error(err);
    pendingRow.remove();
    addBubble("error", err.message || "Something went wrong reaching the agent.");

    // The failure may have happened partway through the graph (e.g. a tool
    // call exhausted its retries) rather than before anything ran. Check
    // whether there's a checkpoint to continue from instead of just losing
    // the turn — using the thread_id from the error body if this was a
    // brand-new thread that never got assigned one before failing.
    const failedThreadId = err.thread_id || currentThreadId;
    if (failedThreadId) {
      currentThreadId = failedThreadId;
      els.chatTitle.textContent = `Thread #${failedThreadId}`;
      els.chatSubtitle.textContent = "Resumed — new messages continue this thread";
      checkInterruptedState(failedThreadId);
    }
  } finally {
    els.sendBtn.disabled = false;
  }
}

els.composerForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = els.messageInput.value.trim();
  if (!message) return;
  els.messageInput.value = "";
  sendMessage(message);
});

els.newThreadBtn.addEventListener("click", startNewThread);

// ---------------- Knowledge base upload ----------------

async function uploadDocument(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    setKbStatus("Only PDF files are supported.", "err");
    return;
  }

  setKbStatus(`Embedding ${file.name}…`, "");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/api/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || "Upload failed.");
    }

    const data = await res.json();
    setKbStatus(`Indexed ${data.filename} — ${data.chunks_indexed} chunks added.`, "ok");
  } catch (err) {
    console.error(err);
    setKbStatus(err.message || "Upload failed. Check that the backend is running.", "err");
  }
}

function setKbStatus(text, kind) {
  els.kbStatus.textContent = text;
  els.kbStatus.className = "kb-status" + (kind ? ` ${kind}` : "");
}

els.fileInput.addEventListener("change", () => {
  const file = els.fileInput.files[0];
  if (file) uploadDocument(file);
});

["dragenter", "dragover"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.add("dragover");
  })
);

["dragleave", "drop"].forEach((evt) =>
  els.dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    els.dropzone.classList.remove("dragover");
  })
);

els.dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file) uploadDocument(file);
});

// ---------------- Mobile drawer ----------------

function openDrawer() {
  els.sidebar.classList.add("open");
  els.backdrop.classList.add("show");
  els.drawerToggle.setAttribute("aria-expanded", "true");
}

function closeDrawer() {
  els.sidebar.classList.remove("open");
  els.backdrop.classList.remove("show");
  els.drawerToggle.setAttribute("aria-expanded", "false");
}

els.drawerToggle.addEventListener("click", () => {
  els.sidebar.classList.contains("open") ? closeDrawer() : openDrawer();
});
els.backdrop.addEventListener("click", closeDrawer);

// ---------------- Utilities ----------------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------------- Init ----------------

checkHealth();
loadThreads();
setInterval(checkHealth, 15000);
