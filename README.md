# Local agentic coding on 128 GB unified memory

Five large models, four realistic coding tasks, 86 hidden tests each, one
ASUS Ascent GX10 (NVIDIA GB10, 128 GB unified memory). Everything ran locally
through [opencode](https://opencode.ai) against an OpenAI-compatible endpoint
on `127.0.0.1`.

This is the big-memory counterpart to
[local-agentic-coding-24gb](https://github.com/DG1001/local-agentic-coding-24gb),
which looked at seven small models on a 24 GB MacBook. The conclusions are
almost disjoint. On 24 GB the limiting factor was tooling — inference engines
breaking chat templates, KV cache blowing past the budget, system prompt size
pushing models off a cliff. On 128 GB almost none of that mattered: with
131,072-token context windows and millions of tokens of KV cache to spare, no
model here ran out of room, and four of the five got at least 84 of 86 tests
right.

What limits you here is **memory bandwidth**, and it decides which models are
worth running at all.

## The short version

| Model | Type | Weights | Hidden tests | Wall clock | Tool calls | Own tests written |
|---|---|---|---|---|---|---|
| **DeepSeek-V4-Flash** | MoE | 88 GB | **86 / 86** | **25:49** | 11 | 73 |
| **Laguna-S-2.1** | MoE | 93 GB | **86 / 86** | 30:56 | 23 | 111 |
| **Qwen3.6-27B** | dense | 52 GB | **86 / 86** | **3:07:36** | 18 | 118 |
| KAT-Coder-V2.5-Dev | MoE | 65 GB | 84 / 86 | 25:59 | 23 | 79 |
| Qwen-AgentWorld-35B-A3B | MoE | 65 GB | 80 / 86 | 41:34 | 21 | 66 |

Three models scored perfectly. The interesting column is wall clock: the dense
27B needed **7.3× longer than DeepSeek** for the exact same result. That gap is
not a software problem and it is not tunable. See below.

## Hardware

- ASUS Ascent GX10 — NVIDIA GB10, 128 GB unified LPDDR5X (121 GiB usable),
  arm64, Ubuntu 24.04.4
- ~273 GB/s memory bandwidth (vendor spec, not measured here)
- vLLM 0.26.0 in Docker for four models; `ds4-server` (llama.cpp-derived,
  from [DeepSeek-v4-Flash-One-DGX-Spark](https://github.com/MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark))
  for DeepSeek
- opencode 1.18.14 as the agent harness

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

| Model | Active params/token | tokens/s |
|---|---|---|
| KAT-Coder-V2.5 | ~3B | 30.4 |
| Qwen-AgentWorld-35B | 3B | 22.9 |
| Laguna-S-2.1 | 8.5B | 18–24 |
| Qwen3.6-27B | 27B (all) | 4.5 |

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
  or `sitecustomize.py` appeared that could bend the grading. All five runs
  were clean.

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

Raw data: [`results/measurements.json`](results/measurements.json),
per-model timelines under [`results/logs/`](results/logs/).

### The tasks that separated nothing

`t1-debug` and `t4-feature` were solved completely by **all five** models. As
discriminators they are worthless — every point of difference came from
`t2-refactor` and `t3-neubau`. If you build on this harness, keep those two and
replace the others with something harder.

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
task names explicitly, stayed empty forever.

The pattern in both: **the model wrote tests for what it built, not for what
was asked.** DeepSeek showed the same failure mode in an earlier pilot run,
where it silently skipped an entire numbered requirement and reported success
because its tests covered only the three it had implemented.

Practical consequence: *never accept "all tests pass" from a local model as
acceptance.* Check against the requirement list.

### Test volume does not predict correctness

Laguna wrote 111 tests, DeepSeek 73 — both perfect. AgentWorld wrote 66 and
lost six points, KAT wrote 79 and lost two. There is a weak correlation at
best. What mattered was *what* was tested, not how much.

### Self-verification

All four task descriptions explicitly asked the model to run `python -m pytest`
before finishing. Tool call counts per model, summed over four tasks:

| Model | Tool calls | Notes |
|---|---|---|
| Laguna | 23 | used tools in every task |
| KAT | 23 | used tools in every task |
| AgentWorld | 21 | used tools in every task |
| Qwen3.6-27B | 18 | |
| DeepSeek | 11 | **zero tool calls in t2 and t3** |

DeepSeek skipped the requested verification entirely on two tasks and was
correct anyway. At this difficulty that is harmless. On harder work it is
exactly where an unnoticed error would slip through.

## The harness matters as much as the model

Same model, same tasks, same hidden tests, same limits (65,536 context, 16,384
output) — only the agent harness differs. Laguna-S-2.1 throughout:

| Harness | Hidden tests | Wall clock |
|---|---|---|
| **opencode** | **86 / 86** | 30:56 |
| Claude Code | **9 / 86** | 1:58:51 |

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

**Load times differ wildly at equal size.** KAT and AgentWorld are both 65 GB.
AgentWorld loads in ~230 s, KAT in **655 s**. The difference tracks tensor
count — 31,333 vs 693 — not bytes. The loader pays per tensor.

## Limitations

Read the numbers with these in mind:

- **One run per model per task.** Language models vary between runs. The
  distance between 86 and 84 is well inside the noise; treat "these three solve
  this class of task reliably" as the finding, not the ranking.
- **The suite is too easy.** Three of five models scored perfectly. A benchmark
  where the top is crowded measures nothing at the top.
- **Four tasks, one language, one domain.** All Python, all small self-contained
  repos, all with fully specified signatures. Nothing here says anything about
  large unfamiliar codebases, other languages, or ambiguous requirements.
- **The 5090 section is arithmetic**, not measurement.
- **Quantization differs across models** (GGUF IQ2_XXS-based mixed for
  DeepSeek, NVFP4 for Laguna, BF16 for the three Qwen-family models). This is
  a comparison of *usable local setups*, not of model weights under equal
  conditions.
- **Bandwidth figure is vendor spec**, not independently measured.
- **The harness comparison is one model, one run.** Claude Code was tested
  against Laguna only, at 65K context. A third harness (Oh My Pi) is being
  measured separately and is not in the table yet.

## Layout

```
bench/
  run.sh                  runs all four tasks for one model, then grades
  run-claude-code.sh      same four tasks, Claude Code as the harness
  run-omp.sh              same four tasks, Oh My Pi as the harness
  tasks/<task>/
    task.md               the prompt handed to the agent, verbatim
    seed/                 starting repository (absent for t3-neubau)
    test_bench.py         hidden grading suite — never visible to the model
results/
  measurements.json       all numbers in this README, machine-readable
  logs/                   per-model timeline of each run
tools/
  model-switch            starts exactly one model, stops the others
  cc-local                launches Claude Code against a local model
configs/
  opencode.json           the five providers as configured
  omp-models.yml          the same models for Oh My Pi
```

Reproducing a run:

```bash
./tools/model-switch kat                    # or ds4 | laguna | agentworld | qwen27b
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
