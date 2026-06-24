# HSMA Proposal Working Notes

This document is the living Markdown companion to the proposal artifacts in this folder.
It captures the current state of the idea in plain language so we can keep extending it as
the brainstorming evolves.

Last updated: 2026-06-22

## Executive Proposal

### Title

Hierarchical Semantic Memory Architecture (HSMA): A Meaning-Centered Memory System for
Long-Horizon Agentic AI

### Core Thesis

Current AI systems largely treat memory as the problem of storing more tokens more cheaply.
HSMA proposes a different way of thinking: memory should be organized around meaning, not just
history. The goal is to make long-running agents scale with accumulated understanding, while
still preserving access to exact evidence when detail matters.

The idea is not really about storing prompts intelligently. It is about storing agent memory
intelligently, including:

- prompts
- responses
- tool outputs
- decisions
- constraints
- plans
- user preferences
- relationships between ideas

### One-Sentence Pitch

HSMA turns memory from a token-storage hierarchy into a meaning-storage hierarchy, while still
preserving escape hatches back to exact evidence.

## Core Architecture

HSMA organizes memory as a multi-level hierarchy:

```text
Raw KV
-> Compressed KV
-> Semantic Summary
-> Concept Node
-> Knowledge Tree / Graph
```

Lower levels preserve exactness. Higher levels preserve meaning.

```text
low level = exact tokens / KV / raw evidence
high level = summaries / concepts / relationships / meaning
```

The system should keep exact, expensive memory only where it is still useful for active
reasoning, and demote older context into cheaper forms when possible.

## What Feels Novel

The novelty is not any one component by itself.

- KV compression already exists.
- RAG already exists.
- Agent summarization already exists.
- Graph memory already exists.

The proposed novelty is the integration:

1. Meaning-to-Meaning Attention for Memory Tiering
2. Semantic Demotion Policy
3. Pointer-Preserving Hierarchy
4. Selective Recovery

In short: HSMA treats neural memory, textual memory, and symbolic memory as one connected
system instead of separate features.

## Novelty Claim

The proposal should not claim novelty for KV compression, RAG, summarization, graph memory, or
multi-tier agent memory by themselves. Those already exist in important prior work.

The safer and stronger novelty claim is:

> HSMA introduces a unified semantic memory architecture that connects inference-time KV memory,
> compressed memory, summaries, concepts, and graph structure into one pointer-preserving
> hierarchy with selective recovery.

Within that broader system, the most novel individual idea may be:

> Meaning-to-Meaning Attention for Memory Tiering

That idea says memory importance should not be defined only by local recency, local attention,
or local retrieval frequency. It should also be defined by semantic dependency:

- what other important meanings depend on this memory?
- if this memory is demoted, what becomes weaker or harder to recover?
- is this memory a foundation for later reasoning, decisions, or plans?

That is the part that feels least like ordinary cache policy and most like a genuinely new way
to define memory importance.

So the proposal can make two levels of claim:

1. **Most novel individual mechanism**
   Meaning-to-Meaning Attention for Memory Tiering

2. **Strongest overall contribution**
   The full HSMA system that combines dependency-aware retention, semantic demotion,
   pointer-preserving abstraction, and selective recovery

Reviewer-safe version:

> The proposal's main novelty is not any single existing memory primitive, but the integration
> of neural, textual, and symbolic memory into a dependency-aware semantic hierarchy. A central
> new idea is Meaning-to-Meaning Attention for Memory Tiering, where retention decisions are
> influenced not only by local importance, but by how strongly other important meanings depend
> on a memory item.

## Pillar 1: Meaning-To-Meaning Attention For Memory Tiering

This is one of the most important parts of the proposal and should be treated as a first-class
mechanism, not a side extension.

In simple words:

> Do not judge each memory item alone. Judge it by what other meanings depend on it.

That is much better than asking only:

- was this attended to recently?
- is this old?
- is this summary short enough?

Because some contexts matter not because they are flashy on their own, but because many other
things quietly rely on them.

A good mental model is:

```text
memory item A = "same-day ranking uses availability first"
memory item B = "stylist discovery policy"
memory item C = "search relevance experiment"
memory item D = "booking UX recommendation"
```

If `B`, `C`, and `D` all depend on `A`, then `A` is more important than it looks locally.

The practical recommendation is to start with a semantic dependency graph with weighted links,
not literal transformer attention.

Possible link types:

- `supports`
- `depends_on`
- `contradicts`
- `refines`
- `derived_from`
- `used_by_active_task`

Then each link gets a weight.

So instead of saying:

> this memory is low-attention, throw it away

the system asks:

> if I demote this memory, what other important memories become weaker, less interpretable, or
> harder to recover?

That is powerful.

A simple retention score could become:

```text
retention_value =
local_importance
+ dependency_importance
+ active_task_usage
+ recovery_cost
+ fanout
- age_decay
- storage_cost
```

Where:

- `local_importance` = how important the item looks by itself
- `dependency_importance` = how much important stuff depends on it
- `fanout` = how many other nodes point to it
- `recovery_cost` = how painful it would be to recover later

