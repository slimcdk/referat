#!/usr/bin/env python3
"""Automatic post-transcription cleanup.

Fixes obvious Danish spelling / speech-to-text errors while preserving meaning,
names, numbers and timing. Corrects each segment in small batches (JSON mode) so
timestamps survive, and falls back to the raw text for any segment the model
drops. Writes transcript_clean.txt (+ .srt) and adds `transcript_clean` to
meeting.json.

The raw transcript.txt is never modified -- it stays the faithful record; the
clean version is for reading and for feeding downstream steps / an AI.
"""
import argparse
import json
import os

import ollama

from summarize import REGULAR_PARTICIPANTS

SYSTEM = ("Du retter automatiske danske transskriptioner. Du retter KUN tydelige "
          "stave- og genkendelsesfejl og bevarer betydning, fakta, navne, tal og "
          "raekkefoelge. Du tilfoejer intet og fjerner intet. Svar KUN med gyldig JSON.")


def _text(r):
    return r["response"] if isinstance(r, dict) else r.response


def _fmt(seconds, sep=","):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", sep)


def _correct_batch(model, batch, participants):
    items = [{"i": i, "text": s["text"]} for i, s in enumerate(batch)]
    names = ", ".join(participants)
    prompt = (
        "Ret oplagte stave- og transskriptionsfejl i hver 'text' herunder til korrekt "
        "dansk. Bevar betydning, fakta, tal og tekniske ord. Tilfoej intet nyt og fjern "
        f"intet. Ret navne til rigtige stavemaader (faste deltagere: {names}). "
        'Returner praecis: {"segments": [{"i": <nummer>, "text": "<rettet tekst>"}]} '
        "med samme antal segmenter og samme 'i'.\n\n"
        + json.dumps({"segments": items}, ensure_ascii=False))
    r = ollama.Client().generate(model=model, system=SYSTEM, prompt=prompt,
                                 format="json", options={"temperature": 0.1, "num_ctx": 8192})
    try:
        out = json.loads(_text(r))
        by_i = {int(x["i"]): x.get("text", "") for x in out.get("segments", [])}
    except Exception:
        by_i = {}
    corrected = []
    for i, s in enumerate(batch):
        t = by_i.get(i)
        corrected.append(t.strip() if isinstance(t, str) and t.strip() else s["text"])
    return corrected


def clean_transcript(outdir, model="gemma3:12b", participants=REGULAR_PARTICIPANTS,
                     batch_size=15, log=print):
    seg = json.load(open(os.path.join(outdir, "segments.json")))
    segments = seg.get("segments", [])
    clean_segs = []
    for start in range(0, len(segments), batch_size):
        batch = segments[start:start + batch_size]
        for s, t in zip(batch, _correct_batch(model, batch, participants)):
            clean_segs.append({"start": s["start"], "end": s["end"], "text": t})
        log(f"[clean] {min(start + batch_size, len(segments))}/{len(segments)} segmenter")

    clean_text = "\n".join(s["text"] for s in clean_segs) + "\n"
    open(os.path.join(outdir, "transcript_clean.txt"), "w").write(clean_text)
    with open(os.path.join(outdir, "transcript_clean.srt"), "w") as f:
        for i, s in enumerate(clean_segs, 1):
            f.write(f"{i}\n{_fmt(s['start'])} --> {_fmt(s['end'])}\n{s['text']}\n\n")

    mp = os.path.join(outdir, "meeting.json")
    if os.path.exists(mp):
        m = json.load(open(mp))
        m["transcript_clean"] = clean_segs
        m["transcript_clean_text"] = clean_text.strip()
        json.dump(m, open(mp, "w"), ensure_ascii=False, indent=2)
    log(f"[clean] wrote transcript_clean.txt (+srt) · {len(clean_segs)} segmenter")
    return clean_segs


def main():
    ap = argparse.ArgumentParser(description="Correct transcript spelling / ASR errors (keeps raw).")
    ap.add_argument("outdir")
    ap.add_argument("-m", "--model", default="gemma3:12b")
    a = ap.parse_args()
    clean_transcript(a.outdir, a.model)


if __name__ == "__main__":
    main()
