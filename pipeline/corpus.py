#!/usr/bin/env python3
"""Aggregate all processed meetings into an AI-friendly corpus + a human index.

Scans output/*/meeting.json and writes, in output/:
  * corpus.jsonl -- one compact record per meeting (metadata + structured fields,
    no full transcript) -- the file to feed an AI to plan across meetings.
  * oversigt.md  -- human index: a table of meetings plus every opgave and
    beslutning aggregated across all meetings, so nothing gets lost between them.
"""
import argparse
import glob
import json
import os


def _load(root):
    metas = []
    for mj in sorted(glob.glob(os.path.join(root, "*", "meeting.json"))):
        try:
            metas.append(json.load(open(mj, encoding="utf-8")))
        except Exception:
            pass
    return metas


def _key(m):
    return m.get("date") or m.get("id") or ""


def build(root, log=print):
    metas = _load(root)

    with open(os.path.join(root, "corpus.jsonl"), "w", encoding="utf-8") as f:
        for m in metas:
            rec = {k: m.get(k) for k in
                   ("id", "title", "date", "duration_sec", "n_segments", "n_keyframes")}
            rec["structured"] = m.get("structured", {})
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    lines = ["# Mødeoversigt", "", f"{len(metas)} møder behandlet.", "",
             "| Dato | Møde | Varighed | Opgaver | Beslutninger |",
             "|---|---|---|---|---|"]
    for m in sorted(metas, key=_key):
        s = m.get("structured", {})
        date = (m.get("date") or "")[:16].replace("T", " ")
        lines.append(f"| {date} | {m.get('id')} | "
                     f"{int((m.get('duration_sec') or 0) // 60)} min | "
                     f"{len(s.get('opgaver', []))} | {len(s.get('beslutninger', []))} |")

    lines += ["", "## Alle opgaver på tværs af møder", ""]
    tasks = False
    for m in sorted(metas, key=_key):
        date = (m.get("date") or m.get("id") or "")[:10]
        for t in m.get("structured", {}).get("opgaver", []):
            tasks = True
            who = t.get("ansvarlig", "") if isinstance(t, dict) else ""
            what = t.get("opgave", str(t)) if isinstance(t, dict) else str(t)
            due = t.get("deadline", "") if isinstance(t, dict) else ""
            lines.append(f"- **{who or '—'}** — {what}"
                         + (f" _(frist: {due})_" if due else "") + f"  · _{date}_")
    if not tasks:
        lines.append("_Ingen opgaver registreret._")

    lines += ["", "## Alle beslutninger på tværs af møder", ""]
    decisions = False
    for m in sorted(metas, key=_key):
        date = (m.get("date") or m.get("id") or "")[:10]
        for b in m.get("structured", {}).get("beslutninger", []):
            decisions = True
            lines.append(f"- {b}  · _{date}_")
    if not decisions:
        lines.append("_Ingen beslutninger registreret._")

    open(os.path.join(root, "oversigt.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    log(f"[corpus] {len(metas)} meetings -> corpus.jsonl + oversigt.md")
    return metas


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Aggregate meetings into corpus.jsonl + oversigt.md")
    ap.add_argument("--root", default=os.path.join(here, "output"))
    a = ap.parse_args()
    build(a.root)


if __name__ == "__main__":
    main()
