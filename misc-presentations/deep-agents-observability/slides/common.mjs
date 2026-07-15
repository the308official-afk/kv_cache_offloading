const C = {
  ink: "#101820",
  ink2: "#172033",
  paper: "#F7F4ED",
  paper2: "#EFEAE1",
  mist: "#E8ECEF",
  line: "#CAD2D9",
  muted: "#667085",
  white: "#FFFFFF",
  blue: "#2563EB",
  blue2: "#1D4ED8",
  green: "#0F9F6E",
  amber: "#D97706",
  red: "#BE123C",
  violet: "#6D28D9",
  slate: "#334155",
};

const D = {
  runShort: "NodeBB-049989... / 2026-05-15 15:56:33",
  model: "Qwen/Qwen2.5-7B-Instruct",
  parser: "hermes",
  worker: "7587894864635169841",
  inputTokens: "12,553",
  cachedTokens: "12,544",
  outputTokens: "2,048",
  cachePct: "99.93%",
  promptChars: "6,906",
  taskChars: "1,330",
  behaviorChars: "8,972",
  ttft: "141.928 ms",
  decode: "5,334.126 ms",
  endToEnd: "81.001 sec",
  toolCalls: "2",
  expectedTools: "9",
  observedTools: "ls, read_file",
};

const SOURCES = "Source: prompt_evolution_report, stage_lifecycle_table, runtime_alignment_analysis, final_summary";

function rect(slide, ctx, x, y, w, h, fill, line = "none", name) {
  const stroke = line === "none" ? { fill: "#00000000", width: 0, style: "solid" } : line;
  return ctx.addShape(slide, { x, y, width: w, height: h, fill, line: stroke, name });
}

function rule(slide, ctx, x, y, w, color = C.line, h = 1) {
  return rect(slide, ctx, x, y, w, h, color);
}

function text(slide, ctx, value, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text: value,
    x,
    y,
    width: w,
    height: h,
    fontSize: opts.size ?? 22,
    color: opts.color ?? C.ink,
    bold: opts.bold ?? false,
    typeface: opts.face ?? (opts.mono ? "Aptos Mono" : opts.title ? "Aptos Display" : "Aptos"),
    align: opts.align ?? "left",
    valign: opts.valign ?? "top",
    fill: opts.fill ?? "#00000000",
    line: opts.line ?? { fill: "#00000000", width: 0, style: "solid" },
    insets: opts.insets ?? { left: 0, right: 0, top: 0, bottom: 0 },
    name: opts.name,
  });
}

function bg(slide, ctx, mode = "light") {
  rect(slide, ctx, 0, 0, ctx.W, ctx.H, mode === "dark" ? C.ink : C.paper);
}

function footer(slide, ctx, section, mode = "light", page) {
  const color = mode === "dark" ? "#A8B3C4" : C.muted;
  rule(slide, ctx, 64, 664, 1152, mode === "dark" ? "#2B3545" : "#D7D1C8");
  text(slide, ctx, section, 64, 680, 340, 18, { size: 10, color, bold: true });
  text(slide, ctx, SOURCES, 410, 680, 620, 18, { size: 9, color });
  text(slide, ctx, String(page).padStart(2, "0"), 1164, 680, 52, 18, { size: 10, color, align: "right", mono: true });
}

function heading(slide, ctx, kicker, claim, mode = "light") {
  const dark = mode === "dark";
  rect(slide, ctx, 64, 52, 8, 24, dark ? C.blue : C.violet);
  text(slide, ctx, kicker.toUpperCase(), 84, 52, 420, 24, { size: 12, color: dark ? "#A8B3C4" : C.muted, bold: true });
  text(slide, ctx, claim, 64, 86, 1010, 98, {
    size: claim.length > 72 ? 34 : 40,
    color: dark ? C.white : C.ink,
    bold: true,
    title: true,
  });
}

function support(slide, ctx, value, mode = "light") {
  text(slide, ctx, value, 64, 612, 980, 34, { size: 15, color: mode === "dark" ? "#CBD5E1" : C.slate });
}

function chip(slide, ctx, label, x, y, w, color, mode = "light") {
  rect(slide, ctx, x, y, w, 30, mode === "dark" ? "#172033" : C.white, { fill: color, width: 1.5, style: "solid" });
  text(slide, ctx, label, x + 10, y + 7, w - 20, 18, { size: 12, color: mode === "dark" ? C.white : C.ink, bold: true, mono: true });
}

function metric(slide, ctx, value, label, note, x, y, w, color, mode = "light") {
  const fill = mode === "dark" ? "#172033" : C.white;
  rect(slide, ctx, x, y, w, 104, fill, { fill: mode === "dark" ? "#344055" : "#DAD4CB", width: 1, style: "solid" });
  text(slide, ctx, value, x + 18, y + 14, w - 36, 36, { size: 30, color, bold: true, title: true });
  text(slide, ctx, label, x + 18, y + 54, w - 36, 18, { size: 12, color: mode === "dark" ? "#D8DEE9" : C.slate, bold: true });
  text(slide, ctx, note, x + 18, y + 76, w - 36, 16, { size: 10.5, color: mode === "dark" ? "#A8B3C4" : C.muted });
}

