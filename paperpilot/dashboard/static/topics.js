async function loadTopics() {
  const root = document.getElementById("topic-map");
  if (!root) return;
  const response = await fetch("/api/topics/timeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ paper_ids: [1], snippets: ["sample"], years: { 1: 2024 } }),
  });
  const data = await response.json();
  root.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
}
loadTopics();
