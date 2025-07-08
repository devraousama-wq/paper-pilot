const form = document.getElementById("chat-form");
const log = document.getElementById("chat-log");
form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = document.getElementById("question").value;
  const response = await fetch("/api/rag/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = await response.json();
  log.textContent = data.answer;
});
