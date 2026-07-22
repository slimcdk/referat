#!/usr/bin/env python3
"""Summarise a meeting into a structured, AI-friendly bundle.

One LLM call (Ollama, JSON mode) turns the transcript + visual notes into a
structured object (resumé, deltagere, emner, beslutninger, opgaver med
ansvarlig/deadline, opfølgning, åbne spørgsmål). From that we write:

  * meeting.json -- everything about the meeting in one machine-readable file.
  * referat.md   -- a human-readable Danish referat rendered from the structured data.

Long meetings (60+ min) made the model return empty JSON when the whole
transcript was fed into JSON mode at once, so those are handled with a
**map-reduce**: summarise the transcript in chunks into concise Danish notes,
then run the single structured extraction on the (much shorter) notes. There is
also an "empty result -> retry via map-reduce" safety net.
"""
import argparse
import json
import os
import re

import ollama

SYSTEM = ("Du er en praecis dansk moedereferent. Du svarer KUN med gyldig JSON og "
          "finder ikke paa noget der ikke staar i materialet.")

# Regular voices across the meetings; used to normalise garbled ASR names.
# Christian is the owner ("mig"). Others show up occasionally -> the model guesses.
REGULAR_PARTICIPANTS = ["Christian", "Tim", "Thomas"]

# Length above which we condense the transcript first (chars OR segments).
LONG_CHARS = 9000
LONG_SEGMENTS = 60

_SECTIONS = [
    ("resume", "Resumé", "text"),
    ("deltagere", "Deltagere", "list"),
    ("emner", "Emner og diskussion", "list"),
    ("beslutninger", "Beslutninger", "list"),
    ("opgaver", "Opgaver / handlinger", "tasks"),
    ("opfoelgning", "Opfølgning", "list"),
    ("aabne_spoergsmaal", "Åbne spørgsmål", "list"),
    ("vist_paa_skaerm", "Vist på skærmen", "list"),
]


def _text(r):
    return r["response"] if isinstance(r, dict) else r.response


def _parse_date(meeting_id):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})[ _](\d{2})-(\d{2})-(\d{2})", meeting_id)
    if not m:
        return None
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}"


