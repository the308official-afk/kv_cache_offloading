import fs from "node:fs";

const CSV_PATH = "/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/results/instance_NodeBB__NodeBB-04998908ba6721d64eba79ae3b65a351dcfbc5b5-vnan_20260518_170604/prompt_evolution_report.csv";
const RESULT_PATH = "/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/results/instance_NodeBB__NodeBB-04998908ba6721d64eba79ae3b65a351dcfbc5b5-vnan_20260518_170604/others/result.json";

const C = {
  ink: "#101820",
  ink2: "#172033",
  paper: "#FFFFFF",
  line: "#D8D0C7",
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

const SOURCE = "";
const STAGE_COLORS = [C.violet, C.blue, C.blue2, C.amber, C.green, C.green, C.red];

const STAGE_LABELS = {
  task_input: "Task Loaded",
  formatted_prompt: "Prompt Built",
  final_model_request: "Request Packaged",
  system_context: "Agent Rules Applied",
  tool_runtime_context: "Tools Attached",
  runtime_preprocessing: "Runtime Prepared",
  model_behavior: "Behavior Recorded",
};

const STAGE_HELP = {
  task_input: {
    question: "What task are we solving?",
    plain: "Original task data before prompt formatting.",
    example: "Repo, bug, requirements, tests.",
  },
  formatted_prompt: {
    question: "What instructions did we give the agent?",
    plain: "Task data rewritten into one runnable prompt.",
    example: "Bug, workspace, tests, expectations.",
  },
  final_model_request: {
    question: "How was the prompt sent to the model?",
    plain: "Prompt wrapped in model request format.",
    example: "Model, messages, request ID, hints.",
  },
  system_context: {
    question: "What behavior rules shaped the model?",
    plain: "Agent instructions layered around the request.",
    example: "Act like a coding agent.",
  },
  tool_runtime_context: {
    question: "What tools and parser were available?",
    plain: "Runtime records tools and parser context.",
    example: "Tools available; parser is hermes.",
  },
  runtime_preprocessing: {
    question: "What did runtime measure before execution?",
    plain: "Runtime prepares request and records metrics.",
    example: "Prompt tokens and cached tokens.",
  },
  model_behavior: {
    question: "What did the model actually do?",
    plain: "Final behavior record after execution.",
    example: "Tool calls, response, outcome.",
  },
};

const PROMPT_BUILDER_LABEL = "Prompt Builder (local helper script)";
const REQUEST_WRAPPER_LABEL = "Request Wrapper (local helper script)";
const PROMPT_BUILDER_LOWER = "prompt builder (local helper script)";

const COMPONENT_HELP = {
  agentbench_runner: {
    label: "Benchmark Loader",
    represents: "Loads the task, repo, tests, and workspace before prompting begins.",
    example: "Here is the repo, bug, tests, and writable workspace.",
    why: "Shows exactly what task entered the pipeline.",
  },
  prompt_builder: {
    label: PROMPT_BUILDER_LABEL,
    represents: "Turns task details into one clear prompt the agent can follow.",
    example: "Fix this bug, inspect files, run these tests.",
    why: "Explains where most prompt text is created.",
  },
  request_dispatch: {
    label: REQUEST_WRAPPER_LABEL,
    represents: "Packages the prompt into the structured request sent to the model service.",
    example: "Adds model name, messages, request ID, and tool mode.",
    why: "Separates prompt content from request metadata.",
  },
  deepagents_app: {
    label: "Deep Agents Layer",
    represents: "Adds coding-agent rules and later records what the agent actually did.",
    example: "Use tools, inspect first, verify before reporting.",
    why: "Connects agent setup to final behavior evidence.",
  },
  frontend_dynamo: {
    label: "Dynamo Runtime Layer",
    represents: "Prepares the request for model execution and tracks runtime/tool state.",
    example: "Adds tool parser, tool list, token/cache measurements.",
    why: "Shows what runtime context surrounded the prompt.",
  },
};

const TRANSFORMATION_HELP = {
  formatted_prompt: {
    flow: "BUILD THE PROMPT",
    does: "Turns raw task fields into one clear instruction message for the agent.",
    example: "Repo + bug + tests + workspace become: inspect this repo, fix this bug, run these tests.",
  },
  final_model_request: {
    flow: "PACKAGE THE REQUEST",
    does: "Wraps the prompt into the format the model endpoint expects.",
    example: "The prompt becomes messages, model, request context, agent hints, and tool choice.",
  },
  system_context: {
    flow: "PACKAGE THE REQUEST",
    does: "Adds the coding-agent behavior rules around the task request.",
    example: "Act like a coding agent, inspect files first, use tools, and verify before reporting.",
  },
  model_behavior: {
    flow: "OBSERVE RUNTIME BEHAVIOR",
    does: "Turns the prepared request into an observed response and outcome record.",
    example: "The model called ls and read_file, finished because of length, and made no workspace change.",
  },
};

const RUNTIME_TRANSFORMATION_HELP = {
  flow: "OBSERVE RUNTIME BEHAVIOR",
  component: "Dynamo Runtime Layer",
  does: "Shows what tools, parser, and runtime preparation were active before execution.",
  example: "Tools like ls, read_file, edit_file, and parser hermes are attached; token/cache counts are recorded.",
};

const DEEP_DIVES = [
  {
    number: 1,
    slide: 6,
    range: "Slides 6-8",
    title: "Task -> Prompt",
    stage: "formatted_prompt",
    color: C.blue,
    component: PROMPT_BUILDER_LABEL,
    before: "Task Loaded",
    after: "Prompt Built",
    changed: "Raw benchmark fields become one prompt field.",
    why: "This is where the task becomes instructions the agent can follow.",
    lookAt: "New field: prompt. Payload grows by +5,576.",
    adds: "prompt",
    size: "+5,576",
  },
  {
    number: 2,
    slide: 9,
    range: "Slides 9-11",
    title: "Prompt -> Request",
    stage: "final_model_request",
    color: C.blue2,
    component: REQUEST_WRAPPER_LABEL,
    before: "Prompt Built",
    after: "Request Packaged",
    changed: "The prompt is wrapped in model request fields.",
    why: "The system now knows the model, messages, request ID, and hints.",
    lookAt: "New fields: model, messages, request_context, agent_hints.",
    adds: "model, messages, request_context, agent_hints",
    size: "0",
  },
  {
    number: 3,
    slide: 12,
    range: "Slides 12-13",
    title: "Request -> Agent Rules",
    stage: "system_context",
    color: C.amber,
    component: "Deep Agents Layer",
    before: "Request Packaged",
    after: "Agent Rules Applied",
    changed: "Coding-agent behavior rules are layered around the request.",
    why: "They tell the agent how to behave: inspect, use tools, and verify.",
    lookAt: "New field: system_prompt.",
    adds: "system_prompt",
    size: "0",
  },
  {
    number: 4,
    slide: 14,
    range: "Slides 14-17",
    title: "Tools -> Runtime Prepared",
    stage: "runtime_preprocessing",
    color: C.green,
    component: "Dynamo Runtime Layer",
    before: "Tools Attached",
    after: "Runtime Prepared",
    changed: "Tool and runtime preparation evidence is attached.",
    why: "We can see tools, parser, token counts, and cache signals.",
    lookAt: "Tool parser plus prompt/cache token fields.",
    adds: "tools, parser, prompt/cache tokens",
    size: "0",
  },
  {
    number: 5,
    slide: 18,
    range: "Slides 18-21",
    title: "Runtime -> Behavior",
    stage: "model_behavior",
    color: C.red,
    component: "Deep Agents Layer",
    before: "Runtime Prepared",
    after: "Behavior Recorded",
    changed: "The prepared request becomes an observed behavior record.",
    why: "We can see what the model actually did, not just what we expected.",
    lookAt: "Tool calls, finish_reason, response_text, workspace_changed.",
    adds: "tool calls, response, outcome",
    size: "+2,066",
  },
];

const TASK_BRIEF = {
  repo: "NodeBB/NodeBB",
  model: "Qwen/Qwen2.5-7B-Instruct",
  title: "Email Validation Status Not Handled Correctly in ACP and Confirmation Logic",
  simpleProblem:
    "In NodeBB's Admin Control Panel, email validation status could show incorrectly, and admin actions like validate or resend email could fail when confirmation keys expired or email data was missing.",
  selectedTests: "test/database.js, test/database/keys.js, test/user/emails.js",
  files: "database adapters + user email logic",
  wrong: [
    "Expired confirmation keys blocked validation.",
    "ACP status could be unclear or wrong.",
    "Validate and resend actions could fail.",
    "Email lookup needed a safer fallback path.",
  ],
  asks: [
    ["Show correct status", "Attach pending and expired flags to users."],
    ["Add batch lookup", "Add db.mget(keys) across database adapters."],
    ["Recover validation email", "Find email from profile or confirmation data."],
    ["Use explicit expiry", "Use timestamp-based confirmation expiry."],
  ],
};

let cachedRows;

function parseCsv(input) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < input.length; i += 1) {
    const ch = input[i];
    const next = input[i + 1];
    if (quoted) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        quoted = false;
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  const headers = rows.shift();
  return rows
    .filter((r) => r.some((cell) => cell.trim()))
    .map((r) => Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])));
}

function csvRows() {
  if (!cachedRows) {
    cachedRows = parseCsv(fs.readFileSync(CSV_PATH, "utf8"));
  }
  return cachedRows;
}

let _baselinePrompt = null;
let _resultJson = null;

function resultJson() {
  if (_resultJson !== null) return _resultJson;
  try {
    _resultJson = JSON.parse(fs.readFileSync(RESULT_PATH, "utf8"));
  } catch {
    _resultJson = {};
  }
  return _resultJson;
}

function promptEvolutionStages() {
  return resultJson()?.prompt_evolution_report?.stages ?? [];
}

function stagePayload(index) {
  return promptEvolutionStages()[index] ?? {};
}

function measurementPayload() {
  return resultJson()?.measurements?.[0] ?? {};
}

function baselinePrompt() {
  if (_baselinePrompt !== null) return _baselinePrompt;
  _baselinePrompt = resultJson()?.result?.baseline_prompt ?? "";
  return _baselinePrompt;
}

function baselinePromptLines() {
  return baselinePrompt().split(/\r?\n/);
}

