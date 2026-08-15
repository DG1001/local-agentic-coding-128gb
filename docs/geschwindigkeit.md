---
title: Speed on this machine
nav_order: 2
description: Bandwidth, the throughput method, what quantization and speculative decoding are worth.
---

[← Uebersicht](index.md)

## The headline: bandwidth, not compute

A dense model must stream **every** weight through the memory bus for **every**
token. Qwen3.6-27B is 51.1 GiB of weights in BF16, so:

```
273 GB/s ÷ 51.1 GiB ≈ 5.3 tokens/s   theoretical ceiling
                       4.4 tokens/s   measured
```

vLLM is extracting about 84% of what the hardware physically allows. That
number matters more than the 4.5 itself: **there is no software fix here.**
If the runtime were the problem you would see a gap of several ×, not 15%.

Two more observations point the same way:

- During the dense run the GPU sat at **96% utilization drawing 43.6 W**. The
  compute units were busy waiting on memory, not computing. Compute-bound work
  at that utilization would pull many times the power.
- Laguna activates only 8.5B of its 117B parameters per token. Same machine,
  same vLLM build, **18.6 tokens/s** — four times faster than the dense model
  while being nearly twice as large on disk.

**On this class of hardware, pick models by *active* parameters, not by file
size.** A 93 GB MoE beats a 52 GB dense model by 4× on throughput.

### Raw generation speed

