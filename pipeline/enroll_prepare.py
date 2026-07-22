#!/usr/bin/env python3
"""Prepare voice enrollment.

Diarize an audio file, extract one representative clip per detected speaker and
save their embeddings, so you can listen to the clips and put names on them.

    <torch-venv> enroll_prepare.py "output/<møde>/audio.wav" [clipdir]

Then listen to clipdir/spk_*.wav and run enroll.py to name them.
"""
import argparse
import json
import os
import subprocess

from diar_common import diarize


def _longest_turn(diar, label):
    best = None
    for turn, _, lab in diar.itertracks(yield_label=True):
        if lab == label and (best is None or turn.duration > best.duration):
            best = turn
    return best


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Prepare speaker enrollment clips.")
    ap.add_argument("audio")
    ap.add_argument("clipdir", nargs="?", default=os.path.join(here, "enroll_clips"))
    ap.add_argument("--max-clip", type=float, default=15.0)
    a = ap.parse_args()
    os.makedirs(a.clipdir, exist_ok=True)

    print(f"diarizing {a.audio} (CPU — taalmodig)...", flush=True)
    diar, label_emb, dur = diarize(a.audio)

    pending = {}
    for lab in sorted(dur, key=lambda x: -dur[x]):
        t = _longest_turn(diar, lab)
        if t is None:
            continue
        length = min(a.max_clip, t.duration)
        clip = f"spk_{lab.split('_')[-1]}.wav"
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", str(t.start), "-t", str(length), "-i", a.audio,
                        os.path.join(a.clipdir, clip)], check=False)
        pending[lab] = {"clip": clip, "seconds": round(dur[lab], 1),
                        "embedding": label_emb[lab].tolist()}
        print(f"  {lab}: {dur[lab]:.0f}s tale -> {clip} ({length:.0f}s)")

    json.dump(pending, open(os.path.join(a.clipdir, "pending.json"), "w"),
              ensure_ascii=False, indent=2)
    print(f"\nLyt til klippene i {a.clipdir} og kør derefter:")
    print("  enroll.py " + a.clipdir + " "
          + " ".join(f"{l.split('_')[-1]}=Navn" for l in pending))


if __name__ == "__main__":
    main()
