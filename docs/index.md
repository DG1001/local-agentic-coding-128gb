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

### The original round: seven models, opencode, one run each

| Model | Type | Weights | Hidden tests | Wall clock | Tool calls | Own tests written |
|---|---|---|---|---|---|---|
| **DeepSeek-V4-Flash** | MoE | 88 GB | **86 / 86** | **25:49** | 57 | 73 |
| **Laguna-S-2.1** | MoE | 93 GB | **86 / 86** | 30:56 | 76 | 111 |
| **Qwen3.6-27B** | dense | 52 GB | **86 / 86** | **3:07:36** | 67 | 118 |
| KAT-Coder-V2.5-Dev | MoE | 65 GB | 84 / 86 | 25:59 | 169 | 79 |
| Qwen-AgentWorld-35B-A3B | MoE | 65 GB | 80 / 86 | 41:34 | 120 | 66 |
| **Qwen3.6-35B-A3B** (NVFP4) | MoE | 23 GB | **86 / 86** | **21:01** | 61 | 132 |
| **Qwen3.8-27B** (NVFP4 + MTP) | dense | 22 GB | **86 / 86** | >1:47 ‡ | 74 | 118 |
| Qwen3.6-35B-A3B (FP8) | MoE | 35 GB | 68 / 86 | 44:30 | 116 | 125 |
| Nemotron-3.5-Lightning-30B-A3B | MoE | 21 GB | 63–85 / 86 † | 36:29 | 220 | 54 |
| **Ornith-1.5-35B-A3B** (NVFP4) | MoE | 23 GB | **86 / 86** § | 1:09:00 | — | — |
| **Qwen3.8-Flash-Next** (Q3_K_XL) | MoE | 84 GB | **86 / 86** ¶ | **33:33** | — | 98 |
| GLM-5.3-Flash (IQ1_S) | MoE | 87 GB | 9 / 86 ‖ | 35:28 | 16 | — |

§ Added later, not part of the original round. Two opencode runs: 69/86 and
86/86. The 69 was `t2-refactor` scoring zero because the rewrite dropped one
function and the hidden suite could not import it — the model's own tests
passed. Tool-call and own-test columns are blank because opencode's transcript
markers changed since the earlier runs; counting them the old way would have
produced numbers that are not comparable.

‡ `t3-neubau` ran into the 90-minute cap with the work already finished — the
hidden suite passed 33/33 against what was on disk. That wall clock is a floor,
not a measurement, so the total is not comparable with the other rows.

¶ Added later. **The first model here to score 86/86 on two consecutive runs**
— 33:33 and 38:24, no task losing a point in either. It is also the first run
on llama.cpp rather than vLLM: `llama-server`, `-c 65536 -ngl 99 --parallel 1
--no-mmap --jinja`. Architecture support (`qwen4exp`) landed days before the
run; before that the checkpoint sat on disk unloadable.

‖ **All nine points are the untouched seed's own score.** Run the hidden suite
against `t1-debug` before any model touches it and it passes 9 of 15; the other
three seeds score zero. GLM-5.3-Flash's contribution across all four tasks is
therefore **nothing at all**, and the row is not a verdict on the model but a
record of a configuration that did not work. See the GLM section below.