Everything below was re-measured in one sitting, one method for all models,
after the original per-model figures turned out to have been collected
inconsistently — see [the correction](#correction-the-old-speed-column-mixed-two-measurements).

| Model | Active params/token | Precision | Generation | End-to-end |
|---|---|---|---|---|
| Nemotron-3.5-Lightning + **DSpark** | 3B | NVFP4 | **121.4** | **91.1** |
| Nemotron-3.5-Lightning-30B-A3B | 3B | NVFP4 | 78.7 | 61.0 |
| Qwen3.6-35B-A3B | 3B | FP8 | 50.0 | 40.2 |
| Qwen-AgentWorld-35B | 3B | BF16 | 30.9 | 26.2 |
| KAT-Coder-V2.5 | ~3B | BF16 | 30.8 | 25.9 |
| DeepSeek-V4-Flash | 8.5B | GGUF Q4-class | 29.0 | 16.5 |
| Laguna-S-2.1 | 8.5B | NVFP4 | 18.6 | 19.5 |
| Qwen3.6-27B | 27B (all) | BF16 | 4.4 | 4.1 |

**Generation** is a one-sentence prompt, 800 output tokens, temperature 0, mean
of two runs. **End-to-end** is ~16,850 input tokens and 800 output tokens,
timed wall-to-wall so prefill counts — the number that matters for an agent
carrying a conversation. Two short requests are discarded after every server
start; without that warm-up the first measurement pays CUDA graph capture and
JIT (Nemotron reads 62.8 instead of 78.7). Raw data:
[`results/throughput.json`](../results/throughput.json).

Three things fall out of it.

**Quantization is a throughput knob.** Rows 2–5 all activate ~3B parameters and
differ only in bytes per weight: NVFP4 78.7, FP8 50.0, BF16 30.8. Same
architecture class, same machine, same vLLM build. On a bandwidth-bound box the
precision of the weights moves throughput as much as the model choice does.

**KAT and AgentWorld are the same speed** — 30.8 and 30.9. Both are 65 GB BF16
MoEs with ~3B active on the same hardware, so the bandwidth argument in this
README *requires* them to be. The old table had them at 30.4 and 22.9, a third
apart, contradicting the repo's own thesis. Nobody noticed, this author
included.

**DeepSeek falls furthest under context.** 29.0 generating, 16.5 end-to-end — a
1.76× drop, against 1.29× for Nemotron, 1.19× for KAT and 1.07× for the dense
27B. Pushing 88 GB of weights through prefill on the llama.cpp-derived server is
expensive, and an agent re-sends its whole transcript every turn. Yet DeepSeek
won the benchmark on wall clock (25:49 for 86/86). Both are true because it
needs far fewer tokens to get there — which is the whole argument of [the
agentic multiplier](#the-agentic-multiplier) seen from the other side.

One caveat on the column itself: tokens are counted by each model's own
tokenizer. The identical filler text is 16,849 tokens for the Qwen family and
20,483 for Laguna, so tokens/s understates a model with a coarser tokenizer
doing the same work.

#### Speculative decoding is worth more than a bigger model

NVIDIA ships Nemotron with **DSpark**, a semi-autoregressive drafter that
proposes a block of candidate tokens per forward pass, and recommends it
specifically for DGX Spark. It is the single largest speed lever measured here:

| | Generation | End-to-end |
|---|---|---|
| Nemotron alone | 78.7 | 61.0 |
| Nemotron + DSpark | **121.4** | **91.1** |
| | 1.54× | 1.49× |

vLLM's own counters corroborate it — mean acceptance length 2.98 out of a
maximum 4, per-position acceptance 0.845 / 0.648 / 0.488, and an overall draft
acceptance rate climbing to 66%.

It helps **more on code than on prose** (1.55× vs 1.29× in a separate paired
measurement), which is the opposite of what we guessed: indentation, closing
brackets and repeated shapes like `def test_…` are exactly what a small drafter
predicts well. And it helps more still on agentic work, where generations are
short: a full benchmark run takes 13:12 with DSpark against 22:20 without, and
`t1-debug` alone 83 s against 156 s.

**It buys time and only time.** The DSpark run also scored 85/86 against 64/86
without — but speculative decoding preserves the target model's output
distribution, so it cannot make a model more correct. Those 21 points are
sampling variance, and finding them is what turned [one run is not a
measurement](streuung.md#one-run-is-not-a-measurement) from a caveat into the most
important paragraph in this README. Do not read the score difference as a
DSpark result.

This costs a newer runtime. **vLLM 0.26.0 cannot load the drafter at all** —
it does not know the `Qwen3DSparkModel` architecture and dies in the embedding
loader with `The size of tensor a (512) must match the size of tensor b (256)`.
The model card names `vllm/vllm-openai:v0.27.1`, and on that image it works
first try. The version by itself buys nothing (78.2 vs 78.7 tok/s without the
drafter); it is purely the price of admission.

#### Correction: the old speed column mixed two measurements

Earlier revisions of this README carried a single "tokens/s" column with per-model
figures collected at different times by different means. Re-measuring all of them
in one sitting showed the column was not comparable:

| Model | Published | Generation | End-to-end |
|---|---|---|---|
| Nemotron-3.5-Lightning | 56.3 | 78.7 | 61.0 |
| Qwen3.6-35B-A3B | 50.5 | 50.0 | 40.2 |
| KAT-Coder-V2.5 | 30.4 | 30.8 | 25.9 |
| Qwen-AgentWorld-35B | 22.9 | 30.9 | 26.2 |
| Qwen3.6-27B | 4.5 | 4.4 | 4.1 |

Nemotron's 56.3 was an end-to-end figure with a ~20,000-token context —
re-measuring that configuration reproduces it at 56.5. Qwen3.6-35B-A3B's 50.5
was a generation figure. **Both were correct and neither was wrong; they were
printed in the same column one row apart**, which made the faster model look
slower. AgentWorld's 22.9 does not reproduce under either method.

Nothing about the benchmark results changes — those were always wall-clock
measurements of complete runs. What changes is the speed table, which now states
its method and reports both numbers.

The lesson is not about tokens per second. **A number is only comparable to
another number if you can say how both were produced**, and "we measured it at
the time" is not an answer. Every figure in this repo that survives is one where
the method is written down next to it.

### The agentic multiplier

Raw throughput understates the difference in practice. Between Qwen3.6-27B and
KAT the token rate differs by 7× (4.4 vs 30.8 tok/s). On an actual task the
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
