#!/usr/bin/env python3
"""Aggregate action items from every processed meeting into a ready-to-use todo list.

Writes, in output/:
  * todos.jsonl -- one action item per line (task, owner, deadline, status,
    meeting_id, date) -- the machine-readable list for an agent to consume.
  * todos.md    -- the same as a checkbox list grouped by owner.

This is deterministic aggregation (no LLM) of each meeting's structured.opgaver.
Point an agent at todos.jsonl / corpus.jsonl (see output/AGENTS.md) to dedupe,
prioritise and phrase them into a maintained todo list.
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


def build(root, log=print):
    metas = _load(root)
    todos = []
    for m in metas:
        date = (m.get("date") or m.get("id") or "")[:10]
        for t in m.get("structured", {}).get("opgaver", []):
            if isinstance(t, dict):
                task = (t.get("opgave") or "").strip()
                owner = (t.get("ansvarlig") or "").strip()
                due = (t.get("deadline") or "").strip()
            else:
                task, owner, due = str(t).strip(), "", ""
            if not task:
                continue
            todos.append({
                "task": task,
                "owner": owner or None,
                "deadline": due or None,
                "status": "open",
                "meeting_id": m.get("id"),
                "meeting_title": m.get("title"),
                "date": date,
            })

    with open(os.path.join(root, "todos.jsonl"), "w", encoding="utf-8") as f:
        for t in todos:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    by_owner = {}
    for t in todos:
        by_owner.setdefault(t["owner"] or "Uden ansvarlig", []).append(t)
    lines = ["# To-do (fra møder)", "",
             f"{len(todos)} opgaver fra {len(metas)} møder. Afkryds selv, eller lad en "
             "agent vedligeholde listen (se AGENTS.md).", ""]
    for owner in sorted(by_owner):
        lines.append(f"## {owner}")
        for t in sorted(by_owner[owner], key=lambda x: x["date"]):
            due = f" _(frist: {t['deadline']})_" if t["deadline"] else ""
            lines.append(f"- [ ] {t['task']}{due}  · _{t['date']}_")
        lines.append("")
    open(os.path.join(root, "todos.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")

    log(f"[todos] {len(todos)} action items from {len(metas)} meetings -> todos.jsonl + todos.md")
    return todos


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="Aggregate meeting action items into todos.jsonl + todos.md")
    ap.add_argument("--root", default=os.path.join(here, "output"))
    a = ap.parse_args()
    build(a.root)


if __name__ == "__main__":
    main()