function stripProvenance(value) {
  if (Array.isArray(value)) {
    return value.map(stripProvenance);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .filter(([key]) => key !== "_provenance")
        .map(([key, nested]) => [key, stripProvenance(nested)]),
    );
  }
  return value;
}

function promptLineCount() {
  return baselinePromptLines().length;
}

function promptCharCount() {
  return baselinePrompt().length;
}

function formatPromptRange(start, end) {
  const lines = baselinePromptLines();
  return lines
    .slice(start - 1, end)
    .map((line, idx) => `${String(start + idx).padStart(3, "0")}: ${line}`)
    .join("\n");
}

function promptExcerpt(start, end) {
  return baselinePromptLines()
    .slice(start - 1, end)
    .join("\n")
    .replaceAll("\\", "\\\\")
    .replaceAll('"', '\\"');
}

function promptJsonSnippet(text, mode = "open") {
  const open = '{\n  "prompt": "';
  const close = '"\n}';
  if (mode === "open") return `${open}${text}`;
  if (mode === "mid") return `...\n${text}`;
  return `...\n${text}${close}`;
}

function wrapJsonPromptLine(line, width = 92) {
  if (!line) return [""];
  const parts = [];
  let remaining = line;
  while (remaining.length > width) {
    let idx = remaining.lastIndexOf(" ", width);
    if (idx <= 0) idx = width;
    parts.push(remaining.slice(0, idx));
    remaining = remaining.slice(idx).trimStart();
  }
  parts.push(remaining);
  return parts;
}

