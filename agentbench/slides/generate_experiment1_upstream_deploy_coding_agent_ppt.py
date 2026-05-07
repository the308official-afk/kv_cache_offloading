from __future__ import annotations

import json
import textwrap
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.enum.text import MSO_VERTICAL_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "agentbench/results/sample__stronger_behavior__001_20260506_155649"
OUT = ROOT / "agentbench/slides/AgentBench_Experiment1_Upstream_Deploy_Coding_Agent_Run.pptx"


BG = RGBColor(248, 250, 252)
NAVY = RGBColor(17, 24, 39)
BLUE = RGBColor(37, 99, 235)
TEAL = RGBColor(13, 148, 136)
AMBER = RGBColor(217, 119, 6)
ROSE = RGBColor(225, 29, 72)
GRAY = RGBColor(107, 114, 128)
LIGHT = RGBColor(229, 231, 235)
WHITE = RGBColor(255, 255, 255)
SOFT_BLUE = RGBColor(219, 234, 254)
SOFT_GREEN = RGBColor(209, 250, 229)
SOFT_ORANGE = RGBColor(254, 243, 199)
SOFT_PINK = RGBColor(255, 228, 230)
SOFT_GRAY = RGBColor(243, 244, 246)


def load_json(path: Path):
    return json.loads(path.read_text())


def shorten(value: str, width: int = 160) -> str:
    single = " ".join(value.split())
    return textwrap.shorten(single, width=width, placeholder="...")


def nonempty_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]


def excerpt_after(text: str, marker: str, *, max_lines: int = 6) -> list[str]:
    lines = nonempty_lines(text)
    for idx, line in enumerate(lines):
        if marker in line:
            return lines[idx : idx + max_lines]
    return lines[:max_lines]


checkpoints = load_json(RUN_DIR / "checkpoints.json")
result = load_json(RUN_DIR / "result.json")
plan = load_json(RUN_DIR / "plan.json")
final_summary = (RUN_DIR / "final_summary.txt").read_text()

checkpoint_1 = next(item for item in checkpoints if item["check_point"].startswith("1."))
checkpoint_3 = next(item for item in checkpoints if item["check_point"].startswith("3."))
checkpoint_4s = [item for item in checkpoints if item["check_point"].startswith("4.")]
checkpoint_5 = next(item for item in checkpoints if item["check_point"].startswith("5."))
checkpoint_4_focus = checkpoint_4s[-1]

task = checkpoint_1["task"]
step_titles = [step["title"] for step in plan["steps"]]
useful_steps = [title for title in step_titles if "dry-run" in title.lower() or "dispatch" in title.lower() or "temporary" in title.lower()]
generic_steps = [title for title in step_titles if title not in useful_steps]
cp3_excerpt = excerpt_after(checkpoint_3["prompt"], "Return only valid JSON", max_lines=8)
cp3_guidance_excerpt = excerpt_after(checkpoint_3["prompt"], "Prefer task-specific steps", max_lines=6)
cp4_plan_excerpt = excerpt_after(checkpoint_4_focus["prompt"], "Approved decomposition plan:", max_lines=6)
cp4_current_step_excerpt = excerpt_after(checkpoint_4_focus["prompt"], "Current step:", max_lines=6)
cp5_step_results_excerpt = excerpt_after(checkpoint_5["prompt"], "Step results:", max_lines=5)
cp5_final_job_excerpt = excerpt_after(checkpoint_5["prompt"], "Produce a final summary with these sections:", max_lines=6)


prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)


def set_bg(slide, color=BG):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title(slide, title: str, subtitle: str | None = None):
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.1), Inches(0.8))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    r = p.add_run()
    r.text = title
    r.font.size = Pt(28)
    r.font.bold = True
    r.font.color.rgb = NAVY
    if subtitle:
        st = slide.shapes.add_textbox(Inches(0.62), Inches(1.05), Inches(12.0), Inches(0.5))
        tf2 = st.text_frame
        p2 = tf2.paragraphs[0]
        r2 = p2.add_run()
        r2.text = subtitle
        r2.font.size = Pt(13)
        r2.font.color.rgb = GRAY


def add_bullets(slide, items, left=0.9, top=1.5, width=11.5, height=5.3, font_size=20, color=NAVY):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = item
        p.level = 0
        p.font.size = Pt(font_size)
        p.font.color.rgb = color
        p.space_after = Pt(8)


def add_box(slide, left, top, width, height, text, fill_color, line_color=WHITE, font_size=15, bold=False, color=NAVY):
    shape = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    shape.line.color.rgb = line_color
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_VERTICAL_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = text
    r.font.size = Pt(font_size)
    r.font.bold = bold
    r.font.color.rgb = color
    return shape


