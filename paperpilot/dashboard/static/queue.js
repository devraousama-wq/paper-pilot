async function loadQueue() {
  const root = document.getElementById("queue-list");
  if (!root) return;
  const response = await fetch("/api/reading/queue");
  const items = await response.json();
  root.innerHTML = items.map((item) => `<li>Paper ${item.paper_id} · ${item.status} · priority ${item.priority}</li>`).join("");
}
loadQueue();