function escapeJsonPromptChunk(value) {
  return value.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

function buildPromptJsonDisplay(lines) {
  const rendered = ['{', '  "prompt": "'];
  lines.forEach((line, idx) => {
    const wrapped = wrapJsonPromptLine(line);
    wrapped.forEach((piece, pieceIdx) => {
      if (idx === 0 && pieceIdx === 0) {
        rendered[1] += escapeJsonPromptChunk(piece);
      } else {
        rendered.push(escapeJsonPromptChunk(piece));
      }
    });
  });
  rendered[rendered.length - 1] += '"';
  rendered.push("}");
  return rendered.join("\n");
}

function promptJsonSlides() {
  const lines = baselinePromptLines();
  const slide1 = buildPromptJsonDisplay([
    ...lines.slice(0, 29),
    "...",
  ]);
  const slide2 = buildPromptJsonDisplay([
    "...",
    "",
    "Requirements:",
    lines[44],
    lines[46],
    lines[48],
    "...",
    "",
    "Selected tests to run:",
    lines[96],
    lines[97],
    lines[98],
    "",
    "Workspace:",
    lines[101],
    lines[102],
    "",
    "Expectations:",
    lines[109],
    lines[110],
    lines[111],
    lines[112],
    lines[113],
  ]);
  return { slide1, slide2 };
}

function promptDetailData() {
  const lines = baselinePromptLines();
  return {
    intro: lines[0],
    taskMeta: [lines[3], lines[4]],
    problemTitle: lines[7].replaceAll("**", ""),
    description: lines[11],
    expected: [lines[25], lines[27], lines[29]],
    actual: [lines[33], lines[35], lines[37]],
    requirements: [shorten(lines[44], 184), shorten(lines[47], 184), shorten(lines[49], 184)],
    selectedTests: [lines[96], lines[97], lines[98]],
    workspace: [lines[101], lines[102]],
    expectations: [lines[109], lines[110], lines[111], lines[112]],
  };
}

function rect(slide, ctx, x, y, w, h, fill, line = "none", name) {
  const stroke = line === "none" ? { fill: "#00000000", width: 0, style: "solid" } : line;
  return ctx.addShape(slide, { x, y, width: w, height: h, fill, line: stroke, name });
}

function rule(slide, ctx, x, y, w, color = C.line, h = 1) {
  return rect(slide, ctx, x, y, w, h, color);
}

function text(slide, ctx, value, x, y, w, h, opts = {}) {
  return ctx.addText(slide, {
    text: String(value ?? ""),
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

function promptSectionBlock(slide, ctx, titleText, bodyText, x, y, w, h, accent) {
  rect(slide, ctx, x, y, w, h, "#FFFFFF", { fill: accent, width: 1.3, style: "solid" });
  rect(slide, ctx, x, y, w, 6, accent);
  text(slide, ctx, titleText, x + 14, y + 12, w - 28, 16, { size: 11, color: accent, bold: true });
  text(slide, ctx, bodyText, x + 14, y + 32, w - 28, h - 42, { size: 10.8, color: C.slate });
}

function promptArtifactEntries(ranges) {
  const lines = baselinePromptLines();
  return ranges.flatMap(([start, end]) =>
    lines.slice(start - 1, end).map((line, idx) => ({ number: start + idx, line })),
  );
}

function isPromptHeading(line) {
  return [
    "Task metadata:",
    "Problem statement:",
    "**Description:**",
    "Steps to reproduce:",
    "**What is expected:**",
    "**What happened instead:**",
    "**Labels:**",
    "Requirements:",
    "Selected tests to run:",
    "Workspace:",
    "Expectations:",
  ].includes(line);
}

function wrapArtifactViewerLine(line, width = 130) {
  if (!line) return [""];
  const parts = [];
  let remaining = line;
  while (remaining.length > width) {
    let idx = remaining.lastIndexOf(" ", width);
    if (idx <= 0) idx = width;
    parts.push(remaining.slice(0, idx));
    remaining = remaining.slice(idx).trimStart();
  }
  parts.push(remaining);
  return parts;
}

function jsonArtifactEntries(value, ranges) {
  const lines = JSON.stringify(value ?? {}, null, 2).split(/\r?\n/);
  return ranges.flatMap(([start, end]) =>
    lines.slice(start - 1, end).map((line, idx) => ({ number: start + idx, line })),
  );
}

function isJsonKeyLine(line) {
  const trimmed = line.trimStart();
  return /^"[^"]+":/.test(trimmed) && !trimmed.startsWith('"_provenance"');
}

function drawJsonArtifactViewer(slide, ctx, options) {
  const {
    accent,
    page,
    titleText,
    subtitleText,
    entries,
    fileLabel = "others/result.json",
    pathLabel = "",
    showLineNumbers = false,
  } = options;

  bg(slide, ctx);
  text(slide, ctx, titleText, 42, 50, 560, 18, { size: 12, color: C.muted, bold: true });
  text(slide, ctx, subtitleText, 42, 78, 1060, 34, { size: 28, color: C.ink, bold: true, title: true });
  rect(slide, ctx, 24, 118, 1232, 540, accent === C.violet ? "#FAF5FF" : "#F7FAFC", { fill: accent, width: 1.9, style: "solid" }, "jsonArtifactPanel");
  rect(slide, ctx, 24, 118, 1232, 10, accent);
  text(slide, ctx, fileLabel, 50, 138, 260, 14, { size: 9.8, color: C.muted, bold: true });
  text(slide, ctx, pathLabel, 736, 138, 490, 14, { size: 9.8, color: C.muted, bold: true, align: "right" });
  rect(slide, ctx, 40, 160, 1200, 486, "#FFFFFF", { fill: accent, width: 1.2, style: "solid" }, "jsonArtifactContent");

  let y = 182;
  let lastNumber = null;
  entries.forEach(({ number, line }) => {
    if (lastNumber !== null && number - lastNumber > 1) {
      y += 7;
    }
    const wrapped = wrapArtifactViewerLine(line, 126);
    const keyLine = isJsonKeyLine(line);
    wrapped.forEach((piece, idx) => {
      if (showLineNumbers) {
        text(slide, ctx, idx === 0 ? String(number).padStart(3, "0") : "", 62, y, 34, 12, {
          size: 7.3,
          color: C.muted,
          mono: true,
          align: "right",
        });
      }
      text(slide, ctx, piece, showLineNumbers ? 110 : 78, y, showLineNumbers ? 1098 : 1130, 12, {
        size: 7.7,
        color: keyLine ? accent : C.ink2,
        mono: true,
        bold: keyLine,
      });
      y += 8.1;
    });
    lastNumber = number;
  });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", page);
}

function drawSectionedJsonArtifactViewer(slide, ctx, options) {
  const {
    accent,
    page,
    titleText,
    subtitleText,
    fileLabel = "others/result.json",
    pathLabel = "",
    sections = [],
    bodySize = 7.3,
    lineStep = 7.2,
    sectionGap = 6,
    headerGap = 10,
  } = options;

  bg(slide, ctx);
  text(slide, ctx, titleText, 42, 50, 620, 18, { size: 12, color: C.muted, bold: true });
  text(slide, ctx, subtitleText, 42, 78, 1060, 34, { size: 28, color: C.ink, bold: true, title: true });
  rect(slide, ctx, 24, 118, 1232, 540, accent === C.violet ? "#FAF5FF" : "#F7FAFC", { fill: accent, width: 1.9, style: "solid" }, "jsonArtifactPanel");
  rect(slide, ctx, 24, 118, 1232, 10, accent);
  text(slide, ctx, fileLabel, 50, 138, 260, 14, { size: 9.8, color: C.muted, bold: true });
  text(slide, ctx, pathLabel, 736, 138, 490, 14, { size: 9.8, color: C.muted, bold: true, align: "right" });
  rect(slide, ctx, 40, 160, 1200, 486, "#FFFFFF", { fill: accent, width: 1.2, style: "solid" }, "jsonArtifactContent");

  let y = 178;
  sections.forEach((section, sectionIdx) => {
    if (sectionIdx > 0) {
      y += sectionGap;
    }
    text(slide, ctx, section.title, 62, y, 1098, 14, {
      size: 9.8,
      color: accent,
      bold: true,
      mono: true,
    });
    y += headerGap;
    rule(slide, ctx, 62, y, 1098, "#E5E7EB");
    y += 6;

    jsonArtifactEntries(section.value, [[1, 999]]).forEach(({ line }) => {
      const wrapped = wrapArtifactViewerLine(line, 126);
      const keyLine = isJsonKeyLine(line);
      wrapped.forEach((piece) => {
        text(slide, ctx, piece, 78, y, 1130, 12, {
          size: bodySize,
          color: keyLine ? accent : C.ink2,
          mono: true,
          bold: keyLine,
        });
        y += lineStep;
      });
    });
  });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", page);
}

function drawPromptArtifactViewer(slide, ctx, options) {
  const {
    accent,
    page,
    titleText,
    subtitleText,
    entries,
    fileLabel = "others/result.json",
    pathLabel = "result.baseline_prompt",
    openingLines = ["{", '  "baseline_prompt": "'],
    closingLines = ['"', "}"],
    showLineNumbers = false,
  } = options;

  bg(slide, ctx);
  text(slide, ctx, titleText, 42, 50, 520, 18, { size: 12, color: C.muted, bold: true });
  text(slide, ctx, subtitleText, 42, 78, 980, 34, { size: 28, color: C.ink, bold: true, title: true });
  rect(slide, ctx, 24, 118, 1232, 540, accent === C.violet ? "#FAF5FF" : "#F5F8FF", { fill: accent, width: 1.9, style: "solid" }, "artifactPanel");
  rect(slide, ctx, 24, 118, 1232, 10, accent);
  text(slide, ctx, fileLabel, 50, 138, 240, 14, { size: 9.8, color: C.muted, bold: true });
  text(slide, ctx, pathLabel, 890, 138, 336, 14, { size: 9.8, color: C.muted, bold: true, align: "right" });
  rect(slide, ctx, 40, 160, 1200, 486, "#FFFFFF", { fill: accent, width: 1.2, style: "solid" }, "artifactContent");
  let prefixY = 182;
  openingLines.forEach((line) => {
    text(slide, ctx, line, 62, prefixY, 1098, 14, {
      size: line.includes('"') ? 11.4 : 12.2,
      color: line.includes('"') ? accent : C.muted,
      mono: true,
      bold: line.includes('"'),
    });
    prefixY += 18;
  });

  let y = prefixY + 2;
  let lastNumber = null;
  entries.forEach(({ number, line }) => {
    if (lastNumber !== null && number - lastNumber > 1) {
      y += 7;
    }
    const heading = isPromptHeading(line);
    const wrapped = wrapArtifactViewerLine(line, 130);
    wrapped.forEach((piece, idx) => {
      if (showLineNumbers) {
        text(slide, ctx, idx === 0 ? String(number).padStart(3, "0") : "", 62, y, 34, 12, {
          size: 7.3,
          color: C.muted,
          mono: true,
          align: "right",
        });
      }
      text(slide, ctx, piece, showLineNumbers ? 110 : 78, y, showLineNumbers ? 1098 : 1130, 12, {
        size: 7.7,
        color: heading ? accent : C.ink2,
        mono: true,
        bold: heading,
      });
      y += 8.1;
    });
    lastNumber = number;
  });

  let suffixY = 606;
  closingLines.forEach((line) => {
    text(slide, ctx, line, 62, suffixY, 1098, 12, { size: 12.2, color: C.muted, mono: true });
    suffixY += 16;
  });
  footer(slide, ctx, "PROMPT EVOLUTION", "light", page);
}

function bg(slide, ctx, mode = "light") {
  rect(slide, ctx, 0, 0, ctx.W, ctx.H, mode === "dark" ? C.ink : C.paper);
}

function footer(slide, ctx, section, mode = "light", page) {
  const color = mode === "dark" ? "#A8B3C4" : C.muted;
  rule(slide, ctx, 64, 664, 1152, mode === "dark" ? "#2B3545" : "#D7D1C8");
  text(slide, ctx, section, 64, 680, 340, 18, { size: 11, color, bold: true });
  if (SOURCE) {
    text(slide, ctx, SOURCE, 442, 680, 450, 18, { size: 9, color });
  }
  text(slide, ctx, String(page).padStart(2, "0"), 1164, 680, 52, 18, { size: 11, color, align: "right", mono: true });
}

function heading(slide, ctx, kicker, claim, mode = "light") {
  const dark = mode === "dark";
  rect(slide, ctx, 64, 52, 8, 24, dark ? C.blue : C.violet);
  text(slide, ctx, kicker.toUpperCase(), 84, 52, 520, 24, { size: 12, color: dark ? "#A8B3C4" : C.muted, bold: true });
  text(slide, ctx, claim, 64, 86, 1060, 104, {
    size: claim.length > 88 ? 31 : 38,
    color: dark ? C.white : C.ink,
    bold: true,
    title: true,
  });
}

function support(slide, ctx, value, mode = "light") {
  text(slide, ctx, value, 64, 610, 1040, 34, { size: 15.5, color: mode === "dark" ? "#CBD5E1" : C.slate });
}

function shorten(value, max = 110) {
  const s = String(value || "none").replace(/\s+/g, " ").trim();
  if (s.length <= max) return s;
  return `${s.slice(0, max - 3).trim()}...`;
}

function compactJson(value, max = 160) {
  const s = String(value || "none").replace(/\s+/g, " ").replaceAll('","', '", "').trim();
  return shorten(s, max);
}

function prettyJson(value) {
  const raw = String(value || "none").trim();
  if (!raw || raw === "none") return "none";
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw
      .replace(/\s+/g, " ")
      .replaceAll("{", "{\n  ")
      .replaceAll("}", "\n}")
      .replaceAll(",", ",\n  ")
      .replaceAll("[", "[\n    ")
      .replaceAll("]", "\n  ]");
  }
}

function componentLabel(key) {
  return COMPONENT_HELP[key]?.label ?? key;
}

function stageLabel(key) {
  return STAGE_LABELS[key] ?? key;
}

function splitPipes(value, maxItems = 3) {
  return String(value || "none")
    .split(" | ")
    .map((part) => part.trim())
    .filter(Boolean)
    .slice(0, maxItems);
}

function listItems(value) {
  return String(value || "none")
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part && part !== "none");
}

function formatSizeChange(value) {
  const n = Number(value || 0);
  if (!n) return "0";
  return n > 0 ? `+${n.toLocaleString("en-US")}` : n.toLocaleString("en-US");
}

function sizeChangeColor(value) {
  const n = Number(value || 0);
  if (n > 3000) return C.blue;
  if (n > 0) return C.red;
  return C.muted;
}

function sizeChangeNote(value) {
  const n = Number(value || 0);
  if (n > 3000) return "Prompt grew here";
  if (n > 0) return "Output record grew";
  return "No payload growth";
}

function drawSizePill(slide, ctx, value, x, y, w, mode = "dark") {
  const color = sizeChangeColor(value);
  const fill = mode === "dark" ? "#111B2C" : C.white;
  rect(slide, ctx, x, y, w, 42, fill, { fill: color, width: 1.6, style: "solid" });
  text(slide, ctx, "Payload size change", x + 12, y + 7, w - 24, 10, { size: 9.2, color: mode === "dark" ? "#93A4BA" : C.muted, bold: true });
  text(slide, ctx, formatSizeChange(value), x + 12, y + 20, w - 24, 19, { size: 16.5, color, bold: true, mono: true });
}

function drawChips(slide, ctx, items, x, y, maxW, color, mode = "dark", maxItems = 6) {
  const shown = items.slice(0, maxItems);
  const extra = items.length - shown.length;
  let cx = x;
  let cy = y;
  const chipH = 22;
  const gap = 6;
  shown.concat(extra > 0 ? [`+${extra} more`] : []).forEach((item) => {
    const label = shorten(item, 28);
    const chipW = Math.min(Math.max(58, label.length * 6.8 + 20), 196);
    if (cx + chipW > x + maxW) {
      cx = x;
      cy += chipH + gap;
    }
    const fill = mode === "dark" ? "#172033" : "#FFFFFF";
    rect(slide, ctx, cx, cy, chipW, chipH, fill, { fill: color, width: 1.2, style: "solid" });
    text(slide, ctx, label, cx + 9, cy + 5, chipW - 18, 11, { size: 9.1, color: mode === "dark" ? "#E5EDF7" : C.slate, bold: true });
    cx += chipW + gap;
  });
}

function drawProgressRail(slide, ctx, current, mode = "dark") {
  const labels = ["Task", "Prompt", "Request", "Runtime", "Behavior"];
  const colors = [C.blue, C.blue, C.blue2, C.green, C.red];
  const x0 = 804;
  const y = 54;
  const w = 78;
  const gap = 8;
  labels.forEach((label, i) => {
    const active = i + 1 === current;
    const x = x0 + i * (w + gap);
    const line = { fill: active ? colors[i] : mode === "dark" ? "#3B4658" : "#D8D0C7", width: 1.2, style: "solid" };
    rect(slide, ctx, x, y, w, 22, active ? colors[i] : "#00000000", line);
    text(slide, ctx, label, x + 6, y + 6, w - 12, 10, {
      size: 9,
      color: active ? C.white : mode === "dark" ? "#A8B3C4" : C.muted,
      bold: true,
      align: "center",
    });
  });
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
    text(slide, ctx, h, cx + 8, y + 8, widths[i] - 16, rowH - 12, { size: opts.headerSize ?? 12, color: dark ? C.white : C.ink, bold: true });
    cx += widths[i];
  });
  rows.forEach((r, idx) => {
    const ry = y + rowH + idx * rowH;
    cx = x;
    r.forEach((cell, i) => {
      rect(slide, ctx, cx, ry, widths[i], rowH, idx % 2 ? altFill : rowFill);
      text(slide, ctx, cell, cx + 8, ry + 7, widths[i] - 16, rowH - 11, {
        size: opts.size ?? 11,
        color: dark ? "#D8DEE9" : C.slate,
        mono: opts.monoCols?.includes(i),
      });
      cx += widths[i];
    });
    rule(slide, ctx, x, ry + rowH - 1, widths.reduce((a, b) => a + b, 0), lineColor);
  });
}

function metric(slide, ctx, value, labelText, note, x, y, w, color, mode = "light") {
  const fill = mode === "dark" ? "#172033" : C.white;
  rect(slide, ctx, x, y, w, 104, fill, { fill: mode === "dark" ? "#344055" : "#DAD4CB", width: 1, style: "solid" });
  text(slide, ctx, value, x + 18, y + 14, w - 36, 36, { size: 30, color, bold: true, title: true });
  text(slide, ctx, labelText, x + 18, y + 54, w - 36, 18, { size: 13.2, color: mode === "dark" ? "#D8DEE9" : C.slate, bold: true });
  text(slide, ctx, note, x + 18, y + 76, w - 36, 16, { size: 11.5, color: mode === "dark" ? "#A8B3C4" : C.muted });
}