This gives a smarter retention rule than plain recency or token-level attention.

Three important uses:

1. **Dependency-aware retention**
   Keep memory hot not only because it is important, but because it is a foundation for other
   important memories.

2. **Dependency-aware demotion**
   If a memory item is demoted, update dependent nodes and preserve stronger pointer structure
   around them.

3. **Dependency-aware recovery**
   When an answer looks weak, recover not just one missing source, but the supporting chain.

The big caution is this:

> semantic dependency is not the same thing as semantic similarity

Two memories can be similar without depending on each other. Two memories can depend strongly
on each other even if they do not look similar on the surface.

So the system should learn or infer links like:

- this policy conclusion depends on this earlier constraint
- this experiment interpretation depends on this exact metric definition
- this plan step depends on this earlier design choice

not just:

- these two memories talk about similar topics

This mechanism may be one of the keys to making the whole proposal work.

## The Shift From Token Influence To Meaning Placement

For your "new shift in thinking," I'd phrase it like this:

Traditional attention organizes computation around tokens. HSMA extends the attention idea upward: memory should also be organized around meanings. Instead of only asking which tokens should influence the next prediction, the system asks which meanings support future reasoning, and uses that to decide where KV blocks, summaries, evidence, and concept nodes should live across GPU, CPU, storage, and graph memory.

The key distinction:

Token-to-token attention:
which tokens matter for the next output?

Meaning-to-Meaning Attention:
which meanings matter enough to preserve, promote, demote, or recover?

## How Traditional Attention Organizes Computation Around Tokens

Traditional attention organizes computation around tokens because the model's basic working unit is the **token**.

A token can be a word, part of a word, punctuation, or a symbol.

Example:

```text
"The stylist is available today"
```

The model may see this as tokens like:

```text
"The" "stylist" "is" "available" "today"
```

When the model generates the next token, it asks:

```text
Which earlier tokens should influence what I say next?
```

So if the prompt is:

```text
The stylist is available today, so the customer can book
```

the model may pay more attention to:

```text
stylist
available
today
book
```

because those tokens help predict the next word.

In transformer attention, each token creates three things:

```text
Query: what am I looking for?
Key: what information do I contain?
Value: what information should I pass forward?
```

Then each token compares itself against other tokens.

In simple words:

```text
this token looks at the other tokens
decides which ones matter
pulls information from them
updates its own representation
```

That is what I mean by:

> traditional attention organizes computation around tokens

The model's reasoning work is arranged around token positions:

```text
token 1 attends to token 2
token 7 attends to token 3
token 20 attends to tokens 4, 9, and 15
```

The KV cache also follows this structure. It stores key/value states for tokens, usually by token position.

So traditional attention is asking:

```text
Which token states should affect the next computation?
```

Your HSMA idea shifts the question upward:

```text
Which meanings should affect long-term memory placement and recovery?
```

So the contrast is:

```text
Traditional attention:
organize model computation around token influence.

HSMA Meaning-to-Meaning Attention:
organize memory management around meaning dependency.
```

## How To Infer Meaning Dependencies

In simple words: we know `B depends on A` by looking for evidence that **B would become weaker, incomplete, or wrong if A were removed**.

You do not need one magic method. You combine several signals.

**1. Direct Reference**
Sometimes B literally points back to A.

Example:

```text
A: "Same-day ranking should prioritize availability first."
B: "Based on the same-day ranking rule, update stylist discovery."
```

Here B depends on A because it says "based on." Easy case.

**2. Shared Entities Plus Role**
If B uses the same entity as A, and A defines a rule/constraint about that entity, B may depend on A.

Example:

```text
A: "For same-day bookings, availability beats distance."
B: "Improve same-day stylist discovery."
```

B talks about same-day stylist discovery. A defines a rule for same-day bookings. So A may support B.

But shared topic alone is not enough. The system should ask:

> does A define something B needs?

**3. Decision / Constraint Tracking**
Some memory types are naturally foundational.

Usually foundational:

- decisions
- constraints
- definitions
- user preferences
- experiment results
- API contracts
- metric definitions

If B is a plan or answer, and A is a constraint that applies to it, then B depends on A.

Example:

```text
A: "Do not use destructive git commands."
B: "Plan for cleaning the repo."
```

B depends on A because the plan must obey that constraint.

**4. Derivation Trail**
When the system creates B from A, it should record that at creation time.

Example:

```text
A: raw experiment result
B: summary of experiment result
C: conclusion based on summary
```

The system should store:

```text
B derived_from A
C depends_on B
C indirectly depends_on A
```

This is the cleanest kind of dependency because the system creates the link as it reasons.

**5. Question Test**
Ask a verifier:

> If A were removed, would B still be correct and complete?

If yes, weak/no dependency.  
If no, dependency.

Example:

```text
A: "Availability first, then reviews, then distance."
B: "Same-day search should rank by availability first."
```

Remove A, and B loses its evidence. So B depends on A.

