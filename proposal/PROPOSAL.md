# HSMA Proposal Working Notes

This document is the living Markdown companion to the proposal artifacts in this folder.
It captures the current state of the idea in plain language so we can keep extending it as
the brainstorming evolves.

Last updated: 2026-06-22

## Current Thesis

Long-horizon agentic AI needs memory that scales with accumulated understanding, not only
with token history.

Today, most systems mainly ask:

> How do we store more tokens more cheaply?

The HSMA direction asks:

> How do we preserve useful understanding at the lowest necessary fidelity?

Yes. That is very close to the heart of it.

A cleaner way to say it is:

> HSMA treats memory as a system for storing and recovering meaning intelligently, not just storing prompt history efficiently.

So instead of asking:

- where do I put these old tokens?
- how do I compress this prompt?
- how do I offload this KV block?

the system asks:

- what does this interaction actually mean?
- how important is that meaning?
- what is the cheapest safe way to preserve it?
- if I need the exact detail later, how do I get back to it?

That is the shift.

The only nuance I'd add is: it is not saying raw prompts, raw text, or raw KV no longer matter. It is saying those should become the lower layers of memory, while higher layers store more abstract meaning.

So the picture is:

```text
low level = exact tokens / KV / raw evidence
high level = summaries / concepts / relationships / meaning
```

And the system moves between them intelligently.

One more small tightening: it is not only about storing prompts intelligently. It is really about storing agent memory intelligently, including:

- prompts
- responses
- tool outputs
- decisions
- constraints
- plans
- user preferences
- relationships between ideas

So yes: your idea is basically about turning the memory hierarchy from a token-storage hierarchy into a meaning-storage hierarchy, while still keeping a path back to exact evidence when needed.

## Core Idea

Instead of keeping all old context forever as one giant pile of tokens or KV state, the
system gradually transforms history into cheaper and more structured forms of memory.

Working hierarchy:

```text
Raw KV
-> Compressed KV
-> Semantic Summary
-> Concept Node
-> Knowledge Tree / Graph
```

The system should preserve exact, expensive memory only where it is still useful for active
reasoning, and demote older context into cheaper forms when possible.

## What Feels Novel

The novelty is not any one component by itself.

- KV compression already exists.
- RAG already exists.
- Agent summarization already exists.
- Graph memory already exists.

The current innovation hypothesis is the integration:

1. A semantic demotion policy that decides the cheapest safe memory form.
2. A pointer-preserving hierarchy that links all memory levels together.
3. A selective recovery path that pulls detail back only when needed.

In short: HSMA treats neural memory, textual memory, and symbolic memory as one connected
system instead of separate features.

## Mental Model

The simplest way to think about HSMA is:

- hot context stays close to the model as raw KV
- warm context becomes compressed or offloaded KV
- cooler context becomes summaries and concept memories
- old but still meaningful context lives in a graph/tree with links back to evidence

This is closer to a semantic memory hierarchy than a flat transcript buffer.

## Core Mechanism 1: Semantic Demotion Policy

The system continuously decides what should stay exact and what can be abstracted.

Possible memory states:

```text
Hot
= keep full KV in HBM

Warm
= keep compressed or offloaded KV

Cool
= keep summary + evidence links

Cold
= keep concept node / graph placement + source pointers

Frozen
= archive raw evidence only
```

The key idea is that demotion should not be based only on age or attention.
It should also consider:

- task relevance
- reuse frequency
- whether the item is a decision or constraint
- whether it is a user preference
- whether a tool output depends on it
- whether it is hard to recover later
- whether it is central in the concept graph

Working scoring idea:

```text
importance
= attention
+ reuse
+ task relevance
+ graph centrality
+ recovery cost
- age decay
```

This is not final math, just the current intuition.

## Core Mechanism 2: Pointer-Preserving Hierarchy

Higher-level abstractions should not replace lower-level evidence blindly.

Every summary or concept node should keep typed pointers back to things like:

- source transcript span
- raw text chunk
- tool output
- compressed KV block
- raw KV segment, if retained
- timestamp
- task state
- dependency edges

Simple example:

```text
Concept node:
"Stylist ranking policy"

Summary:
"Same-day ranking prioritizes availability, then reviews, then distance."

Pointers:
- source transcript span
- ranking experiment output
- compressed KV block
- archived raw chunk
- parent topic in graph
```