function card(slide, ctx, title, body, x, y, w, h, color, mode = "light") {
  const fill = mode === "dark" ? "#172033" : C.white;
  rect(slide, ctx, x, y, w, h, fill, { fill: color, width: 2, style: "solid" });
  rect(slide, ctx, x, y, 8, h, color);
  text(slide, ctx, title, x + 20, y + 16, w - 40, 24, { size: 17.5, color: mode === "dark" ? C.white : C.ink, bold: true });
  text(slide, ctx, body, x + 20, y + 48, w - 40, h - 60, { size: 13.5, color: mode === "dark" ? "#D8DEE9" : C.slate });
}

function codeFontSize(code) {
  const lines = String(code).split("\n").length;
  if (lines <= 6) return 14.2;
  if (lines <= 12) return 12.2;
  if (lines <= 18) return 10.8;
  if (lines <= 24) return 8.9;
  return 8.2;
}

function codePanel(slide, ctx, label, code, x, y, w, h, color, mode = "dark") {
  const dark = mode === "dark";
  const fill = dark ? "#0E1726" : C.white;
  const header = dark ? "#162132" : "#E9E1D6";
  const labelColor = dark ? C.white : C.ink;
  const codeColor = dark ? "#DDE6F3" : C.ink2;
  rect(slide, ctx, x, y, w, h, fill, { fill: color, width: 2, style: "solid" });
  rect(slide, ctx, x, y, w, 42, header);
  text(slide, ctx, label, x + 18, y + 11, w - 36, 20, { size: 13.2, color: labelColor, bold: true });
  text(slide, ctx, code, x + 18, y + 58, w - 36, h - 70, { size: codeFontSize(code), color: codeColor, mono: true });
}

function explainBand(slide, ctx, info, color, mode = "dark") {
  const dark = mode === "dark";
  const fill = dark ? "#111B2C" : C.white;
  const labelColor = dark ? "#93A4BA" : C.muted;
  const bodyColor = dark ? "#E5EDF7" : C.ink;
  rule(slide, ctx, 64, 196, 1152, color, 2);
  rule(slide, ctx, 64, 258, 1152, dark ? "#2B3545" : C.line, 1);
  rect(slide, ctx, 64, 196, 8, 62, color);
  text(slide, ctx, "Flow area", 88, 207, 90, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.flow, 88, 222, 190, 16, { size: 12.2, color: bodyColor, bold: true });
  text(slide, ctx, "Component", 296, 207, 90, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.component, 296, 222, 180, 16, { size: 12.2, color: color, bold: true });
  text(slide, ctx, "What it does", 500, 207, 110, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.does, 500, 222, 318, 28, { size: 11.7, color: bodyColor });
  text(slide, ctx, "Example", 842, 207, 80, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.example, 842, 222, 340, 28, { size: 11.7, color: bodyColor });
}

function walkthroughBand(slide, ctx, info, color, mode = "dark") {
  const dark = mode === "dark";
  const labelColor = dark ? "#93A4BA" : C.muted;
  const bodyColor = dark ? "#E5EDF7" : C.ink;
  rule(slide, ctx, 64, 196, 1152, color, 2);
  rule(slide, ctx, 64, 258, 1152, dark ? "#2B3545" : C.line, 1);
  rect(slide, ctx, 64, 196, 8, 62, color);
  text(slide, ctx, "What changed", 88, 207, 110, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.changed, 88, 222, 270, 28, { size: 11.6, color: bodyColor });
  text(slide, ctx, "Why it matters", 386, 207, 110, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.why, 386, 222, 280, 28, { size: 11.6, color: bodyColor });
  text(slide, ctx, "What to look at", 694, 207, 120, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.lookAt, 694, 222, 326, 28, { size: 11.6, color: bodyColor });
  text(slide, ctx, "Component", 1050, 207, 90, 12, { size: 9.8, color: labelColor, bold: true });
  text(slide, ctx, info.component, 1050, 222, 138, 16, { size: 11.2, color, bold: true });
}

function drawJsonTransition(p, ctx, row, kicker, claim, page, dive) {
  const slide = p.slides.add();
  bg(slide, ctx);
  const color = STAGE_COLORS[csvRows().indexOf(row)] ?? C.blue;
  const step = dive ?? DEEP_DIVES.find((item) => item.stage === row.stage);
  const help = TRANSFORMATION_HELP[row.stage] ?? {
    flow: "PROMPT EVOLUTION",
    does: "Shows how this stage changes the shape of the payload.",
    example: row.outcome,
  };
  const info = { ...help, component: componentLabel(row.owned_by) };
  heading(slide, ctx, step ? `Step ${step.number} of 5 | ${step.title} | ${step.component}` : `${info.flow} | ${info.component}`, claim);
  if (step) {
    drawProgressRail(slide, ctx, step.number, "light");
    walkthroughBand(slide, ctx, step, step.color, "light");
  } else {
    explainBand(slide, ctx, info, color, "light");
  }
  text(slide, ctx, stageLabel(row.stage), 64, 260, 260, 22, { size: 18, color: C.ink, bold: true });
  text(slide, ctx, "Added in this step", 342, 262, 132, 12, { size: 10, color: C.muted, bold: true });
  drawChips(slide, ctx, listItems(row.added_keys), 476, 258, 390, color, "light", 5);
  drawSizePill(slide, ctx, row.size_change, 1014, 250, 202, "light");
  codePanel(slide, ctx, "Before", prettyJson(row.json_keys_before), 64, 300, 548, 306, "#8D99A8", "light");
  codePanel(slide, ctx, "After - added fields are called out above", prettyJson(row.json_keys_after), 668, 300, 548, 306, color, "light");
  support(slide, ctx, `${sizeChangeNote(row.size_change)} | ${shorten(row.outcome, 130)}`);
  footer(slide, ctx, "PROMPT EVOLUTION", "light", page);
  return slide;
}

function drawComponentMap(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Component Map", "Each layer has a clear job in the prompt pipeline.");
  const components = Object.entries(COMPONENT_HELP).map(([key, info]) => {
    return [info.label, info.represents, info.example];
  });
  rowTable(slide, ctx, ["Layer", "Responsible for", "Simple example"], components, 64, 212, [220, 540, 390], 76, {
    size: 11,
    headerSize: 11.5,
  });
  footer(slide, ctx, "PROMPT EVOLUTION", "light", 1);
  return slide;
}

function drawIntro(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Plain-English Introduction", "This setup traces how one task changes as it moves through the agent system.");
  text(
    slide,
    ctx,
    "Think of it like tracking a package: we see what entered the system, how it was repackaged at each handoff, and what came out at the end.",
    64,
    198,
    680,
    48,
    { size: 20, color: C.slate },
  );
  const steps = [
    ["1", "Raw task enters", "Repo, bug report, tests, and workspace are loaded."],
    ["2", "Task becomes a prompt", "The scattered task details become one instruction message."],
    ["3", "Prompt becomes a request", "The message is wrapped with model, context, and tool settings."],
    ["4", "Runtime context is attached", "Tools, parser, token counts, and cache signals are recorded."],
    ["5", "Behavior is recorded", "The final trace shows tool calls, response, and workspace outcome."],
  ];
  steps.forEach((step, i) => {
    const y = 282 + i * 62;
    rect(slide, ctx, 64, y, 680, 48, i % 2 ? "#F2EDE5" : "#FBF8F2");
    rect(slide, ctx, 64, y, 34, 34, STAGE_COLORS[Math.min(i, STAGE_COLORS.length - 1)]);
    text(slide, ctx, step[0], 64, y + 8, 34, 18, { size: 14.5, color: C.white, bold: true, align: "center", mono: true });
    text(slide, ctx, step[1], 116, y + 7, 220, 18, { size: 15, color: C.ink, bold: true });
    text(slide, ctx, step[2], 338, y + 7, 380, 22, { size: 12.7, color: C.slate });
  });
  rect(slide, ctx, 794, 214, 410, 380, C.white, { fill: C.violet, width: 2, style: "solid" });
  rect(slide, ctx, 794, 214, 410, 8, C.violet);
  text(slide, ctx, "Who Is Involved", 822, 244, 300, 26, { size: 22, color: C.ink, bold: true, title: true });
  const owners = [
    ["Benchmark Loader", "loads the task and workspace."],
    [PROMPT_BUILDER_LABEL, "writes the agent instructions."],
    [REQUEST_WRAPPER_LABEL, "packages the model request."],
    ["Deep Agents Layer", "adds behavior rules and records behavior."],
    ["Dynamo Runtime Layer", "prepares tools, parser, and runtime state."],
  ];
  owners.forEach((owner, i) => {
    const y = 300 + i * 52;
    text(slide, ctx, owner[0], 822, y, 156, 16, { size: 12.7, color: [C.violet, C.blue, C.blue2, C.amber, C.green][i], bold: true });
    text(slide, ctx, owner[1], 994, y, 176, 32, { size: 12, color: C.slate });
  });
  footer(slide, ctx, "PROMPT EVOLUTION", "light", 1);
  return slide;
}