function callout(slide, ctx, title, body, x, y, w, h, color, mode = "light") {
  const fill = mode === "dark" ? "#172033" : C.white;
  rect(slide, ctx, x, y, w, h, fill, { fill: color, width: 2, style: "solid" });
  rect(slide, ctx, x, y, 8, h, color);
  text(slide, ctx, title, x + 22, y + 18, w - 42, 26, { size: 18, color: mode === "dark" ? C.white : C.ink, bold: true });
  text(slide, ctx, body, x + 22, y + 50, w - 42, h - 62, { size: 14, color: mode === "dark" ? "#D8DEE9" : C.slate });
}

function stageNode(slide, ctx, label, owner, x, y, w, color, mode = "light") {
  const fill = mode === "dark" ? "#172033" : C.white;
  rect(slide, ctx, x, y, w, 78, fill, { fill: color, width: 2, style: "solid" });
  text(slide, ctx, label, x + 12, y + 14, w - 24, 24, { size: 15, color: mode === "dark" ? C.white : C.ink, bold: true, mono: true });
  text(slide, ctx, owner, x + 12, y + 44, w - 24, 18, { size: 11, color: mode === "dark" ? "#A8B3C4" : C.muted });
}

function rowTable(slide, ctx, headers, rows, x, y, widths, rowH, opts = {}) {
  const mode = opts.mode ?? "light";
  const dark = mode === "dark";
  const headFill = dark ? "#1B2638" : "#E7E0D6";
  const rowFill = dark ? "#111B2C" : "#FBF8F2";
  const altFill = dark ? "#162132" : "#F2EDE5";
  const lineColor = dark ? "#334155" : "#D8D0C7";
  let cx = x;
  headers.forEach((h, i) => {
    rect(slide, ctx, cx, y, widths[i], rowH, headFill);
    text(slide, ctx, h, cx + 8, y + 8, widths[i] - 16, rowH - 12, { size: opts.headerSize ?? 11, color: dark ? C.white : C.ink, bold: true });
    cx += widths[i];
  });
  rows.forEach((r, idx) => {
    const ry = y + rowH + idx * rowH;
    cx = x;
    r.forEach((cell, i) => {
      rect(slide, ctx, cx, ry, widths[i], rowH, idx % 2 ? altFill : rowFill);
      text(slide, ctx, String(cell), cx + 8, ry + 7, widths[i] - 16, rowH - 11, { size: opts.size ?? 10.5, color: dark ? "#D8DEE9" : C.slate, mono: opts.monoCols?.includes(i) });
      cx += widths[i];
    });
    rule(slide, ctx, x, ry + rowH - 1, widths.reduce((a, b) => a + b, 0), lineColor);
  });
}

function bar(slide, ctx, label, value, max, x, y, w, color, suffix = "") {
  text(slide, ctx, label, x, y, 210, 22, { size: 13, color: C.slate, bold: true });
  rect(slide, ctx, x + 220, y + 3, w, 16, "#E4DDD3");
  rect(slide, ctx, x + 220, y + 3, Math.max(4, w * value / max), 16, color);
  text(slide, ctx, `${value.toLocaleString()}${suffix}`, x + 230 + w, y - 1, 62, 22, { size: 12, color: C.ink, bold: true, mono: true });
}

function drawCover(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  rect(slide, ctx, 0, 0, 20, 720, C.blue);
  rect(slide, ctx, 20, 0, 6, 720, C.green);
  text(slide, ctx, "EXECUTIVE TECHNICAL BRIEFING", 72, 58, 520, 24, { size: 13, color: "#A8B3C4", bold: true });
  text(slide, ctx, "End-to-End Observability for Deep Agents + Dynamo + SGLang", 72, 108, 870, 178, { size: 52, color: C.white, bold: true, title: true });
  text(slide, ctx, "How a single SWE-bench task becomes a prompt, a runtime request, and an explainable outcome.", 76, 306, 700, 58, { size: 22, color: "#D8DEE9" });
  metric(slide, ctx, "7", "prompt lineage stages", "task_input to model_behavior", 72, 436, 220, C.violet, "dark");
  metric(slide, ctx, "5/5", "alignment rows agreed", "no runtime divergence found", 318, 436, 220, C.green, "dark");
  metric(slide, ctx, "0", "workspace changes", "execution gap isolated", 564, 436, 220, C.red, "dark");
  const nodes = ["Task", "Prompt", "Request", "Runtime", "Worker", "Behavior"];
  nodes.forEach((n, i) => {
    const x = 845 + i * 66;
    rect(slide, ctx, x, 514 - i * 30, 42, 42, i % 2 ? "#23314A" : "#1A2638", { fill: [C.blue, C.violet, C.green, C.amber, C.blue2, C.red][i], width: 1.5, style: "solid" });
    text(slide, ctx, n, x - 8, 566, 54, 18, { size: 9.5, color: "#CBD5E1", align: "center" });
  });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 1);
  return slide;
}

