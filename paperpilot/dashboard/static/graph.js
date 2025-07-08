async function loadGraph() {
  const root = document.getElementById("graph-root");
  if (!root) return;
  const response = await fetch("/api/citations/edges");
  const edges = await response.json();
  root.innerHTML = `<pre>${JSON.stringify(edges, null, 2)}</pre>`;
}
loadGraph();
