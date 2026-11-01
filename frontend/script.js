const form = document.querySelector("#chat-form");
const input = document.querySelector("#question");
const sendButton = document.querySelector("#send");
const newChatButton = document.querySelector("#new-chat");
const welcome = document.querySelector("#welcome");
const messages = document.querySelector("#messages");
const conversation = document.querySelector("#conversation");
const status = document.querySelector("#status");
const suggestions = document.querySelectorAll("[data-question]");

let history = [];
let busy = false;

function scrollToBottom() {
  conversation.scrollTop = conversation.scrollHeight;
}

function setBusy(value) {
  busy = value;
  sendButton.disabled = value;
  newChatButton.disabled = value;

  suggestions.forEach((button) => {
    button.disabled = value;
  });

  form.setAttribute("aria-busy", String(value));
  sendButton.textContent = value ? "Working…" : "Send ↗";
}

function setStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function addMessage(role, text, sources = []) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "YOU" : "IRONSTORE AI";

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = text;

  article.append(label, body);

  if (sources.length > 0) {
    const sourceList = document.createElement("div");
    sourceList.className = "sources";

    const heading = document.createElement("p");
    heading.className = "sources-heading";
    heading.textContent = "SOURCES · Expand to inspect the supporting passages";
    sourceList.append(heading);

    sources.forEach((source) => {
      const details = document.createElement("details");
      details.className = "source-card";

      const summary = document.createElement("summary");
      const filename = source.filename
        .replace(/^IronStore_/, "")
        .replace(/\.pdf$/i, "")
        .replaceAll("_", " ");

      summary.textContent =
        `[${source.label}] ${filename} · PDF page ${source.page}`;

      const excerpt = document.createElement("p");
      excerpt.textContent = source.excerpt;

      const link = document.createElement("a");
      const encodedPath = source.source
        .split("/")
        .map(encodeURIComponent)
        .join("/");

      link.href = `/documents/${encodedPath}#page=${source.page}`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Open source PDF ↗";

      details.append(summary, excerpt, link);
      sourceList.append(details);
    });

    article.append(sourceList);
  }

  messages.append(article);
  scrollToBottom();
  return article;
}

async function sendQuestion(question) {
  question = question.trim();

  if (!question || busy) return;

  if (question.length > 4000) {
    setStatus("Please keep your question under 4,000 characters.", true);
    return;
  }

  welcome.hidden = true;
  const userMessage = addMessage("user", question);

  input.value = "";
  setBusy(true);
  setStatus("Searching company documents…");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        chat_history: history.slice(-6),
      }),
    });

    if (!response.ok) {
      let message = "The request failed. Please try again.";

      try {
        const error = await response.json();

        if (typeof error.detail === "string") {
          message = error.detail;
        }
      } catch {
        // Keep the readable fallback if the server returns a non-JSON error.
      }

      throw new Error(message);
    }

    const result = await response.json();
    addMessage("assistant", result.answer, result.sources);

    history.push(
      { role: "user", content: question },
      { role: "assistant", content: result.answer }
    );

    history = history.slice(-6);
    setStatus("");
  } catch (error) {
    // Remove the failed turn so displayed messages match stored history.
    userMessage.remove();
    welcome.hidden = messages.children.length > 0;

    if (!input.value.trim()) {
      input.value = question;
    }

    setStatus(
      error instanceof TypeError
        ? "Could not reach the server. Check that FastAPI is running."
        : error.message,
      true
    );
  } finally {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  sendQuestion(input.value);
});

input.addEventListener("keydown", (event) => {
  if (
    event.key === "Enter" &&
    !event.shiftKey &&
    !event.isComposing
  ) {
    event.preventDefault();
    form.requestSubmit();
  }
});

suggestions.forEach((button) => {
  button.addEventListener("click", () => {
    sendQuestion(button.dataset.question);
  });
});

newChatButton.addEventListener("click", () => {
  if (busy) return;

  history = [];
  messages.replaceChildren();
  welcome.hidden = false;
  input.value = "";
  setStatus("");
  conversation.scrollTop = 0;
  input.focus();
});