function drawExecutiveSummary(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Executive Summary", "The reporting layer turned one opaque agent run into a cross-system operating trace.");
  callout(slide, ctx, "Visibility", "We can now see the run move from raw task input to formatted prompt, request envelope, runtime preprocessing, worker execution, and final behavior.", 70, 214, 344, 220, C.blue);
  callout(slide, ctx, "Control", "Every stage carries an owner label and evidence trail, which makes failures assignable instead of mysterious.", 468, 214, 344, 220, C.violet);
  callout(slide, ctx, "Latest finding", "Instrumentation worked: parser, tools, worker, and alignment evidence were captured. The agent still failed to edit the workspace.", 866, 214, 344, 220, C.red);
  rect(slide, ctx, 70, 464, 1140, 104, C.ink);
  text(slide, ctx, "Central message for executives", 94, 486, 260, 20, { size: 13, color: "#A8B3C4", bold: true });
  text(slide, ctx, "The latest run did not solve the coding task; it proved we can diagnose where the failure happened.", 94, 516, 900, 42, { size: 22, color: C.white, bold: true, title: true });
  support(slide, ctx, "This reframes the work from guesswork to operating visibility: prompt assembly, runtime behavior, and agent effectiveness can now be separated.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 2);
  return slide;
}

function drawOldProblem(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Why It Matters", "The old failure mode was ambiguity, not just low performance.", "dark");
  rect(slide, ctx, 80, 220, 500, 280, "#172033", { fill: "#445065", width: 1, style: "solid" });
  rect(slide, ctx, 700, 220, 500, 280, "#172033", { fill: C.green, width: 1.5, style: "solid" });
  text(slide, ctx, "Before", 110, 246, 220, 28, { size: 22, color: C.red, bold: true, title: true });
  text(slide, ctx, "Final answer only", 110, 292, 340, 34, { size: 30, color: C.white, bold: true, title: true });
  text(slide, ctx, "When a run failed, the team could not quickly tell whether the issue was prompt construction, Deep Agents behavior, Dynamo routing, SGLang execution, tool parsing, or the model itself.", 110, 352, 420, 94, { size: 17, color: "#D8DEE9" });
  text(slide, ctx, "After", 730, 246, 220, 28, { size: 22, color: C.green, bold: true, title: true });
  text(slide, ctx, "Traceable evidence chain", 730, 292, 390, 34, { size: 30, color: C.white, bold: true, title: true });
  text(slide, ctx, "The run now carries stage ownership, prompt structure, tool/runtime context, worker evidence, and final behavior into a coherent report family.", 730, 352, 420, 94, { size: 17, color: "#D8DEE9" });
  text(slide, ctx, "Manager impact: faster debugging, clearer ownership, and a more honest separation between platform readiness and agent success.", 126, 548, 1020, 34, { size: 23, color: C.white, bold: true, title: true, align: "center" });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 3);
  return slide;
}

function drawWhatBuilt(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "What We Built", "Every major stage now has an owner, an evidence record, and an artifact trail.");
  const layers = [
    ["AgentBench runner", "Task loading, workspace prep, run lifecycle, artifact collection", C.violet],
    ["Deep Agents app", "Agent construction, request context, response capture, behavior evidence", C.blue],
    ["Dynamo frontend", "Tool parser observation, prompt tokenization, cache signals, routing", C.green],
    ["SGLang worker", "Prefill/decode activity, worker id, cache/recompute evidence", C.amber],
    ["Reports", "Prompt evolution, lifecycle, runtime alignment, final summary", C.red],
  ];
  layers.forEach((l, i) => {
    const y = 202 + i * 70;
    const left = 100 + i * 18;
    const width = 710 - i * 28;
    rect(slide, ctx, left, y, width, 52, C.white, { fill: l[2], width: 2, style: "solid" });
    text(slide, ctx, l[0], left + 28, y + 11, 210, 24, { size: 18, color: C.ink, bold: true });
    text(slide, ctx, l[1], left + 300, y + 13, width - 328, 24, { size: 13, color: C.slate });
  });
  metric(slide, ctx, "4", "core report families", "prompt, lifecycle, runtime, summary", 930, 214, 230, C.blue);
  metric(slide, ctx, "51", "lifecycle table rows", "setup through run summary tables", 930, 326, 230, C.violet);
  metric(slide, ctx, "1", "worker observed", D.worker, 930, 438, 230, C.green);
  support(slide, ctx, "The architecture is intentionally split: benchmark wrapper responsibilities stay in AgentBench; actual agent runtime uses Deep Agents.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 4);
  return slide;
}

