---
title: One run is not a measurement
nav_order: 3
description: Thirteen runs of one model span more than seven different models do.
---

[← Overview](index.md)

## Nemotron: solved it, then threw it away

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
thrashing](harness.md#the-harness-matters-as-much-as-the-model) below, and it points at
the same missing property: **compaction must preserve what has already been
achieved, not just what was asked.** A summary that
carries the goal but drops the completion state turns a finished agent into one
that starts over. Nemotron is a heavy reasoner, which is why it hit the limit at
all — at 65,536 context the same task compacted too, and there the model
responded by asking the user what to do next and stopping.

### The obvious next question, and the answer we did not expect

An earlier version of this section ended here, with the claim that the 0/17 was
"a harness result, not a model result" and said nothing about Nemotron's ability
to refactor Python. That claim was cheap to test and it did not survive.

The same model ran the same four tasks again through the Java harness described
[below](harness.md#testing-that-theory-a-fourth-harness-written-to-check-one-claim) — same
131,072-token window, same 32,768-token output cap, but a harness that **elides**
old tool results instead of summarizing the conversation. There is no compaction
step to lose state in.

`t2-refactor` came out **0 / 17 again.** Not from compaction — from a circular
import between `wandler/__init__.py` and `wandler/basis.py` that the model spent
all 80 turns failing to repair:

```
ImportError: cannot import name 'MITGELIEFERT' from partially initialized
module 'wandler.basis' (most likely due to a circular import)
```

It hit the turn limit at **52,183 of 96,304 usable tokens — 46% of the window
still free.** 63 of its 86 tool calls were `bash`, most of them one-liners
checking whether the last edit had helped. It never got as far as the working
solution the opencode run had already produced.

So the honest reading is the uncomfortable one:

- **What is true:** opencode's compaction destroyed a complete, verified
  solution. The `git checkout -- .` is in the log, and the summary that caused
  it was a generic template about media attachments that did not apply.
- **What is not true:** that the compaction is *why* the score is zero. Given a
  harness that never compacts, more turns and half the context unused, the model
  fails the same task by a different route.

Two runs, two roads into the same unimportable package. A model that solves a
task once and then loops on a circular import when asked again is unreliable on
that task — not merely unlucky in one harness.

### One run is not a measurement

A third run settled it, and not in the direction either earlier explanation
predicted. Same model, same harness, same 131,072 / 32,768 limits, the only
change being NVIDIA's DSpark draft model on the server side:

| Run | Harness | Speculative decoding | t2-refactor | Total | Wall clock |
|---|---|---|---|---|---|
| 1 | opencode | no | 0 / 17 · 1341 s | 63 / 86 | 36:29 |
| 2 | Java harness | no | 0 / 17 · 473 s (turn limit) | 64 / 86 | 22:20 |
| 3 | Java harness | **DSpark** | **17 / 17** · 144 s | **85 / 86** | **13:12** |

`t2-refactor` went from zero to full marks, finishing cleanly in 43 turns with
`STANDARD` in `wandler/einheiten.py` exactly as specified.

**Speculative decoding cannot explain that.** It preserves the target model's
output distribution — it makes a model faster, not better. It accounts for the
1.69× wall-clock gain, which matches the 1.54× measured on raw throughput. The
21 extra points are sampling luck.

So all three explanations offered for this cell were wrong in turn:

1. *"Compaction destroyed it."* True as an event, false as the cause — run 2
   never compacted and still scored zero.
2. *"The model is unreliable on this task."* Closer, but it was stated as a
   property of the model when it is a property of a **single sample**.
3. *"63/86 is Nemotron's score."* There is no such number. Three runs gave
   63, 64 and 85.

**The spread is 22 points — 26% of the total, and wider than the distance from
first to last place in the summary table.** Every other entry in that table is
one run. Nothing in this repo can distinguish 86/86 from 80/86; the only
defensible reading is a two-way split between models that solve this class of
task and models that do not.

### A second model, and it does the same thing

Nemotron could have been peculiar. Qwen3.6-35B-A3B in NVFP4 was then run twice,
back to back, same harness, same server, nothing changed between them:

| | run 1 | run 2 |
|---|---|---|
| t1-debug | 15/15 | 15/15 |
| t2-refactor | **16/17** | **0/17** |
| t3-neubau | 33/33 | 33/33 |
| t4-feature | *0/21 — harness gap, see below* | 19/21 |
| **Total** | 64/86 | 67/86 |

`t2-refactor` swung the full width of the task between two consecutive runs of
the same binary. Run 2 placed `STANDARD` in `__init__.py` instead of
`einheiten.py` — a different wrong address than the FP8 build of the same model
chose, which is a fifth variation on [one path in one
task](benchmark.md#three-ways-to-fail-the-same-task).

#### The harness gap in run 1

`t4-feature` in run 1 reads 0/21 in one second. That is not a model result:

```
[harness] Zug 1: STOP, 0 Werkzeug(e), 2014/96304 Token
[harness] FERTIG nach 1 Zuegen, 0 Werkzeugaufrufen, 0 s
[harness] Token: 2014 Eingabe, 4 Ausgabe
[README]
```

The model answered with four tokens, called no tool, and the harness accepted
that as a finished run — exit code 0, untouched directory. The existing defence
only fires when the output limit is hit; this was a clean `STOP`.

It happened **twice in about sixty task runs** — the other case scored 9/15 on
an untouched seed and sits inside the Abgleich series below, depressing one
round by roughly six points. jaja now nudges once when a run would end without
having called a single tool, and accepts the answer if the model insists.

Read run 1 as **64 of 65 attempted points**. And note what this means for every
other number in this repo: a harness gap that swallows a whole task looks
exactly like a bad model.

### Does asking the model to re-read the task help?

The most promising idea to come out of the failures above was to stop accepting
the model's own "done": before finishing, walk the task statement sentence by
sentence and say, for each requirement, whether it is met and where. Ten runs,
five with and five without, alternating:

| Round | without | with |
|---|---|---|
| 1 | 79 | 81 |
| 2 | 71 | 81 |
| 3 | 80 | 47 |
| 4 | 73 | 79 |
| 5 | 63 | 75 |
| **mean** | **73.2 ± 3.1** | **72.6 ± 6.5** |

Paired, the difference is −0.6 points at t = −0.07 on four degrees of freedom.
Nothing.

**But the series could not have found an effect, and that is the more useful
result.** 17 of 40 task runs hit the 80-turn limit; not one of the ten runs
finished all four tasks inside it. The binding constraint was the turn budget,
not the mechanism — and the check itself spends turns from that same budget, so
the arm being tested was handed a handicap. A rerun with a limit that does not
bind is the obvious next step and has not been done.

Two things worth keeping from it anyway: the loop detector fired **once in 40
runs**, so its threshold of six consecutive failures is not trigger-happy. And
much of what looked like model variance in these runs is **censoring** — the
same task ends at 29/33 or 14/33 depending on where 80 turns happened to cut
it, which is not the model being random.

That limitation was stated from the first revision and treated as boilerplate,
including by the person writing it. It is now measured, and it is larger than
the effects the table was being used to discuss. Re-running all seven models
several times each would cost six to eight hours of machine time and is the
obvious next step; until someone does it, treat every ranking here as a
two-bucket sort.

#### What this does not undermine

Not everything in this repo is one sample of a noisy variable:

- **The bandwidth arithmetic.** 4.4 tok/s measured against a 5.3 tok/s ceiling
  is a hardware property, reproducible on demand, and it does not vary by run.
- **The throughput table**, re-measured in one sitting with a stated method.
- **Named defects.** "KAT's parser keeps the comma attached to the column name"
  is a fact about an artifact you can open and read, not a score. The same holds
  for the three `t2` import failures and for opencode's `git checkout -- .`.
- **Claude Code's 9/86.** Four tasks that all died with the same compaction
  error, one of them starting from an empty directory, is a mechanism, not a
  draw from a distribution.

The rule that separates them: **a number needs repetition, a mechanism needs
evidence.** This repo has plenty of the second and almost none of the first.

## Outside the benchmark: a research task, three identical runs

Everything above is coding. The same question was put to an agent doing
research instead — Hermes Agent with Nemotron-3.5-Lightning, told to search the
web for AI and agentic-coding news plus new open-weight models and build an
HTML page from it. Same wording, same harness, same local SearXNG, three runs,
nothing changed between them.

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| words | 65 | 718 | 530 |
| links | 0 | 1 | 14 (13 domains, 10 resolving) |
| seconds | 117 | 126 | 63 |
| searches / extracts | 8 / 3 | 5 / 3 | 6 / 0 |

Run 1 produced a shell: navigation buttons, category headings, and the line
"use the navigation buttons above to switch between categories" — with nothing
under them. It had searched *more* than the others and written the least. Run 3
produced the best-sourced page of the day, better than the same model without
speculative decoding (5 links) and better than Ornith on the same task, which
wrote 1069 words and cited nothing.

**The spread within one configuration is larger than any difference measured
between configurations.** That is the same lesson as Nemotron's 47–85 across
thirteen benchmark runs, but sharper: a coding task has a hidden suite that
says 0/33 or 33/33, so at least the failure is legible. A research page that
looks plausible and contains no verifiable claim fails quietly.

It also disposed of a hypothesis. The first DSpark run looked like evidence
that speculative decoding degrades agent behaviour — a 65-word husk against 415
words without it. Two repeats removed the case: the mechanism worked throughout
(2,307 drafts, 66 % of draft tokens accepted), and the outlier was an outlier.
By the same token the 64 → 85 jump DSpark showed in the benchmark should be
read as one run, not as an effect.
