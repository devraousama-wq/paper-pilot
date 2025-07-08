async function loadSections() {
  const root = document.getElementById("sections");
  if (!root) return;
  const paperId = root.dataset.paperId;
  const response = await fetch(`/api/parsers/papers/${paperId}/sections`);
  const sections = await response.json();
  root.innerHTML = sections.map((section) => `
    <section class="panel">
      <h3>${section.title}</h3>
      <p>${section.content.slice(0, 1200)}</p>
    </section>
  `).join("");
}
loadSections();