function drawComponentFlow(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Component Flow", "Each layer has a clear job in the prompt pipeline.");

  const flow = [
    ["SWE-bench Pro", "real coding task", C.violet],
    ["AgentBench", "loads task", C.blue],
    [PROMPT_BUILDER_LABEL, "writes prompt", C.blue2],
    ["Deep Agents", "agent behavior", C.amber],
    ["Dynamo Frontend", "prepares request", C.green],
    ["SGLang Worker", "runs model", C.green],
    ["Evidence", "captures shape", C.red],
  ];

  const x0 = 64;
  const y0 = 206;
  const boxW = 108;
  const gap = 10;
  flow.forEach(([title, note, color], i) => {
    const x = x0 + i * (boxW + gap);
    rect(slide, ctx, x, y0, boxW, 74, C.white, { fill: color, width: 1.6, style: "solid" });
    rect(slide, ctx, x, y0, boxW, 7, color);
    text(slide, ctx, title, x + 10, y0 + 18, boxW - 20, 20, { size: title.length > 13 ? 10.3 : 11.4, color: C.ink, bold: true });
    text(slide, ctx, note, x + 10, y0 + 43, boxW - 20, 18, { size: 9.3, color: C.slate });
    if (i < flow.length - 1) {
    text(slide, ctx, "->", x + boxW - 1, y0 + 29, gap + 2, 16, { size: 11.5, color, bold: true, align: "center", mono: true });
    }
  });

  const rows = [
    ["SWE-bench Pro Task", "Real software-engineering bug task with repo, tests, and expected behavior.", C.violet],
    ["AgentBench Bootstrap", "Our simple local harness that loads the benchmark task and prepares the workspace.", C.blue],
    [PROMPT_BUILDER_LABEL, "Our local helper that turns task fields into one agent prompt.", C.blue2],
    ["Deep Agents App", "Uses Deep Agents from LangChain to apply coding-agent behavior and tool workflow.", C.amber],
    ["Dynamo Frontend", "Receives the model request and prepares it for runtime execution.", C.green],
    ["SGLang Worker", "Runs model execution and returns response/runtime signals.", C.green],
    ["Prompt Evolution Evidence", "Captures payload shape, added fields, size changes, and runtime facts.", C.red],
  ];
  rows.forEach(([label, body, color], i) => {
    const y = 320 + i * 40;
    rect(slide, ctx, 64, y, 816, 34, i % 2 ? "#F1EBE2" : "#FBF8F2");
    rect(slide, ctx, 64, y, 7, 34, color);
    text(slide, ctx, label, 82, y + 7, 202, 16, { size: 11.3, color, bold: true });
    text(slide, ctx, body, 302, y + 7, 552, 20, { size: 10.6, color: C.slate });
  });

  rect(slide, ctx, 918, 206, 298, 394, C.white, { fill: C.violet, width: 2, style: "solid" });
  rect(slide, ctx, 918, 206, 298, 8, C.violet);
  text(slide, ctx, "Where This Came From", 944, 238, 220, 22, { size: 18, color: C.ink, bold: true, title: true });
  const sourceRows = [
    ["Deep Agents", "langchain-ai/deepagents"],
    ["Dynamo", "ai-dynamo/dynamo"],
    ["Benchmark", "ScaleAI/SWE-bench_Pro"],
    ["Local glue", `AgentBench loader + ${PROMPT_BUILDER_LOWER}`],
    ["Instrumentation", "Deep Agents app/harness logs + Dynamo/SGLang runtime JSON logs"],
  ];
  sourceRows.forEach(([label, value], i) => {
    const y = 288 + i * 54;
    text(slide, ctx, label, 944, y, 110, 13, { size: 10.4, color: C.muted, bold: true });
    text(slide, ctx, value, 944, y + 16, 232, 26, { size: value.length > 46 ? 9.7 : 11.2, color: C.slate });
  });
  footer(slide, ctx, "PROMPT EVOLUTION", "light", 2);
  return slide;
}

function drawBenchmarkContext(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Benchmark Context", "Why SWE-bench Pro was the right benchmark.");

  text(
    slide,
    ctx,
    "SWE-bench Pro gives us realistic software-engineering tasks, not toy prompts: codebase context, a bug or requested behavior, requirements, tests, and an expected fix path.",
    64,
    190,
    1060,
    50,
    { size: 17.8, color: C.slate },
  );

  const cards = [
    {
      title: "Real Repo Task",
      label: "What it is",
      body: "A benchmark built around realistic software-engineering tasks with repo context, problem details, requirements, and tests.",
      color: C.blue,
    },
    {
      title: "Agent Workflow Stress Test",
      label: "Why we used it",
      body: "It exercises prompt construction, tool use, runtime execution, and result capture instead of only testing text generation.",
      color: C.violet,
    },
    {
      title: "End-to-End Observability",
      label: "Why it matters here",
      body: "It makes prompt growth and stage-by-stage transformation visible as the task moves through every layer.",
      color: C.green,
    },
  ];
  cards.forEach((cardData, i) => {
    const x = 64 + i * 390;
    rect(slide, ctx, x, 262, 336, 218, C.white, { fill: cardData.color, width: 2, style: "solid" });
    rect(slide, ctx, x, 262, 336, 8, cardData.color);
    text(slide, ctx, cardData.label.toUpperCase(), x + 24, 292, 200, 12, { size: 9.8, color: C.muted, bold: true });
    text(slide, ctx, cardData.title, x + 24, 318, 286, 48, { size: cardData.title.length > 20 ? 21 : 24, color: C.ink, bold: true, title: true });
    text(slide, ctx, cardData.body, x + 24, 382, 286, 68, { size: 13.8, color: C.slate });
    if (i < cards.length - 1) {
      text(slide, ctx, "->", x + 342, 354, 36, 20, { size: 15.5, color: cardData.color, bold: true, align: "center", mono: true });
    }
  });

  rect(slide, ctx, 64, 520, 1152, 72, "#FBF8F2", { fill: C.amber, width: 1.5, style: "solid" });
  rect(slide, ctx, 64, 520, 8, 72, C.amber);
  text(slide, ctx, "Experiment task", 92, 538, 140, 16, { size: 11.5, color: C.amber, bold: true });
  text(
    slide,
    ctx,
    "The next slide shows the exact NodeBB issue that traveled through the pipeline.",
    238,
    536,
    520,
    28,
    { size: 13.8, color: C.ink, bold: true },
  );
  text(slide, ctx, "Benchmark used: ScaleAI/SWE-bench_Pro", 238, 564, 460, 16, { size: 12, color: C.slate });
  text(slide, ctx, "The task is realistic enough to expose prompt growth, request packaging, runtime preparation, and final behavior.", 824, 540, 340, 36, { size: 12, color: C.slate });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 3);
  return slide;
}

function drawTaskBrief(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Experiment Task", "The task asked the agent to fix a real NodeBB email validation bug.");

  text(
    slide,
    ctx,
    "This is the concrete work item that entered the pipeline before it became a prompt, then a model request, then runtime behavior.",
    64,
    202,
    740,
    34,
    { size: 16.8, color: C.slate },
  );

  rect(slide, ctx, 874, 186, 342, 50, C.white, { fill: C.blue2, width: 1.8, style: "solid" });
  rect(slide, ctx, 874, 186, 8, 50, C.blue2);
  text(slide, ctx, "LLM model used", 898, 198, 132, 12, { size: 10.3, color: C.muted, bold: true });
  text(slide, ctx, TASK_BRIEF.model, 898, 210, 286, 18, { size: 13.5, color: C.ink, bold: true, mono: true });

  rect(slide, ctx, 64, 242, 438, 332, C.white, { fill: C.blue, width: 2, style: "solid" });
  rect(slide, ctx, 64, 242, 438, 8, C.blue);
  text(slide, ctx, "What entered the system", 92, 274, 330, 24, { size: 20, color: C.ink, bold: true, title: true });
  text(slide, ctx, "Repository", 92, 318, 110, 13, { size: 10.6, color: C.muted, bold: true });
  text(slide, ctx, TASK_BRIEF.repo, 210, 316, 250, 16, { size: 13.6, color: C.ink, bold: true });
  text(slide, ctx, "Task title", 92, 354, 110, 13, { size: 10.6, color: C.muted, bold: true });
  text(slide, ctx, TASK_BRIEF.title, 210, 350, 246, 48, { size: 13, color: C.ink, bold: true });
  text(slide, ctx, "Problem in simple words", 92, 416, 210, 13, { size: 10.6, color: C.muted, bold: true });
  text(slide, ctx, TASK_BRIEF.simpleProblem, 92, 438, 360, 80, { size: 13.1, color: C.slate });
  text(slide, ctx, "Selected tests", 92, 530, 110, 13, { size: 10.6, color: C.muted, bold: true });
  text(slide, ctx, TASK_BRIEF.selectedTests, 210, 524, 250, 32, { size: 11, color: C.slate, mono: true });

  rect(slide, ctx, 538, 242, 300, 332, "#FBF8F2", { fill: C.amber, width: 2, style: "solid" });
  rect(slide, ctx, 538, 242, 300, 8, C.amber);
  text(slide, ctx, "What was going wrong", 566, 274, 240, 24, { size: 20, color: C.ink, bold: true, title: true });
  TASK_BRIEF.wrong.forEach((item, i) => {
    const y = 324 + i * 54;
    rect(slide, ctx, 566, y, 26, 26, C.amber);
    text(slide, ctx, String(i + 1), 566, y + 6, 26, 12, { size: 10, color: C.white, bold: true, align: "center", mono: true });
    text(slide, ctx, item, 606, y, 190, 36, { size: 12.4, color: C.slate });
  });
  text(slide, ctx, `Main areas: ${TASK_BRIEF.files}`, 566, 528, 238, 28, { size: 10.8, color: C.muted, bold: true });

  rect(slide, ctx, 874, 242, 342, 332, C.white, { fill: C.green, width: 2, style: "solid" });
  rect(slide, ctx, 874, 242, 342, 8, C.green);
  text(slide, ctx, "What the agent was asked to fix", 902, 274, 280, 48, { size: 20, color: C.ink, bold: true, title: true });
  TASK_BRIEF.asks.forEach(([title, body], i) => {
    const y = 330 + i * 46;
    rect(slide, ctx, 902, y, 286, 38, i % 2 ? "#F1EBE2" : "#FBF8F2", { fill: C.green, width: 1.1, style: "solid" });
    rect(slide, ctx, 902, y, 28, 38, C.green);
    text(slide, ctx, String(i + 1), 902, y + 10, 28, 14, { size: 9.6, color: C.white, bold: true, mono: true, align: "center" });
    text(slide, ctx, title, 944, y + 5, 220, 14, { size: 11.8, color: C.ink, bold: true });
    text(slide, ctx, body, 944, y + 21, 220, 16, { size: 9.8, color: C.slate });
  });

  rect(slide, ctx, 902, 532, 286, 28, "#F1EBE2");
  text(slide, ctx, "Next: watch this task become a prompt, request, runtime record, and behavior trace.", 914, 536, 262, 22, {
    size: 10.2,
    color: C.slate,
    bold: true,
  });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 4);
  return slide;
}

