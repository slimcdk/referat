#!/usr/bin/env python3
"""Build a self-contained HTML report for one processed meeting.

Reads a meeting output dir (referat.md, visuals.json, segments.json, keyframes/)
and writes report.html with everything inlined -- base64 images, inline CSS/JS --
so it opens in any browser with no dependencies. The keyframes are shown as a
visual timeline next to their descriptions, so the screens that matter are right
there to highlight a point; click an image to enlarge it.
"""
import argparse
import base64
import html
import json
import os
import re


def _esc(s):
    return html.escape(s, quote=False)


def _inline(s):
    """Escape, then render **bold** and `code`."""
    s = _esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_to_html(md):
    """Minimal markdown -> HTML: headings, bullet lists, bold, paragraphs."""
    out, in_list = [], False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            if in_list:
                out.append("</ul>")
                in_list = False
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            continue
        m = re.match(r"^\s*[\*\-]\s+(.*)$", line)
        if m:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_inline(m.group(1))}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        out.append(f"<p>{_inline(line)}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _data_uri(path):
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def _mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def _load(outdir, name):
    p = os.path.join(outdir, name)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def build(outdir, title=None):
    name = title or os.path.basename(os.path.normpath(outdir))
    referat_md = _load(outdir, "referat.md") or "_Intet referat._"
    visuals = json.loads(_load(outdir, "visuals.json") or "[]")
    seg_raw = _load(outdir, "segments.json")
    segs = json.loads(seg_raw)["segments"] if seg_raw else []
    dur = json.loads(seg_raw).get("duration", 0) if seg_raw else 0

    kfdir = os.path.join(outdir, "keyframes")
    cards = []
    for v in visuals:
        img = os.path.join(kfdir, v["file"])
        thumb = (f'<img loading="lazy" src="{_data_uri(img)}" alt="skaermbillede" '
                 'onclick="zoom(this.src)">') if os.path.exists(img) else ""
        cards.append(
            f'<figure class="shot">{thumb}'
            f'<figcaption><span class="ts">{_mmss(v["t"])}</span>'
            f'{_esc(v["description"])}</figcaption></figure>')
    gallery = "\n".join(cards) or "<p>Ingen skærmbilleder.</p>"

    rows = "\n".join(
        f'<div class="line"><span class="ts">{_mmss(s["start"])}</span>'
        f'<span class="tx">{_esc(s["text"])}</span></div>' for s in segs)

    stats = (f"{_mmss(dur)} varighed · {len(segs)} passager · "
             f"{len(visuals)} skærmbilleder")

    return _PAGE.format(name=_esc(name), stats=_esc(stats),
                        referat=md_to_html(referat_md), gallery=gallery,
                        transcript=rows or "<p>Intet transskript.</p>")


_PAGE = """<!doctype html>
<html lang="da"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Referat – {name}</title>
<style>
  :root {{ color-scheme: light dark; --bg:#fff; --fg:#1a1a1a; --mut:#666;
           --card:#f6f7f9; --bd:#e3e5e9; --accent:#3b6cff; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg:#15171c; --fg:#e8eaed;
           --mut:#9aa0aa; --card:#1e2127; --bd:#2c313a; --accent:#7aa2ff; }} }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--fg);
    font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:28px 20px 80px; }}
  header h1 {{ margin:0 0 4px; font-size:1.7rem; }}
  header .stats {{ color:var(--mut); font-size:.9rem; }}
  h2 {{ margin:2.2rem 0 .8rem; font-size:1.25rem; border-bottom:1px solid var(--bd);
       padding-bottom:.3rem; }}
  section.referat h2 {{ font-size:1.1rem; border:0; margin:1.4rem 0 .4rem; }}
  section.referat ul {{ margin:.3rem 0 .3rem 1.1rem; padding:0; }}
  section.referat li {{ margin:.2rem 0; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
    gap:14px; }}
  figure.shot {{ margin:0; background:var(--card); border:1px solid var(--bd);
    border-radius:12px; overflow:hidden; display:flex; flex-direction:column; }}
  figure.shot img {{ width:100%; aspect-ratio:16/9; object-fit:cover; cursor:zoom-in;
    background:#000; }}
  figure.shot figcaption {{ padding:10px 12px; font-size:.86rem; color:var(--fg); }}
  .ts {{ display:inline-block; font-variant-numeric:tabular-nums; font-weight:600;
    color:var(--accent); margin-right:.5rem; }}
  details {{ margin-top:.6rem; }}
  summary {{ cursor:pointer; color:var(--mut); }}
  .line {{ display:flex; gap:.6rem; padding:.28rem 0; border-bottom:1px solid var(--bd); }}
  .line .tx {{ flex:1; }}
  code {{ background:var(--card); padding:.05rem .3rem; border-radius:4px; font-size:.9em; }}
  #lb {{ position:fixed; inset:0; background:rgba(0,0,0,.9); display:none;
    align-items:center; justify-content:center; cursor:zoom-out; z-index:9; padding:20px; }}
  #lb img {{ max-width:100%; max-height:100%; border-radius:6px; }}
</style></head>
<body><div class="wrap">
  <header><h1>{name}</h1><div class="stats">{stats}</div></header>

  <h2>Referat</h2>
  <section class="referat">{referat}</section>

  <h2>Skærmbilleder (visuel tidslinje)</h2>
  <div class="grid">{gallery}</div>

  <h2>Transskript</h2>
  <details><summary>Vis fuldt transskript</summary>
    <div class="transcript">{transcript}</div>
  </details>
</div>
<div id="lb" onclick="this.style.display='none'"><img id="lbimg" alt=""></div>
<script>
  function zoom(src){{ var lb=document.getElementById('lb');
    document.getElementById('lbimg').src=src; lb.style.display='flex'; }}
</script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser(description="Build a self-contained HTML meeting report.")
    ap.add_argument("outdir", help="a meeting output dir (…/output/<name>)")
    ap.add_argument("--title", default=None)
    ap.add_argument("-o", "--out", default=None, help="output html path (default OUTDIR/report.html)")
    a = ap.parse_args()
    htmlout = a.out or os.path.join(a.outdir, "report.html")
    with open(htmlout, "w", encoding="utf-8") as f:
        f.write(build(a.outdir, a.title))
    print(f"wrote {htmlout}")


if __name__ == "__main__":
    main()
