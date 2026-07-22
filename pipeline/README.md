# Meeting pipeline (local)

Turn an OBS recording of an online meeting into:

- `transcript.txt` / `.srt` — Danish speech-to-text (fixed: no more repetition loops)
- `transcript_clean.txt` / `.srt` — same transcript with obvious spelling/ASR errors auto-corrected (raw is kept)
- `keyframes/` + `visuals.md` — what was shown on screen (description + OCR)
- `referat.md` — a human-readable Danish referat (resumé, beslutninger, opgaver …)
- `meeting.json` — **everything in one machine-readable file**: metadata + full
  timestamped transcript + visual timeline + structured fields (deltagere,
  beslutninger, opgaver `{ansvarlig, opgave, deadline}`, opfølgning, åbne spørgsmål).
  This is the file to feed an AI.
- `report.html` — a self-contained visual report (referat + screenshot timeline + transcript).

Across meetings, `corpus.py` builds `output/corpus.jsonl` (compact per-meeting records
for AI planning) and `output/oversigt.md` (every opgave + beslutning aggregated).

Everything runs **locally**. Ollama can't transcribe audio, so speech uses
**faster-whisper** with the Danish `hviske-v2` model; the **vision** and
**summary** steps use Ollama with **Gemma3** (`gemma3:4b` fast, `gemma3:12b`
sharper — spreads across both GPUs).

## Pipeline

```
recording.mp4
  ├─ ffmpeg ─ audio.wav ─ faster-whisper (hviske-v2, VAD, CPU) ─ transcript.txt/.srt/segments.json
  │                                                           └─ gemma3 clean ─ transcript_clean.txt
  ├─ ffmpeg ─ keyframes (periodic + scene) ─ gemma3 (Ollama, GPU) ─ visuals.md/.json
  └─ transcript + visuals ─ gemma3 (Ollama) ─ meeting.json + referat.md + report.html
```

## Where each model runs (and why — this hardware is the constraint)

Two 6 GB GPUs: `cuda:0` = GTX 980 Ti (Maxwell), `cuda:1` = GTX 1060 (Pascal, shared
with the desktop). CUDA orders by capability, **not** by `nvidia-smi` slot.

| Stage | Model | Runs on | Notes |
|---|---|---|---|
| Transcribe | `hviske-v2` (large-v3, int8) | **CPU** | ~5× realtime, reliable |
| Describe | `gemma3:4b` | **GPU** | 4.4 GB, 100% offload, ~5 s/frame |
| Summarize | `gemma3:4b` | **GPU** | same model, text mode |

What we tried and rejected on these cards (measured, not guessed):

- **Whisper on GPU** — large-v3 is 1.55 B params: float32 ≈ 6.2 GB (won't fit 6 GB),
  and int8 OOMs on the desktop-shared 1060. CPU int8 is faster-than-realtime and
  frees both GPUs for Ollama, so that's the default. (`--whisper-device cuda` still
  tries GPU → falls back to CPU.)
- **`qwen2.5-vl` (3B/7B)** — its vision tower needs ~10 GB and can't be split across
  GPUs, so Ollama runs it 100% on CPU; partial `num_gpu` is rejected outright.
- **`qwen2.5:7b`** — **segfaults the CUDA runner on load** on these old GPUs.
- **Gemma3** works: light SigLIP vision that fits/splits (you already run `gemma3:27b`
  spread across both GPUs + CPU), and it's multimodal so one model does both jobs.

## One-time setup (already done, kept for reference)

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python faster-whisper ollama pillow tqdm \
                                         nvidia-cublas-cu12 nvidia-cudnn-cu12
ollama pull gemma3:4b          # fast vision + summary (~3.3 GB)
ollama pull gemma3:12b         # sharper vision + summary (~8 GB, spreads across both GPUs)
./convert_model.sh             # syvai/hviske-v2 -> models/hviske-v2-ct2 (int8)
```

## Run

```bash
# one meeting (full: audio + video + referat)
.venv/bin/python process_meeting.py "../recordings/2026-06-25 10-15-28.mp4"

# audio + referat only, skip the (slower) video description
.venv/bin/python process_meeting.py REC.mp4 --skip-video

# all recordings — resumable (skips done), rebuilds the corpus at the end
.venv/bin/python batch.py                     # gemma3:12b, beam 5 (accuracy)
.venv/bin/python batch.py --beam 1            # ~40% faster transcription
.venv/bin/python batch.py --vision-model gemma3:4b --text-model gemma3:4b   # faster, rougher
```

Output lands in `output/<recording-name>/`; cross-meeting files in `output/`
(`corpus.jsonl`, `oversigt.md`).

## Individual steps

```bash
.venv/bin/python transcribe.py audio.wav -o OUTDIR
.venv/bin/python keyframes.py  REC.mp4  -o OUTDIR
.venv/bin/python describe.py   OUTDIR   -m gemma3:12b
.venv/bin/python summarize.py  OUTDIR   -m gemma3:12b   # -> meeting.json + referat.md
.venv/bin/python clean.py      OUTDIR   -m gemma3:12b   # correct transcript spelling (keeps raw)
.venv/bin/python report.py     OUTDIR                   # -> report.html
.venv/bin/python corpus.py                              # rebuild corpus.jsonl + oversigt.md
```

## Tuning

- **Sharper OCR / better minutes** — step up to a bigger Gemma spread across both
  GPUs + CPU (as you do with 27B): `--vision-model gemma3:12b` /
  `--text-model gemma3:12b` (or `27b`). Slower, but much stronger at reading dense
  slides/emails. Force spreading with `OLLAMA_SCHED_SPREAD=1` on the Ollama service.
- **Missed slide changes / too many frames** — adjust `--scene` (0.15 busier, 0.4 calmer)
  and `--min-gap` in `keyframes.py`.
- **Transcript still loops** — the fixes live in `transcribe.py` (VAD,
  `condition_on_previous_text=False`, temperature fallback, repetition penalty).
- **Long meetings** — `summarize.py` sizes `num_ctx` to the transcript (Ollama defaults
  to only 4096 tokens); very long ones spill to CPU/RAM (works, slower).

## Why not just Ollama?

Ollama has no speech-to-text. The old `../transscribe/` scripts used HF-transformers
Whisper with greedy decoding and no VAD, which fell into endless repetition
("goddag goddag goddag …"). faster-whisper + VAD + the decoding guards fixes that.
