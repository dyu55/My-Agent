const $ = (selector) => document.querySelector(selector);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
};
let selectedRun = null;
let displayedSteps = [];
async function get(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Could not load this run");
  return data;
}
function error(message) {
  $("#error").textContent = message;
  $("#error").hidden = false;
}
function showTab(name) {
  requestAnimationFrame(drawDependencies);
  document
    .querySelectorAll(".tab-panel")
    .forEach((p) => (p.hidden = p.id !== `${name}-tab`));
  document.querySelectorAll("[data-tab]").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === name);
    if (b.dataset.tab === name) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
}
document
  .querySelectorAll("[data-tab]")
  .forEach((button) => (button.onclick = () => showTab(button.dataset.tab)));
$("#refresh").onclick = () => refresh().catch((e) => error(e.message));
async function refresh() {
  const [health, runs] = await Promise.all([
    get("/api/health"),
    get("/api/runs"),
  ]);
  $("#workspace-name").textContent = health.workspace;
  $("#run-count").textContent = String(runs.length).padStart(2, "0");
  $("#runs").replaceChildren();
  $("#empty").hidden = !!runs.length;
  $("#detail").hidden = !runs.length;
  if (!runs.length) return;
  if (!runs.some((r) => r.id === selectedRun)) selectedRun = runs[0].id;
  runs.forEach((run) => {
    const button = el(
      "button",
      `run-item ${run.id === selectedRun ? "active" : ""}`,
    );
    button.append(
      el("strong", "", run.task),
      el("small", "", `${run.status.toUpperCase()} · ${run.id.slice(0, 8)}`),
    );
    button.onclick = () => {
      selectedRun = run.id;
      refresh().catch((e) => error(e.message));
    };
    $("#runs").append(button);
  });
  render(await get(`/api/runs/${selectedRun}`));
  $("#error").hidden = true;
}
function render({ run, events, changes, has_pending_action }) {
  displayedSteps = run.steps;
  $("#provider").textContent =
    run.provider === "demo"
      ? "DEMO REPLAY · REAL EXECUTION"
      : `${run.provider.toUpperCase()} · ${run.model}`;
  $("#task").textContent = run.task;
  $("#run-status").textContent =
    run.status === "succeeded" ? "✓ Run completed" : run.status;
  $("#run-status").className = `status ${run.status}`;
  $("#run-id").textContent = `RUN / ${run.id.slice(0, 8)}`;
  $("#run-time").textContent = `${run.elapsed_seconds.toFixed(1)}s elapsed`;
  $("#steps-metric").textContent =
    `${run.steps.filter((s) => s.status === "succeeded").length} / ${run.steps.length}`;
  $("#files-metric").textContent = String(changes.length).padStart(2, "0");
  $("#calls-metric").textContent = String(run.calls).padStart(2, "0");
  const testEvents = events.filter(
    (e) => e.kind === "tool_completed" && e.payload.tool === "run_tests",
  );
  const latest = testEvents.at(-1)?.payload;
  const verified = run.verified_version === run.mutation_version && latest?.ok;
  $("#tests-metric").textContent = latest?.data?.passed ?? "—";
  $("#tests-note").textContent = latest
    ? `${latest.data.failed || 0} failed · ${latest.data.skipped || 0} skipped${verified ? " · current changes verified" : ""}`
    : "No test execution recorded";
  $("#diff-count").textContent = changes.length;
  $("#event-count").textContent = events.length;
  $("#steps").replaceChildren();
  run.steps.forEach((step, i) => {
    const row = el("article", "step");
    row.dataset.step = step.id;
    const phase = el(
      "span",
      `step-number ${step.status === "succeeded" ? "" : "pending"}`,
      `NODE ${String(i + 1).padStart(2, "0")} / ${step.status === "succeeded" ? "✓" : step.status.toUpperCase()}`,
    );
    phase.dataset.status = step.status;
    row.append(phase);
    const content = el("div", "step-content");
    const title = el("div", "step-title", step.title);
    title.append(el("span", "", step.status));
    content.append(
      title,
      el("p", "", step.summary || "Waiting for execution."),
    );
    const tags = el("div", "step-tags");
    const tools = [
      ...new Set(
        events
          .filter(
            (e) => e.kind === "tool_completed" && e.payload.step === step.id,
          )
          .map((e) => e.payload.tool),
      ),
    ];
    tools.forEach((name) => tags.append(el("span", "", name)));
    content.append(
      tags,
      el(
        "small",
        "step-dependency",
        step.depends_on.length
          ? `DEPENDS ON / ${step.depends_on.join(", ")}`
          : "ENTRY POINT / NO DEPENDENCIES",
      ),
    );
    row.append(content);
    $("#steps").append(row);
  });
  requestAnimationFrame(drawDependencies);
  $("#outcome-title").textContent =
    run.status === "succeeded"
      ? "Completed, with evidence."
      : run.status === "paused"
        ? "Ready when you are."
        : "Work you can inspect.";
  $("#summary").textContent =
    run.summary ||
    "The run is in progress. Refresh to see the latest checkpoint.";
  $("#verification").replaceChildren();
  $("#verification").append(el("span", "", verified ? "✓" : "◷"));
  const v = el(
    "div",
    "",
    verified
      ? "Tests passed after the latest changes"
      : has_pending_action
        ? "Interrupted action needs review"
        : run.needs_verification
          ? "Verification is still required"
          : "No code verification required",
  );
  v.append(
    el(
      "small",
      "",
      verified
        ? "Based on process exit and the JUnit report."
        : "Completion follows the persisted execution state.",
    ),
  );
  $("#verification").append(v);
  $("#changes").replaceChildren();
  if (!changes.length)
    $("#changes").append(
      el("p", "diff-warning", "No file-tool changes were recorded."),
    );
  changes.forEach((change) => {
    const card = el("article", "diff-card");
    const heading = el("div", "diff-heading", change.path);
    heading.append(el("span", "", change.created ? "NEW FILE" : "MODIFIED"));
    card.append(heading);
    if (!change.current_matches)
      card.append(
        el(
          "p",
          "diff-warning",
          "This file has changed since the agent edited it. Undo will require review.",
        ),
      );
    const pre = el("pre", "diff-code");
    change.diff
      .split("\n")
      .forEach((line) =>
        pre.append(
          el(
            "span",
            `diff-line ${line.startsWith("@@") ? "hunk" : line.startsWith("+") ? "add" : line.startsWith("-") ? "remove" : ""}`,
            line,
          ),
        ),
      );
    card.append(pre);
    $("#changes").append(card);
  });
  $("#events").replaceChildren();
  events.forEach((event) => {
    const row = el("article", "event");
    row.append(el("span", "event-seq", String(event.seq).padStart(2, "0")));
    const info = el("div", "event-info");
    info.append(
      el(
        "strong",
        "",
        event.kind.replaceAll("_", " ") +
          (event.payload.tool ? ` · ${event.payload.tool}` : ""),
      ),
    );
    const summary =
      event.payload.summary ||
      event.payload.error ||
      (event.kind === "tool_completed"
        ? event.payload.ok
          ? "Tool returned a successful result."
          : "Tool reported a failure."
        : "");
    if (summary) info.append(el("p", "", summary));
    if (event.payload.output) {
      const details = el("details");
      details.append(
        el("summary", "", "Inspect tool output"),
        el("pre", "", event.payload.output),
      );
      info.append(details);
    }
    row.append(
      info,
      el("time", "event-time", new Date(event.created_at).toLocaleTimeString()),
    );
    $("#events").append(row);
  });
  const lastTool = events.filter((e) => e.kind === "tool_completed").at(-1);
  $("#terminal-tool").textContent = lastTool?.payload.tool || "NO TOOL";
  $("#terminal-command").textContent = lastTool
    ? `${lastTool.payload.tool} / ${lastTool.payload.step || "run"}`
    : "Awaiting tool output";
  $("#terminal-output").textContent =
    lastTool?.payload.output ||
    lastTool?.payload.error ||
    "No tool output recorded.";
  $("#terminal-result").textContent = lastTool
    ? (lastTool.payload.ok ? "SUCCESS" : "FAILED") +
      " / " +
      (lastTool.payload.data?.returncode !== undefined
        ? `EXIT ${lastTool.payload.data.returncode}`
        : "TOOL RESULT")
    : "NO RESULT";
  $("#footer-state").textContent =
    run.provider === "demo"
      ? "DETERMINISTIC DEMO · REAL TOOLS"
      : "LOCAL EXECUTION · PERSISTED STATE";
}
refresh().catch((e) => error(e.message));

