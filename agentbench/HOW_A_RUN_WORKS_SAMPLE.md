# How A Run Works Sample

Using your latest report at [prompt_evolution_report.csv](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/agentbench/results/instance_NodeBB__NodeBB-04998908ba6721d64eba79ae3b65a351dcfbc5b5-vnan_20260515_155633/prompt_evolution_report.csv), the `json_keys_before` and `json_keys_after` columns are showing the **shape of the data object** before and after each stage, using keys only.

Here’s what each row is saying.

## `task_input`
- `json_keys_before = none`
- `json_keys_after = {"repo","base_commit","problem_statement","requirements","selected_test_files_to_run","workspace_path"}`

Meaning:
- before this stage, there is no structured task object yet
- after this stage, AgentBench has loaded the raw SWE-bench task fields into a task-shaped object

So this is the moment where the run gets its initial structured input.

## `formatted_prompt`
- `json_keys_before = {task fields...}`
- `json_keys_after = {"prompt":"..."}`

Meaning:
- before this stage, the data is still spread across many separate task fields
- after this stage, those fields have been collapsed into one single prompt string

So this row is showing a big structural simplification:
- many dataset fields
- become one formatted prompt

## `final_model_request`
- `json_keys_before = {"prompt":"..."}`
- `json_keys_after = {"model","messages", "request_context", "agent_hints", "tool_choice"}`

Meaning:
- before this stage, we only have a plain prompt string
- after this stage, that prompt is wrapped into a real chat request object

This is one of the most important transformations:
- plain text prompt
- becomes OpenAI-style request structure

Especially:
- `prompt` turns into `messages[0].content`
- request metadata is added
- routing hints are added

## `system_context`
- `json_keys_before = request object with model/messages/request_context/agent_hints/tool_choice`
- `json_keys_after = same thing + "system_prompt"`

Meaning:
- before this stage, the request already exists
- after this stage, Deep Agents’ system instruction layer is added

So structurally, this is a smaller change:
- the request stays a request
- but now it has system-level behavior instructions too

## `tool_runtime_context`
- `json_keys_before = request + system_prompt`
- `json_keys_after = same thing + expected tools + parser fields`

Meaning:
- before this stage, the request has prompt and system context
- after this stage, it becomes explicitly tool-capable

New structure appears for:
- `expected_builtin_tools`
- `tool_parser_names_seen`
- `tool_parser_observed`

So this row is showing:
- the request is now enriched with tool/runtime capability context

## `runtime_preprocessing`
- `json_keys_before = tool-capable request`
- `json_keys_after = same thing + prompt/cache metrics`

Meaning:
- before this stage, the request is already tool-capable
- after this stage, runtime preprocessing measurements are attached

New structure appears for:
- `prompt_tokens`
- `cached_prompt_tokens`
- `cached_input_tokens`

So this is not a semantic prompt rewrite. It is a runtime-measurement enrichment step.

## `model_behavior`
- `json_keys_before = runtime-prepared request state`
- `json_keys_after = response/transcript/outcome state`

Meaning:
- before this stage, the object still represents the prepared request
- after this stage, the object represents what actually happened

This is the other biggest structural shift in the report:
- request-oriented structure
- becomes response/outcome-oriented structure

Now the keys are about:
- `messages`
- `tool_calls`
- `observed_tool_call_names`
- `observed_tool_result_names`
- `finish_reason`
- `response_text`
- `workspace_changed`

So this row is showing the transition from:
- what we were about to send / had prepared
to:
- what the model actually did and what outcome we got

## The Big Picture
Across all rows, the JSON-shape story is:

1. no structure
2. raw task object
3. single prompt string
4. full model request object
5. request plus system instructions
6. request plus tool/runtime context
7. request plus runtime preprocessing metrics
8. final response/outcome object

So the `json_keys_before` / `json_keys_after` columns are basically showing the **object-shape evolution of the run** from raw task input all the way to final model behavior.