function drawSystemFlow(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "System Flow", "The run now has a visible route from dataset input to runtime evidence.");
  const nodes = [
    ["SWE-bench task", "problem + tests", C.violet],
    ["Prompt builder", "114-line prompt", C.blue],
    ["Deep Agents", "request + tools", C.blue2],
    ["Dynamo", "parser + routing", C.green],
    ["SGLang worker", "prefill + decode", C.amber],
    ["Behavior", "tools + finish", C.red],
    ["Artifacts", "reports + tables", C.slate],
  ];
  nodes.forEach((n, i) => {
    const x = 54 + i * 172;
    stageNode(slide, ctx, n[0], n[1], x, 292, 136, n[2]);
    if (i < nodes.length - 1) {
      rule(slide, ctx, x + 136, 331, 36, C.line, 3);
      rect(slide, ctx, x + 166, 324, 10, 16, C.line);
    }
  });
  const lanes = [
    ["Prompt layer", 168, C.violet],
    ["Agent layer", 340, C.blue],
    ["Runtime layer", 512, C.green],
    ["Evidence layer", 1028, C.red],
  ];
  lanes.forEach((l) => {
    text(slide, ctx, l[0], l[1], 226, 140, 18, { size: 12, color: l[2], bold: true, align: "center" });
    rule(slide, ctx, l[1] + 12, 250, 116, l[2], 2);
  });
  support(slide, ctx, "The visual route matters because failures can now be located along the path instead of assigned to a generic agent failure.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 5);
  return slide;
}

function drawReportFamilies(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Evidence Pack", "Four report families create the complete management story.", "dark");
  const reports = [
    ["stage_lifecycle_table", "Chronology", "Shows when the run moved through setup, workflow, runtime log collection, and artifact writing.", C.green],
    ["prompt_evolution_report", "Transformation", "Shows how task fields became prompt text, request envelope, runtime context, and model behavior.", C.violet],
    ["runtime_alignment_analysis", "Cross-layer check", "Compares Deep Agents decisions with Dynamo and SGLang runtime evidence.", C.blue],
    ["final_summary", "Outcome", "Preserves the actual final response so claims can be checked against what the model really said.", C.red],
  ];
  reports.forEach((r, i) => {
    const x = i % 2 === 0 ? 88 : 682;
    const y = i < 2 ? 224 : 416;
    rect(slide, ctx, x, y, 510, 142, "#172033", { fill: r[3], width: 2, style: "solid" });
    text(slide, ctx, r[0], x + 24, y + 22, 360, 24, { size: 18, color: C.white, bold: true, mono: true });
    text(slide, ctx, r[1], x + 24, y + 54, 160, 20, { size: 13, color: r[3], bold: true });
    text(slide, ctx, r[2], x + 24, y + 82, 438, 36, { size: 14, color: "#D8DEE9" });
  });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 6);
  return slide;
}

function drawPromptSpine(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Prompt Evolution", "Prompt evolution is now visible as a seven-stage lineage.");
  const stages = [
    ["task_input", "agentbench_runner", C.violet],
    ["formatted_prompt", "prompt_builder", C.blue],
    ["final_model_request", "request_dispatch", C.blue2],
    ["system_context", "deepagents_app", C.amber],
    ["tool_runtime_context", "frontend_dynamo", C.green],
    ["runtime_preprocessing", "frontend_dynamo", C.green],
    ["model_behavior", "deepagents_app", C.red],
  ];
  rule(slide, ctx, 95, 334, 1078, C.line, 3);
  stages.forEach((s, i) => {
    const x = 76 + i * 178;
    rect(slide, ctx, x + 44, 306, 34, 34, s[2]);
    text(slide, ctx, String(i + 1), x + 44, 314, 34, 18, { size: 14, color: C.white, bold: true, align: "center", mono: true });
    text(slide, ctx, s[0], x, 362, 122, 34, { size: 12, color: C.ink, bold: true, mono: true, align: "center" });
    text(slide, ctx, s[1], x, 408, 122, 18, { size: 10, color: C.muted, align: "center" });
  });
  callout(slide, ctx, "Why this matters", "The report records what changed and what stayed stable, making it possible to distinguish true prompt mutation from runtime metadata and final behavior.", 165, 470, 950, 96, C.violet);
  footer(slide, ctx, "MAIN NARRATIVE", "light", 7);
  return slide;
}