This is important because the graph is a map, not the full territory.

## Core Mechanism 3: Selective Recovery

The system should not assume summaries or concept graphs can magically recreate exact old KV.

Instead, when more detail is needed, it should recover deeper context by following pointers
downward.

Current recovery ladder:

```text
Question arrives
-> traverse concept graph / summaries
-> if enough, answer
-> else fetch source evidence
-> else replay source spans to regenerate fresh KV
-> else rehydrate compressed KV
-> else restore deeper raw state if available
```

The current preferred framing is:

> selective recovery = retrieve evidence, replay source spans, or rehydrate compressed KV

This is stronger and more believable than claiming the system can perfectly reconstruct lost KV
from a vague summary.

## New Current Idea: Weak-Answer Detection

A key recent extension is that the system may be able to detect when an answer is weak because
it is relying on overly abstracted memory.

High-level flow:

```text
Try answer from summary / concept / graph layer
-> evaluate whether the answer looks under-supported
-> if weak, recover deeper evidence
-> regenerate the answer
```

The important insight is:

The trigger should not rely only on model confidence.

Better trigger signals may include:

- the question asks for exact wording, numbers, code, dates, or exceptions
- the generated answer makes claims not directly supported by loaded evidence
- multiple summaries or graph nodes conflict
- the current memory tier is too abstract for the requested detail
- the answer uses uncertain language
- the topic is tagged as a decision, policy, or unresolved task

Possible runtime framing:

```text
weakness_score
= detail_demand
+ evidence_gap
+ conflict_score
+ importance_of_question
+ model uncertainty
- support_from_loaded_memory
```

If the weakness score crosses a threshold, the system escalates to deeper recovery and retries.

## New Current Idea: Relative Semantic Delta Memory

Another possible extension is to store new prompts in relation to earlier prompts instead of
always storing them as fully independent memory items.

Simple version:

```text
Prior prompts:
A, B, C, ... Y

New prompt:
Z

System finds:
closest semantic anchor = A

Then stores:
Z = A + semantic delta
```

The goal is to avoid repeatedly storing the same semantic structure when the new prompt mostly
overlaps with earlier context.

Example:

```text
A:
"Evaluate KV offloading for long-horizon agent workloads."

Z:
"Evaluate KV offloading for long-horizon coding agents, especially when summaries lose details."

Relative representation:
anchor = A
delta = add coding-agent focus + weak-summary failure concern
```

This is different from ordinary prompt compression because the compressed object is not just a
shorter version of `Z`. It is a pointer-preserving relation:

```text
Z memory record:
- nearest anchor: A
- shared semantic structure: KV offloading + long-horizon agents
- delta: coding agents + detail loss from summaries
- source pointer: raw prompt Z
- recovery pointer: anchor A evidence + Z evidence
```

This may fit HSMA well because it adds another kind of demotion:

```text
full prompt
-> semantic parse
-> nearest anchor
-> relative delta
-> graph update
```

The system could use this for:

- repeated user questions with small changes
- iterative experiment design
- multi-turn refinement of the same idea
- agent plans that evolve gradually
- prompts that share a stable task structure but differ in constraints

Important caveat:

The delta must not replace the raw prompt. It should be a compact routing and reuse structure.
The original prompt still needs a pointer so exact wording can be recovered later.

Open question:

Can relative semantic deltas be made reliable enough to reduce prompt/KV/storage cost without
causing the system to miss small but important differences?

## New Current Idea: Hint-Aware Resource Policy

DeepAgents or an agent runtime may mark a request, prompt, phase, or memory item as important.
For example, it may say:

```text
priority = high
reuse_likelihood = high
agent_phase = execution
latency_sensitivity = medium
```

The HSMA question is whether Dynamo or a similar serving runtime can combine those hints with
live hardware pressure to choose the right memory action.

Possible actions:

```text
keep full KV in GPU cache
keep compressed KV in GPU/CPU tier
summarize and keep summary hot
move raw KV to secondary tier
archive raw evidence only
evict if the value is too low
```

The important design principle:

Hints should be treated as weighted signals, not absolute commands.

