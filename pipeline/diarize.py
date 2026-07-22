#!/usr/bin/env python3
"""Label a meeting's transcript with speaker names using enrolled voiceprints.

    <torch-venv> diarize.py "output/<møde>" [--threshold 0.40]

Diarizes audio.wav (CPU), matches each speaker to the nearest enrolled voiceprint
(cosine similarity; unknowns -> "Gæst N"), maps the transcript segments to
speakers by time overlap, and writes:
  * transcript_speakers.txt  — "[MM:SS] Navn: tekst"
  * speakers.json            — label->name mapping + durations
  * adds `speakers` + `deltagere_diar` to meeting.json
"""
import argparse
import json
import os

from diar_common import cosine, diarize, load_voiceprints


def _mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def main():
    ap = argparse.ArgumentParser(description="Speaker-label a meeting transcript.")
    ap.add_argument("outdir")
    ap.add_argument("--threshold", type=float, default=0.40,
                    help="min cosine similarity to accept a voiceprint match")
    a = ap.parse_args()

    vps = load_voiceprints()
    if not vps:
        print("Ingen voiceprints endnu — kør enroll_prepare.py + enroll.py foerst.")
    audio = os.path.join(a.outdir, "audio.wav")
    print(f"diarizing {audio} (CPU)...", flush=True)
    diar, label_emb, dur = diarize(audio)

    label_name, used, guest = {}, set(), 0
    for lab in sorted(label_emb, key=lambda x: -dur[x]):
        best, bestsim = None, -1.0
        for nm, e in vps.items():
            s = cosine(label_emb[lab], e)
            if s > bestsim:
                best, bestsim = nm, s
        if best and bestsim >= a.threshold and best not in used:
            label_name[lab] = best
            used.add(best)
        else:
            guest += 1
            label_name[lab] = f"Gæst {guest}"
        print(f"  {lab} ({dur[lab]:.0f}s tale) -> {label_name[lab]} (bedste sim {bestsim:.2f})")

    turns = [(t.start, t.end, lab) for t, _, lab in diar.itertracks(yield_label=True)]

    def speaker_at(s, e):
        best, best_ov = None, 0.0
        for ts, te, lab in turns:
            ov = max(0.0, min(e, te) - max(s, ts))
            if ov > best_ov:
                best_ov, best = ov, lab
        return label_name.get(best, "?")

    # write the speaker into each transcript segment (segments.json becomes the labeled source)
    segpath = os.path.join(a.outdir, "segments.json")
    seg_obj = json.load(open(segpath))
    for sg in seg_obj["segments"]:
        sg["speaker"] = speaker_at(sg["start"], sg["end"])
    json.dump(seg_obj, open(segpath, "w"), ensure_ascii=False, indent=2)
    segs = seg_obj["segments"]

    with open(os.path.join(a.outdir, "transcript_speakers.txt"), "w") as f:
        for sg in segs:
            f.write(f"[{_mmss(sg['start'])}] {sg['speaker']}: {sg['text']}\n")

    deltagere = sorted(set(label_name.values()), key=lambda n: (n.startswith("Gæst"), n))
    json.dump({"label_name": label_name, "deltagere": deltagere,
               "seconds": {k: round(v, 1) for k, v in dur.items()}},
              open(os.path.join(a.outdir, "speakers.json"), "w"), ensure_ascii=False, indent=2)

    mp = os.path.join(a.outdir, "meeting.json")
    if os.path.exists(mp):
        m = json.load(open(mp))
        m["speakers"] = label_name
        m["deltagere_diar"] = sorted(set(label_name.values()), key=lambda n: (n.startswith("Gæst"), n))
        json.dump(m, open(mp, "w"), ensure_ascii=False, indent=2)

    print("-> transcript_speakers.txt + speakers.json (+ meeting.json opdateret)")


if __name__ == "__main__":
    main()