def add_text_panel(slide, left, top, width, height, title, body, fill=WHITE, title_color=NAVY):
    panel = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(left),
        Inches(top),
        Inches(width),
        Inches(height),
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = fill
    panel.line.color.rgb = LIGHT
    tf = panel.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP

    p1 = tf.paragraphs[0]
    r1 = p1.add_run()
    r1.text = title
    r1.font.size = Pt(16)
    r1.font.bold = True
    r1.font.color.rgb = title_color

    for idx, line in enumerate(body.split("\n")):
        p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(13)
        p.font.color.rgb = NAVY
        p.space_after = Pt(4)
        if idx == 0:
            p.space_before = Pt(6)
    return panel


def add_sections_text(
    slide,
    sections,
    *,
    left=0.85,
    top=1.55,
    width=11.7,
    height=5.6,
    section_title_size=18,
    body_size=15,
):
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_VERTICAL_ANCHOR.TOP

    first = True
    for title, body_lines in sections:
        p_title = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p_title.space_before = Pt(0 if p_title is tf.paragraphs[0] else 10)
        p_title.space_after = Pt(2)
        r_title = p_title.add_run()
        r_title.text = title
        r_title.font.size = Pt(section_title_size)
        r_title.font.bold = True
        r_title.font.color.rgb = BLUE

        for line in body_lines:
            p_body = tf.add_paragraph()
            p_body.text = line
            p_body.font.size = Pt(body_size)
            p_body.font.color.rgb = NAVY
            p_body.space_after = Pt(3)


def add_arrow(slide, left, top, width=0.5):
    shape = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.CHEVRON, Inches(left), Inches(top), Inches(width), Inches(0.45))
    shape.fill.solid()
    shape.fill.fore_color.rgb = BLUE
    shape.line.color.rgb = BLUE
    return shape


# Slide 1
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "AgentBench Experiment 1", "Upstream Deploy-Coding-Agent Variant Run")
add_box(
    slide,
    0.8,
    1.5,
    11.7,
    1.0,
    "Best one-line summary: complex tasks from sources like SWE-bench Pro are broken into several steps by the Deep Agents app before the resulting planning, execution, and synthesis requests are sent through the local Dynamo frontend.",
    SOFT_BLUE,
    LIGHT,
    20,
    True,
)
add_bullets(
    slide,
    [
        "Scope: only Experiment 1, using the upstream deploy-coding-agent variant as the core testbed.",
        "Evidence source: real run sample__stronger_behavior__001_20260506_155649.",
        "This deck focuses on how the payload evolves across checkpoints 1, 3, 4, and 5.",
    ],
    top=3.0,
    font_size=22,
)

# Slide 2
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Setup Components", "All components used in the upstream variant run")
add_box(slide, 0.6, 1.55, 1.8, 0.85, "Task source\nsample JSON or SWE-bench Pro", SOFT_BLUE)
add_box(slide, 2.7, 1.55, 1.7, 0.85, "AgentBench runner\nsingle-host wrapper", SOFT_GREEN)
add_box(slide, 4.7, 1.55, 1.8, 0.85, "Deep Agents app\nactive harness", SOFT_ORANGE)
add_box(slide, 6.8, 1.55, 2.0, 0.85, "Upstream deploy-coding-agent\ninstructions + skills", SOFT_PINK)
add_box(slide, 9.1, 1.55, 1.6, 0.85, "Dynamo frontend\nlocalhost:8000", SOFT_BLUE)
add_box(slide, 11.0, 1.55, 1.7, 0.85, "Local SGLang\nworker", SOFT_GREEN)
for x in [2.45, 4.45, 6.55, 8.85, 10.75]:
    add_arrow(slide, x, 1.75)
add_box(slide, 1.0, 3.2, 3.2, 1.0, "Checkpoint logging\n1 / 3 / 4 / 5 to stdout + checkpoints.json", WHITE, LIGHT, 17, True)
add_box(slide, 4.6, 3.2, 3.2, 1.0, "Saved artifacts\nresult.json / plan.json / step_results.json / final_summary.txt", WHITE, LIGHT, 17, True)
add_box(slide, 8.2, 3.2, 3.8, 1.0, "Runtime note\nthis run still resolved deepagents from python_environment, not the cloned repo path", SOFT_ORANGE, LIGHT, 16, True)
add_bullets(
    slide,
    [
        "The app variant is upstream_deploy_coding_agent.",
        "The stronger-behavior helper used an easier sample task and a 4-step budget.",
    ],
    top=4.85,
    font_size=18,
)