function drawOwnership(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Ownership", "Ownership is no longer hidden inside one black-box run.");
  const headers = ["Component", "Stages owned", "Evidence now visible"];
  const rows = [
    ["agentbench_runner", "task_input", "repo, base commit, selected tests, workspace path"],
    ["prompt_builder", "formatted_prompt", "114-line prompt, char count, task fields merged"],
    ["request_dispatch", "final_model_request", "model, frontend, tool_choice, request_id"],
    ["deepagents_app", "system_context, model_behavior", "instruction surface, response text, finish reason, workspace outcome"],
    ["frontend_dynamo", "tool_runtime_context, runtime_preprocessing", "parser=hermes, tool surface, prompt tokens, cache signals"],
  ];
  rowTable(slide, ctx, headers, rows, 76, 214, [230, 330, 560], 56, { size: 12.5, headerSize: 12 });
  support(slide, ctx, "The component labels are our reporting vocabulary, not necessarily standalone scripts. They make the trace discussable with clear owners.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 8);
  return slide;
}

function drawJsonShapes(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Object Shape", "The most important transformations are object-shape changes, not cosmetic text edits.", "dark");
  const rows = [
    ["task_input -> formatted_prompt", "repo, base_commit, problem_statement, requirements, tests, workspace_path", "prompt", C.violet],
    ["formatted_prompt -> final_model_request", "prompt", "model, messages[], request_context, agent_hints, tool_choice", C.blue],
    ["runtime_preprocessing -> model_behavior", "request metadata, tools, parser, token/cache fields", "messages[], observed_tool_calls, finish_reason, response_text, workspace_changed", C.red],
  ];
  rows.forEach((r, i) => {
    const y = 218 + i * 128;
    text(slide, ctx, r[0], 74, y - 26, 460, 20, { size: 15, color: C.white, bold: true });
    rect(slide, ctx, 74, y, 480, 80, "#172033", { fill: "#40506A", width: 1, style: "solid" });
    rect(slide, ctx, 650, y, 480, 80, "#172033", { fill: r[3], width: 1.5, style: "solid" });
    text(slide, ctx, "BEFORE", 94, y + 12, 82, 16, { size: 10, color: "#A8B3C4", bold: true });
    text(slide, ctx, r[1], 94, y + 34, 420, 32, { size: 13, color: "#D8DEE9", mono: true });
    text(slide, ctx, "AFTER", 670, y + 12, 82, 16, { size: 10, color: r[3], bold: true });
    text(slide, ctx, r[2], 670, y + 34, 420, 32, { size: 13, color: "#FFFFFF", mono: true });
    rule(slide, ctx, 558, y + 40, 82, r[3], 3);
  });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 9);
  return slide;
}

function drawPromptGrowth(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Prompt Growth", "Prompt construction created most textual growth; runtime added measurement context.");
  bar(slide, ctx, "Raw task input", 1330, 9000, 96, 238, 370, C.violet);
  bar(slide, ctx, "Formatted prompt", 6906, 9000, 96, 292, 370, C.blue);
  bar(slide, ctx, "Final request", 6906, 9000, 96, 346, 370, C.green);
  bar(slide, ctx, "Model behavior artifact", 8972, 9000, 96, 400, 370, C.red);
  metric(slide, ctx, D.inputTokens, "runtime prompt tokens", "captured during preprocessing", 830, 218, 270, C.blue);
  metric(slide, ctx, D.cachedTokens, "cached input tokens", `${D.cachePct} of input tokens`, 830, 330, 270, C.green);
  metric(slide, ctx, D.outputTokens, "output tokens", "run stopped at length", 830, 442, 270, C.red);
  support(slide, ctx, "The textual payload stabilized after prompt construction; runtime stages mainly attach parser, token, cache, and behavior evidence.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 10);
  return slide;
}

function drawRuntimeReadiness(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Runtime Readiness", "The runtime path was ready: parser observed, tools exposed, worker selected.", "dark");
  metric(slide, ctx, "hermes", "tool parser observed", "frontend runtime evidence", 76, 218, 250, C.green, "dark");
  metric(slide, ctx, D.expectedTools, "expected tools exposed", "write/edit/execute available", 360, 218, 250, C.blue, "dark");
  metric(slide, ctx, D.worker.slice(0, 8), "worker selected", "SGLang prefill + decode seen", 644, 218, 250, C.amber, "dark");
  metric(slide, ctx, D.cachePct, "input cache share", `${D.cachedTokens}/${D.inputTokens} tokens`, 928, 218, 250, C.green, "dark");
  rect(slide, ctx, 94, 392, 1090, 138, "#172033", { fill: "#344055", width: 1, style: "solid" });
  text(slide, ctx, "Expected tool surface", 116, 414, 220, 18, { size: 13, color: "#A8B3C4", bold: true });
  const tools = ["write_todos", "ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute", "task"];
  tools.forEach((tool, i) => chip(slide, ctx, tool, 116 + (i % 5) * 196, 446 + Math.floor(i / 5) * 38, 166, tools.includes(tool) && ["ls", "read_file"].includes(tool) ? C.green : C.blue, "dark"));
  text(slide, ctx, "Observed tools were only ls and read_file; the platform exposed edit/write/execute, but the agent did not use them.", 126, 546, 940, 26, { size: 19, color: C.white, bold: true, title: true, align: "center" });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 11);
  return slide;
}

