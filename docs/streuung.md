---
title: One run is not a measurement
nav_order: 3
description: Thirteen runs of one model span more than seven different models do.
---

[← Uebersicht](index.md)

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