# Slide 3
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Processing Flow", "How one experiment run moves through the stack")
add_bullets(
    slide,
    [
        "1. AgentBench loads one task from a local sample JSON or SWE-bench Pro.",
        "2. Checkpoint 1 logs the normalized task before Deep Agents planning starts.",
        "3. The Deep Agents app sends a planning prompt to Dynamo and logs Checkpoint 3.",
        "4. The resulting plan becomes one or more step execution requests and each is logged at Checkpoint 4.",
        "5. After the step results come back, the app sends one final synthesis request and logs Checkpoint 5.",
        "6. AgentBench saves result.json, checkpoints.json, plan.json, step_results.json, and final_summary.txt.",
    ],
    top=1.55,
    font_size=19,
)

# Slide 4
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Experiment Modes", "Main ways to run the upstream deploy-coding-agent variant")
cmd_text = (
    "Sample task\n"
    "bash agentbench/run_upstream_deploy_coding_agent_single_host.sh\n\n"
    "SWE-bench Pro input\n"
    "bash agentbench/run_upstream_deploy_coding_agent_single_host.sh \\\n"
    "  --dataset ScaleAI/SWE-bench_Pro \\\n"
    "  --split test \\\n"
    "  --index 0\n\n"
    "Stronger-behavior sample run used in this deck\n"
    "bash agentbench/run_upstream_deploy_coding_agent_stronger_behavior_single_host.sh"
)
box = slide.shapes.add_shape(MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(12.0), Inches(4.6))
box.fill.solid()
box.fill.fore_color.rgb = NAVY
box.line.color.rgb = NAVY
tf = box.text_frame
tf.word_wrap = True
p = tf.paragraphs[0]
r = p.add_run()
r.text = cmd_text
r.font.name = "Courier New"
r.font.size = Pt(17)
r.font.color.rgb = WHITE
add_bullets(
    slide,
    [
        "This deck uses the stronger-behavior run so the checkpoint slides are filled with real outputs.",
    ],
    top=6.3,
    font_size=17,
)

# Slide 5
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Checkpoint Map", "Ordered observability points in the upstream pipeline")
add_box(slide, 0.8, 1.55, 2.5, 0.8, "1\nTask loaded before\nDeep Agents harness", SOFT_BLUE, LIGHT, 17, True)
add_box(slide, 3.6, 1.55, 2.5, 0.8, "3\nPlanning request leaving\nDeep Agents harness", SOFT_GREEN, LIGHT, 17, True)
add_box(slide, 6.4, 1.55, 2.5, 0.8, "4\nStep execution request\nleaving harness", SOFT_ORANGE, LIGHT, 17, True)
add_box(slide, 9.2, 1.55, 2.5, 0.8, "5\nFinal synthesis request\nleaving harness", SOFT_PINK, LIGHT, 17, True)
for x in [3.2, 6.0, 8.8]:
    add_arrow(slide, x, 1.75)
add_bullets(
    slide,
    [
        "1: measured at the point just before the loaded task enters the Deep Agents harness.",
        "3: measured at the point where the planning stage is about to send its first request to the Dynamo frontend.",
        "4: measured at the point where the execution stage is about to send one step-level request to the Dynamo frontend.",
        "5: measured at the point where the synthesis stage is about to send the final combined request to the Dynamo frontend.",
    ],
    top=3.0,
    font_size=18,
)

# Slide 6
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Observed Run Configuration", "Actual run used to fill the checkpoint slides")
add_box(slide, 0.8, 1.5, 4.0, 2.3, "Run ID\nsample__stronger_behavior__001_20260506_155649\n\nTask source\njson:agentbench/sample_task_stronger.json\n\nInstance ID\nsample__stronger_behavior__001", WHITE, LIGHT, 16, True)
add_box(slide, 5.1, 1.5, 3.1, 2.3, "App variant\nupstream_deploy_coding_agent\n\nModel\nQwen/Qwen2.5-0.5B\n\nRuntime source\npython_environment", SOFT_BLUE, LIGHT, 16, True)
add_box(slide, 8.5, 1.5, 3.8, 2.3, "Workspace\nnone provided\n\nPlan step count\n4\n\nCheckpoint file\ncheckpoints.json", SOFT_GREEN, LIGHT, 16, True)
add_bullets(
    slide,
    [
        f"Problem statement: {shorten(task['problem_statement'], 180)}",
        "This run was chosen because it shows Checkpoint 1, Checkpoint 3, four separate Checkpoint 4 events, and Checkpoint 5.",
    ],
    top=4.25,
    font_size=18,
)

