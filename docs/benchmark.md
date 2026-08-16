---
title: The benchmark and what it found
nav_order: 4
description: Task design, per-task results, and the defects worth reading.
---

[← Overview](index.md)

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

Raw data: [`results/measurements.json`](../results/measurements.json),
per-model timelines under [`results/logs/`](../results/logs/).

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
| Nemotron-3.5-Lightning | had it right, verified it, then lost it to compaction — and failed the task again in a harness that never compacts | collection error | **0 / 17** |
| Qwen3.6-35B-A3B (NVFP4) | put it in **`__init__.py`** and nowhere else | 24 pass | **0 / 17** |

("Own tests" is that model's own suite for `t2` alone.)

The score spread between the first two rows is an artifact worth understanding
before you read any of these numbers as capability. AgentWorld's registry
*existed* at the named path and was merely empty, so the hidden suite imported
fine and failed three assertions. Qwen's registry does not exist at that path at
all, so `from wandler.einheiten import STANDARD` raises at **collection** time
and pytest reports zero of seventeen. Same class of mistake, one import line
apart, 14 points of difference.

Four models, four placements, one path. Three of them wrote a working,
importable, tested library — just not at the address the task gives. And the
fourth case is the sharpest: **the same model at the same quantisation scored
16/17 on one run and 0/17 on the next**, which means this is not even a stable
property of a model, let alone of a family.

That is the finding, and it is not about Python: **a requirement that names an
exact path is graded all-or-nothing by any import-time check.** If you grade
agent output with a test suite, one misplaced symbol can zero a task the model
otherwise solved. Both of these models produced working, tested, usable
libraries. Neither produced the library that was asked for.

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
