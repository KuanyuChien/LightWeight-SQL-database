(function () {
  const data = window.DASHBOARD_DATA;
  if (!data) {
    throw new Error("Dashboard data is missing. Run scripts/generate_dashboard_data.py first.");
  }

  const formatInteger = (value) => new Intl.NumberFormat("en-US").format(value);
  const formatSeconds = (value) => `${Number(value).toFixed(3)}s`;
  const formatMs = (value) => `${Number(value).toFixed(3)} ms/run`;

  const setText = (selector, text) => {
    const element = document.querySelector(selector);
    if (element) {
      element.textContent = text;
    }
  };

  const heroMetrics = [
    {
      label: "Coverage",
      value: `${formatInteger(data.testSnapshot.passed)}/${formatInteger(data.testSnapshot.total)}`,
      detail: `${data.testSnapshot.coveragePercent.toFixed(1)}% of the local staged sqllogictest corpus is passing.`,
    },
    {
      label: "Timeouts",
      value: data.testSnapshot.timedOut === 0 ? "None" : formatInteger(data.testSnapshot.timedOut),
      detail: "Latest tracked staged validation reported no timed-out cases.",
    },
    {
      label: "Runtime",
      value: formatSeconds(data.testSnapshot.runtimeSeconds),
      detail: `Tracked full staged run improved from ${formatSeconds(data.testSnapshot.previousRuntimeSeconds)}.`,
    },
  ];

  document.getElementById("hero-metrics").innerHTML = heroMetrics
    .map(
      (metric) => `
        <article class="metric-card">
          <span class="metric-label">${metric.label}</span>
          <strong class="metric-value">${metric.value}</strong>
          <p class="metric-detail">${metric.detail}</p>
        </article>
      `,
    )
    .join("");

  setText("#project-title", data.project.title);
  setText("#project-description", data.project.description);
  setText("#agent-workflow", data.project.agentWorkflow);
  setText("#project-story", data.project.story);
  setText("#scope-summary", data.testSnapshot.knownScope);
  setText("#scope-note", data.testSnapshot.externalScopeNote);
  setText("#hotspot-line", `Slowest tracked passing cases: ${data.testSnapshot.hotspots}`);

  document.getElementById("bug-box").innerHTML = `
    <p><strong>Tracked root cause:</strong> ${data.testSnapshot.bugSummary.rootCause}</p>
    <p><strong>Fix:</strong> ${data.testSnapshot.bugSummary.fix}</p>
    <p><strong>Result:</strong> ${data.testSnapshot.bugSummary.result}</p>
  `;

  document.getElementById("file-list").innerHTML = data.testSnapshot.localFiles
    .map((fileName) => `<span class="file-pill">${fileName}</span>`)
    .join("");

  document.getElementById("story-cards").innerHTML = data.storyCards
    .map(
      (card) => `
        <article class="story-card">
          <span class="story-label">${card.label}</span>
          <strong class="story-value">${card.value}</strong>
          <p class="story-detail">${card.detail}</p>
        </article>
      `,
    )
    .join("");

  const testStats = [
    {
      label: "Passing Tests",
      value: formatInteger(data.testSnapshot.passed),
      detail: `Iteration ${data.testSnapshot.latestIteration} in PROGRESS.md keeps the suite at full local coverage.`,
    },
    {
      label: "Total Tests",
      value: formatInteger(data.testSnapshot.total),
      detail: "Current scope is the five local sqllogictest files listed in current_stage.txt.",
    },
    {
      label: "Timeouts",
      value: data.testSnapshot.timedOut === 0 ? "0" : formatInteger(data.testSnapshot.timedOut),
      detail: "The timeout spike from select4 was resolved by join pruning and indexed lookups.",
    },
    {
      label: "Tracked Runtime",
      value: formatSeconds(data.testSnapshot.runtimeSeconds),
      detail: data.testSnapshot.latestNotes,
    },
  ];

  document.getElementById("test-stats").innerHTML = testStats
    .map(
      (stat) => `
        <article class="stat-card">
          <span class="stat-label">${stat.label}</span>
          <strong class="stat-value">${stat.value}</strong>
          <p class="stat-detail">${stat.detail}</p>
        </article>
      `,
    )
    .join("");

  const maxTiming = Math.max(...data.testSnapshot.fileTimings.map((timing) => timing.seconds));
  document.getElementById("timing-bars").innerHTML = data.testSnapshot.fileTimings
    .map(
      (timing) => `
        <div class="bar-row">
          <div class="bar-meta">
            <span>${timing.name}</span>
            <span>${formatSeconds(timing.seconds)}</span>
          </div>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${(timing.seconds / maxTiming) * 100}%"></div>
          </div>
        </div>
      `,
    )
    .join("");

  const maxBenchmark = Math.max(...data.benchmarkSnapshot.metrics.map((metric) => metric.avgMsPerRun));
  document.getElementById("benchmark-bars").innerHTML = data.benchmarkSnapshot.metrics
    .map(
      (metric) => `
        <article class="benchmark-card">
          <span class="benchmark-label">${metric.label}</span>
          <strong>${formatMs(metric.avgMsPerRun)}</strong>
          <div class="bar-track">
            <div class="bar-fill" style="width: ${(metric.avgMsPerRun / maxBenchmark) * 100}%"></div>
          </div>
          <p class="benchmark-detail">Target: ${formatMs(data.benchmarkSnapshot.targetMs)} on the three-way join hotspot.</p>
        </article>
      `,
    )
    .join("");

  document.getElementById("timeline").innerHTML = data.milestones
    .map(
      (milestone) => `
        <article class="timeline-item">
          <div class="timeline-head">
            <span class="timeline-date">${milestone.date}</span>
            ${milestone.testsPassing ? `<span class="timeline-tests">${formatInteger(milestone.testsPassing)} tests</span>` : ""}
          </div>
          <h3>${milestone.title}</h3>
          <p class="timeline-summary">${milestone.summary}</p>
        </article>
      `,
    )
    .join("");

  document.getElementById("query-grid").innerHTML = data.examples
    .map((example) => {
      const resultMarkup =
        example.kind === "result"
          ? `
            <table>
              <thead>
                <tr>${example.columns.map((column) => `<th>${column}</th>`).join("")}</tr>
              </thead>
              <tbody>
                ${example.rows
                  .map((row) => `<tr>${row.map((value) => `<td>${String(value)}</td>`).join("")}</tr>`)
                  .join("")}
              </tbody>
            </table>
          `
          : `<p class="query-note">${example.note}</p>`;

      return `
        <article class="query-card">
          <div>
            <span class="query-label">${example.label}</span>
          </div>
          <pre><code>${example.sql}</code></pre>
          ${resultMarkup}
        </article>
      `;
    })
    .join("");

  // SQL Playground
  const sqlInput = document.getElementById("sql-input");
  const sqlResult = document.getElementById("sql-result");
  const sqlStatus = document.getElementById("sql-status");
  const runBtn = document.getElementById("sql-run");
  const resetBtn = document.getElementById("sql-reset");

  async function executeSQL(sql, reset) {
    sqlStatus.textContent = "Running…";
    runBtn.disabled = true;
    try {
      const response = await fetch("/api/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sql, reset: !!reset }),
      });
      const result = await response.json();
      if (!result.success) {
        sqlResult.innerHTML = `<p class="result-error">Error: ${result.error}</p>`;
        sqlStatus.textContent = "Error";
        return;
      }
      if (!result.rows || result.rows.length === 0) {
        sqlResult.innerHTML = `<p class="result-ok">✓ Statement executed successfully (no rows returned).</p>`;
        sqlStatus.textContent = "OK";
        return;
      }
      const colCount = result.rows[0].length;
      const headers = (result.columns && result.columns.length === colCount)
        ? result.columns
        : Array.from({ length: colCount }, (_, i) => `col${i + 1}`);
      sqlResult.innerHTML = `
        <table>
          <thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
          <tbody>${result.rows.map((row) => `<tr>${row.map((v) => `<td>${v === null ? "NULL" : v}</td>`).join("")}</tr>`).join("")}</tbody>
        </table>`;
      sqlStatus.textContent = `${result.rows.length} row${result.rows.length === 1 ? "" : "s"}`;
    } catch (err) {
      sqlResult.innerHTML = `<p class="result-error">Network error – is the server running? (python dashboard/serve.py)</p>`;
      sqlStatus.textContent = "Failed";
    } finally {
      runBtn.disabled = false;
    }
  }

  runBtn.addEventListener("click", () => executeSQL(sqlInput.value));
  resetBtn.addEventListener("click", () => {
    executeSQL("", true);
    sqlResult.innerHTML = `<p class="result-ok">✓ Engine reset – all tables cleared.</p>`;
    sqlStatus.textContent = "Reset";
  });

  sqlInput.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      executeSQL(sqlInput.value);
    }
  });
})();