function drawPipeline(p, ctx) {
  const rows = csvRows();
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Pipeline Map", "Seven checkpoints show how a task becomes model behavior.");
  const groups = [
    { title: "Build The Prompt", color: C.blue, start: 0, count: 2, x: 64, w: 330 },
    { title: "Package The Request", color: C.violet, start: 2, count: 2, x: 426, w: 330 },
    { title: "Observe Runtime Behavior", color: C.green, start: 4, count: 3, x: 788, w: 428 },
  ];
  groups.forEach((g, groupIndex) => {
    rect(slide, ctx, g.x, 214, g.w, 376, C.white, { fill: g.color, width: 2, style: "solid" });
    rect(slide, ctx, g.x, 214, g.w, 8, g.color);
    text(slide, ctx, g.title, g.x + 22, 240, g.w - 44, 24, { size: 18, color: C.ink, bold: true, title: true });
    if (groupIndex < 2) {
      text(slide, ctx, "->", g.x + g.w + 11, 390, 26, 24, { size: 16, color: C.muted, bold: true, align: "center", mono: true });
    }
    rows.slice(g.start, g.start + g.count).forEach((r, j) => {
      const step = g.start + j + 1;
      const cardH = g.count === 3 ? 84 : 118;
      const y = 288 + j * (cardH + 18);
      const color = STAGE_COLORS[step - 1];
      rect(slide, ctx, g.x + 22, y, g.w - 44, cardH, j % 2 ? "#F2EDE5" : "#FBF8F2", { fill: "#00000000", width: 0, style: "solid" });
      rect(slide, ctx, g.x + 22, y, 34, 34, color);
      text(slide, ctx, String(step), g.x + 22, y + 8, 34, 18, { size: 13, color: C.white, bold: true, align: "center", mono: true });
      text(slide, ctx, stageLabel(r.stage), g.x + 70, y + 4, g.w - 104, 22, { size: 14.5, color: C.ink, bold: true });
      text(slide, ctx, componentLabel(r.owned_by), g.x + 70, y + 30, g.w - 104, 16, { size: 9.4, color, bold: true });
      text(slide, ctx, STAGE_HELP[r.stage].question, g.x + 70, y + 50, g.w - 104, cardH - 64, { size: 11.2, color: C.slate });
    });
  });
  support(slide, ctx, "Read it left to right: the task is loaded, shaped into prompt instructions, packaged for the model, then runtime behavior is observed.");
  footer(slide, ctx, "PROMPT EVOLUTION", "light", 2);
  return slide;
}

function drawStructureOverview(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Structure Roadmap", "This map shows the five handoffs we will inspect next.");
  text(
    slide,
    ctx,
    "Use this as the audience map: each row below is one handoff. The summary slide comes first, then the following proof slides show the exact JSON artifacts from the latest run.",
    64,
    204,
    1040,
    42,
    { size: 16.2, color: C.slate },
  );

  const x = 64;
  const y = 250;
  const rowH = 72;
  const widths = [86, 238, 254, 286, 128, 160];
  const headers = ["Slide", "Handoff", "From -> To", "What to watch", "Size", "Added"];
  let cx = x;
  headers.forEach((h, i) => {
    rect(slide, ctx, cx, y, widths[i], 34, "#E7E0D6");
    text(slide, ctx, h, cx + 10, y + 8, widths[i] - 20, 16, { size: 11.5, color: C.ink, bold: true });
    cx += widths[i];
  });

  DEEP_DIVES.forEach((dive, i) => {
    const ry = y + 34 + i * rowH;
    const fill = i % 2 ? "#F1EBE2" : "#FBF8F2";
    cx = x;
    rect(slide, ctx, x, ry, widths.reduce((a, b) => a + b, 0), rowH, fill);
    rect(slide, ctx, x, ry, 8, rowH, dive.color);
    text(slide, ctx, dive.range ?? `Slide ${dive.slide}`, cx + 14, ry + 14, widths[0] - 24, 18, { size: 12.6, color: dive.color, bold: true });
    text(slide, ctx, `Step ${dive.number} of 5`, cx + 14, ry + 38, widths[0] - 24, 12, { size: 9.4, color: C.muted, bold: true });
    cx += widths[0];
    text(slide, ctx, dive.title, cx + 12, ry + 12, widths[1] - 24, 20, { size: 14.6, color: C.ink, bold: true });
    text(slide, ctx, dive.component, cx + 12, ry + 38, widths[1] - 24, 12, { size: 9.8, color: dive.color, bold: true });
    cx += widths[1];
    text(slide, ctx, `${dive.before} -> ${dive.after}`, cx + 12, ry + 18, widths[2] - 24, 18, { size: 12, color: C.slate });
    cx += widths[2];
    text(slide, ctx, dive.lookAt, cx + 12, ry + 11, widths[3] - 24, 36, { size: 10.8, color: C.slate });
    cx += widths[3];
    text(slide, ctx, dive.size, cx + 12, ry + 16, widths[4] - 24, 18, { size: 13.6, color: dive.color, bold: true, mono: true, align: "right" });
    cx += widths[4];
    text(slide, ctx, shorten(dive.adds, 44), cx + 12, ry + 15, widths[5] - 24, 28, { size: 10.3, color: C.slate });
    rule(slide, ctx, x, ry + rowH - 1, widths.reduce((a, b) => a + b, 0), C.line);
  });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 5);
  return slide;
}

function drawPromptJourney(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "How To Read The Prompt Journey", "The same task moves through five handoffs; each layer repackages it for the next one.");

  text(
    slide,
    ctx,
    "The easiest mental model: the NodeBB task is the package. Each stage keeps the same core problem, but adds the structure the next system layer needs.",
    64,
    190,
    1040,
    48,
    { size: 17.2, color: C.slate },
  );

  const steps = [
    {
      title: "Task Arrives",
      component: "Benchmark Loader",
      plain: "The run starts with the real bug, repo, requirements, and tests.",
      example: "Fix NodeBB email validation.",
      color: C.blue,
    },
    {
      title: "Task Becomes Instructions",
      component: PROMPT_BUILDER_LABEL,
      plain: "The scattered task fields become one clear prompt.",
      example: "Inspect, fix, validate, report.",
      color: C.blue2,
    },
    {
      title: "Prompt Becomes Request",
      component: REQUEST_WRAPPER_LABEL,
      plain: "The prompt is wrapped with model and request metadata.",
      example: "Send to Qwen with context.",
      color: C.violet,
    },
    {
      title: "Runtime Adds Context",
      component: "Dynamo Frontend",
      plain: "Tools, parser, token counts, and cache signals are attached.",
      example: "Tools like ls and read_file.",
      color: C.green,
    },
    {
      title: "Behavior Is Recorded",
      component: "Deep Agents Layer",
      plain: "The trace shows what the model actually did.",
      example: "Tool calls, response, outcome.",
      color: C.red,
    },
  ];

  const x0 = 64;
  const y = 274;
  const w = 212;
  const h = 224;
  const gap = 18;
  steps.forEach((step, i) => {
    const x = x0 + i * (w + gap);
    rect(slide, ctx, x, y, w, h, C.white, { fill: step.color, width: 2, style: "solid" });
    rect(slide, ctx, x, y, w, 8, step.color);
    rect(slide, ctx, x + 20, y + 30, 34, 34, step.color);
    text(slide, ctx, String(i + 1), x + 20, y + 39, 34, 14, { size: 12.2, color: C.white, bold: true, align: "center", mono: true });
    text(slide, ctx, step.title, x + 20, y + 80, w - 40, 44, { size: 15.8, color: C.ink, bold: true, title: true });
    text(slide, ctx, `Handled by: ${step.component}`, x + 20, y + 126, w - 40, 14, { size: 9.2, color: step.color, bold: true });
    text(slide, ctx, step.plain, x + 20, y + 146, w - 40, 34, { size: 10.6, color: C.slate });
    text(slide, ctx, "Example", x + 20, y + 184, 70, 10, { size: 9.0, color: C.muted, bold: true });
    text(slide, ctx, step.example, x + 20, y + 197, w - 40, 14, { size: 9.8, color: step.color, bold: true });
    if (i < steps.length - 1) {
    text(slide, ctx, "->", x + w + 2, y + 98, gap - 4, 16, { size: 13.5, color: step.color, bold: true, align: "center", mono: true });
    }
  });

  rect(slide, ctx, 64, 526, 1152, 76, "#FBF8F2", { fill: C.amber, width: 1.8, style: "solid" });
  rect(slide, ctx, 64, 526, 8, 76, C.amber);
  text(slide, ctx, "What to remember", 96, 552, 180, 14, { size: 11.8, color: C.amber, bold: true });
  text(
    slide,
    ctx,
    "The task does not become a different problem. It becomes easier for each system layer to act on, observe, and explain.",
    284,
    546,
    820,
    42,
    { size: 17.6, color: C.ink, bold: true },
  );

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 6);
  return slide;
}

function drawStructureDetails(p, ctx) {
  const rows = csvRows();
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Structure Details", "Three grouped transformations explain the overall shape change.");
  const groups = [
    {
      title: "Task -> Prompt",
      color: C.blue,
      rows: [rows[0], rows[1]],
      message: "Dataset fields are merged into one runnable user prompt.",
    },
    {
      title: "Prompt -> Request",
      color: C.violet,
      rows: [rows[2], rows[3]],
      message: "The prompt is wrapped with request metadata and agent context.",
    },
    {
      title: "Runtime -> Behavior",
      color: C.green,
      rows: [rows[4], rows[5], rows[6]],
      message: "Runtime evidence is attached, then final behavior is recorded.",
    },
  ];
  groups.forEach((g, i) => {
    const x = 64 + i * 394;
    rect(slide, ctx, x, 218, 342, 400, C.white, { fill: g.color, width: 2, style: "solid" });
    rect(slide, ctx, x, 218, 342, 8, g.color);
    text(slide, ctx, g.title, x + 24, 244, 294, 28, { size: 22, color: C.ink, bold: true, title: true });
    text(slide, ctx, g.message, x + 24, 286, 294, 44, { size: 13.4, color: C.slate });
    g.rows.forEach((r, j) => {
      const y = 346 + j * 84;
      text(slide, ctx, stageLabel(r.stage), x + 24, y, 210, 18, { size: 12, color: g.color, bold: true });
      text(slide, ctx, `Before: ${shorten(r.structure_before, 72)}`, x + 24, y + 24, 290, 18, { size: 10.5, color: C.muted });
      text(slide, ctx, `After: ${shorten(r.structure_after, 76)}`, x + 24, y + 44, 290, 28, { size: 10.5, color: C.slate });
    });
  });
  footer(slide, ctx, "PROMPT EVOLUTION", "light", 3);
  return slide;
}

