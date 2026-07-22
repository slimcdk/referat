#!/usr/bin/env python3
"""End-to-end pipeline for one OBS meeting recording.

    audio  -> Danish transcript (faster-whisper + hviske-v2, CPU)
    diarize-> speaker names on the transcript (pyannote, CPU, uses voiceprints.json)
    clean  -> spelling/ASR-corrected transcript (raw is kept)
    video  -> keyframes -> visual descriptions (Ollama, gemma3)
    both   -> structured meeting.json + Danish referat.md + report.html

Usage:
    ./process_meeting.py "../recordings/2026-06-25 10-15-28.mp4"
    ./process_meeting.py REC.mp4 --skip-video --no-clean --no-diarize
"""
import argparse
import os
import subprocess

import ctcuda
import transcribe
import keyframes
import describe
import summarize
import clean
import report

HERE = os.path.dirname(os.path.abspath(__file__))
# pyannote lives in the torch venv (needs torch); diarize.py runs there as a subprocess.
TORCH_PY = os.path.normpath(os.path.join(HERE, "..", "transscribe", "venv", "bin", "python"))
VOICEPRINTS = os.path.join(HERE, "voiceprints.json")


def _extract_audio(rec, audio):
    print("[1/8] extracting audio (16 kHz mono)...")
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", rec, "-ac", "1", "-ar", "16000", "-vn", audio], check=True)


def main():
    ap = argparse.ArgumentParser(description="Transcribe + describe one meeting recording.")
    ap.add_argument("recording")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--whisper-model", default=os.path.join(HERE, "models", "hviske-v2-ct2"))
    ap.add_argument("--whisper-device", default="cpu", choices=["cpu", "cuda"],
                    help="cpu (default) keeps both GPUs free for Ollama; cuda is opt-in")
    ap.add_argument("--beam", type=int, default=5,
                    help="Whisper beam size; 1 is ~40%% faster, 5 more accurate")
    ap.add_argument("--vision-model", default="gemma3:4b")
    ap.add_argument("--text-model", default="gemma3:4b")
    ap.add_argument("--skip-video", action="store_true", help="audio + referat only")
    ap.add_argument("--no-clean", action="store_true", help="skip transcript spelling correction")
    ap.add_argument("--no-diarize", action="store_true", help="skip speaker naming (pyannote, CPU)")
    a = ap.parse_args()
    if a.whisper_device != "cpu":
        ctcuda.ensure_cuda_libs()

    rec = os.path.abspath(a.recording)
    name = os.path.splitext(os.path.basename(rec))[0]
    outdir = a.outdir or os.path.join(HERE, "output", name)
    os.makedirs(outdir, exist_ok=True)
    print(f"== Meeting : {name}\n== Output  : {outdir}\n")

    audio = os.path.join(outdir, "audio.wav")
    if not os.path.exists(audio):
        _extract_audio(rec, audio)

    print("[2/8] transcribing (Danish, VAD, anti-loop)...")
    transcribe.transcribe_file(audio, outdir, a.whisper_model, language="da",
                               beam=a.beam, device=a.whisper_device)

    if a.no_diarize:
        print("[3/8] diarization: skipped")
    elif not os.path.exists(VOICEPRINTS):
        print("[3/8] diarization: skipped (ingen voiceprints.json — kør enroll foerst)")
    elif not os.path.exists(TORCH_PY):
        print("[3/8] diarization: skipped (torch-venv ikke fundet)")
    else:
        print("[3/8] diarizing speakers (pyannote, CPU — kan tage tid)...")
        r = subprocess.run([TORCH_PY, os.path.join(HERE, "diarize.py"), outdir], check=False)
        if r.returncode != 0:
            print("      (diarization fejlede — fortsaetter uden talernavne)")

    if a.skip_video:
        print("[4/8] keyframes: skipped\n[5/8] visual description: skipped")
    else:
        print("[4/8] extracting keyframes (periodic + scene-change)...")
        idx = keyframes.extract(rec, outdir)
        print(f"      {len(idx)} keyframes")
        print("[5/8] describing keyframes (Ollama vision)...")
        describe.describe(outdir, model=a.vision_model)

    print("[6/8] structured summary -> meeting.json + referat.md (Ollama)...")
    summarize.summarize(outdir, title=name, model=a.text_model)

    if a.no_clean:
        print("[7/8] transcript cleanup: skipped")
    else:
        print("[7/8] correcting transcript spelling (Ollama)...")
        clean.clean_transcript(outdir, model=a.text_model)

    print("[8/8] building HTML report...")
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as f:
        f.write(report.build(outdir, name))

    print(f"\n[OK] Done -> {outdir}")
    print("     meeting.json · referat.md · report.html · transcript.txt/.srt"
          + ("" if a.no_diarize else " · transcript_speakers.txt")
          + ("" if a.no_clean else " · transcript_clean.txt")
          + ("" if a.skip_video else " · visuals.md · keyframes/"))


if __name__ == "__main__":
    main()
