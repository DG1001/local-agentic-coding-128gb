---
title: The harness matters as much as the model
nav_order: 5
description: opencode, Oh My Pi, Claude Code, a purpose-built Java harness, DeepSeek Harness — and why the harness decides which model looks better.
---

[← Overview](index.md)

## The harness matters as much as the model

Same model, same tasks, same hidden tests, same limits (65,536 context, 16,384
output) — only the agent harness differs. Laguna-S-2.1 throughout:

| Harness | Hidden tests | Wall clock |
|---|---|---|
| **opencode** | **86 / 86** | 30:56 |
| **Oh My Pi** | **86 / 86** | 45:35 |
| Claude Code | **9 / 86** | 1:58:51 |

(A fourth harness, written later to test one specific claim, also reaches
86/86 here in 37:13 — see
[below](#testing-that-theory-a-fourth-harness-written-to-check-one-claim).)

Every one of Claude Code's four tasks ended with the same error:

```
Autocompact is thrashing: the context refilled to the limit within
3 turns of the previous compact, 3 times in a row.
```

Including `t3-neubau`, which starts from an **empty directory** — 57 minutes,
zero files written. So it is not about reading an existing codebase into
context: Claude Code's own baseline footprint (system prompt, tool
definitions, working state) exceeds what a ~49K input budget can sustain.
opencode does the same four tasks on the same budget without compacting once.

**On a 65K-context local model, use opencode.** Whether Claude Code works at
128K is untested here.

Compaction is not a Claude Code problem, though — it is a compaction problem.
opencode compacted twice across all runs in this repo, and one of those two
[destroyed a solution a model had already finished and
verified](variance.md#nemotron-solved-it-then-threw-it-away). The difference is frequency,
not kind: opencode's smaller footprint means it gets there rarely, on the tasks
where a model reasons at length. (That model went on to fail the same task in a
harness that never compacts, so the compaction cost it work, not the score —
read the section before quoting it.)

## What the harness is actually worth

There is a claim you hear often about agents: that the fastest way to improve
one is not a better model but a better loop around it. The measurements here
support it — and then sharpen it into something less comfortable.

**Every harness win in this repo is the removal of a total failure, not an
improvement.** Four of them, all large:

| What happened | Cost | Fixed by |
|---|---|---|
| A turn hit the output cap with no tool call and was treated as finished | 33 points, 683 s, zero files written | retrying with a nudge to act |
| Compaction summarised away the fact that the work was already done | a solved task thrown out and rebuilt from scratch | not compacting |
| The turn budget cut mid-task | `t4-feature` at 18–20 instead of 21/21 | raising 80 to 200 |
| A four-token answer with no tool call was accepted as a finished run | 21 points in one second | nudging when a run ends with zero tool calls |

None of these made a good run better. Each stopped a good run from being
discarded. That is worth a great deal — Claude Code scores 9/86 against
opencode's 86/86 on the same model for exactly this reason — but it is a
different claim from "a better loop gets you more".

**The one deliberate attempt to add points with a better loop measured
nothing.** `--abgleich` asks the model, before it may finish, to walk the task
statement sentence by sentence and say for each requirement whether it is met
and where. It is the obvious fix for the dominant failure in this benchmark:
models that build something working instead of what was asked. Thirteen runs
later there is no effect — and the logs say why:

```
ab200-mit-r1   t2:  0 tool calls after the check
               t3:  0
               t4:  0
```

In four of six cases the question produced no further action at all. The model
ticked the requirements off in prose and stopped. In one of those runs it
confirmed its requirements while `from typing import dict` sat in the file,
breaking every import — its own tests could not collect either.

**A model that believes it is finished will confirm that belief when asked.**
The check enquired about beliefs where it needed observations. "Walk the
requirements" is a question; "run the tests and show me the output" is a tool
call. The next version has to demand the second.

So the sharper version of the claim, and the one this repo can actually
support: **the loop decides whether you get what the model can do. It does not
decide what the model can do.** Nothing in the harness moves 4.4 tokens per
second, or Nemotron's 38-point spread across thirteen runs at an unchanged
harness, or four models missing the same import path in four different ways.

(The claim usually extends to orchestration graphs as well. Nothing here tests
that — every run in this repo is a single agent in a single loop.)

## The surprise: the harness changes *correctness*, not just speed

Running all four models through Oh My Pi as well turned the speed comparison
into something more interesting.

| Model | opencode | Oh My Pi |
|---|---|---|
| Laguna-S-2.1 | 86 / 86 · 31 min | **86 / 86** · 45 min |
| DeepSeek-V4-Flash | **86 / 86** · 26 min | 53 / 86 · 43 min |
| KAT-Coder-V2.5 | 84 / 86 · 26 min | **85 / 86** · 78 min |
| Qwen-AgentWorld-35B | 80 / 86 · 42 min | **86 / 86** · 92 min |

**Seven points that opencode left on the table, Oh My Pi collects — same models,
same tasks, same hidden suites.** These are not rounding: each was a specific,
identified defect.

- **KAT, `t3`** — opencode: the query parser split `waehle name, ort` on
  whitespace and kept the comma glued to the column name. Oh My Pi: parses it
  correctly. (31/33 → 32/33)
- **AgentWorld, `t2`** — opencode: a second `STANDARD = Register()` in
  `__init__.py` shadowed the imported one, so the path the task names
  explicitly stayed empty forever while everything visible worked. Oh My Pi:
  one registry, correctly imported and filled. (14/17 → 17/17)
- **AgentWorld, `t3`** — opencode: three missing input-validation errors.
  Oh My Pi: all present. (30/33 → 33/33)

The price is consistent: **two to three times the wall clock.** Oh My Pi runs
more turns and more tool calls per task, and that extra work is where the
defects get caught. If you have the time budget, it buys real correctness; if
you don't, opencode gets you 97% of the score in a third of the time.

### The one failure, and why it is instructive

DeepSeek-V4-Flash scores 53/86 with Oh My Pi — but 15/15, 17/17 and 21/21 on
`t1`, `t2` and `t4`. The entire deficit is `t3`, which produced **zero files in
683 seconds**. The JSON event stream explains it exactly:

```
turn_end   stopReason: "length"
           usage.output: 16384        ← exactly the output cap
           content blocks: ['thinking']
           thinking length: 60,371 characters
```

The model spent the whole turn planning the implementation in its head, hit the
16,384-token output cap mid-thought, and never emitted a single tool call. The
harness saw a turn with no action, ended it, and exited `0`.

**Why only `t3`:** the other three tasks ship a seed repository, so the obvious
first move is a `read` or `ls` — the model acts immediately and thinks in
smaller chunks afterwards. `t3` is pure specification with no file to anchor
on, so the model tries to work the whole design out up front.

This is not a harness bug and not really a model failure. It is an unlucky
interaction between a model that thinks at length, a task with nothing to act
on first, and **an output cap that thinking and acting draw from the same
pool.** Raising `maxTokens` to 32,768 would very likely fix it — and would also
destroy comparability with the opencode runs, so the number stands as measured.

A harness could defend against this: if a turn ends with `stopReason: "length"`
and produced no tool call, retry with a nudge to act rather than treating it as
a finished turn.

### Testing that theory: a fourth harness, written to check one claim

The paragraph above is a hypothesis, and hypotheses in this space are cheap.
So it got built: a minimal agent harness in Java 21, no dependencies —
[**jaja**](https://github.com/DG1001/jaja), source and tests included. It was
built to check one thing — whether the `t3` failure is a harness behaviour or a
model limit — and later reused for a second question about Nemotron. It is
deliberately not competitive with the tools it is measured against.

**DeepSeek-V4-Flash:**

| Task | Java harness | opencode | Oh My Pi | Claude Code |
|---|---|---|---|---|
| t1-debug (15) | 15 · 509 s | 15 · **283 s** | 15 · 575 s | 15 · 1508 s |
| t2-refactor (17) | 17 · **197 s** | 17 · 213 s | 17 · 581 s | — |
| t3-neubau (33) | **33** · 1122 s | **33** · **564 s** | **0** · 1014 s | — |
| t4-feature (21) | 21 · 563 s | 21 · **489 s** | 21 · 866 s | — |
| **Total** | **86 / 86** · 40 min | **86 / 86** · **27 min** | 53 / 86 · 51 min | — |

**Laguna-S-2.1**, run afterwards to check the result was not specific to one
model:

| Task | Java harness | opencode | Oh My Pi | Claude Code |
|---|---|---|---|---|
| t1-debug (15) | 15 · 215 s | 15 · **152 s** | 15 · 526 s | **9** · 984 s |
| t2-refactor (17) | 17 · 304 s | 17 · **266 s** | 17 · 453 s | **0** · 893 s |
| t3-neubau (33) | 33 · 1400 s | 33 · **973 s** | 33 · 1180 s | **0** · 3433 s |
| t4-feature (21) | 21 · **314 s** | 21 · 465 s | 21 · 576 s | **0** · 1821 s |
| **Total** | **86 / 86** · 37 min | **86 / 86** · **31 min** | **86 / 86** · 45 min | 9 / 86 · 1:58 h |

**The answer is that it was a harness behaviour.** The same model, on the same
task, with the same 65,536 / 16,384 limits, produces a complete and correct
implementation once the harness treats a `length` stop with no tool call as
something to retry rather than as a finished turn. Nothing about the model
changed.

Read the rest of those tables honestly, though: **matching opencode is the
ceiling here, not a win.** The Java harness scores exactly what opencode scores
and takes 20–47% longer to do it. A hand-written harness reaching parity says
more about how few moving parts an agent loop actually needs than about the
harness — and these four tasks are not hard enough to separate two harnesses
that both finish them.

The gap is not uniform, which is worth more than the totals. On Laguna's
`t4-feature` the Java harness is the fastest of the four (314 s against
opencode's 465 s); the entire deficit is `t3-neubau`, where Laguna took 60 tool
calls and worked in very small steps. Where a task rewards deliberation the
extra turns cost wall clock; where it rewards a direct edit they do not.

**Nemotron-3.5-Lightning**, added later for a different question — whether its
`t2` zero was [opencode's compaction](variance.md#nemotron-solved-it-then-threw-it-away).
Both runs at 131,072 / 32,768, so the harness is the only difference:

| Task | Java harness | opencode |
|---|---|---|
| t1-debug (15) | **15** · **156 s** | 14 · 269 s |
| t2-refactor (17) | 0 · **473 s** | 0 · 1341 s |
| t3-neubau (33) | **33** · 419 s | 32 · **316 s** |
| t4-feature (21) | 16 · 292 s | **17** · **263 s** |
| **Total** | **64 / 86** · **22:20** | 63 / 86 · 36:29 |

A third run followed, same harness and limits, with NVIDIA's DSpark draft model
on the server: **85 / 86 in 13:12**, with `t2-refactor` at 17/17. That result
belongs to [one run is not a
measurement](variance.md#one-run-is-not-a-measurement) rather than to this comparison — it
says more about run-to-run variance than about any harness.

One point apart on the total, and **every single task different underneath.**
The Java harness gains a point on `t1` (commercial rounding, which opencode's
run got wrong) and one on `t3`; it loses one on `t4`. Even the `t4` losses are
disjoint: under opencode, reservations did not survive a reload and old files
were not migrated; under the Java harness both work and the reservation logic
itself is wrong instead. Same model, same task, same five points lost — nothing
in common about *which* five.

That is the useful contrast with the Oh My Pi comparison above, where seven
recovered points traced to three named defects and the direction was consistent.
Here the differences cancel. **A one-point total gap across two harnesses is
noise, and the per-task movement underneath it shows how much noise a single run
can hide.** Every number in this repo is one run per pairing; this is what that
costs.

The wall clock inverts too: 22:20 against 36:29, the first time the Java harness
is faster rather than 20–47% slower. Almost all of it is `t2`, where opencode
burned 1341 s and the Java harness hit its turn limit after 473 s. Failing
faster is not a feature.

#### What the tool set is worth, measured

An earlier revision shipped only `read` and `bash`; the model had to do
everything else through the shell. Adding `write`, `edit`, `glob` and `grep`
changed two numbers in opposite directions:

| Task | read + bash | six tools |
|---|---|---|
| t3-neubau | 31 / 33 · 1293 s | **33 / 33** · **1122 s** |
| t1-debug | 15 / 15 · **319 s** | 15 / 15 · 509 s |

`t3` writes a lot of files, and dedicated tools both fixed the two missing
points and cut the wall clock. `t1` is a bug hunt across a handful of files,
where the longer tool list buys nothing and its prefill cost stays on the
bill — and on this hardware prefill is the expensive part. Tool sets are not
free, and "more tools" is not a direction, it is a trade against the task.

Actual usage across all four tasks: `bash` 23, `read` 22, `write` 16,
`edit` 15, `glob` 5, `grep` 1. Both search tools together account for 7% of
calls — on a four-task benchmark with small repositories, which is exactly the
setting where they should matter least.

Two implementation notes that cost real debugging time, both invisible in
normal operation:

- **A timeout that never fires.** Reading a subprocess's output with
  `readAllBytes()` *before* `waitFor(timeout)` blocks in the read, so the
  timeout is dead code. Everything works until the first command that hangs,
  and then the run stops forever. Fixed by reading on a separate virtual
  thread, concurrently with the wait.
- **Java's `PathMatcher` and `**/`.** The glob `**/*.py` requires at least one
  directory level, so it does not match `main.py` in the project root. Models
  write that pattern constantly and mean "all of them". Without a fallback that
  also tries the pattern with the `**/` stripped, a model silently fails to see
  the main file of a flat project.

### No translation proxy needed

Every guide says to put LiteLLM or claude-code-router between Claude Code and
a local model. On this setup that is unnecessary — **both servers speak the
Anthropic Messages API natively**:

- vLLM ships an `anthropic` entrypoint (`/v1/messages`,
  `/v1/messages/count_tokens`) — present in the 0.26.0 image
- `ds4-server` implements it too, returning proper content blocks,
  `stop_reason`, and `usage`

Point `ANTHROPIC_BASE_URL` at the local port and it works. See
[`tools/cc-local`](../tools/cc-local).

### Three configuration traps, none of them documented

Each cost a failed run. All three fail *mid-task*, not at startup.

**1. `--default-chat-template-kwargs '{"enable_thinking": false}'` — set it
server-side.** The Anthropic Messages API has no `chat_template_kwargs` field,
so an Anthropic-protocol client cannot send it. Without the server-side
default, a reasoning model's chain of thought lands in the answer text along
with an orphaned `</think>`:

```
"content": [{"type": "text", "text": "</think>Ok."}]
```

Request-level values still take precedence, so an OpenAI-protocol client that
sets it per request (like opencode) is unaffected.

**2. `CLAUDE_CODE_MAX_OUTPUT_TOKENS` — the default is 32,000.** On a
65,536-context model that leaves 33,536 for input, and once the conversation
grows past it *every* request fails:

```
HTTP 500: you requested 32000 output tokens and your prompt contains
at least 33537 input tokens, for a total of at least 65537 tokens
```

**3. `CLAUDE_CODE_MAX_CONTEXT_TOKENS` must be the usable *input* budget, not
the context window.** Auto-compaction does not subtract the output
reservation — it fills input up to the number you give it and adds
`max_output` on top. Give it `context − max_output`.

Getting all three right still was not enough: it then hit the compaction
thrashing above.

## A fifth harness: DeepSeek Harness, and a server that refused

[DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) appeared on
13 August 2026 — MIT, plugin-first, everything from the inference layer to the
agent loop declared as a replaceable component. Its `headless` profile answers
one task and exits, which is exactly the shape this bench needs, so
[`bench/run-dsh.sh`](../bench/run-dsh.sh) is `bench/run.sh` with `dsh --profile
headless` in place of `opencode run`: same four tasks, same hidden suites, same
86 points.

Two setup traps, both silent:

- The default model is `deepseek-official/deepseek-v4-flash`, and it asks for a
  key to the remote service. A local endpoint needs a custom provider **and**
  an `agent-default-model` override in `$DSH_HOME/settings.yaml`.
- `pnpm dsh` resolves only from inside the repository. Running against a task
  directory elsewhere needs the built `apps/cli/lib/bin.js` directly.

Four models, one run each ([dsh-measurements.json](../results/dsh-measurements.json)):

| Model | t1 (15) | t2 (17) | t3 (33) | t4 (21) | Total | Wall clock |
|---|---|---|---|---|---|---|
| DeepSeek-V4-Flash | 15 | 17 | 33 | 21 | **86 / 86** | 54:00 |
| Qwen3.6-35B-A3B (NVFP4) | 12 | 17 | 31 | 19 | 79 / 86 | 35:00 |
| Qwen3.8-27B | 15 | 17 | 32 | 14 | 78 / 86 | 47:00 |
| Nemotron-3.5-Lightning | 15 | 17 | 0 | 14 | 46 / 86 | 22:00 |

Against the other harnesses, same models:

| Model | opencode | Java harness | DeepSeek Harness |
|---|---|---|---|
| DeepSeek-V4-Flash | 86 | 86 | **86** |
| Qwen3.6-35B-A3B (NVFP4) | 86 | 64 / 67 | 79 |
| Qwen3.8-27B | 86 | 86 | 78 |
| Nemotron-3.5-Lightning | 63 | 64 (85 with DSpark) | 46 |

DeepSeek-V4-Flash is the only model here that reaches 86/86 under all three,
and it pays for it: 54 minutes against Qwen3.6's 35 for seven points fewer.
Nemotron's `t3-neubau` is its familiar failure — files written, nothing
importable, 28 log lines and a stop on the largest task.

One column is missing rather than empty. The headless profile prints the final
assistant message and no transcript, so there is nothing to count tool calls
from. A zero there would mean "not measured".

### The two runs that had to be thrown away

The DeepSeek-V4-Flash run took three attempts, and the two discarded ones are
worth more than the number they produced.

`ds4-server` v0.5.4 refused requests mid-run:

```
serial right-size: no graph fits (prompt=36552 need_min=37576
                                  boot -c 65536); refusing 503
```

The first diagnosis — memory exhausted, 117 of 121 GB in use — was wrong, and
the second attempt disproved it: with the window cut to 49,152 the server
refused a **13,973-token** request. Far inside the window. The size was never
the problem; the server sized the graph for session-less requests by estimate
and refused when the estimate did not fit.

Updating to v0.6.2 removed the refusals entirely — it measures the graph rather
than estimating it (`serial graph estimate reconcile: est=4604.2 MiB
measured=4178.3 MiB drift=-9.2% (lease basis = measured)`) and allocates the
session graph lazily. Four tasks, four exit codes of zero, no refusals, 86/86.

The part worth keeping: **both discarded attempts scored exactly 65/86 with
completely different distributions** — 12/33 and 21/21 in one, 33/33 and 0/21
in the other, depending only on when the refusal landed. Two identical totals,
neither of them a model result. A benchmark that reports one number per model
would have published that twice without a flicker.

## Two models of the same build, twenty points apart — in one harness

Ornith-1.5-35B-A3B arrived on 19 August 2026: MIT, Qwen3.5-MoE architecture,
35B total and 3B active, 23 GB at NVFP4. That is Qwen3.6-35B-A3B (NVFP4) to
the gigabyte, and the throughput agrees — 78.4 against 78.3 tok/s generating,
58.9 against 57.9 end-to-end. Same size, same shape, same speed, different
training. There is no cleaner like-for-like pair in this collection.

They do not behave the same.

| | opencode | Java harness |
|---|---|---|
| Qwen3.6-35B-A3B (NVFP4) | 86 / 86 | 64, 67 |
| Ornith-1.5-35B-A3B (NVFP4) | 69, 86 | **85 / 86** |

Under opencode the two are indistinguishable at their best. Under the Java
harness they are twenty points apart, and the harness has not changed between
the two rows — the model has. Whatever the Java harness asks of a model that
opencode does not, Ornith supplies it and Qwen3.6 does not.

That sharpens the claim this page has been making. "The loop decides whether
you get what the model can do" is true, and here is its mirror image: **which
loop you measure decides which model looks better.** A benchmark that fixes
one harness and ranks models is measuring the pair, not the model. Both rows
above are real, and they disagree about which model to pick.

Ornith also finishes in 28 minutes where opencode takes 69, and it does so
while hitting the 80-turn limit on two tasks — with the work already done.
`t4-feature` scored 21/21 despite being cut off mid-run.

### The 69 that was not a result

Ornith's first opencode run scored 69/86, and the whole gap sat in
`t2-refactor`:

```
ImportError: cannot import name 'eintragen' from 'wandler.basis'
```

The `Register` class was there, built correctly, and the model's own tests
passed with sixteen green. But the rewrite had dropped one function that the
hidden suite imports, so collection failed and a solved task scored zero. The
second run scored 17/17 on the same task in 150 seconds.

Seventeen points on one missing line, with nothing systematic behind it. If
this repo published one run per model — as its own summary table does — Ornith
would sit at 69 and the like-for-like comparison above would never have been
noticed.