# Slide 7
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Checkpoint 1", "Task ingestion stage")
add_sections_text(
    slide,
    [
        (
            "Represents",
            [
                "Stage name: task ingestion",
                "Meaning: the raw normalized task before Deep Agents planning starts",
                "Checkpoint type: internal harness boundary, not yet a frontend-bound model request",
                "Measured at: the point just before the loaded task enters the Deep Agents harness",
            ],
        ),
        (
            "Payload at this stage",
            [
                f"instance_id: {task['instance_id']}",
                f"repo: {task['repo']}",
                "still a task record, not yet a model request",
                "no request wrapper yet",
                "no hints attached yet",
                f"selected_test_files_to_run: {task['selected_test_files_to_run']}",
            ],
        ),
        (
            "Example task excerpt",
            [
                f"problem_statement: {shorten(task['problem_statement'], 115)}",
                f"requirements: {shorten(task['requirements'], 95)}",
                f"interface: {shorten(task['interface'], 95)}",
            ],
        ),
        (
            "What changed here",
            [
                "The external task source was normalized into one task record.",
                "Wrapper metadata also exists around it: check_point, task_index, task_source, app_variant.",
                "No planning prompt yet.",
                "No phase-specific hints yet.",
            ],
        ),
        (
            "What goes to the next stage",
            [
                "This task record is expanded into a planning prompt.",
                "The next stage adds task_metadata, phase=planning, prompt text, and planning hints.",
                "Destination: Dynamo frontend via the planning request at Checkpoint 3.",
            ],
        ),
    ],
    body_size=14,
    section_title_size=17,
)

# Slide 8
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Checkpoint 3", "Planning request leaving the Deep Agents harness")
add_sections_text(
    slide,
    [
        (
            "Represents",
            [
                "Stage name: planning request",
                "Meaning: the first outbound model request that asks the harness to break the task into steps",
                "Checkpoint type: first Dynamo-bound request in the pipeline",
                "Measured at: the point where the planning stage is about to send its first request to the Dynamo frontend",
            ],
        ),
        (
            "Payload at this stage",
            [
                "prompt text: task record rendered into a planning prompt",
                "request wrapper: task_metadata + phase + prompt_preview",
                f"phase: {checkpoint_3['phase']}",
                f"hints: agent_phase={checkpoint_3['hints']['agent_phase']}, latency_sensitivity={checkpoint_3['hints']['latency_sensitivity']}, expected_output_tokens={checkpoint_3['hints']['expected_output_tokens']}",
                f"step_limit: {checkpoint_3['step_limit']}",
            ],
        ),
        (
            "Example planning prompt excerpt",
            cp3_excerpt + ["..."] + cp3_guidance_excerpt,
        ),
        (
            "What changed here",
            [
                "The raw task record became prompt text.",
                "Planning hints were attached under nvext.agent_hints.",
                "A prompt_preview field was added for observability.",
                "This is where the payload changes from 'task object' to 'frontend-bound request'.",
            ],
        ),
        (
            "What goes to the next stage",
            [
                f"Planning response preview: {shorten(plan['planning_response_text'], 150)}",
                "The planning output is parsed into a decomposition plan.",
                "That plan becomes one or more per-step execution requests at Checkpoint 4.",
            ],
        ),
    ],
    body_size=14,
    section_title_size=17,
)

# Slide 9
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Checkpoint 4", "Step execution requests leaving the harness")
add_sections_text(
    slide,
    [
        (
            "Represents",
            [
                "Stage name: per-step execution request",
                "Meaning: one outbound request for one current step after a plan exists",
                f"Occurrences in this run: {len(checkpoint_4s)} separate Checkpoint 4 events",
                "Measured at: the point where the execution stage is about to send one step-level request to the Dynamo frontend",
            ],
        ),
        (
            "Payload at this stage",
            [
                "prompt text: planning context rendered into one step-specific execution prompt",
                "request wrapper: task_metadata + phase + step_index + step_title + prompt_preview",
                "phase pattern: step_n_execution",
                f"hints: agent_phase changes per step, expected_output_tokens={checkpoint_4s[0]['hints']['expected_output_tokens']}",
                f"step title in focus: {checkpoint_4_focus['step_title']}",
            ],
        ),
        (
            "Example step-execution prompt excerpt",
            cp4_plan_excerpt + ["..."] + cp4_current_step_excerpt,
        ),
        (
            "What changed here",
            [
                "The single planning output became multiple outbound requests.",
                "Each request now includes the approved decomposition plan in the prompt.",
                "Each request also includes the current step and any completed step summaries.",
                "The agent_phase hint changes from planning to step_n_execution.",
            ],
        ),
        (
            "What goes to the next stage",
            [
                "Dynamo receives one request per planned step.",
                "Each response is stored as a step summary/result.",
                "After all step requests complete, those accumulated results feed the synthesis request at Checkpoint 5.",
            ],
        ),
    ],
    body_size=14,
    section_title_size=17,
)