def _num_ctx(text):
    approx = len(text) // 3 + 1500
    return min(24576, max(8192, ((approx + 1023) // 1024) * 1024))


def _seg_line(s):
    """Prefix a transcript segment with its speaker name if the meeting was diarized."""
    sp = s.get("speaker")
    return f"{sp}: {s['text']}" if sp else s["text"]


def _prompt(source_text, visuals, participants):
    vis = "\n".join(f"[{int(v['t'] // 60):02d}:{int(v['t'] % 60):02d}] {v['description']}"
                    for v in visuals) or "(ingen visuelle noter)"
    names = ", ".join(participants)
    return f"""Analyser materialet fra et dansk online moede og udtraek det vigtigste.
Faste deltagere er typisk: {names} (Christian er ejeren). Ret oplagte
transskriptionsfejl i navne til disse (fx "Timon"->"Tim"). Brug kun fornavne, og
angiv hver person praecis een gang. Deltagere = dem der faktisk deltager/taler,
ikke blot personer der naevnes. Personer udenfor gruppen: gaet ud fra konteksten.

Returner ET JSON-objekt paa dansk med praecis disse noegler:

{{
  "resume": "4-8 saetningers sammenfatning",
  "deltagere": ["navne paa deltagerne"],
  "emner": ["kort punkt pr. emne der blev droeftet"],
  "beslutninger": ["konkrete beslutninger"],
  "opgaver": [{{"ansvarlig": "navn eller ''", "opgave": "hvad", "deadline": "hvornaar eller ''"}}],
  "opfoelgning": ["hvad skal foelges op / naeste skridt"],
  "aabne_spoergsmaal": ["uafklarede spoergsmaal"],
  "vist_paa_skaerm": ["hvad der blev vist paa skaermen, ud fra skaerm-noterne"]
}}

Brug tomme lister hvor der ikke er noget. Vaer tro mod indholdet.

=== MATERIALE (transskription / noter) ===
{source_text}

=== SKAERM (visuelt) ===
{vis}
"""


def _coerce(obj):
    out = {}
    for key, _, kind in _SECTIONS:
        v = obj.get(key)
        if key == "resume":
            out[key] = v if isinstance(v, str) else (str(v) if v else "")
        elif key == "opgaver":
            out[key] = v if isinstance(v, list) else []
        else:
            out[key] = v if isinstance(v, list) else ([] if v is None else [str(v)])
    return out


def _is_empty(s):
    if (s.get("resume") or "").strip():
        return False
    return not any(s.get(key) for key, _, _ in _SECTIONS if key != "resume")


def _extract(model, source_text, visuals, participants, log):
    r = ollama.Client().generate(
        model=model, system=SYSTEM,
        prompt=_prompt(source_text, visuals, participants),
        format="json", options={"temperature": 0.2, "num_ctx": _num_ctx(source_text)})
    raw = _text(r).strip()
    try:
        return _coerce(json.loads(raw))
    except Exception:
        m = re.search(r"\{.*\}", raw, re.S)  # salvage first JSON object
        if m:
            try:
                return _coerce(json.loads(m.group(0)))
            except Exception:
                pass
        log("[summarize] WARNING: kunne ikke parse JSON; gemmer raa resume")
        return _coerce({"resume": raw[:1500]})


def _dedupe(items):
    seen, out = set(), []
    for it in items:
        s = (it or "").strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def _dedupe_tasks(tasks):
    seen, out = set(), []
    for t in tasks:
        if not isinstance(t, dict):
            t = {"ansvarlig": "", "opgave": str(t), "deadline": ""}
        opg = (t.get("opgave") or "").strip()
        key = ((t.get("ansvarlig") or "").strip().lower(), opg.lower())
        if opg and key not in seen:
            seen.add(key)
            out.append({"ansvarlig": (t.get("ansvarlig") or "").strip(),
                        "opgave": opg, "deadline": (t.get("deadline") or "").strip()})
    return out


def _merge(structs):
    """Merge per-chunk structured objects (concatenate + dedupe)."""
    merged = {}
    for key, _, _ in _SECTIONS:
        if key == "resume":
            merged[key] = ""  # synthesised separately
        elif key == "opgaver":
            allt = []
            for s in structs:
                allt.extend(s.get("opgaver") or [])
            merged[key] = _dedupe_tasks(allt)
        else:
            allx = []
            for s in structs:
                allx.extend(s.get(key) or [])
            merged[key] = _dedupe(allx)
    return merged


def _synth_resume(model, resumes, log):
    joined = " ".join(r for r in resumes if r).strip()
    if not joined:
        return ""
    try:
        r = ollama.Client().generate(
            model=model,
            prompt=("Skriv ét samlet resumé paa dansk (4-8 saetninger) af et moede ud fra "
                    "disse delnoter. Ingen indledning.\n\n" + joined),
            options={"temperature": 0.2, "num_ctx": _num_ctx(joined)})
        return _text(r).strip() or joined[:1500]
    except Exception:
        return joined[:1500]


def _extract_chunked(model, segments, visuals, participants, log, chunk=40):
    """Long meetings: extract structure per chunk (short inputs work in JSON mode),
    then merge. Avoids the empty-output failure on very long inputs."""
    structs = []
    for i in range(0, len(segments), chunk):
        ctext = "\n".join(_seg_line(s) for s in segments[i:i + chunk])
        structs.append(_extract(model, ctext, [], participants, log))
        log(f"[summarize] chunk {min(i + chunk, len(segments))}/{len(segments)} segmenter")
    merged = _merge(structs)
    merged["resume"] = _synth_resume(model, [s.get("resume", "") for s in structs], log)
    if visuals:  # screen items from the (separate) visual notes
        vstruct = _extract(model, "(brug kun skaermnoterne nedenfor)", visuals, participants, log)
        merged["vist_paa_skaerm"] = _dedupe((merged.get("vist_paa_skaerm") or [])
                                            + (vstruct.get("vist_paa_skaerm") or []))
    return merged


def _render_referat(title, meta, structured):
    lines = [f"# Referat – {title}", ""]
    stamp = []
    if meta.get("date"):
        stamp.append(meta["date"].replace("T", " "))
    if meta.get("duration_sec"):
        stamp.append(f"{int(meta['duration_sec'] // 60)} min")
    if stamp:
        lines += ["_" + " · ".join(stamp) + "_", ""]
    for key, heading, kind in _SECTIONS:
        val = structured.get(key)
        if not val:
            continue
        lines.append(f"## {heading}")
        if kind == "text":
            lines += [val, ""]
        elif kind == "tasks":
            for t in val:
                who = (t.get("ansvarlig") or "").strip() if isinstance(t, dict) else ""
                what = (t.get("opgave") or "").strip() if isinstance(t, dict) else str(t)
                due = (t.get("deadline") or "").strip() if isinstance(t, dict) else ""
                pre = f"**{who}** — " if who else ""
                suf = f" _(frist: {due})_" if due else ""
                lines.append(f"- {pre}{what}{suf}")
            lines.append("")
        else:
            lines += [f"- {item}" for item in val] + [""]
    return "\n".join(lines).rstrip() + "\n"


def summarize(outdir, title, model="gemma3:4b", participants=REGULAR_PARTICIPANTS, log=print):
    seg = json.load(open(os.path.join(outdir, "segments.json")))
    segments = seg.get("segments", [])
    transcript_text = "\n".join(_seg_line(s) for s in segments)
    vpath = os.path.join(outdir, "visuals.json")
    visuals = json.load(open(vpath)) if os.path.exists(vpath) else []

    long_meeting = len(transcript_text) > LONG_CHARS or len(segments) > LONG_SEGMENTS
    log(f"[summarize] model={model} ({len(segments)} segmenter"
        + (", chunk-vis udtraek" if long_meeting else "") + ")")
    if long_meeting:
        structured = _extract_chunked(model, segments, visuals, participants, log)
    else:
        structured = _extract(model, transcript_text, visuals, participants, log)
        if _is_empty(structured):  # short input still failed -> fall back to chunking
            log("[summarize] tomt resultat -> chunk-vis udtraek")
            structured = _extract_chunked(model, segments, visuals, participants, log)
    if _is_empty(structured):
        log("[summarize] ADVARSEL: resultatet er stadig tomt")

    # if the meeting was diarized, trust the real attendees over the LLM's guess
    sp = os.path.join(outdir, "speakers.json")
    if os.path.exists(sp):
        delt = json.load(open(sp)).get("deltagere")
        if delt:
            structured["deltagere"] = delt

    meeting_id = os.path.basename(os.path.normpath(outdir))
    meeting = {
        "id": meeting_id,
        "title": title,
        "date": _parse_date(meeting_id),
        "duration_sec": round(seg.get("duration", 0), 1),
        "language": seg.get("language", "da"),
        "model": model,
        "n_segments": len(segments),
        "n_keyframes": len(visuals),
        "structured": structured,
        "transcript_text": transcript_text,
        "transcript": segments,
        "visuals": visuals,
    }
    json.dump(meeting, open(os.path.join(outdir, "meeting.json"), "w"),
              ensure_ascii=False, indent=2)

    referat = _render_referat(title, meeting, structured)
    open(os.path.join(outdir, "referat.md"), "w").write(referat)
    log(f"[summarize] wrote meeting.json ({len(structured.get('opgaver', []))} opgaver) + referat.md")
    return meeting


def main():
    ap = argparse.ArgumentParser(description="Structured summary -> meeting.json + referat.md")
    ap.add_argument("outdir")
    ap.add_argument("--title", default=None)
    ap.add_argument("-m", "--model", default="gemma3:4b")
    a = ap.parse_args()
    title = a.title or os.path.basename(os.path.normpath(a.outdir))
    summarize(a.outdir, title, a.model)


if __name__ == "__main__":
    main()