// Draw only the dependencies present in the persisted plan, including branches.
function drawDependencies() {
  const board = $("#steps");
  if (!board || !board.offsetWidth || $("#overview-tab").hidden) return;
  const box = board.getBoundingClientRect();
  const ns = "http://www.w3.org/2000/svg";
  const make = (tag, attrs) => {
    const n = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v)));
    return n;
  };
  board.querySelector(".flow-links")?.remove();
  const svg = make("svg", {
    class: "flow-links",
    viewBox: `0 0 ${box.width} ${box.height}`,
    "aria-hidden": "true",
  });
  const defs = make("defs", {}),
    marker = make("marker", {
      id: "dependency-arrow",
      viewBox: "0 0 10 10",
      refX: 9,
      refY: 5,
      markerWidth: 5,
      markerHeight: 5,
      orient: "auto-start-reverse",
    });
  marker.append(make("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: "#65a5bc" }));
  defs.append(marker);
  svg.append(defs);
  const elements = new Map(
    [...board.querySelectorAll(".step")].map((n) => [
      n.dataset.step,
      n.getBoundingClientRect(),
    ]),
  );
  displayedSteps.forEach((step) =>
    step.depends_on.forEach((id) => {
      const from = elements.get(id),
        to = elements.get(step.id);
      if (!from || !to) return;
      let d;
      if (Math.abs(from.top - to.top) < 5) {
        const x1 = from.right - box.left,
          y1 = from.top + from.height / 2 - box.top,
          x2 = to.left - box.left,
          y2 = to.top + to.height / 2 - box.top;
        d = `M${x1},${y1} C${x1 + 18},${y1} ${x2 - 18},${y2} ${x2},${y2}`;
      } else {
        const x1 = from.left + from.width / 2 - box.left,
          y1 = from.bottom - box.top,
          x2 = to.left + to.width / 2 - box.left,
          y2 = to.top - box.top;
        d = `M${x1},${y1} C${x1},${y1 + 14} ${x2},${y2 - 14} ${x2},${y2}`;
      }
      svg.append(
        make("path", {
          d,
          fill: "none",
          stroke: "#65a5bc",
          "stroke-width": 1.5,
          "marker-end": "url(#dependency-arrow)",
        }),
      );
    }),
  );
  board.prepend(svg);
}
new ResizeObserver(() => requestAnimationFrame(drawDependencies)).observe(
  $("#steps"),
);
