document.getElementById("generate-review")?.addEventListener("click", async () => {
  const topic = document.getElementById("topic").value;
  const response = await fetch("/api/review/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, paper_summaries: ["Sample paper summary"] }),
  });
  const data = await response.json();
  document.getElementById("review-output").textContent = data.markdown;
});
