---
title: Running these models
nav_order: 6
description: vLLM flags and configuration traps that cost real debugging time.
---

[← Overview](index.md)

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

**Read the model card for the runtime version before blaming your config.**
Nemotron's DSpark draft model would not load under vLLM 0.26.0 — the embedding
loader dies with `RuntimeError: The size of tensor a (512) must match the size
of tensor b (256)` — and that looked like a broken checkpoint or a bad flag for
a while. It was neither: 0.26.0 does not know the `Qwen3DSparkModel`
architecture. The card names `vllm/vllm-openai:v0.27.1` in one line, and on that
image it works first try and is worth
[1.5× throughput](speed.md#speculative-decoding-is-worth-more-than-a-bigger-model).
`tools/model-switch nemotronspec` starts it.

**Load times differ wildly at equal size.** KAT and AgentWorld are both 65 GB.
AgentWorld loads in ~230 s, KAT in **655 s**. The difference tracks tensor
count — 31,333 vs 693 — not bytes. The loader pays per tensor.

## The engine wedges, and it looks like a slow model

Twice on this machine, both times after roughly 900–950 requests and shortly
after a client was killed mid-request, vLLM stopped answering:

```
/v1/models             answers
/metrics               answers — 1 request "running", 0 waiting, counters frozen
GPU                    96 %
/v1/chat/completions   times out, indefinitely
docker logs            not one error line
```

Nothing in that picture says "broken". A health check on `/v1/models` passes,
the GPU looks busy, the logs look clean. What actually happens is that the run
you started is talking to a corpse, and you find out an hour later.

It cost a throughput measurement that read "28 minutes" when the engine had
been dead for 27 of them, and then a second one before the pattern was
recognised. The published `end_to_end` numbers were re-measured after a
restart; nothing in `results/` comes from a wedged engine.

This is a known, open vLLM problem —
[#50880](https://github.com/vllm-project/vllm/issues/50880) matches the
signature exactly, down to metrics staying responsive while the EngineCore
thread remains runnable, and maintainers have narrowed it to the
`execute_model` / model-forward path without finding a cause.
[#32262](https://github.com/vllm-project/vllm/issues/32262) is the same shape
on different hardware. Both open, no fix, no version to upgrade to. Disabling
MTP, prefix caching and chunked prefill changed nothing for the reporters;
`--enforce-eager` avoided it and is too expensive to run that way.

So the runners here do not try to prevent it. They try to notice it:
[`bench/bereit.sh`](../bench/bereit.sh) sends a four-token request with a
30-second ceiling before every task, restarts the container once if it times
out, and marks the task `rc=99, "Motor haengt"` if the engine does not come
back. A failure should look like a failure, not like a model that scores zero.

When the engine is healthy the check costs nothing measurable — it returns in
under a second. That is the whole argument for running it before every task
rather than once per run: the wedge does not wait for a convenient moment.

**The tell, if you are watching:** GPU utilisation pinned high while
`vllm:num_requests_running` sits still. On a unified-memory machine like the
GB10 there is no separate VRAM figure to sanity-check it against — NVML
reports `[N/A]` for GPU memory, because the 121 GB in the ordinary memory
display already is the whole story.
