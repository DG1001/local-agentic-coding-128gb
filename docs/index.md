---
title: Overview
nav_order: 1
description: Seven large local LLMs on one GX10 — what limits them, and why one run per model was not enough.
---

Seven large local LLMs, four realistic coding tasks, 86 hidden tests each, one
ASUS Ascent GX10 — **NVIDIA GB10, 128 GB unified memory**, the same chip and
memory configuration as the NVIDIA DGX Spark. Everything ran locally through
[opencode](https://opencode.ai), [Claude Code](https://claude.com/claude-code)
and [Oh My Pi](https://github.com/can1357/oh-my-pi) against endpoints on
`127.0.0.1` — no cloud API, no per-token cost. A fourth, purpose-built harness
was added later to test specific claims about the other three; see
[below](harness.md#testing-that-theory-a-fourth-harness-written-to-check-one-claim).

Models: DeepSeek-V4-Flash, Laguna-S-2.1 (poolside), KAT-Coder-V2.5,
Qwen-AgentWorld-35B-A3B, Qwen3.6-27B, and — added later — NVIDIA
Nemotron-3.5-Lightning-30B-A3B and Qwen3.6-35B-A3B. Served with vLLM and a
llama.cpp-derived server.

This is the big-memory counterpart to
[local-agentic-coding-24gb](https://github.com/DG1001/local-agentic-coding-24gb),
which looked at seven small models on a 24 GB MacBook. The conclusions are
almost disjoint. On 24 GB the limiting factor was tooling — inference engines
breaking chat templates, KV cache blowing past the budget, system prompt size
pushing models off a cliff. On 128 GB almost none of that mattered: with
131,072-token context windows and millions of tokens of KV cache to spare, no
model here ran out of room, and four of the first five got at least 84 of 86
tests right. The two models added later scored markedly lower, and in both cases
the whole gap is one task graded all-or-nothing — worth reading before the
ranking is taken at face value.

What limits you here is **memory bandwidth**, and it decides which models are
worth running at all. And — the finding that surprised us most — **which agent
harness you point at the model changes not just how long it takes, but how many
tests pass.**

## The short version

| Model | Type | Weights | Hidden tests | Wall clock | Tool calls | Own tests written |
|---|---|---|---|---|---|---|
| **DeepSeek-V4-Flash** | MoE | 88 GB | **86 / 86** | **25:49** | 57 | 73 |
| **Laguna-S-2.1** | MoE | 93 GB | **86 / 86** | 30:56 | 76 | 111 |
| **Qwen3.6-27B** | dense | 52 GB | **86 / 86** | **3:07:36** | 67 | 118 |
| KAT-Coder-V2.5-Dev | MoE | 65 GB | 84 / 86 | 25:59 | 169 | 79 |
| Qwen-AgentWorld-35B-A3B | MoE | 65 GB | 80 / 86 | 41:34 | 120 | 66 |
| Qwen3.6-35B-A3B | MoE | 35 GB | 68 / 86 | 44:30 | 116 | 125 |
| Nemotron-3.5-Lightning-30B-A3B | MoE | 21 GB | 63–85 / 86 † | 36:29 | 220 | 54 |

† **Not a typo, and the most important number in this table.** Nemotron is the
only model here that was run more than once. Three runs on the identical tasks
at identical limits produced 63/86, 64/86 and 85/86 — a 22-point spread that is
**wider than the gap between first and last place in this table**, every other
row of which is a single run. Details in [one run is not a
measurement](variance.md#one-run-is-not-a-measurement). Read the ranking accordingly: it
separates "solves this class of task" from "does not", and nothing finer.

Three models scored perfectly. The interesting column is wall clock: the dense
27B needed **7.3× longer than DeepSeek** for the exact same result. That gap is
not a software problem and it is not tunable. See below.

## Hardware

- ASUS Ascent GX10 — NVIDIA GB10, 128 GB unified LPDDR5X (121 GiB usable),
  arm64, Ubuntu 24.04.4
- ~273 GB/s memory bandwidth (vendor spec, not measured here)
- vLLM 0.26.0 in Docker for six models, 0.27.1 for the DSpark measurement;
  `ds4-server` (llama.cpp-derived,
  from [DeepSeek-v4-Flash-One-DGX-Spark](https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark))
  for DeepSeek
- opencode 1.18.14, Claude Code 2.1.226 and Oh My Pi 17.2.12 as agent harnesses,
  plus a purpose-built Java harness for one follow-up question

Comparable hardware: the NVIDIA DGX Spark uses the same GB10 superchip and the
same 128 GB unified LPDDR5X, so the bandwidth findings below transfer directly.
Nothing here depends on the ASUS badge.

Only one model runs at a time — DeepSeek alone occupies ~113 GiB. The
[`tools/model-switch`](https://github.com/DG1001/local-agentic-coding-128gb/blob/main/tools/model-switch) script in this repo stops whatever
is running before starting the next one.

## The four findings

Each is a link to the evidence, not a summary that stands alone.

### 1. Bandwidth decides which models are worth running

A dense model streams every weight for every token; a mixture-of-experts streams
only the active ones. On this machine that is a 27× spread between the fastest
and slowest model measured, and **no software fixes it** — the dense 27B runs at
84% of what 273 GB/s physically allows.

Quantization is the second lever and it is nearly as large: among models that
activate ~3B parameters, NVFP4 reads 78.7 tok/s where BF16 reads 30.8.
Speculative decoding is the third, worth another 1.5×.

![Throughput by model](charts/throughput.svg)

→ [**Speed on this machine**](speed.md) — the arithmetic, the
method, what quantization and speculative decoding are each worth, and a
correction to an earlier version of this table.

### 2. One run is not a measurement — and this is the big one

Every row of the summary table is a single run. Nemotron is the only model that
was run repeatedly, thirteen times on the identical tasks. **Those thirteen runs
span 38 points. The seven different models span 23.**

![Score spread across repeated runs](charts/variance.svg)

The ranking above therefore separates "solves this class of task" from "does
not", and nothing finer. Three separate explanations were offered for one of
those low scores before repetition showed all three were wrong.

→ [**One run is not a measurement**](variance.md) — the three explanations,
why each failed, and what in this repo is *not* affected by it.

### 3. The harness changes correctness, not just speed

Same model, same tasks, same limits — swapping opencode for Oh My Pi recovers
seven points across three named defects. Claude Code scores 9/86 on a
65K-context model because its own baseline footprint will not fit, and every
task dies in compaction thrashing.

→ [**The harness matters as much as the model**](harness.md) — including a
purpose-built Java harness written to test one claim, and what its tool set is
worth measured.

### 4. Green tests are not acceptance

Every model ran `pytest` in every task. It told us nothing. Three models failed
the same task in three different ways, each with a green self-written suite,
each by building something that works instead of what was specified. One wrote
125 passing tests and scored 68/86.

![Hidden tests passed per task](charts/tasks.svg)

→ [**The benchmark and what it found**](benchmark.md) — task design, per-task
results, and the three defects in detail.

### Also here

→ [**Running these models**](operations.md) — vLLM flags that cost real
debugging time, and three configuration traps that all fail mid-task.

## Limitations

Read the numbers with these in mind:

- **One run per model per task — and that is now the headline limitation, not
  a footnote.** The only model run three times spread 22 points across those
  runs, wider than first-to-last in the summary table. See [one run is not a
  measurement](variance.md#one-run-is-not-a-measurement). Treat "these solve this class of
  task, those do not" as the finding; treat every ordering finer than that as
  unsupported.
- **The suite is too easy at the top.** Three of seven models scored perfectly.
  A benchmark where the top is crowded measures nothing at the top. The two
  later models did produce spread — but almost all of it comes from one
  all-or-nothing import in one task, which is spread from grading mechanics, not
  from difficulty.
- **Qwen3.6-35B-A3B ran once, under opencode only.** It and
  Nemotron-3.5-Lightning were added months after the original five, on the same
  tasks and the same 131,072-context configuration. Nemotron has since been run
  through the Java harness as well (64 / 86 against 63 / 86 — one point apart on
  the total, every task different underneath); Qwen3.6-35B-A3B has no second
  harness, so treat its 68 / 86 as a number about that pairing.
- **A one-run-per-pairing benchmark hides more movement than the totals show.**
  The first two Nemotron runs differ by a single point and disagree on all four
  tasks, including *which* five points `t4` loses; the third differs from both by
  21 points. Where this repo reports a gap, assume noise unless a named defect is
  attached to it.
- **Four tasks, one language, one domain.** All Python, all small self-contained
  repos, all with fully specified signatures. Nothing here says anything about
  large unfamiliar codebases, other languages, or ambiguous requirements.
- **The 5090 section is arithmetic**, not measurement.
- **Quantization differs across models** (GGUF IQ2_XXS-based mixed for
  DeepSeek, NVFP4 for Laguna, BF16 for the three Qwen-family models). This is
  a comparison of *usable local setups*, not of model weights under equal
  conditions.
- **Bandwidth figure is vendor spec**, not independently measured.
- **The harness comparison is one run per pairing.** Oh My Pi covers four
  models, Claude Code only Laguna (at 65K context — it never got far enough to
  be worth extending). Seven recovered points across three distinct defects is
  a pattern, not a proof; a second run per pairing could move any single number.
- **The Java harness ran once per model, on two of the original five.** It answers a
  single question — was the `t3` failure a harness behaviour — and answers it
  clearly, because the failure mode was specific and the fix targeted it
  directly. Both models reaching 86/86 makes the parity harder to dismiss as
  luck, but it is still two runs. It is not evidence that it would hold up on
  harder work, on the other three models, or on anything resembling a real
  codebase. It was written to test a claim, not to be used.
- **Qwen3.6-27B was deliberately skipped in the Oh My Pi round.** At 4.5 tok/s
  it took 187 minutes under opencode; at Oh My Pi's 2–3× that is over ten hours
  for a model already shown to be impractical here. An omission, not a gap in
  the data.

## Alles weitere

Aufbau, Rohdaten und Reproduktion stehen im
[Repository](https://github.com/DG1001/local-agentic-coding-128gb) —
einschliesslich der Aufgaben, der verdeckten Testsuiten und der
Skripte, mit denen jede Zahl hier entstanden ist.