This can be done by a small model, rules, or both.

**6. Contradiction / Tension Test**
Check whether A and B conflict.

Example:

```text
A: "Same-day ranking prioritizes availability."
B: "Same-day ranking prioritizes distance."
```

This is not `depends_on`. It is more like:

```text
B contradicts A
```

That link is still useful, because contradiction should also prevent careless demotion.

**7. Active Task Usage**
If the current task uses B, then things B depends on become more important.

Example:

```text
Current task: "Write final ranking policy."
B: "Stylist discovery policy."
A: "Availability-first rule."
```

If B is active and B depends on A, then A should get boosted too.

That is the key performance idea.

**A Practical First Algorithm**

For every new memory item `B`, compare it against likely relevant older items `A`:

1. Find candidate older memories using embeddings, topic match, entities, timestamps, and active task.
2. Ask what type each item is: `decision`, `constraint`, `fact`, `tool_result`, `plan`, `summary`, etc.
3. Run dependency checks:
   - Does B cite A?
   - Does B use a term/rule defined by A?
   - Is B derived from A?
   - Would B become wrong or incomplete without A?
   - Does B contradict A?
4. Store typed edges:
   - `depends_on`
   - `supports`
   - `refines`
   - `contradicts`
   - `derived_from`
   - `used_by_active_task`
5. Give each edge a confidence score.

Example record:

```text
B: "Same-day stylist discovery should rank available stylists first."

Edges:
- depends_on A: "For same-day bookings, availability beats distance." confidence=0.92
- refines C: "General stylist discovery should balance reviews and distance." confidence=0.71
- used_by_active_task D: "Build ranking policy proposal." confidence=0.88
```

**Important Point**

This should not be treated as perfect truth. It should be treated as **probabilistic evidence**.

So the system does not say:

> B definitely depends on A forever.

It says:

> B probably depends on A with confidence 0.92.

Then retention can use that confidence.

The simplest version:

```text
dependency_importance(A) =
sum(importance(B) * dependency_confidence(B depends_on A))
```

So if many important memories depend on A, A becomes important too.

That is how the system knows to keep A in a stronger tier.

**The Cleanest Answer**

You achieve this dependency system by combining:

- explicit provenance when one memory is created from another
- LLM or classifier-based relation extraction
- rule-based checks for decisions, constraints, definitions, and tool results
- verifier tests that ask whether B still works without A
- confidence scores instead of hard yes/no links

In one sentence:

> We know B depends on A when B uses A as evidence, constraint, definition, source, or reasoning support, and we store that relationship as a weighted edge in the memory graph.

## Resource Utilization Impact Of Meaning-To-Meaning Attention

Yes. The impact is mostly **better resource utilization through safer selectivity**.

Meaning-to-Meaning Attention does not magically make one token cheaper. Its value is that it lets the system know **which old memories are foundations** and which old memories are safe to demote. That means the runtime can keep fewer things in expensive memory without causing bad forgetting.

**Simple Scenario**

Assume an 8B-ish model where KV cache costs roughly:

```text
KV per token ~= 0.5 MB
```

So:

```text
100k tokens full KV ~= 48.8 GB
40k tokens full KV  ~= 19.5 GB
18k tokens full KV  ~= 8.8 GB
12k tokens full KV  ~= 5.9 GB
```

Without Meaning-to-Meaning Attention, the system may need to be conservative. It may keep `40k` tokens hot because it does not know which old details are foundational.

With Meaning-to-Meaning Attention, it may keep only:

```text
12k active tokens
+ 6k foundational tokens
= 18k hot tokens
```

That gives:

```text
19.5 GB -> 8.8 GB
```

About:

```text
2.2x less hot KV memory
```

Compared to keeping the whole `100k` history hot:

```text
48.8 GB -> 8.8 GB
```

About:

```text
5.6x less hot KV memory
```

**What does that mean for speed?**

If decode is heavily memory-bound, reducing active KV reads helps.

Using a rough Amdahl estimate:

```text
speedup = 1 / (non_memory_part + memory_part / KV_reduction)
```

If `70%` of latency is KV/memory movement:

Against conservative `40k` hot tokens:

```text
KV reduction = 40k / 18k = 2.2x

speedup = 1 / (0.3 + 0.7 / 2.2)
        ~= 1.6x
```

Against full `100k` hot tokens:

```text
KV reduction = 100k / 18k = 5.6x

speedup = 1 / (0.3 + 0.7 / 5.6)
        ~= 2.35x
```

So a realistic impact from this idea could be:

```text
1.4x to 1.8x faster versus a conservative hot-memory policy
2x to 3x faster versus full-history hot KV
```

depending on how memory-bound the workload is.

**Concurrency impact**

This may be the bigger win.

If one long-running agent session needs:

```text
without M2M: 19.5 GB hot KV
with M2M:     8.8 GB hot KV
```

Then the same GPU memory budget can support roughly:

```text
19.5 / 8.8 ~= 2.2x more active long-running sessions
```

Against full-history KV:

```text
48.8 / 8.8 ~= 5.6x more sessions
```

So resource utilization improves because expensive HBM is spent on the memories that actually matter.

**Recovery impact**

Without Meaning-to-Meaning Attention, the system may demote the wrong thing, then later recover slowly or answer badly.

With it, the system keeps foundational memories stronger, so recovery should be less frequent and more targeted.

Example:

```text
Fast path speedup vs full hot KV ~= 2.35x
```

If only `5%` of turns need expensive recovery:

```text
overall speedup ~= 2.1x
```

If `10%` need recovery:

```text
overall speedup ~= 1.9x
```

If `20%` need recovery:

```text
overall speedup ~= 1.6x
```

So the system wins most when Meaning-to-Meaning Attention reduces unnecessary recovery.

**Metadata overhead**

The dependency graph itself should be much cheaper than KV.

Example:

```text
100k memory nodes
embedding per node ~= 3 KB
node embeddings ~= 300 MB
edges / metadata maybe tens of MB
```

That is small compared with:

```text
100k full KV ~= 48.8 GB
```

So the graph overhead is likely acceptable if it lets you demote large amounts of KV safely.

**Bottom line**

The impact is:

- lower HBM usage
- lower KV bandwidth per generated token
- more concurrent long-running agents
- fewer expensive recovery events
- fewer reasoning failures from demoting foundational context
- better use of CPU/storage tiers because the system knows what is safe to move

In one sentence:

> Meaning-to-Meaning Attention improves resource utilization by letting the system spend expensive memory on foundational meanings, not just recent tokens.

That is the practical value: it makes aggressive memory tiering safer.

## How Meaning-To-Meaning Attention Improves Resource Utilization And Throughput

Meaning-to-Meaning Attention improves resource utilization because it helps the system avoid treating all old context equally.

The simple idea:

> Keep the memories that future reasoning depends on in stronger memory, and push less important memories into cheaper forms.

Traditional KV systems mostly care about things like:

```text
recently used
currently active
shared prefix
memory pressure
cheap to evict/reload
```

Your idea adds another question:

```text
Is this meaning foundational to future reasoning?
```

That changes resource usage in a few ways.

**1. Less GPU Memory Waste**

GPU memory is expensive. Full KV cache for long context can get huge fast.

Rough example for an 8B-ish model:

```text
KV per token ≈ 0.5 MB
100,000 tokens ≈ 50 GB of KV
```

If a normal system keeps too much old KV hot, GPU memory fills up quickly.

HSMA might say:

```text
Keep 15k-20k tokens worth of important/foundational KV hot.
Compress or demote the rest.
Keep summaries, concept nodes, and pointers for the older material.
```

So instead of keeping 50 GB hot, maybe it keeps:

```text
20k tokens ≈ 10 GB hot KV
```

That is roughly a **5x reduction in hot KV footprint**.

**2. Higher Throughput**

If each active agent session uses less GPU KV memory, the same GPU can support more concurrent sessions.

Example:

```text
Traditional:
1 long-running agent needs 50 GB KV

HSMA:
1 long-running agent needs 10 GB hot KV
```

In a KV-limited setup, that could mean:

```text
same GPU memory budget supports about 5x more active long-context sessions
```

Real speedup will be lower because compute, scheduling, and recovery overhead still matter. But the memory-side capacity improvement can be large.

**3. Lower Latency For Common Cases**

Most prompts do not need every old detail. They need the right few details.

So HSMA can run the cheap path most of the time:

```text
use hot KV
use summaries
use concept graph
use important recovered evidence only when needed
```

Instead of dragging a massive history through every request.

That can reduce:

```text
attention work
KV reads
memory bandwidth pressure
GPU cache pressure
prefill cost
```

So the system may answer faster when abstract memory is enough.

**4. Better Use Of Slow Memory**

Slow memory is not bad. It is just bad when the system uses it blindly.

HSMA gives slow memory a better role:

```text
GPU/HBM: hot, foundational, currently useful KV
CPU RAM: recoverable compressed KV and recent-but-less-hot state
SSD/storage: raw evidence, transcripts, old tool outputs
Graph memory: meanings, summaries, dependency links
```

So instead of “slow memory = forgotten stuff,” slow memory becomes part of an organized recovery system.

**5. Less Bad Eviction**

This may be the biggest quality win.

A traditional engine may evict an old KV block because it has not been used recently.

But that block might contain:

```text
the original user constraint
the ranking rule
the evaluation definition
the reason a design choice was made
```

Meaning-to-Meaning Attention can notice:

```text
many later memories depend on this one
```

and keep it stronger, or at least preserve better recovery pointers.

That improves resource use because the system spends memory on what matters, not just what is recent.

**Bottom Line**

Meaning-to-Meaning Attention can improve:

```text
GPU memory utilization: less hot KV waste
throughput: more concurrent long-running agents
latency: less unnecessary context processing
recovery quality: fetch the right details when needed
reasoning reliability: fewer failures from losing foundational context
```

The one-line version:

> It makes memory placement depend on meaning importance, not just token recency or cache mechanics. That lets the system use expensive memory for the context that actually protects future reasoning.

## Pillar 2: Semantic Demotion Policy

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
- what other meanings depend on it

Working scoring idea:

```text
importance =
attention
+ reuse
+ task relevance
+ graph centrality
+ dependency_importance
+ recovery cost
- age decay
```

This is not final math, just the current intuition.

## Pillar 3: Pointer-Preserving Hierarchy

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

## Pillar 4: Selective Recovery

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

Preferred framing:

> selective recovery = retrieve evidence, replay source spans, or rehydrate compressed KV

This is stronger and more believable than claiming the system can perfectly reconstruct lost KV
from a vague summary.

## How The Core Ideas Fit Into The Overall Picture

Yes. Here's the simple version of how each one fits into the bigger system.

**1. Meaning-to-Meaning Attention for Memory Tiering**

What it is:
A way to decide memory importance by looking at what other meanings depend on it.

Why it matters:
Some old context looks unimportant by itself, but is actually a foundation for many newer ideas.

What benefit it brings:
It helps the system protect **foundational memories** instead of only protecting whatever was
recent or flashy.

Without it:
The system may throw away a quiet but crucial idea just because it was old or low-attention.

So in the overall picture:
**this idea helps the system know what is structurally important.**

**2. Semantic Demotion Policy**

What it is:
The rule that decides the cheapest safe form for each memory item.

Why it matters:
Not everything needs to stay as full KV or raw text. Some things can safely become summaries or
concept memories.

What benefit it brings:
It reduces memory cost and lets the system scale to long histories.

Without it:
The system either keeps too much expensive memory, or throws things away blindly.

So in the overall picture:
**this is the part that makes the whole system efficient.**

**3. Pointer-Preserving Hierarchy**

What it is:
A memory structure where higher-level abstractions keep links back to the lower-level evidence.

Why it matters:
Summaries and graphs are useful, but they are not the original source. If you lose the link
back, the system can become vague or wrong.

What benefit it brings:
It gives the system **safe abstraction**. You can compress meaning without losing the ability to
verify or recover detail.

Without it:
The system turns into a lossy summarizer that forgets where things came from.

So in the overall picture:
**this is what makes abstraction trustworthy.**

**4. Selective Recovery**

What it is:
A way to go back down the memory hierarchy only when more detail is needed.

Why it matters:
You do not want to carry all raw detail all the time. But you also do not want to answer a
precision question from a blurry summary.

What benefit it brings:
It keeps the system cheap most of the time, but still capable of exact answers when necessary.

Without it:
Either everything stays expensive forever, or the system gives weak answers because it cannot
recover lost detail.

So in the overall picture:
**this is what balances efficiency with accuracy.**

**How they fit together**

These are not four separate tricks. They are four parts of one loop:

1. **Meaning-to-Meaning Attention**
   tells you what is foundational.

2. **Semantic Demotion Policy**
   decides how cheaply each thing can be stored.

3. **Pointer-Preserving Hierarchy**
   keeps links back to the exact source.

4. **Selective Recovery**
   brings exact detail back when the task needs it.

So the overall system becomes:

- smart about what matters
- cheap about how it stores it
- safe about how it abstracts it
- flexible about when it restores detail

That is why all four are needed.

If one is missing:

- without meaning-to-meaning attention, the system may forget foundations
- without semantic demotion, it does not scale
- without pointer-preserving hierarchy, it becomes unreliable
- without selective recovery, it loses precision

So in one line:

> Each idea solves one part of the central problem: how to store less, remember better, and still recover exact detail when it matters.

## Supporting Extension: Weak-Answer Detection

A key extension is that the system may be able to detect when an answer is weak because it is
relying on overly abstracted memory.

High-level flow:

```text
Try answer from summary / concept / graph layer
-> evaluate whether the answer looks under-supported
-> if weak, recover deeper evidence
-> regenerate the answer
```

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
weakness_score =
detail_demand
+ evidence_gap
+ conflict_score
+ importance_of_question
+ model uncertainty
- support_from_loaded_memory
```

If the weakness score crosses a threshold, the system escalates to deeper recovery and retries.

## Supporting Extension: Relative Semantic Delta Memory

Another extension is to store new prompts in relation to earlier prompts instead of always
storing them as fully independent memory items.

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
shorter version of `Z`. It is a pointer-preserving relation.

Possible use cases:

- repeated user questions with small changes
- iterative experiment design
- multi-turn refinement of the same idea
- agent plans that evolve gradually
- prompts that share a stable task structure but differ in constraints

Important caveat:

The delta must not replace the raw prompt. It should be a compact routing and reuse structure.
The original prompt still needs a pointer so exact wording can be recovered later.

## Supporting Extension: Hint-Aware Resource Policy

DeepAgents or an agent runtime may mark a request, prompt, phase, or memory item as important.
For example:

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

The design principle:

> hints should be treated as weighted signals, not absolute commands

Possible scoring frame:

```text
retention_value =
agent_priority
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