function drawRuntimeAlignment(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Runtime Alignment", "Runtime alignment found consistency across five major decision points.");
  const rows = [
    ["request_dispatch", "routed to worker", "agreed"],
    ["tool_availability", "parser hermes observed", "agreed"],
    ["tool_use", "ls + read_file results returned", "agreed"],
    ["runtime_execution", "prefill + decode seen", "agreed"],
    ["stop_behavior", "finish_reason=length", "agreed"],
  ];
  rowTable(slide, ctx, ["Decision point", "Runtime evidence", "Status"], rows, 76, 226, [255, 435, 120], 54, { size: 13.2, headerSize: 12 });
  metric(slide, ctx, "5", "decision rows", "all compared to runtime evidence", 930, 226, 220, C.blue);
  metric(slide, ctx, "0", "diverged rows", "no routing/runtime mismatch", 930, 342, 220, C.green);
  metric(slide, ctx, D.endToEnd, "end-to-end latency", "model call wall time", 930, 458, 220, C.amber);
  support(slide, ctx, "The point is not that the run succeeded; it is that the system can now prove where it did and did not behave as expected.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 12);
  return slide;
}

function drawCaseStudy(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Latest Run", "The latest run exposed the exact execution gap: inspect-only behavior, no patch.", "dark");
  metric(slide, ctx, D.toolCalls, "observed tool calls", "ls, read_file", 84, 220, 240, C.amber, "dark");
  metric(slide, ctx, "False", "workspace_changed", "no diff or patch artifact", 374, 220, 240, C.red, "dark");
  metric(slide, ctx, "length", "finish reason", "response hit output cap", 664, 220, 240, C.red, "dark");
  metric(slide, ctx, D.outputTokens, "output tokens", "truncated prose patch", 954, 220, 240, C.amber, "dark");
  rect(slide, ctx, 104, 382, 1072, 170, "#172033", { fill: C.red, width: 2, style: "solid" });
  text(slide, ctx, "Executive interpretation", 134, 408, 220, 18, { size: 13, color: "#FBD1D9", bold: true });
  text(slide, ctx, "The platform was observable and tool-capable. The agent behaved like an advisor: it proposed code in text instead of editing files.", 134, 440, 850, 56, { size: 23, color: C.white, bold: true, title: true });
  text(slide, ctx, "This is an effectiveness gap, not an instrumentation gap.", 134, 518, 580, 20, { size: 15, color: "#F8DAE0", bold: true });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 13);
  return slide;
}

function drawLearned(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "What We Learned", "This is the right kind of failure because it is explainable and assignable.");
  callout(slide, ctx, "Instrumentation succeeded", "We captured prompt shape, request context, tool parser state, token/cache measurements, worker activity, tool outcomes, finish reason, and workspace-change state.", 86, 228, 500, 250, C.green);
  callout(slide, ctx, "Agent effectiveness still failed", "The model inspected files and generated implementation guidance, but did not invoke edit/write/execute. It ended with finish_reason=length and no workspace patch.", 696, 228, 500, 250, C.red);
  rect(slide, ctx, 224, 510, 832, 64, C.ink);
  text(slide, ctx, "Management takeaway: observability is now strong enough to prioritize agent behavior improvements with evidence.", 250, 526, 780, 30, { size: 15.5, color: C.white, bold: true, align: "center" });
  footer(slide, ctx, "MAIN NARRATIVE", "light", 14);
  return slide;
}

function drawRisks(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Gaps And Risks", "Remaining risks are now specific enough to manage.");
  const rows = [
    ["system_prompt_chars=0", "Suspicious reporting/runtime field", "Verify instruction loading and persistence path", "High"],
    ["finish_reason=length", "Run hit output limit before completion", "Tune budget and enforce edit-before-summary behavior", "High"],
    ["Read-only tool behavior", "Only ls and read_file used", "Strengthen tool policy and evaluate write/edit call rates", "High"],
    ["Alignment not full causality", "Consistent logs are not causal proof", "Add request-level causal IDs and richer runtime events", "Medium"],
  ];
  rowTable(slide, ctx, ["Risk", "Why it matters", "Next control", "Priority"], rows, 70, 214, [250, 330, 390, 120], 66, { size: 12.5, headerSize: 11 });
  support(slide, ctx, "The value of the reporting layer is that these are no longer vague concerns; they are named, measured, and traceable.");
  footer(slide, ctx, "MAIN NARRATIVE", "light", 15);
  return slide;
}

function drawRoadmap(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Next Steps", "The next phase should turn observability into control loops and dashboards.", "dark");
  const steps = [
    ["1", "Validate suspicious fields", "Confirm why system_prompt_chars=0 appears and whether instruction content is missing or unreported.", C.amber],
    ["2", "Deepen runtime alignment", "Add stronger request IDs, causal links, and richer frontend/worker decision evidence.", C.blue],
    ["3", "Improve agent behavior", "Track edit/write/execute rates and enforce progress beyond prose recommendations.", C.red],
    ["4", "Package dashboards", "Promote report families into manager-ready recurring dashboards and run-comparison views.", C.green],
  ];
  steps.forEach((s, i) => {
    const x = 88 + i * 292;
    rect(slide, ctx, x, 244, 238, 260, "#172033", { fill: s[3], width: 2, style: "solid" });
    text(slide, ctx, s[0], x + 22, 266, 48, 48, { size: 34, color: s[3], bold: true, title: true, mono: true });
    text(slide, ctx, s[1], x + 22, 330, 190, 48, { size: 22, color: C.white, bold: true, title: true });
    text(slide, ctx, s[2], x + 22, 398, 190, 74, { size: 13, color: "#D8DEE9" });
  });
  footer(slide, ctx, "MAIN NARRATIVE", "dark", 16);
  return slide;
}