A high-priority prompt should be harder to evict, but it should not be impossible to demote.
Otherwise the system can become inefficient or unfair under pressure.

Possible scoring frame:

```text
retention_value
= agent_priority
+ reuse_likelihood
+ active_task_relevance
+ recovery_cost
+ latency_sensitivity
+ semantic_importance
- memory_cost
- current_resource_pressure
- fairness_penalty
```

This gives the runtime a way to preserve important agent context while still making practical
hardware-aware choices.

Example:

```text
High priority + high reuse + low pressure
=> keep full KV hot

High priority + high reuse + high pressure
=> keep summary hot, move raw/compressed KV to secondary tier

High priority + low reuse + high pressure
=> keep concept/summary hot, archive raw evidence

Low priority + low reuse + high pressure
=> demote or evict aggressively
```

This fits the HSMA idea because the runtime is not just asking:

> Is this prompt important?

It is asking:

> Given importance, resource pressure, recovery cost, and future utility, what is the cheapest
> safe memory form for this prompt right now?

Open question:

Can runtime hints from DeepAgents be reliable enough to improve KV retention and memory-tier
placement without over-protecting the wrong prompts?

## Quality Tradeoff

This idea can lose quality if it abstracts too aggressively.

The honest tradeoff is:

- exact local detail can get weaker if summaries replace evidence too early
- long-horizon reasoning can get stronger if the system stops drowning in huge flat history

Highest-risk categories:

- exact numbers
- code details
- policy wording
- legal or contractual constraints
- one-off exceptions

Lower-risk categories:

- topic organization
- repeated facts
- long-term preferences
- task history
- unresolved goals
- high-level relationships

So the safe version of HSMA is:

- abstraction helps routing
- evidence is still preserved somewhere
- when precision matters, the runtime goes back down

## Practical Mapping To Current Repo Thinking

This proposal lines up naturally with the memory-tier mindset already present in our
`kv_cache_offloading` work.

Current practical mapping:

```text
gpu_only
= active KV in HBM

gpu_cpu
= active KV in HBM + warm KV in CPU RAM

gpu_cpu_storage
= active KV in HBM + warm KV in CPU RAM + colder KV in storage
```

HSMA extends this into a more semantic direction:

```text
gpu_only
gpu_cpu
gpu_cpu_storage
gpu_cpu_storage_semantic
```

Where the new semantic tier would add:

- summaries
- concept nodes
- graph memory
- evidence pointers
- selective recovery logic

## Current Research Roadmap

The current order of attack should stay conservative:

1. Prove the long-horizon memory problem clearly on real agent workloads.
2. Build a software-only HSMA prototype.
3. Add semantic demotion and pointer tracking.
4. Test selective recovery paths.
5. Add weak-answer detection and retry.
6. Measure memory saved, latency added, and answer quality retained.
7. Only then ask what deserves hardware acceleration.

## What Would Need To Be Measured

Key validation questions:

- Does HSMA reduce peak KV memory at acceptable quality?
- Does it reduce HBM bandwidth pressure?
- Does long-horizon recall improve or stay stable?
- How often are summaries enough?
- How often must the system recover exact evidence?
- Does weak-answer detection actually catch failures before the user sees them?
- What is the latency cost of recovery and retry?

## Current Open Questions

- How should memory units be defined: token spans, turns, facts, tasks, tool outputs, or all of the above?
- How should concept nodes be created and updated over time?
- How should graph drift be controlled?
- How aggressive should demotion be for different workloads?
- What signals best predict that detail will matter later?
- When is raw text replay enough, and when is compressed-KV rehydration better?
- Can weak-answer detection be made reliable enough to justify the extra recovery step?
- Which parts of this should stay software, and which parts might eventually justify hardware support?

## Current One-Paragraph Summary

HSMA is a proposal for a semantic memory-management layer for long-horizon agentic AI.
Instead of keeping all history forever as raw tokens or KV cache, the system gradually demotes
older context into compressed KV, summaries, concept nodes, and a knowledge graph while
preserving pointers back to the underlying evidence. When a question can be answered from
abstract memory, the system stays cheap. When the answer looks weak or under-supported, the
runtime selectively recovers deeper context, such as source spans, compressed KV, or archived
state, and retries. The long-term goal is to make agents scale with understanding, not merely
with accumulated token history.