# Slide 10
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Checkpoint 5", "Final synthesis request leaving the harness")
add_sections_text(
    slide,
    [
        (
            "Represents",
            [
                "Stage name: final synthesis request",
                "Meaning: the final outbound merge request after step execution is complete",
                "Checkpoint type: one last Dynamo-bound request that combines step outputs into one answer",
                "Measured at: the point where the synthesis stage is about to send the final combined request to the Dynamo frontend",
            ],
        ),
        (
            "Payload at this stage",
            [
                "prompt text: accumulated step outputs rendered into one synthesis prompt",
                "request wrapper: task_metadata + phase + prompt_preview + step_count",
                f"phase: {checkpoint_5['phase']}",
                f"new field: step_count={checkpoint_5['step_count']}",
                f"hints: agent_phase={checkpoint_5['hints']['agent_phase']}, expected_output_tokens={checkpoint_5['hints']['expected_output_tokens']}",
            ],
        ),
        (
            "Example synthesis prompt excerpt",
            cp5_step_results_excerpt + ["..."] + cp5_final_job_excerpt,
        ),
        (
            "What changed here",
            [
                "Per-step results were aggregated into one combined prompt.",
                "The request is no longer about a single step; it is about the whole task again.",
                "The agent_phase hint changes from step_n_execution to synthesis.",
            ],
        ),
        (
            "What goes to the next stage",
            [
                f"Final summary preview: {shorten(final_summary, 150)}",
                "Dynamo returns one final combined answer.",
                "That answer is saved into final_summary.txt and result.json.",
            ],
        ),
    ],
    body_size=14,
    section_title_size=17,
)

# Slide 11
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Payload Evolution Summary", "How the structure changes from checkpoint to checkpoint")
add_box(slide, 0.55, 1.55, 2.7, 1.0, "1\nTask record", SOFT_BLUE, LIGHT, 20, True)
add_box(slide, 3.45, 1.55, 2.9, 1.0, "3\nPlanning request", SOFT_GREEN, LIGHT, 20, True)
add_box(slide, 6.6, 1.55, 2.9, 1.0, "4\nStep request(s)", SOFT_ORANGE, LIGHT, 20, True)
add_box(slide, 9.75, 1.55, 2.8, 1.0, "5\nSynthesis request", SOFT_PINK, LIGHT, 20, True)
for x in [3.1, 6.25, 9.4]:
    add_arrow(slide, x, 1.82, width=0.45)
add_text_panel(
    slide,
    0.75,
    3.0,
    12.0,
    3.0,
    "Structure change by stage",
    "\n".join(
        [
            "Checkpoint 1: task fields only -> instance_id, repo, problem_statement, requirements, interface, selected tests.",
            "Checkpoint 3: task fields become a planning prompt -> prompt text gains JSON/output constraints and planning guidance; wrapper gains phase + planning hints.",
            "Checkpoint 4: planning output becomes per-step requests -> prompt text gains approved plan + current step + prior summaries; wrapper gains step_index + step_title.",
            "Checkpoint 5: step outputs become one merge request -> prompt text gains accumulated step results + final summary sections; wrapper gains step_count + synthesis hints.",
            "Measurement points: just before harness entry for Checkpoint 1; just before outbound planning / step / synthesis requests for Checkpoints 3 / 4 / 5.",
        ]
    ),
    WHITE,
)

# Slide 12
slide = prs.slides.add_slide(prs.slide_layouts[6])
set_bg(slide)
add_title(slide, "Recommended Presentation Pattern", "How to present checkpoints clearly in future decks")
add_bullets(
    slide,
    [
        "Use the same four labels on every checkpoint slide: Represents, Payload at this stage, What changed here, What goes to the next stage.",
        "Color-code field categories consistently: task fields, prompt fields, hint fields, and step/synthesis fields.",
        "Show only one short real excerpt per checkpoint; let the field-shape summary carry the slide.",
        "When a checkpoint repeats, as Checkpoint 4 does, explain that it is one request per planned step.",
    ],
    top=1.7,
    font_size=20,
)

OUT.parent.mkdir(parents=True, exist_ok=True)
prs.save(OUT)
print(f"Wrote {OUT}")