function drawAppendixIndex(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  text(slide, ctx, "TECHNICAL APPENDIX", 72, 62, 420, 22, { size: 13, color: "#A8B3C4", bold: true });
  text(slide, ctx, "Raw Evidence Pack", 72, 122, 720, 72, { size: 54, color: C.white, bold: true, title: true });
  text(slide, ctx, "The appendix preserves the dense report evidence behind the executive story.", 76, 210, 680, 34, { size: 21, color: "#D8DEE9" });
  const items = [
    "Source artifact inventory",
    "Prompt evolution stage table",
    "Lifecycle chronology sample",
    "Runtime alignment evidence",
    "JSON key before/after excerpts",
    "Final response and behavior evidence",
    "Glossary and methodology"
  ];
  items.forEach((item, i) => {
    const y = 310 + i * 38;
    text(slide, ctx, String(i + 1).padStart(2, "0"), 110, y, 42, 18, { size: 13, color: C.blue, bold: true, mono: true });
    rule(slide, ctx, 164, y + 9, 42, "#344055");
    text(slide, ctx, item, 226, y, 520, 20, { size: 18, color: C.white });
  });
  footer(slide, ctx, "APPENDIX", "dark", 17);
  return slide;
}

function drawSourceInventory(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Appendix: Sources", "The artifact family is broad enough to support reproducible diagnosis.");
  const rows = [
    ["prompt_evolution_report", "md / json / csv", "Prompt lineage, structure changes, key additions, model behavior"],
    ["stage_lifecycle_table", "csv", "Chronological events from initialization through artifact generation"],
    ["runtime_alignment_analysis", "md / json", "Decision-vs-runtime agreement table and worker evidence"],
    ["final_summary", "txt", "Actual model response text and truncation evidence"],
    ["others/runtime_events", "json / jsonl", "Frontend and worker observations converted into runtime events"],
  ];
  rowTable(slide, ctx, ["Artifact", "Format", "Management use"], rows, 70, 220, [300, 180, 650], 58, { size: 12.8, headerSize: 12 });
  footer(slide, ctx, "APPENDIX", "light", 18);
  return slide;
}

function drawPromptTable(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Appendix: Prompt Evolution", "The stage table shows exactly what changed at each prompt/request boundary.");
  const rows = [
    ["task_input", "agentbench_runner", "Task payload established", "1,330 chars"],
    ["formatted_prompt", "prompt_builder", "Task fields merged into one runnable prompt", "6,906 chars"],
    ["final_model_request", "request_dispatch", "Prompt wrapped in request envelope", "6,906 chars"],
    ["system_context", "deepagents_app", "System/app layer recorded; chars measured as 0", "0 system chars"],
    ["tool_runtime_context", "frontend_dynamo", "Tools, parser, token/cache context attached", "12,553 tokens"],
    ["runtime_preprocessing", "frontend_dynamo", "Parser observed and cached input counted", "12,544 cached"],
    ["model_behavior", "deepagents_app", "Tool transcript and outcome captured", "no workspace change"],
  ];
  rowTable(slide, ctx, ["Stage", "Owner", "What changed", "Outcome"], rows, 54, 202, [250, 210, 500, 210], 50, { size: 10.8, headerSize: 10.5, monoCols: [0, 1] });
  footer(slide, ctx, "APPENDIX", "light", 19);
  return slide;
}

function drawLifecycle(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Appendix: Lifecycle Trace", "The lifecycle table records the chronology from setup through artifact generation.");
  const rows = [
    ["1", "run_initialized", "agentbench_runner", "Run directory, ids, execution context initialized"],
    ["8", "task_prompt_built", "prompt_builder", "Canonical task prompt constructed from payload"],
    ["12", "baseline_agent_request_dispatched", "request_dispatch", "Baseline Deep Agents request sent to Dynamo frontend"],
    ["13", "frontend_dynamo_runtime_observed", "frontend_dynamo", "Frontend-side runtime observation aligned to request"],
    ["15", "sglang_worker_prefill_observed", "sglang_worker", "Worker emitted prefill-batch observation"],
    ["18", "baseline_agent_response_received", "deepagents_app", "Model response received"],
    ["38-40", "prompt_evolution_report written", "artifact_writer", "JSON, Markdown, and CSV prompt evolution artifacts written"],
  ];
  rowTable(slide, ctx, ["Seq", "Stage", "Component", "Summary"], rows, 52, 206, [70, 310, 190, 590], 48, { size: 10.6, headerSize: 10.5, monoCols: [0, 1] });
  footer(slide, ctx, "APPENDIX", "light", 20);
  return slide;
}