† **Not a typo, and the most important number in this table.** Nemotron has
since been run **thirteen** times on the identical tasks, scoring anywhere from
47 to 85 — a 38-point spread, **wider than the whole field above**, every other
row of which is a single run. A second model repeated twice swung a full task
(16/17 to 0/17) between consecutive runs. Details in [one run is not a
measurement](variance.md#one-run-is-not-a-measurement). Read the ranking accordingly: it
separates "solves this class of task" from "does not", and nothing finer.

Three models scored perfectly. The interesting column is wall clock: the dense
27B needed **7.3× longer than DeepSeek** for the exact same result. That gap is
not a software problem and it is not tunable. See below.

### The same model at two precisions

Qwen3.6-35B-A3B is the one model here measured twice at different precision
under the same harness, and the result is a warning rather than a finding:

| | Hidden tests | Wall clock | Generation |
|---|---|---|---|
| FP8 (35 GB) | 68 / 86 | 44:30 | 50.0 tok/s |
| **NVFP4 (23 GB)** | **86 / 86** | **21:01** | 78.3 tok/s |

The more aggressively quantized build scores *higher* and runs twice as fast.
That does not make 4 bits better than 8. **The entire difference is one task**,
`t2-refactor`, of which this model has now produced **0, 16, 0 and 17** across
four runs. The FP8 run drew a zero and this one a seventeen. Two single runs,
one confound removed, and the number still says nothing about precision — which
is the whole argument of [one run is not a
measurement](variance.md#one-run-is-not-a-measurement) in one table.

What the pair does support is the throughput claim: 1.57× from halving the
bytes per weight, measured on identical hardware and software.

### What a score costs in speed

![Score against throughput](charts/tradeoff.svg)

Everything above is in this one picture: score up, throughput right, and a
vertical bar wherever the same configuration was run more than once.

**Qwen3.6-35B-A3B at NVFP4 holds both ends: 86/86 in 21:01, at 57.9 end-to-end
tokens per second.** That is the fastest perfect run here — DeepSeek needs
25:49 at 16.5 tok/s, Laguna 30:56 at 19.5 — and it is three times further right
than either.

> **This replaces an earlier reading of the same chart.** Before that run, the
> four configurations at 86/86 all sat at 19.5 tok/s or below, and this section
> said nothing faster had ever reached full marks — that past some point the
> trade becomes speed against knowing what you will get. One run moved the
> frontier by a factor of three and the sentence did not survive it. A boundary
> drawn through the fastest point you happen to have measured is a statement
> about your sample, not about the machine.

What does survive is the shape of the bars. Nemotron with DSpark is the fastest
configuration on the chart and has scored anywhere from 47 to 85 across eleven
runs — that tall bar is not an error bar, it is eleven actual results. The same
Qwen3.6-35B-A3B that reached 86 also produced 64 and 67 on two earlier runs.
**Being fast does not cost you points; it does not buy you consistency
either.** The vertical extent of a bar, not its position, is what should decide
whether you would rely on a configuration.

Two models added later sit at the ends of this picture. Qwen3.8-Flash-Next is
the only point here whose repeated runs land on the same value — two runs, 86
both times, at 23.7 end-to-end tokens per second. **GLM-5.3-Flash is
deliberately not plotted:** its 9 is the score of the untouched seed, so
placing it on a score axis would assert something the measurement does not
support.

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

Every row of the summary table is a single run. Two models have since been run
repeatedly: Nemotron thirteen times, Qwen3.6-35B-A3B twice. **Nemotron's thirteen
runs span 38 points. The seven different models span 23.** Qwen's two runs
disagree by a whole task.

![Score spread across repeated runs](charts/variance.svg)

The ranking above therefore separates "solves this class of task" from "does
not", and nothing finer. Three separate explanations were offered for one of
those low scores before repetition showed all three were wrong.

→ [**One run is not a measurement**](variance.md) — the three explanations,
why each failed, and what in this repo is *not* affected by it.

### 3. The loop decides whether you get what the model can do

Same model, same tasks, same limits — swapping opencode for Oh My Pi recovers
seven points across three named defects. Claude Code scores 9/86 on a
65K-context model because its own baseline footprint will not fit, and every
task dies in compaction thrashing.

There is a popular version of this: that the fastest way to improve an agent is
a better loop rather than a better model. The measurements here support it and
then narrow it. **Every harness win in this repo is the removal of a total
failure** — a turn that ended without acting, a compaction that discarded
finished work, a turn budget that cut mid-task, a four-token answer accepted as
a completed run. None of them made a good run better; each stopped a good run
from being thrown away.

And the one deliberate attempt to *add* points with a better loop measured
nothing. Asking the model to walk the task statement before finishing produced
**no further tool call at all in four of six cases** — it confirmed its own
requirements in prose, once while a broken import sat in the file. A model that
believes it is finished will say so when asked; checking needs an observation,
not a question.

→ [**What the harness is actually worth**](harness.md#what-the-harness-is-actually-worth)
— the four failures it removed, the one improvement it did not deliver, and a
purpose-built Java harness written to test a claim.

### 4. Green tests are not acceptance

Every model ran `pytest` in every task. It told us nothing. Three models failed
the same task in three different ways, each with a green self-written suite,
each by building something that works instead of what was specified. One wrote
125 passing tests and scored 68/86.

![Hidden tests passed per task](charts/hidden-tests.svg)

→ [**The benchmark and what it found**](benchmark.md) — task design, per-task
results, and the three defects in detail.

## Two GGUF models on llama.cpp

Everything above ran on vLLM. These two ran on `llama-server`, both at 65,536
context, `--parallel 1 --no-mmap --jinja`, both far larger on disk than
anything in the original round — and they landed at opposite ends of the
result.

| | Qwen3.8-Flash-Next | GLM-5.3-Flash |
|---|---|---|
| Architecture | MoE, 125B total / 6B active | MoE, 177B total |
| Quantisation | Unsloth UD-Q3_K_XL, 84 GB | Unsloth UD-IQ1_S, 87 GB |
| Generation | 29.0 tok/s | 18.8 tok/s |
| End-to-end (16.8k in) | 23.7 tok/s | 17.7 tok/s |
| Hidden tests | **86 / 86**, twice | 9 / 86 — the seed's own score |
| Wall clock | 33:33 and 38:24 | 35:28 |

### Qwen3.8-Flash-Next: the first model to repeat a perfect score

Two consecutive opencode runs, 86/86 both times. That has not happened before
in this collection. Ornith needed two attempts (69, then 86); Qwen3.6-35B-A3B
produced 64 and 67 before its 86; Nemotron has scored anywhere from 47 to 85
across thirteen runs. **The variation here is wall clock only** — and almost
all of it sits in one task, `t3-neubau`, at 779 s against 1319 s.

It is not the fastest perfect run: Qwen3.6-35B-A3B at NVFP4 still holds that
at 21:01 and 57.9 end-to-end tokens per second. But at 29.0 tok/s it beats
Laguna's 30:56 while scoring the same, and it does it as a 6B-active model
read from a 3-bit GGUF.

**Two runs are not a distribution.** The model that looks most consistent here
is the one with the fewest runs behind it, which is exactly the trap
[one run is not a measurement](variance.md#one-run-is-not-a-measurement)
describes. Read the pair as "did not fall over twice", not as "reliable".

### GLM-5.3-Flash: a model that does not drive the loop

Under opencode it scored 9/86, and the transcripts say why the number is not
about coding ability:

| Task | Wall clock | Hidden | Tool lines | Transcript |
|---|---|---|---|---|
| t1-debug | 504 s | 9/15 | 3 | 683 B |
| t2-refactor | 569 s | 0/17 | 6 | 1,137 B |
| t3-neubau | 513 s | 0/33 | 0 | 35 B — the banner, nothing else |
| t4-feature | 542 s | 0/21 | 7 | 505 B |

It reads a few files and stops. No edit, no test run, exit code 0 every time.

**The nine points are not its own.** The `t1-debug` seed passes 9 of its 15
hidden tests before any model touches it — the task is to find the remaining
bugs. The other three seeds score zero, two of them because the hidden suite
cannot even import what is there. So the row totals the seed and nothing else.

**What was ruled out.** No error in the opencode log during the window, none
in the llama.cpp log. A single tool-call request sent by hand against the same
server returns a well-formed `tool_calls` block after 43 tokens, so tool
calling works. One hypothesis fitted the suspiciously uniform 504–569 s
exactly — 8,192 output tokens at 18.8 tok/s is 436 s, so the model might have
been spending its whole output budget on reasoning — and that hand-sent
request refuted it: 43 completion tokens, 102 characters of reasoning.

Most of all: **the same engine, the same flags and the same harness produced
86/86 with Qwen3.8-Flash-Next an hour later.** That removes the loop, the
server and the machine from the list of suspects.

A second harness separates model from loop, so GLM was run again under the
Hermes agent, same tasks, `--max-turns 80`. It failed in the opposite manner:
instead of stopping after five minutes it ground on until the 90-minute cap cut
it off (exit 124), against 158 s for Qwen3.8-Flash on the same task. **And it
finished at 9/15 — the seed's score again.** Ninety minutes of work, nothing
the hidden suite can see. Two harnesses, two opposite failure modes, the same
zero contribution.

**So this row is a finding about a configuration, not a ranking of a model.**
Something about this build, this quantisation or this chat template does not
survive contact with an agent loop. IQ1_S is an aggressive quantisation and
the obvious suspect, but nothing here tests that — a run at a larger
quantisation would, and has not been done. Until then, 9/86 means "did not
work here", and that is all it means.

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
  conditions. One model has since been measured at two precisions —
  Qwen3.6-35B-A3B at FP8 and NVFP4 — and scored in the same band while running
  1.57× faster. That is one data point on one model, not a general result.
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

## Everything else

Setup, raw data and reproduction steps are in the
[repository](https://github.com/DG1001/local-agentic-coding-128gb) — including
the tasks, the hidden test suites, and the scripts every number here came out
of.