function drawJsonTaskPrompt(p, ctx) {
  const rows = csvRows();
  const slide = drawJsonTransition(p, ctx, rows[1], "JSON: Task To Prompt", "First, the raw task becomes one prompt object.", 6, DEEP_DIVES[0]);
  support(
    slide,
    ctx,
    `Prompt grew here | user_prompt_lines=${promptLineCount()} | user_prompt_chars=${promptCharCount()} | next two slides show the actual prompt field contents.`,
  );
  return slide;
}

function drawPromptFieldDetail1(p, ctx) {
  const slide = p.slides.add();
  drawPromptArtifactViewer(slide, ctx, {
    accent: C.blue,
    page: 7,
    titleText: "PROMPT FIELD (1 OF 2)",
    subtitleText: "Verbatim artifact view of the prompt value",
    entries: promptArtifactEntries([[1, 42]]),
  });
  return slide;
}

function drawPromptFieldDetail2(p, ctx) {
  const slide = p.slides.add();
  drawPromptArtifactViewer(slide, ctx, {
    accent: C.violet,
    page: 8,
    titleText: "PROMPT FIELD (2 OF 2)",
    subtitleText: "Verbatim continuation of the same prompt value",
    entries: promptArtifactEntries([[44, 57], [96, 114]]),
  });
  return slide;
}

function drawJsonPromptRequest(p, ctx) {
  const rows = csvRows();
  return drawJsonTransition(p, ctx, rows[2], "JSON: Prompt To Request", "Next, the prompt is wrapped for the model.", 9, DEEP_DIVES[1]);
}

function drawRequestPayloadDetail1(p, ctx) {
  const slide = p.slides.add();
  drawPromptArtifactViewer(slide, ctx, {
    accent: C.blue2,
    page: 10,
    titleText: "REQUEST PAYLOAD (1 OF 2)",
    subtitleText: "Verbatim prompt content inside the packaged message object",
    fileLabel: "others/result.json",
    pathLabel: "prompt_evolution_report.stages[2].initial_messages[0]",
    openingLines: ["{", '  "role": "user",', '  "content": "'],
    closingLines: ['"', "}"],
    entries: promptArtifactEntries([[1, 42]]),
  });
  return slide;
}