## The Key Nut To Crack

The key nut to crack is:

> Can the system predict what details future-you will need exactly, before it throws those
> details away?

That is the real problem.

In simple words, the idea only works if the system gets good at this judgment:

- this old context can safely become a summary
- this one must stay exact
- this one can be compressed
- this one can be abstracted, but only if a strong pointer back to the source is kept
- this answer looks weak, so the system should go fetch deeper evidence before replying

Everything else is more straightforward engineering:

- building the graph
- storing summaries
- moving KV between GPU, CPU, and storage
- keeping pointers between layers

Those are hard, but they are not the deepest risk.

The deepest risk is bad forgetting.

Example:

- if the system summarizes "we discussed ranking policy," that may be fine
- but if the real detail was "availability first, then reviews, then distance, only for same-day bookings," losing that exact wording can break the answer later

One-sentence version:

> The idea succeeds or fails based on whether it can abstract aggressively without accidentally
> throwing away future-critical detail.

A successful version needs to do three things well:

- demote safely
- preserve escape hatches
- recover in time

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
- meaning-to-meaning dependency tracking

## Potential Benefits

If HSMA works, the benefits could be substantial:

- much lower active KV memory
- much higher session capacity and concurrency
- better long-horizon recall
- less prompt bloat and less irrelevant history in active reasoning
- smarter recovery when detail matters
- better reuse across repeated or slightly modified tasks
- better multi-agent collaboration through shared semantic memory
- phase-aware memory loading
- lower retrieval overhead when the system can jump to the right semantic branch
- better hardware utilization across GPU, CPU, and storage tiers

The biggest practical win may not be single-turn speed. It may be making very long-lived
agents economically and operationally feasible.

## Overall Benefits If All Four Ideas Work Together

Yes.

**If all four ideas were implemented correctly, the system could absolutely be faster overall.**
But the main win would not just be "faster token generation." The bigger win would be:

- less wasted work
- less memory pressure
- fewer long-horizon mistakes
- better reuse of earlier reasoning
- better recovery when detail matters

In simple words, the system gets faster because it stops behaving like it has to drag its whole
life story around all the time.

Instead of:

- keeping too much hot memory
- rereading too much old history
- forgetting important foundations
- recovering the wrong things
- redoing reasoning from scratch

it becomes better at:

- keeping the right things hot
- demoting the safe things
- protecting foundational meanings
- jumping back to exact evidence only when needed
- reusing earlier structure instead of rebuilding it every time

So yes, it can be faster in a few different ways:

**1. Faster long-context turns**  
Because the active memory is smaller.

**2. Faster repeated work**  
Because the system can reuse meaning, not just raw text.

**3. Faster recovery**  
Because it follows pointers to the right evidence instead of searching blindly.

**4. Faster multi-agent work**  
Because agents can share semantic memory instead of each keeping huge duplicate histories.

**5. Faster system-level throughput**  
Because lower active KV means more sessions and more concurrent agents per machine.

The overall benefits to agentic AI could be very big:

- **better long-horizon reasoning**
- **less plan drift**
- **more stable memory over long sessions**
- **fewer failures from bad forgetting**
- **better use of GPU/CPU/storage tiers**
- **better scalability for long-running agents**
- **better multi-agent coordination**
- **more economically feasible persistent agents**

So the deepest benefit is not just speed.

It is this:

> agents become more reliable, more scalable, and more efficient at the same time.

That is why this way of thinking matters. It changes memory from "store more history" into
"preserve the right meaning, and recover exact detail only when it matters."

## Back-Of-The-Envelope Speedups

Short answer:

If HSMA really works, the biggest win is probably not "10x faster answers" across the board.
The biggest win is:

- much lower active KV memory
- much higher session capacity / concurrency
- noticeable speedups on long-context turns
- making very long agent histories feasible at all

For end-to-end latency, a realistic target is more like 1.5x to 3x on long-horizon workloads,
not 10x.
For active HBM footprint and concurrency, 5x to 8x is plausible in a strong case.

Back-of-the-envelope:

Let us use a simple 8B-ish model example:

KV bytes per token is roughly:

```text
2 x num_layers x hidden_size x bytes_per_value
= 2 x 32 x 4096 x 2
= 524,288 bytes per token
~= 0.5 MB per token
```

So:

- 100k tokens of full KV is about 48.8 GB
- 200k tokens of full KV is about 97.7 GB
- 16k tokens of full KV is about 7.8 GB

Now compare two worlds.

Conventional approach:

Keep all 100k tokens active as full KV.

```text
HBM KV footprint ~= 48.8 GB
```

HSMA-style approach:

Suppose the system keeps:

- 12k tokens as hot raw KV
- 16k tokens as warm compressed KV at about 4x compression
- the rest as summaries / concept nodes / graph / archived evidence

Then:

- 12k raw KV ~= 5.9 GB
- 16k warm KV at 4x compression ~= 2.0 GB
- total active+warm KV-like footprint ~= 7.8 GB

So the KV footprint goes from:

```text
48.8 GB -> 7.8 GB
```

That is about:

```text
48.8 / 7.8 ~= 6.25x reduction
```

If you compare against a more aggressive case with only 12k hot KV, the reduction is:

```text
48.8 / 5.9 ~= 8.3x
```

So a reasonable memory-saving range is:

- conservative strong case: about 5x to 6x
- more aggressive case: about 8x

What does that mean for speed?

For decode, every generated token has to read the active KV. If HSMA shrinks the active read
set by 6.25x, the memory-bound part of decode gets that benefit.

But total latency is not all KV movement. Some of it is fixed model compute.

Using a simple Amdahl-style estimate:

If 70% of token latency is memory/KV movement and 30% is other compute, then:

```text
speedup = 1 / (0.3 + 0.7 / 6.25)
        ~= 2.43x
```

If only 50% of latency is memory-bound, then:

```text
speedup = 1 / (0.5 + 0.5 / 6.25)
        ~= 1.72x
```

So for long-context turns, a believable range is:

- about 1.7x to 2.4x faster from active-memory reduction alone
- in a stronger 8.3x reduction case, maybe 1.8x to 2.6x
- with very memory-bound decoding, maybe pushing toward 3x

What about retry / recovery overhead?

HSMA is not free. Sometimes it will answer from summary memory, notice the answer is weak,
fetch deeper evidence, and retry.

If:

- 90% of turns use the fast path
- 10% of turns need recovery and become slower

then an optimistic 2.4x fast-path speedup becomes more like:

```text
overall ~= 1.9x
```

If 20% of turns need recovery, it drops more like:

```text
overall ~= 1.5x
```

If 30% of turns need recovery, you may be down around:

```text
overall ~= 1.3x
```

So the system only really wins if recovery is rare and targeted.

Where the really big gains are:

The biggest gains are probably in capacity, not per-request speed.

If active KV footprint drops by 6.25x, then in a KV-limited serving setup you can roughly fit:

- about 6x more long-lived sessions
- or use the same memory budget for much longer histories
- or avoid pushing huge old histories through GPU memory at all

That is a major systems win.

Honest bottom line:

If you pull this off well, expected ranges are something like:

- HBM / active KV reduction: 5x to 8x
- long-context latency speedup: 1.5x to 3x
- KV-limited concurrency improvement: 4x to 8x
- bigger practical win: very long agent histories become feasible without keeping enormous full KV hot

## Angles For Even Bigger Gains

The really huge gains may come from avoiding work, not just storing memory better.

Promising angles:

- reuse meaning, not just recover it
- branch-level reuse through semantic deltas
- multi-agent shared semantic memory
- phase-aware memory
- turning summaries into execution shortcuts
- precomputing semantic maintenance in the background
- preferring exact-text recovery before raw-KV recovery

If there is a single biggest underexplored angle right now, it is:

> shared semantic memory plus delta-based reuse across repeated agent work

That is where the gains can move from nice memory optimization to the whole system working
differently.

## How HSMA Can Work Side By Side With Traditional KV Engines

Yes. They should work side by side.

Your idea does not replace traditional KV management. It adds a smarter decision layer on top of it.

Think of it like two levels:

```text
Traditional KV engine:
How do we store, page, reuse, evict, and reload KV blocks efficiently?

HSMA semantic layer:
Which blocks are actually important for future reasoning?
```

The traditional engine handles the low-level mechanics:

```text
GPU memory pressure
KV paging
prefix caching
radix tree reuse
CPU offload
batch scheduling
block eviction
block reload
```

HSMA gives it better priorities:

```text
this block is foundational
this block is safe to summarize
this block has many dependent meanings
this block is cheap to recover
this block should be demoted but keep pointers
this block should stay hot even though it is old
```

So the combined system could work like this:

```text
1. The normal engine tracks KV blocks, recency, reuse, and memory pressure.
2. HSMA attaches semantic metadata to some KV blocks.
3. Meaning-to-Meaning Attention scores which meanings are important.
4. The engine uses those scores when deciding what to keep in GPU, move to CPU, compress, summarize, or archive.
5. If detail is needed later, HSMA follows pointers back to the exact evidence or KV block.
```

In simple words:

> The traditional KV system is the memory manager.  
> HSMA is the judgment layer that tells it what is worth protecting.

That is actually the strongest version of the idea. You do not need to rebuild everything from scratch. You can plug semantic priority into existing KV-cache systems.

## Comparison With SGLang Radix Tree Prompt Reuse

SGLang’s radix tree and your idea are related, but they operate at **different levels**.