function drawAlignmentTable(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Appendix: Runtime Alignment", "Alignment rows connect agent-side decisions to runtime-side evidence.");
  const rows = [
    ["request_dispatch", "Frontend observed request; routed to worker", "agreed", D.ttft],
    ["tool_availability", "Parser hermes reported; tool path available", "agreed", "2 tool calls"],
    ["tool_use", "Runtime returned ls and read_file results", "agreed", "ls, read_file"],
    ["runtime_execution", "Worker prefill/decode seen; cached=8,448", "agreed", D.decode],
    ["stop_behavior", "finish_reason=length; response preview captured", "agreed", D.endToEnd],
  ];
  rowTable(slide, ctx, ["Decision", "Runtime evidence", "Judgment", "Timing/context"], rows, 52, 220, [230, 500, 150, 280], 58, { size: 11, headerSize: 10.5, monoCols: [0, 2] });
  footer(slide, ctx, "APPENDIX", "light", 21);
  return slide;
}

function drawJsonAppendix(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Appendix: JSON Shapes", "JSON before/after columns show object-shape evolution without dumping full payloads.", "dark");
  const rows = [
    ["task_input", "none", "{ repo, base_commit, problem_statement, requirements, selected_tests, workspace_path }"],
    ["final_model_request", "{ prompt }", "{ model, messages[], request_context, agent_hints, tool_choice }"],
    ["model_behavior", "{ runtime-prepared request fields }", "{ messages[], observed_tool_call_names[], finish_reason, response_text, workspace_changed }"],
  ];
  rowTable(slide, ctx, ["Stage", "Before", "After"], rows, 70, 220, [220, 360, 520], 78, { size: 12, headerSize: 11, mode: "dark", monoCols: [0, 1, 2] });
  footer(slide, ctx, "APPENDIX", "dark", 22);
  return slide;
}

function drawResponseAppendix(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Appendix: Final Response", "The final response proves the model generated guidance rather than code changes.");
  rect(slide, ctx, 74, 218, 740, 266, C.ink);
  text(slide, ctx, "Final response excerpt", 98, 240, 260, 18, { size: 12, color: "#A8B3C4", bold: true });
  text(slide, ctx, "The `email.js` file contains the necessary functions for handling email validation and confirmation. Let's break down the required changes:\n\n1. Implement `getEmailForValidation`...\n2. Update `loadUserInfo`...\n3. Implement `mget` method...\n\nLet's update the file...", 98, 272, 660, 166, { size: 16, color: "#E5E7EB", mono: true });
  callout(slide, ctx, "Behavior flags", "observed_tool_calls=2\n tools_used=ls, read_file\n finish_reason=length\n workspace_changed=False\n git diff stat nonempty=False", 860, 218, 320, 266, C.red);
  footer(slide, ctx, "APPENDIX", "light", 23);
  return slide;
}

function drawGlossary(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Appendix: Glossary", "Shared definitions keep the executive narrative and technical appendix consistent.");
  const rows = [
    ["agentbench_runner", "Our benchmark wrapper: loads task, prepares workspace, invokes app, collects reports"],
    ["prompt_builder", "Our prompt-formatting component label: turns SWE-bench fields into the runnable prompt"],
    ["Deep Agents", "Upstream agent runtime used for agent execution and tool-capable behavior"],
    ["Dynamo frontend", "OpenAI-compatible frontend that observes parser/tool/runtime request behavior"],
    ["SGLang worker", "Worker runtime that emits prefill/decode and cache/recompute evidence"],
    ["Runtime alignment", "Comparison of agent-side decisions with frontend and worker evidence"],
  ];
  rowTable(slide, ctx, ["Term", "Definition"], rows, 72, 218, [260, 850], 55, { size: 12.4, headerSize: 11, monoCols: [0] });
  footer(slide, ctx, "APPENDIX", "light", 24);
  return slide;
}

const slides = [
  drawCover,
  drawExecutiveSummary,
  drawOldProblem,
  drawWhatBuilt,
  drawSystemFlow,
  drawReportFamilies,
  drawPromptSpine,
  drawOwnership,
  drawJsonShapes,
  drawPromptGrowth,
  drawRuntimeReadiness,
  drawRuntimeAlignment,
  drawCaseStudy,
  drawLearned,
  drawRisks,
  drawRoadmap,
  drawAppendixIndex,
  drawSourceInventory,
  drawPromptTable,
  drawLifecycle,
  drawAlignmentTable,
  drawJsonAppendix,
  drawResponseAppendix,
  drawGlossary,
];

export async function renderSlide(presentation, ctx, number) {
  const fn = slides[number - 1];
  if (!fn) {
    throw new Error(`Unknown slide number ${number}`);
  }
  return fn(presentation, ctx);
}

export const slideCount = slides.length;
