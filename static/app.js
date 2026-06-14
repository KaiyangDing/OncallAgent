// OnCall Agent 前端逻辑
// 对接新后端契约:统一响应信封 { success, data, error };SSE 标准事件流。

const API = "/api";
const sessionId = "web-" + Math.random().toString(36).slice(2, 10);

const messagesEl = document.getElementById("messages");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send-btn");
const diagnoseBtn = document.getElementById("diagnose-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const fileInput = document.getElementById("file-input");

let busy = false;

// ---- 消息渲染 ----

function clearWelcome() {
  const w = messagesEl.querySelector(".welcome");
  if (w) w.remove();
}

// 追加一条消息,返回该元素(便于流式更新)
function addMessage(role, text = "") {
  clearWelcome();
  const el = document.createElement("div");
  el.className = "msg " + role;
  el.textContent = text;
  messagesEl.appendChild(el);
  scrollToBottom();
  return el;
}

// 把 bot 元素内容按 Markdown 渲染
function renderMarkdown(el, text) {
  el.innerHTML = marked.parse(text);
  scrollToBottom();
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setBusy(state) {
  busy = state;
  sendBtn.disabled = state;
  diagnoseBtn.disabled = state;
  inputEl.disabled = state;
}

// ---- 通用 SSE 读取:逐行解析 event/data ----
// 标准 SSE:事件以空行分隔,event: 与 data: 各占一行。
async function readSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // 归一化换行(sse-starlette 默认用 \r\n),再按空行切分事件块
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() || ""; // 末块可能不完整,留到下次

    for (const block of blocks) {
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      onEvent(event, data);
    }
  }
}

// ---- 对话(流式)----

async function sendChat(question) {
  addMessage("user", question);
  const botEl = addMessage("bot", "");
  let full = "";

  try {
    const resp = await fetch(`${API}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    await readSSE(resp, (event, data) => {
      if (event === "done") return;
      // 对话流的 data 是纯文本片段,直接累加
      full += data;
      renderMarkdown(botEl, full);
    });

    if (!full) renderMarkdown(botEl, "_(无回复内容)_");
  } catch (err) {
    botEl.textContent = "出错了:" + err.message;
  }
}

// ---- AIOps 诊断(流式)----

async function runDiagnosis() {
  addMessage("user", "🔍 一键诊断当前系统");
  const statusEl = addMessage("status", "诊断中,正在制定计划…");
  let reportEl = null;

  try {
    const resp = await fetch(`${API}/diagnosis`, { method: "POST" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    await readSSE(resp, (event, data) => {
      if (event === "done" || !data) return;
      const evt = JSON.parse(data); // 诊断事件是结构化 JSON

      if (evt.type === "plan") {
        statusEl.textContent = `已制定诊断计划,共 ${evt.steps.length} 步,开始执行…`;
      } else if (evt.type === "step") {
        statusEl.textContent = `已完成:${evt.step.slice(0, 40)}…`;
      } else if (evt.type === "report") {
        statusEl.remove();
        reportEl = addMessage("bot", "");
        renderMarkdown(reportEl, evt.report);
      }
    });
  } catch (err) {
    statusEl.textContent = "诊断出错:" + err.message;
  }
}

// ---- 文档上传 ----

async function uploadFile(file) {
  const statusEl = addMessage("status", `上传中:${file.name}…`);
  try {
    const form = new FormData();
    form.append("file", file);
    const resp = await fetch(`${API}/documents`, { method: "POST", body: form });
    const body = await resp.json();
    if (body.success) {
      statusEl.textContent = `已索引「${body.data.source}」,共 ${body.data.chunks} 个片段`;
    } else {
      statusEl.textContent = "上传失败:" + (body.error || "未知错误");
    }
  } catch (err) {
    statusEl.textContent = "上传出错:" + err.message;
  }
}

// ---- 事件绑定 ----

async function handleSend() {
  const q = inputEl.value.trim();
  if (!q || busy) return;
  inputEl.value = "";
  setBusy(true);
  await sendChat(q);
  setBusy(false);
  inputEl.focus();
}

sendBtn.addEventListener("click", handleSend);
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSend();
});

diagnoseBtn.addEventListener("click", async () => {
  if (busy) return;
  setBusy(true);
  await runDiagnosis();
  setBusy(false);
});

newChatBtn.addEventListener("click", () => {
  if (busy) return;
  messagesEl.innerHTML =
    '<div class="welcome">新对话已开始。注意:本页会话 ID 不变,后端仍记得历史。</div>';
});

fileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file || busy) return;
  setBusy(true);
  await uploadFile(file);
  setBusy(false);
  fileInput.value = "";
});