SGLang RadixAttention is mainly about **reusing exact token/KV prefixes**. If many requests begin with the same system prompt, same conversation prefix, same tool definitions, or same previous turns, SGLang stores the KV cache in a radix tree and reuses the shared prefix instead of recomputing it. The SGLang docs describe this as detecting shared prefixes, reusing cached KV states, storing completed requests, and evicting old entries when memory fills. Sources: [SGLang prefix caching](https://sgl-project-sglang-93.mintlify.app/concepts/prefix-caching), [SGLang RadixAttention](https://sgl-project-sglang-93.mintlify.app/concepts/radix-attention), [LMSYS SGLang blog](https://lmsys.org/blog/2024-01-17-sglang/).

Your **Meaning-to-Meaning Attention for Memory Tiering** is different. It is not asking:

> do these prompts share the same token prefix?

It asks:

> what meanings depend on what other meanings?

So SGLang reuses this:

```text
same tokens -> reuse same KV prefix
```

Your idea tracks this:

```text
meaning A supports meaning B
meaning B affects plan C
plan C depends on constraint D
```

That means your system could preserve a memory because it is **semantically foundational**, even if its exact tokens are old, not recent, or not part of the current prefix.

A simple contrast:

| System | What It Indexes | Main Question | Reuse Type |
|---|---|---|---|
| SGLang radix tree | token sequences / KV prefixes | “Have I seen this exact prefix before?” | exact KV reuse |
| Meaning-to-Meaning tiering | concepts, decisions, constraints, dependencies | “What important meanings depend on this?” | semantic retention and recovery |

The important point is: **your idea can sit above SGLang rather than replace it.**

SGLang can be the low-level KV reuse engine. HSMA can be the semantic control layer that says:

- this prefix/KV block is tied to an important decision
- this old context supports many later meanings
- this subagent cache is temporary and safe to demote
- this source span must stay recoverable
- this memory should get stronger retention priority

That matters especially for agentic systems, because NVIDIA’s Dynamo docs note that normal radix cache behavior can let short-lived subagent KV compete with a lead agent’s long-lived prefix for eviction in agentic workloads: [Dynamo SGLang agentic workloads](https://docs.nvidia.com/dynamo/backends/sg-lang/agentic-workloads).

So the clean framing is:

> SGLang’s radix tree reuses identical token/KV prefixes. HSMA’s Meaning-to-Meaning Attention decides which semantic foundations deserve stronger retention, even when token prefixes are not identical.

In simple words:

**SGLang remembers repeated text efficiently.  
Your idea remembers what the repeated or old text means, and what depends on it.**

They are complementary. SGLang answers “can I reuse this KV?” HSMA answers “is this memory important enough to keep, demote, or recover later?”

## Current Research Roadmap

The current order of attack should stay conservative:

1. Prove the long-horizon memory problem clearly on real agent workloads.
2. Build a software-only HSMA prototype.
3. Add meaning-to-meaning dependency tracking.
4. Add semantic demotion and pointer tracking.
5. Test selective recovery paths.
6. Add weak-answer detection and retry.
7. Measure memory saved, latency added, and answer quality retained.
8. Only then ask what deserves hardware acceleration.

## Manager-Friendly Hardware Pitch

The Manager-Friendly Pitch
I would frame it like this:
Today, GPU memory systems mostly manage KV cache as token blocks. They are good at paging, reuse, and eviction, but they do not know which blocks are semantically important. HSMA proposes adding a semantic-priority layer so memory hardware can protect the KV blocks that future reasoning depends on, while aggressively demoting less important context.

## What Would Need To Be Measured

Key validation questions:

- Does HSMA reduce peak KV memory at acceptable quality?
- Does it reduce HBM bandwidth pressure?
- Does long-horizon recall improve or stay stable?
- How often are summaries enough?
- How often must the system recover exact evidence?
- Does weak-answer detection actually catch failures before the user sees them?
- What is the latency cost of recovery and retry?
- Does dependency-aware retention outperform plain recency / attention policies?
- Can delta-based reuse cut repeated-work cost without missing important differences?

## Current Open Questions

- How should memory units be defined: token spans, turns, facts, tasks, tool outputs, or all of the above?
- How should concept nodes be created and updated over time?
- How should graph drift be controlled?
- How aggressive should demotion be for different workloads?
- What signals best predict that detail will matter later?
- When is raw text replay enough, and when is compressed-KV rehydration better?
- Can weak-answer detection be made reliable enough to justify the extra recovery step?
- Can relative semantic deltas be made reliable enough to cut storage without missing critical differences?
- How should dependency weights be learned or updated over time?
- Which parts of this should stay software, and which parts might eventually justify hardware support?

## One-Paragraph Summary

HSMA is a proposal for a semantic memory-management layer for long-horizon agentic AI.
Instead of keeping all history forever as raw tokens or KV cache, the system gradually demotes
older context into compressed KV, summaries, concept nodes, and a knowledge graph while
preserving typed pointers back to exact evidence. A central mechanism is Meaning-to-Meaning
Attention for Memory Tiering: memories are retained not only based on their own local
importance, but also based on how many other important meanings depend on them. When a question
can be answered from abstract memory, the system stays cheap. When the answer looks weak or
under-supported, the runtime selectively recovers deeper context, such as source spans,
compressed KV, or archived state, and retries. With extensions like weak-answer detection,
relative semantic delta memory, and hint-aware resource policy, HSMA aims to make agents scale
with understanding rather than with accumulated token history.
