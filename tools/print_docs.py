#!/usr/bin/env python3
"""Build docs/print.html (cheat sheet + playbook + game plan) for printing, in case laptops
aren't allowed.  python3 tools/print_docs.py  then open docs/print.html and print (Cmd-P)."""
import html, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ["docs/CHEATSHEET.md", "docs/PLAYBOOK.md", "docs/GAMEPLAN.md"]

CSS = """body{font:9.5px/1.3 -apple-system,Helvetica,Arial,sans-serif;margin:8mm;columns:2;column-gap:7mm}
h1{font-size:14px;margin:4px 0;column-span:all;border-bottom:2px solid #000}
h2{font-size:11.5px;margin:7px 0 2px;break-after:avoid}h3{font-size:10px;margin:5px 0 2px;break-after:avoid}
table{border-collapse:collapse;width:100%;margin:2px 0;break-inside:avoid}td,th{border:1px solid #999;padding:1px 3px;vertical-align:top}
th{background:#eee}code{font:9px Menlo,monospace;background:#f2f2f2}ul,ol{margin:1px 0;padding-left:14px}
p{margin:2px 0}hr{border:0;border-top:1px solid #999}@page{size:letter;margin:0}"""

def inline(t):
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<i>\1</i>", t)

def md_to_html(md):
    out, lines, i, lst = [], md.splitlines(), 0, None
    def close_list():
        nonlocal lst
        if lst: out.append(f"</{lst}>"); lst = None
    while i < len(lines):
        ln = lines[i]; s = ln.strip()
        if s.startswith("|"):
            close_list(); rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c): rows.append(cells)
                i += 1
            out.append("<table>" + "".join(
                "<tr>" + "".join(f"<{'th' if r == 0 else 'td'}>{inline(c)}</{'th' if r == 0 else 'td'}>" for c in row) + "</tr>"
                for r, row in enumerate(rows)) + "</table>")
            continue
        m = re.match(r"^(#{1,3})\s+(.*)", s)
        if m: close_list(); out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
        elif re.match(r"^(\s*)[-*]\s+", ln) or re.match(r"^\s*\d+\.\s+", ln):
            kind = "ol" if re.match(r"^\s*\d+\.", ln) else "ul"
            if lst != kind: close_list(); out.append(f"<{kind}>"); lst = kind
            out.append("<li>" + inline(re.sub(r"^\s*([-*]|\d+\.)\s+", "", ln)) + "</li>")
        elif s == "---": close_list(); out.append("<hr>")
        elif s.startswith("```"):
            close_list(); i += 1; code = []
            while i < len(lines) and not lines[i].strip().startswith("```"): code.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
        elif s: close_list(); out.append(f"<p>{inline(s)}</p>")
        else: close_list()
        i += 1
    close_list()
    return "\n".join(out)

def build(path=os.path.join(ROOT, "docs", "print.html")):
    body = "\n".join(md_to_html(open(os.path.join(ROOT, d)).read()) for d in DOCS)
    with open(path, "w") as fh:
        fh.write(f"<!doctype html><meta charset=utf-8><title>Trading Challenge — print</title><style>{CSS}</style>{body}")
    return path

if __name__ == "__main__":
    print("wrote", build())
