#!/usr/bin/env python3
"""Transcribe Danish meeting audio with faster-whisper.

Tuned to avoid Whisper's repetition/hallucination loops that broke the old
transformers pipeline (the endless "goddag goddag goddag ..."):

  * Silero VAD strips silence / non-speech        -> the single biggest fix
  * condition_on_previous_text=False              -> a loop can't feed itself
  * temperature fallback + compression-ratio /
    log-prob thresholds                           -> re-decode degenerate parts
  * repetition_penalty + no_repeat_ngram_size     -> belt and braces

Backend: defaults to CPU. hviske-v2 is Whisper large-v3 (1.55B params); float32
weights are ~6.2 GB (won't fit a 6 GB card) and int8 won't reliably fit the
desktop-shared 1060 either, so the GPUs are left for Ollama. CPU int8 runs at
~2x realtime here, which is plenty. Pass device="cuda" to try the GPUs anyway
(falls back to CPU on OOM).

Writes transcript.txt, transcript.srt and segments.json into the output dir.
"""
import os

from ctcuda import ensure_cuda_libs

# Decoding options that keep meeting audio from looping. beam_size is passed in.
_OPTS = dict(
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
    condition_on_previous_text=False,
    temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    compression_ratio_threshold=2.4,
    log_prob_threshold=-1.0,
    no_speech_threshold=0.6,
    repetition_penalty=1.15,
    no_repeat_ngram_size=3,
)


def _fmt(seconds, sep=","):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", sep)


def _candidates(device):
    if device == "cpu":
        return [("cpu", 0, "int8")]
    # GPU opt-in. large-v3 float32 is ~6.2 GB (won't fit 6 GB), so try only int8
    # (1.55 GB, needs Pascal+) then float16 (3.1 GB), then fall back to CPU.
    import ctranslate2
    n = ctranslate2.get_cuda_device_count()
    return ([("cuda", i, "int8") for i in range(n)]
            + [("cuda", i, "float16") for i in range(n)]
            + [("cpu", 0, "int8")])


def _write(outdir, info, segs):
    import json
    json.dump({"language": info.language, "duration": info.duration, "segments": segs},
              open(os.path.join(outdir, "segments.json"), "w"), ensure_ascii=False, indent=2)
    with open(os.path.join(outdir, "transcript.txt"), "w") as f:
        f.write("\n".join(s["text"] for s in segs) + "\n")
    with open(os.path.join(outdir, "transcript.srt"), "w") as f:
        for i, s in enumerate(segs, 1):
            f.write(f"{i}\n{_fmt(s['start'])} --> {_fmt(s['end'])}\n{s['text']}\n\n")


def transcribe_file(audio, outdir, model, language="da", beam=5, device="cpu", log=print):
    if device != "cpu":
        ensure_cuda_libs()
    import gc
    import time
    from faster_whisper import WhisperModel

    os.makedirs(outdir, exist_ok=True)
    last = None
    for dev, idx, ct in _candidates(device):
        try:
            m = WhisperModel(model, device=dev, device_index=idx, compute_type=ct)
        except Exception as e:  # unsupported compute type on this card, etc.
            last = f"{dev}:{idx}/{ct} load {type(e).__name__}"
            continue
        try:
            t0 = time.time()
            segments, info = m.transcribe(audio, language=language, beam_size=beam, **_OPTS)
            segs, prev = [], None
            for s in segments:  # generator: transcription actually runs here
                text = s.text.strip()
                if not text or text == prev:  # drop back-to-back duplicates
                    continue
                prev = text
                segs.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": text})
                log(f"  [{_fmt(s.start)[:8]}] {text}")
            dt = time.time() - t0
            log(f"[transcribe] device={dev}:{idx} compute={ct} · {len(segs)} segments · "
                f"audio {info.duration:.0f}s · {dt:.0f}s ({info.duration / max(dt, 1):.1f}x realtime)")
            _write(outdir, info, segs)
            return segs
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                log(f"[transcribe] OOM on {dev}:{idx}/{ct} -> trying next backend")
                del m
                gc.collect()
                last = f"{dev}:{idx}/{ct} OOM"
                continue
            raise
    raise RuntimeError("Whisper failed on every backend. Last: " + str(last))


def main():
    import argparse

    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Transcribe Danish meeting audio (faster-whisper).")
    ap.add_argument("audio", help="audio or video file")
    ap.add_argument("-o", "--outdir", default=".")
    ap.add_argument("-m", "--model", default=os.path.join(here, "models", "hviske-v2-ct2"),
                    help="CT2 model dir, or a name like 'large-v3'")
    ap.add_argument("-l", "--language", default="da")
    ap.add_argument("--beam", type=int, default=5)
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                    help="cpu (default, reliable here) or cuda (opt-in, falls back to cpu)")
    a = ap.parse_args()
    if a.device != "cpu":
        ensure_cuda_libs()
    transcribe_file(a.audio, a.outdir, a.model, a.language, a.beam, a.device)


if __name__ == "__main__":
    main()