function drawRequestPayloadDetail2(p, ctx) {
  const slide = p.slides.add();
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.blue2,
    page: 11,
    titleText: "REQUEST PAYLOAD (2 OF 2)",
    subtitleText: "Verbatim metadata attached to the same packaged request",
    pathLabel: "prompt_evolution_report.stages[2].{tool_choice, request_context, agent_hints}",
    entries: jsonArtifactEntries({
      tool_choice: "auto",
      request_context: stripProvenance(stagePayload(2).request_context ?? {}),
      agent_hints: stripProvenance(stagePayload(2).agent_hints ?? {}),
    }, [[1, 999]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawJsonRequestSystem(p, ctx) {
  const rows = csvRows();
  return drawJsonTransition(p, ctx, rows[3], "JSON: Request To System Context", "Then, agent rules are layered into the request.", 12, DEEP_DIVES[2]);
}

function drawSystemContextDetail(p, ctx) {
  const slide = p.slides.add();
  const stage = stripProvenance(stagePayload(3));
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.amber,
    page: 13,
    titleText: "SYSTEM CONTEXT",
    subtitleText: "Exact persisted keys behind the agent-rules transition",
    pathLabel: "prompt_evolution_report.stages[3].{system_prompt, added_keys, keys_before, keys_after, result_summary}",
    entries: jsonArtifactEntries({
      system_prompt: stage.system_prompt ?? "",
      added_keys: stage.added_keys ?? "",
      keys_before: stage.keys_before ?? "",
      keys_after: stage.keys_after ?? "",
      result_summary: stage.result_summary ?? "",
    }, [[1, 999]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawJsonRuntimePreprocessing(p, ctx) {
  const rows = csvRows();
  const slide = p.slides.add();
  bg(slide, ctx);
  const dive = DEEP_DIVES[3];
  heading(slide, ctx, `Step ${dive.number} of 5 | ${dive.title} | ${dive.component}`, "Then, runtime adds tool and token context.");
  const left = rows[4];
  const right = rows[5];
  drawProgressRail(slide, ctx, dive.number, "light");
  walkthroughBand(slide, ctx, dive, C.green, "light");
  text(slide, ctx, `${stageLabel(left.stage)} -> ${stageLabel(right.stage)}`, 64, 260, 320, 22, { size: 17, color: C.ink, bold: true });
  text(slide, ctx, "Added in these steps", 410, 262, 140, 12, { size: 10, color: C.muted, bold: true });
  drawChips(slide, ctx, ["expected_builtin_tools", "tool_parser_*", "prompt/cache tokens"], 558, 258, 392, C.green, "light", 3);
  drawSizePill(slide, ctx, right.size_change, 1014, 250, 202, "light");
  codePanel(slide, ctx, "After Tools Attached", prettyJson(left.json_keys_after), 64, 300, 548, 306, C.green, "light");
  codePanel(slide, ctx, "After Runtime Prepared - added fields called out above", prettyJson(right.json_keys_after), 668, 300, 548, 306, C.green, "light");
  support(slide, ctx, `${sizeChangeNote(right.size_change)} | ${right.outcome}`);
  footer(slide, ctx, "PROMPT EVOLUTION", "light", 14);
  return slide;
}

function drawToolRuntimeDetail(p, ctx) {
  const slide = p.slides.add();
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.green,
    page: 15,
    titleText: "TOOL RUNTIME CONTEXT (1 OF 2)",
    subtitleText: "Verbatim stage object showing the request once tool and parser context are attached",
    pathLabel: "prompt_evolution_report.stages[4]",
    entries: jsonArtifactEntries(stripProvenance(stagePayload(4)), [[1, 21]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawRuntimeMetricsDetail(p, ctx) {
  const slide = p.slides.add();
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.green,
    page: 16,
    titleText: "TOOL RUNTIME CONTEXT (2 OF 2)",
    subtitleText: "Verbatim continuation of the same stage object from slide 15",
    pathLabel: "prompt_evolution_report.stages[4] (continued)",
    entries: jsonArtifactEntries(stripProvenance(stagePayload(4)), [[22, 43]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawRuntimeMetricsDetail2(p, ctx) {
  const slide = p.slides.add();
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.green,
    page: 17,
    titleText: "RUNTIME PREPARATION",
    subtitleText: "Exact measurement record for the same prepared request",
    pathLabel: "measurements[0]",
    entries: jsonArtifactEntries(stripProvenance(measurementPayload()), [[1, 999]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawJsonRuntimeBehavior(p, ctx) {
  const rows = csvRows();
  return drawJsonTransition(p, ctx, rows[6], "JSON: Runtime To Behavior", "Finally, we observe what the model actually did.", 18, DEEP_DIVES[4]);
}

function drawBehaviorDetail(p, ctx) {
  const slide = p.slides.add();
  const stage = stripProvenance(stagePayload(6));
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.red,
    page: 19,
    titleText: "MODEL BEHAVIOR (1 OF 3)",
    subtitleText: "Exact stage-analysis fields recorded for the observed outcome",
    pathLabel: "prompt_evolution_report.stages[6].{stage, component, question_answered, changed_from, change_summary, delta_summary, result_summary, prompt_preview, prompt_chars, major_additions, added_elements, removed_elements, unchanged_core, key_facts}",
    entries: jsonArtifactEntries({
      stage: stage.stage,
      component: stage.component,
      question_answered: stage.question_answered,
      changed_from: stage.changed_from,
      change_summary: stage.change_summary,
      delta_summary: stage.delta_summary,
      result_summary: stage.result_summary,
      prompt_preview: stage.prompt_preview,
      prompt_chars: stage.prompt_chars,
      major_additions: stage.major_additions,
      added_elements: stage.added_elements,
      removed_elements: stage.removed_elements,
      unchanged_core: stage.unchanged_core,
      key_facts: stage.key_facts,
    }, [[1, 999]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawBehaviorDetail2(p, ctx) {
  const slide = p.slides.add();
  const stage = stripProvenance(stagePayload(6));
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.red,
    page: 20,
    titleText: "MODEL BEHAVIOR (2 OF 3)",
    subtitleText: "Exact structure-evolution fields recorded for the observed outcome",
    pathLabel: "prompt_evolution_report.stages[6].{structure_before, structure_after, keys_before, keys_after, json_keys_before, json_keys_after, added_keys, removed_keys, changed_keys, chars_before, chars_after, char_delta}",
    entries: jsonArtifactEntries({
      structure_before: stage.structure_before,
      structure_after: stage.structure_after,
      keys_before: stage.keys_before,
      keys_after: stage.keys_after,
      json_keys_before: stage.json_keys_before,
      json_keys_after: stage.json_keys_after,
      added_keys: stage.added_keys,
      removed_keys: stage.removed_keys,
      changed_keys: stage.changed_keys,
      chars_before: stage.chars_before,
      chars_after: stage.chars_after,
      char_delta: stage.char_delta,
    }, [[1, 999]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawBehaviorDetail3(p, ctx) {
  const slide = p.slides.add();
  const stage = stripProvenance(stagePayload(6));
  drawJsonArtifactViewer(slide, ctx, {
    accent: C.red,
    page: 21,
    titleText: "MODEL BEHAVIOR (3 OF 3)",
    subtitleText: "Exact observed tool-use and response fields recorded for the outcome",
    pathLabel: "prompt_evolution_report.stages[6].{observed_tool_call_names, observed_tool_result_names, observed_tool_call_count, finish_reason, response_text}",
    entries: jsonArtifactEntries({
      observed_tool_call_names: stage.observed_tool_call_names,
      observed_tool_result_names: stage.observed_tool_result_names,
      observed_tool_call_count: stage.observed_tool_call_count,
      finish_reason: stage.finish_reason,
      response_text: stage.response_text,
    }, [[1, 999]]),
    showLineNumbers: false,
  });
  return slide;
}

function drawKeys(p, ctx) {
  const rows = csvRows();
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Added Fields", "Each stage adds specific fields that explain the handoff.");
  text(
    slide,
    ctx,
    "The easiest way to read this slide: the left column names the step, the middle shows the new fields created at that step, and the right side shows whether the payload grew.",
    64,
    198,
    930,
    36,
    { size: 16, color: C.slate },
  );

  const x = 64;
  const y = 238;
  const widths = [204, 520, 296, 132];
  const rowH = 54;
  const headers = ["Stage", "Fields added here", "Meaning of the change", "Size"];
  let cx = x;
  headers.forEach((h, i) => {
    rect(slide, ctx, cx, y, widths[i], 34, "#E7E0D6");
    text(slide, ctx, h, cx + 10, y + 8, widths[i] - 20, 16, { size: 11.6, color: C.ink, bold: true });
    cx += widths[i];
  });

  rows.forEach((r, i) => {
    const ry = y + 34 + i * rowH;
    const fill = i % 2 ? "#F1EBE2" : "#FBF8F2";
    const color = STAGE_COLORS[i];
    rect(slide, ctx, x, ry, widths.reduce((a, b) => a + b, 0), rowH, fill);
    rect(slide, ctx, x, ry, 8, rowH, color);
    text(slide, ctx, stageLabel(r.stage), x + 18, ry + 7, widths[0] - 30, 17, { size: 12.4, color: C.ink, bold: true });
    text(slide, ctx, componentLabel(r.owned_by), x + 18, ry + 29, widths[0] - 30, 12, { size: 9.8, color, bold: true });
    drawChips(slide, ctx, listItems(r.added_keys), x + widths[0] + 12, ry + 10, widths[1] - 24, color, "light", 2);
    text(
      slide,
      ctx,
      shorten(r.changed_keys === "none" ? r.what_changed : r.changed_keys, 92),
      x + widths[0] + widths[1] + 12,
      ry + 10,
      widths[2] - 24,
      28,
      { size: 10.3, color: C.slate },
    );
    text(
      slide,
      ctx,
      formatSizeChange(r.size_change),
      x + widths[0] + widths[1] + widths[2] + 10,
      ry + 10,
      widths[3] - 20,
      16,
      { size: 13.4, color: sizeChangeColor(r.size_change), bold: true, mono: true, align: "right" },
    );
    text(
      slide,
      ctx,
      sizeChangeNote(r.size_change),
      x + widths[0] + widths[1] + widths[2] + 10,
      ry + 29,
      widths[3] - 20,
      12,
      { size: 9, color: C.muted, align: "right" },
    );
    rule(slide, ctx, x, ry + rowH - 1, widths.reduce((a, b) => a + b, 0), C.line);
  });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 22);
  return slide;
}

function drawFacts(p, ctx) {
  const rows = csvRows();
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Evidence Summary", "Each stage leaves a short proof trail executives can inspect.");

  const promptRow = rows[1];
  const runtimeRow = rows[5];
  const behaviorRow = rows[6];
  metric(slide, ctx, formatSizeChange(promptRow.size_change), PROMPT_BUILDER_LABEL, "largest growth: raw task becomes prompt", 64, 194, 344, C.blue);
  metric(slide, ctx, formatSizeChange(runtimeRow.size_change), "Runtime Preparation", "same request, more runtime evidence", 468, 194, 344, C.green);
  metric(slide, ctx, formatSizeChange(behaviorRow.size_change), "Behavior Record", "response and tool outcome are added", 872, 194, 344, C.red);

  const x = 64;
  const y = 326;
  const widths = [184, 382, 426, 160];
  const rowH = 43;
  const headers = ["Stage", "Key facts", "Outcome", "Size signal"];
  let cx = x;
  headers.forEach((h, i) => {
    rect(slide, ctx, cx, y, widths[i], 32, "#E7E0D6");
    text(slide, ctx, h, cx + 10, y + 7, widths[i] - 20, 16, { size: 11.5, color: C.ink, bold: true });
    cx += widths[i];
  });

  rows.forEach((r, i) => {
    const ry = y + 32 + i * rowH;
    const fill = i % 2 ? "#F1EBE2" : "#FBF8F2";
    const color = STAGE_COLORS[i];
    rect(slide, ctx, x, ry, widths.reduce((a, b) => a + b, 0), rowH, fill);
    rect(slide, ctx, x, ry, 6, rowH, color);
    text(slide, ctx, stageLabel(r.stage), x + 16, ry + 7, widths[0] - 28, 15, { size: 10.8, color: C.ink, bold: true });
    text(slide, ctx, shorten(r.key_facts, 84), x + widths[0] + 10, ry + 7, widths[1] - 20, 20, { size: 9.8, color: C.slate });
    text(slide, ctx, shorten(r.outcome, 92), x + widths[0] + widths[1] + 10, ry + 7, widths[2] - 20, 20, { size: 9.8, color: C.slate });
    text(
      slide,
      ctx,
      `${formatSizeChange(r.size_change)} | ${sizeChangeNote(r.size_change)}`,
      x + widths[0] + widths[1] + widths[2] + 10,
      ry + 8,
      widths[3] - 20,
      18,
      { size: 9.5, color: sizeChangeColor(r.size_change), bold: true },
    );
    rule(slide, ctx, x, ry + rowH - 1, widths.reduce((a, b) => a + b, 0), C.line);
  });

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 23);
  return slide;
}

function drawFinalSummary(p, ctx) {
  const slide = p.slides.add();
  bg(slide, ctx);
  heading(slide, ctx, "Final Summary", "We can now explain how one real engineering task becomes model behavior.");

  text(
    slide,
    ctx,
    "This experiment followed a NodeBB SWE-bench Pro task through the prompt pipeline: task intake, prompt construction, model request packaging, runtime preparation, and observed behavior.",
    64,
    190,
    980,
    42,
    { size: 17.2, color: C.slate },
  );

  const cards = [
    {
      title: "What went in",
      stat: "Real NodeBB task",
      body: "A concrete email-validation bug with repo context, requirements, selected tests, and a target workspace.",
      color: C.blue,
    },
    {
      title: "What changed",
      stat: "+5,576 chars",
      body: "The largest transformation happened when raw task fields became one runnable agent prompt.",
      color: C.violet,
    },
    {
      title: "What ran",
      stat: "Qwen 2.5 7B",
      body: "The prompt was packaged and sent through the stack using Qwen/Qwen2.5-7B-Instruct.",
      color: C.green,
    },
    {
      title: "What came out",
      stat: "Behavior trace",
      body: "The final record shows tool calls, response status, and whether the workspace changed.",
      color: C.red,
    },
  ];

  cards.forEach((item, i) => {
    const x = 64 + i * 292;
    rect(slide, ctx, x, 272, 252, 188, C.white, { fill: item.color, width: 2, style: "solid" });
    rect(slide, ctx, x, 272, 252, 8, item.color);
    text(slide, ctx, item.title.toUpperCase(), x + 22, 304, 170, 12, { size: 9.8, color: C.muted, bold: true });
    text(slide, ctx, item.stat, x + 22, 330, 200, 30, { size: item.stat.length > 12 ? 22 : 26, color: item.color, bold: true, title: true });
    text(slide, ctx, item.body, x + 22, 382, 202, 58, { size: 12.6, color: C.slate });
  });

  rect(slide, ctx, 64, 508, 1152, 84, "#FBF8F2", { fill: C.amber, width: 1.8, style: "solid" });
  rect(slide, ctx, 64, 508, 8, 84, C.amber);
  text(slide, ctx, "Simple takeaway", 96, 530, 180, 16, { size: 12.2, color: C.amber, bold: true });
  text(
    slide,
    ctx,
    "The prompt pipeline is now explainable stage by stage: we can see the structure before and after each handoff, the fields each layer adds, and the evidence produced by the run.",
    96,
    548,
    1020,
    36,
    { size: 16.8, color: C.ink, bold: true },
  );

  footer(slide, ctx, "PROMPT EVOLUTION", "light", 24);
  return slide;
}

function drawMajorTransformations(p, ctx) {
  const rows = csvRows();
  const slide = p.slides.add();
  bg(slide, ctx, "dark");
  heading(slide, ctx, "Major Transformations", "Three grouped changes explain most of the payload evolution.");
  const groups = [
    {
      title: "Task -> Prompt",
      color: C.blue,
      rows: [rows[0], rows[1]],
      message: "Raw task fields become one runnable prompt string.",
    },
    {
      title: "Prompt -> Request",
      color: C.violet,
      rows: [rows[2], rows[3]],
      message: "Prompt content stays stable while request and system context are layered on.",
    },
    {
      title: "Runtime -> Behavior",
      color: C.green,
      rows: [rows[4], rows[5], rows[6]],
      message: "Tool/runtime fields and preprocessing metrics lead into final behavior shape.",
    },
  ];
  groups.forEach((g, i) => {
    const x = 72 + i * 398;
    rect(slide, ctx, x, 220, 330, 330, "#172033", { fill: g.color, width: 2, style: "solid" });
    text(slide, ctx, g.title, x + 24, 246, 260, 28, { size: 24, color: C.white, bold: true, title: true });
    text(slide, ctx, g.message, x + 24, 292, 270, 48, { size: 13.5, color: "#D8DEE9" });
    g.rows.forEach((r, j) => {
      const y = 370 + j * 52;
      text(slide, ctx, stageLabel(r.stage), x + 24, y, 160, 18, { size: 11.2, color: C.white, bold: true });
      text(slide, ctx, shorten(r.structure_after, 66), x + 24, y + 22, 270, 28, { size: 9.2, color: "#CBD5E1" });
    });
  });
  support(slide, ctx, "This slide is the fast read: construct the prompt, wrap the request, attach runtime context, then record behavior.", "dark");
  footer(slide, ctx, "PROMPT EVOLUTION", "dark", 12);
  return slide;
}

const slides = [
  drawIntro,
  drawComponentFlow,
  drawBenchmarkContext,
  drawTaskBrief,
  drawStructureOverview,
  drawJsonTaskPrompt,
  drawPromptFieldDetail1,
  drawPromptFieldDetail2,
  drawJsonPromptRequest,
  drawRequestPayloadDetail1,
  drawRequestPayloadDetail2,
  drawJsonRequestSystem,
  drawSystemContextDetail,
  drawJsonRuntimePreprocessing,
  drawToolRuntimeDetail,
  drawRuntimeMetricsDetail,
  drawRuntimeMetricsDetail2,
  drawJsonRuntimeBehavior,
  drawBehaviorDetail,
  drawBehaviorDetail2,
  drawBehaviorDetail3,
  drawKeys,
  drawFacts,
  drawFinalSummary,
];

export async function renderSlide(presentation, ctx, number) {
  const fn = slides[number - 1];
  if (!fn) {
    throw new Error(`Unknown slide number ${number}`);
  }
  return fn(presentation, ctx);
}

export const slideCount = slides.length;
