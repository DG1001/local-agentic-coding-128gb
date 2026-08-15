# Local agentic coding on 128 GB unified memory (DGX Spark class)

Seven large local LLMs, four realistic coding tasks, 86 hidden tests each, one
ASUS Ascent GX10 — **NVIDIA GB10, 128 GB unified memory**, the same chip and
memory configuration as the NVIDIA DGX Spark. Everything ran locally through
[opencode](https://opencode.ai), [Claude Code](https://claude.com/claude-code)
and [Oh My Pi](https://github.com/can1357/oh-my-pi) against endpoints on
`127.0.0.1` — no cloud API, no per-token cost. A fourth, purpose-built harness
was added later to test one specific claim; see
[below](#testing-that-theory-a-fourth-harness-written-to-check-one-claim).

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
tests right. The two models added later scored markedly lower — and for reasons
worth reading, because neither is about capability.

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
| Nemotron-3.5-Lightning-30B-A3B | MoE | 21 GB | 63 / 86 | 36:29 | 220 | 54 |

Three models scored perfectly. The interesting column is wall clock: the dense
27B needed **7.3× longer than DeepSeek** for the exact same result. That gap is
not a software problem and it is not tunable. See below.

The bottom two rows are the later additions and they read worse than they are:
**each lost all 17 points of one task, and neither loss was a failure to solve
it.** Details in [three ways to fail the same
task](#three-ways-to-fail-the-same-task).

## Hardware

- ASUS Ascent GX10 — NVIDIA GB10, 128 GB unified LPDDR5X (121 GiB usable),
  arm64, Ubuntu 24.04.4
- ~273 GB/s memory bandwidth (vendor spec, not measured here)
- vLLM 0.26.0 in Docker for six models; `ds4-server` (llama.cpp-derived,
  from [DeepSeek-v4-Flash-One-DGX-Spark](https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark))
  for DeepSeek
- opencode 1.18.14, Claude Code 2.1.226 and Oh My Pi 17.2.12 as agent harnesses,
  plus a purpose-built Java harness for one follow-up question

Comparable hardware: the NVIDIA DGX Spark uses the same GB10 superchip and the
same 128 GB unified LPDDR5X, so the bandwidth findings below transfer directly.
Nothing here depends on the ASUS badge.

Only one model runs at a time — DeepSeek alone occupies ~113 GiB. The
[`tools/model-switch`](tools/model-switch) script in this repo stops whatever
is running before starting the next one.

## The headline: bandwidth, not compute

A dense model must stream **every** weight through the memory bus for **every**
token. Qwen3.6-27B is 51.1 GiB of weights in BF16, so:

```
273 GB/s ÷ 51.1 GiB ≈ 5.3 tokens/s   theoretical ceiling
                       4.5 tokens/s   measured
```

vLLM is extracting about 85% of what the hardware physically allows. That
number matters more than the 4.5 itself: **there is no software fix here.**
If the runtime were the problem you would see a gap of several ×, not 15%.

Two more observations point the same way:

- During the dense run the GPU sat at **96% utilization drawing 43.6 W**. The
  compute units were busy waiting on memory, not computing. Compute-bound work
  at that utilization would pull many times the power.
- Laguna activates only 8.5B of its 117B parameters per token. Same machine,
  same vLLM build, **18–24 tokens/s** — four times faster than the dense model
  while being nearly twice as large on disk.

**On this class of hardware, pick models by *active* parameters, not by file
size.** A 93 GB MoE beats a 52 GB dense model by 4× on throughput.

### Raw generation speed

| Model | Active params/token | Precision | tokens/s |
|---|---|---|---|
| Nemotron-3.5-Lightning-30B-A3B | 3B | NVFP4 | **56.3** |
| Qwen3.6-35B-A3B | 3B | FP8 | 50.5 |
| KAT-Coder-V2.5 | ~3B | BF16 | 30.4 |
| Qwen-AgentWorld-35B | 3B | BF16 | 22.9 |
| Laguna-S-2.1 | 8.5B | NVFP4 | 18–24 |
| Qwen3.6-27B | 27B (all) | BF16 | 4.5 |

The top four rows all activate ~3B parameters per token and differ only in how
many bytes each of those parameters costs to fetch. **The spread from 22.9 to
56.3 tok/s is quantization alone** — same architecture class, same machine, same
vLLM build. On a bandwidth-bound machine the precision of the weights is a
throughput knob of the same order as the model choice itself, and the two new
models are the fastest here because they are the only 3B-active models that
ship at 4 and 8 bits rather than 16.

### The agentic multiplier

Raw throughput understates the difference in practice. Between Qwen3.6-27B and
KAT the token rate differs by 7× (4.5 vs 30.4 tok/s). On an actual task the
wall clock differed by **20×** (1788 s vs 90 s for the same bug hunt).

The extra factor is model behaviour, not hardware: the slower model also needed
more tokens and more turns to reach the same answer. When you compare local
models, benchmark the task, not the token rate.

## What about a 5090?

Reasonable question, and the arithmetic is tempting: an RTX 5090 has ~1792 GB/s,
6.5× the GB10. A 4-bit quantized 27B would be ~14 GB, giving a theoretical
ceiling north of 100 tok/s — an entirely different experience from 4.5.

**But 32 GB is a hard wall.** DeepSeek-V4-Flash (88 GB) and Laguna (93 GB) do
not run on a 5090 at all, and those were two of the three models that scored
86/86 here. The GX10 spends its bandwidth budget buying capacity, and capacity
is what puts this model class on your desk.

So it is not "money for speed" — it is **speed for model class**. Also worth
weighing:

- **Power.** The 5090 alone is rated 575 W; a system around it pulls 700–800 W
  under load. The GX10's GPU drew 43.6 W during these runs, whole box likely
  around 100 W.
- **Not measured here.** Everything in this section is arithmetic, not
  benchmark data. And a 4-bit quant is *not the same model* as the BF16 one we
  measured — you cannot carry the 86/86 across.

## The benchmark

Four tasks, deliberately different in kind, because "extend this module" only
tests one skill. Each has a **hidden test suite the model never sees**. The
model's own claim of success is ignored; only the hidden suite counts.

| Task | Kind | Hidden tests | What it probes |
|---|---|---|---|
| `t1-debug` | Bug hunt | 15 | Four real bugs in a cash-book module, reported as *user complaints* with no pointer to the code. The five existing tests are green and catch none of them. |
| `t2-refactor` | Refactor | 17 | Convert a module-global registry into an injectable object while keeping the old module-level API working. Two requirements that pull against each other. |
| `t3-neubau` | Greenfield | 33 | Empty directory, spec only: a small query engine over tabular data with its own query language, numeric-vs-string comparison, stable sort, fixed evaluation order. |
| `t4-feature` | Cross-cutting | 21 | Add stock reservations through model, persistence, service and CLI — including keeping old on-disk JSON loadable. |

Design rules that turned out to matter:

- **Signatures are specified verbatim in the task.** Otherwise grading measures
  naming luck rather than capability.
- **Grading is external.** Copied in after the run, executed against the
  model's working tree.
- **The seed repos' own tests pass but are inadequate.** In `t1` all four bugs
  survive the existing suite. A model that trusts green tests fails.
- **Integrity check.** After each run we verify no `conftest.py`, `pytest.ini`
  or `sitecustomize.py` appeared that could bend the grading. All runs were
  clean.

### Why the tasks are in German

The seed repos, task descriptions and identifiers are German (`Eintrag`,
`aufteilen`, `wandle`, `Bestand`). This was not a stylistic choice — it is the
environment the tasks were written in, and translating them now would mean
publishing a harness that differs from the one that produced these numbers.

It has an incidental benefit worth naming: German identifiers make it much less
likely that a model has memorized an equivalent public repository. What you are
measuring is closer to actual capability and further from recall.

If you want to reuse the harness, `bench/run.sh` and the task layout are
language-agnostic — swap in your own `task.md` + `test_bench.py`.

## Results in detail

| Task | DeepSeek | Laguna | Qwen3.6-27B | KAT | AgentWorld |
|---|---|---|---|---|---|
| t1-debug (15) | 15 · 283 s | 15 · 152 s | 15 · 1788 s | 15 · **90 s** | 15 · 236 s |
| t2-refactor (17) | 17 · 213 s | 17 · 266 s | 17 · 3169 s | 17 · **168 s** | **14** · 349 s |
| t3-neubau (33) | 33 · **564 s** | 33 · 973 s | 33 · 2762 s | **31** · 954 s | **30** · 967 s |
| t4-feature (21) | 21 · 489 s | 21 · 465 s | 21 · 3537 s | 21 · **347 s** | 21 · 942 s |
| **Total** | **86 / 86** | **86 / 86** | **86 / 86** | 84 / 86 | 80 / 86 |

The two later additions, run identically (opencode, 131,072 context, one run
each) but months apart, so they are kept in their own table rather than folded
into the one above:

| Task | Qwen3.6-35B-A3B | Nemotron-3.5-Lightning |
|---|---|---|
| t1-debug (15) | 15 · 217 s | **14** · 269 s |
| t2-refactor (17) | **0** · 473 s | **0** · 1341 s |
| t3-neubau (33) | **32** · 1542 s | **32** · **316 s** |
| t4-feature (21) | 21 · 438 s | **17** · 263 s |
| **Total** | 68 / 86 · 44:30 | 63 / 86 · 36:29 |

Nemotron's `t3-neubau` is the fastest greenfield run of any model here — 316 s
against DeepSeek's 564 s and Qwen3.6-27B's 2762 s, for 32 of 33 points. Where
it is not fighting itself it is very fast.

Raw data: [`results/measurements.json`](results/measurements.json),
per-model timelines under [`results/logs/`](results/logs/).

### The tasks that separated nothing

`t1-debug` and `t4-feature` were solved completely by **all five** models of the
original round. As discriminators they were worthless — every point of
difference came from `t2-refactor` and `t3-neubau`.

That held until Nemotron, which lost a point on `t1` and four on `t4`. So the
honest version is weaker than the original claim: these two tasks separate
nothing *among models that are good enough*, and start separating again as soon
as one is not. `t1`'s single point is worth naming because it is a classic —
`runde_cent(Decimal("0.125"))` returned `0.12`, Python's default banker's
rounding, where the docstring says commercial half-up. Every other model caught
it.

### The two failures worth reading

Both losses came from the Qwen-family MoE models, and both are the kind of bug
that a self-written test suite structurally cannot catch.

**KAT-Coder, `t3`** — its query parser splits on whitespace and keeps the comma
attached, so `waehle name, ort` looks for a column literally named `name,`.
Only the no-space form works. That exact spacing appears in the example *in the
task description*, and KAT never used it in any of its 27 self-written tests.

**AgentWorld, `t2`** — it created `STANDARD = Register()` in `einheiten.py` as
specified, then created a *second* `STANDARD = Register()` in `__init__.py`
that shadowed the import. Everything visible worked: the CLI, the legacy
module functions, its own tests. But `wandler.einheiten.STANDARD`, the path the
task names explicitly, stayed empty forever. Two models added later missed the
same path in two further ways — see [three ways to fail the same
task](#three-ways-to-fail-the-same-task).

The pattern in both: **the model wrote tests for what it built, not for what
was asked.** DeepSeek showed the same failure mode in an earlier pilot run,
where it silently skipped an entire numbered requirement and reported success
because its tests covered only the three it had implemented.

Practical consequence: *never accept "all tests pass" from a local model as
acceptance.* Check against the requirement list.

### Three ways to fail the same task

`t2-refactor` names one path verbatim: the standard registry must be reachable
as `wandler.einheiten.STANDARD`. Three of the seven models put it somewhere
else, each in a different way, and each with a green self-written suite:

| Model | What it did | Own tests | Hidden |
|---|---|---|---|
| Qwen-AgentWorld-35B | correct object in `einheiten.py`, plus a **second** one in `__init__.py` that shadowed it | 12 pass | 14 / 17 |
| Qwen3.6-35B-A3B | put the object in **`basis.py`** and re-exported it from `__init__.py` | 21 pass | **0 / 17** |
| Nemotron-3.5-Lightning | had it right, verified it, then destroyed it (see below) | collection error | **0 / 17** |

("Own tests" is that model's own suite for `t2` alone.)

The score spread between the first two rows is an artifact worth understanding
before you read any of these numbers as capability. AgentWorld's registry
*existed* at the named path and was merely empty, so the hidden suite imported
fine and failed three assertions. Qwen's registry does not exist at that path at
all, so `from wandler.einheiten import STANDARD` raises at **collection** time
and pytest reports zero of seventeen. Same class of mistake, one import line
apart, 14 points of difference.

That is the finding, and it is not about Python: **a requirement that names an
exact path is graded all-or-nothing by any import-time check.** If you grade
agent output with a test suite, one misplaced symbol can zero a task the model
otherwise solved. Both of these models produced working, tested, usable
libraries. Neither produced the library that was asked for.

### Nemotron: solved it, then threw it away

Nemotron's `t2` is the most instructive run in this whole repo, because the
model was finished and correct partway through. Its own verification script
printed:

```
=== Two Independent Registers ===   r1 has einheit: True   r2 has einheit: False
=== kopie() ===                     kopie has same units: True
=== All tests passed! ===
```

and it summarized: *"All 17 tests pass (5 original + 12 new)."* Then the
conversation hit opencode's compaction, which injected this:

```
The previous request exceeded the provider's size limit due to large media
attachments. The conversation was compacted and media files were removed
from context. […]
Continue if you have next steps, or stop and ask for clarification.
```

There were no media attachments; the summary is a generic template. What the
model saw after compaction was a task description, no memory of having finished
it, and an instruction to continue. Its next tool call was:

```
$ git checkout -- .
```

It discarded a complete, verified solution and started over — then ran out of
turns mid-rebuild, leaving `wandler/__init__.py` calling an `_einheiten` name
that no longer existed. The package could not be imported at all. **0 / 17 for
a task it had solved 20 minutes earlier.**

This is the same failure class as [Claude Code's compaction
thrashing](#the-harness-matters-as-much-as-the-model) below, and it points at
the same missing property: **compaction must preserve what has already been
achieved, not just what was asked.** A summary that
carries the goal but drops the completion state turns a finished agent into one
that starts over. Nemotron is a heavy reasoner, which is why it hit the limit at
all — at 65,536 context the same task compacted too, and there the model
responded by asking the user what to do next and stopping.

Worth stating plainly: **this is a harness result, not a model result.** Nothing
in the 0/17 measures Nemotron's ability to refactor Python.

### Test volume does not predict correctness

Laguna wrote 111 tests, DeepSeek 73 — both perfect. AgentWorld wrote 66 and
lost six points, KAT wrote 79 and lost two. There is a weak correlation at
best. What mattered was *what* was tested, not how much.

Qwen3.6-35B-A3B settles it: **125 self-written tests, all passing, 68 / 86** —
more tests than any perfect model wrote, including 70 for the one task where it
still missed a point. Test count is not a signal.

### Self-verification

All four task descriptions explicitly asked the model to run `python -m pytest`
before finishing. Counted from the opencode logs, summed over four tasks:

| Model | pytest runs | Read/search calls | All tool calls |
|---|---|---|---|
| Nemotron-3.5-Lightning | 44 | 36 | 220 |
| KAT | 21 | 23 | 169 |
| AgentWorld | 15 | 21 | 120 |
| Qwen3.6-35B-A3B | 18 | 18 | 116 |
| Laguna | 6 | 23 | 76 |
| Qwen3.6-27B | 8 | 18 | 67 |
| DeepSeek | 5 | 11 | 57 |

**Every model ran pytest in every task.** Compliance with that instruction was
universal and tells you nothing.

> **Correction.** An earlier version of this table showed a single "tool calls"
> column with values 11–23 and concluded that DeepSeek "skipped the requested
> verification entirely" in `t2` and `t3`. That was wrong. The column counted
> only opencode's `→` lines — reads, lists, globs and greps — and not bash or
> file writes. DeepSeek's two zeros meant it read no files with the read tool in
> those tasks (it used `cat` through bash in `t2`, and `t3` starts from an empty
> directory with nothing to read); it ran pytest in both. The raw JSON now
> carries `read_search_calls`, `all_tool_calls` and `pytest_runs` separately.

What the corrected numbers do show is a 4× spread in how much work each model
does for the same result. DeepSeek reaches 86/86 in 57 tool calls; Nemotron
spends 220 for 63/86, 92 of them in the one task it destroyed and rebuilt. More
tool calls is not more diligence — it is usually a model that is lost.

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
[cost a model a solved task](#nemotron-solved-it-then-threw-it-away). The
difference is frequency, not kind: opencode's smaller footprint means it gets
there rarely, on the tasks where a model reasons at length.

### The surprise: the harness changes *correctness*, not just speed

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
[**jaja**](https://github.com/DG1001/jaja), source and tests included. It exists to check one thing —
whether the `t3` failure is a harness behaviour or a model limit — and it is
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
[`tools/cc-local`](tools/cc-local).

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

## Gotchas that cost real time

Things that were not obvious and are not in the docs:

**`--kv-cache-dtype fp8` is the highest-leverage flag on this machine.** For
Laguna it took KV cache capacity from 56,202 to **168,326 tokens** — 3× — at
unchanged speed (18.3 → 18.7 tok/s) and no visible quality loss. Before finding
it, the server was dying at startup with no useful message because
`--max-model-len 262144` (the model author's recommendation) left ~7 GiB for
cache after 95.93 GiB of weights. On any memory problem here, start with this
flag, not with a smaller model.

**Never start the container with `--rm`.** When it dies you lose exactly the
logs you need. Use `docker rm -f` beforehand instead.

**`--language-model-only` for text-only checkpoints in multimodal clothing.**
KAT-Coder and AgentWorld both declare `Qwen3_5MoeForConditionalGeneration` with
a `vision_config` but ship **zero** `visual.*` weights. AgentWorld's
`config.json` even says `language_model_only: True` — but vLLM 0.26.0 reads
that only from the CLI flag, not from the model config. Without it, vLLM builds
27 vision blocks and aborts with
`ValueError: Following weights were not initialized from checkpoint: {'visual.…'}`.

**vLLM's `Avg generation throughput` in the log is misleading.** It averages
over windows including idle time and will show ~1 tok/s while the model is
really doing 18–24.

**Slow weight loading is not the SSD.** 161 MB/s during load vs 2.3–2.6 GB/s
measured with `dd iflag=direct`. There is simply no page cache left, because
vLLM pre-allocated its pool first.

**`--gpu-memory-utilization` grabs its share whether needed or not.** At 0.85
that is ~103 GiB. For Qwen3.6-27B, which needs 51 GiB, the remainder became a
1.48M-token KV cache that no workload here could use — while the host swapped
4.5 GiB. Lower it per model when you need headroom.

**Nemotron's Mamba cache needs a bigger batch limit than vLLM's default.**
`--mamba-cache-mode align` asserts that the state block size (4176 here) fits
inside `max_num_batched_tokens`, whose default is 2048. The server aborts at
startup on an assertion, not a readable error. Pass
`--max-num-batched-tokens 8192`.

**vLLM 0.26.0 cannot load Nemotron's DSpark draft model.** NVIDIA recommends
speculative decoding with the paired DSpark checkpoint for single-Spark use, but
the embedding loader fails with `RuntimeError: The size of tensor a (512) must
match the size of tensor b (256)`. The main model loads cleanly. All Nemotron
numbers here are therefore *without* speculative decoding — 56.3 tok/s is the
floor, not the ceiling, for this model on this hardware.
[`tools/model-switch`](tools/model-switch) keeps the flag behind `SPEC=1`.

**Load times differ wildly at equal size.** KAT and AgentWorld are both 65 GB.
AgentWorld loads in ~230 s, KAT in **655 s**. The difference tracks tensor
count — 31,333 vs 693 — not bytes. The loader pays per tensor.

## Limitations

Read the numbers with these in mind:

- **One run per model per task.** Language models vary between runs. The
  distance between 86 and 84 is well inside the noise; treat "these three solve
  this class of task reliably" as the finding, not the ranking.
- **The suite is too easy at the top.** Three of seven models scored perfectly.
  A benchmark where the top is crowded measures nothing at the top. The two
  later models did produce spread — but almost all of it comes from one
  all-or-nothing import in one task, which is spread from grading mechanics, not
  from difficulty.
- **The two later models ran once, under opencode only.** Nemotron-3.5-Lightning
  and Qwen3.6-35B-A3B were added months after the original five, on the same
  tasks and the same 131,072-context configuration, but they have no Oh My Pi or
  Java-harness counterpart. Given that Nemotron's entire `t2` result is a
  compaction artifact, a second harness would very likely move its total — treat
  63 / 86 as a number about this pairing, not about the model.
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

## Layout

```
bench/
  run.sh                  runs all four tasks for one model, then grades
  run-claude-code.sh      same four tasks, Claude Code as the harness
  run-omp.sh              same four tasks, Oh My Pi as the harness
  run-java.sh             same four tasks, the purpose-built Java harness
                          (github.com/DG1001/jaja)
  tasks/<task>/
    task.md               the prompt handed to the agent, verbatim
    seed/                 starting repository (absent for t3-neubau)
    test_bench.py         hidden grading suite — never visible to the model
results/
  measurements.json       opencode runs, machine-readable
  omp-measurements.json   Oh My Pi runs, machine-readable
  java-measurements.json  purpose-built-harness run, machine-readable
  logs/                   per-model, per-harness timeline of each run
tools/
  model-switch            starts exactly one model, stops the others
  cc-local                launches Claude Code against a local model
configs/
  opencode.json           the seven providers as configured
  omp-models.yml          the models for Oh My Pi (the original five)
```

Reproducing a run:

```bash
./tools/model-switch kat   # ds4 | laguna | agentworld | qwen27b | nemotron | qwen36moe
./bench/run.sh kat kat/kat-coder-v2.5       # <label> <opencode provider/model>
```

Results land in `runs/<label>/`. Requires opencode, Docker, Python 3.12 and
the models on disk.

### One harness note

Long `opencode run` invocations must be detached with `setsid`, or a session
manager can reap them mid-flight and take the child process with it. Two early
runs died this way and looked like model failures until the logs said
otherwise. `run.sh` writes a completion file that an external watcher polls.

## License

MIT — see [LICENSE](LICENSE). The seed repositories and task descriptions are
part of this repo and under the same license; the models themselves are not,
and each carries its own terms.
