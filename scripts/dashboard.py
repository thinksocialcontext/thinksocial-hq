#!/usr/bin/env python3
"""ThinkSocial HQ dashboard. A few pages, one command, Python standard library only.

  python3 scripts/dashboard.py            then open http://localhost:8765
  python3 scripts/dashboard.py --once     print the page data as JSON and exit

Pages:
  /                 Overview: waiting on Desiree, agents and their states, work per space, recent ledger
  /clients          Clients: every client with status, services, open KB questions and next action
  /client/<slug>    One client: profile, onboarding progress, open questions, that client's ledger
  /inventory        Inventory: invoices not yet read, lines this week by client, lines held, sheets ready
  /team             Team: roster, who covers which client, coverage gaps
  /growth           Growth: pipeline by stage and value
  /ops              Ops: tool stack and billing tracker
  /memory           Memory: every memory with its space and client tags
  /ledger           Ledger: every job, filtered by ?space= or ?client=

Every space page ends with the ledger jobs recorded in that space. Until the private files exist
(clients/INDEX.md, team/roster.csv, growth/pipeline.md, ops/billing.csv, inventory/master/master.csv)
each page shows the committed examples and labels them SAMPLE. It binds to 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlencode, urlsplit

ROOT = Path(__file__).resolve().parent.parent


def env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name) or default)


APPROVALS = env_path("HQ_APPROVALS_DIR", ROOT / "approvals")
MEMORY = env_path("HQ_MEMORY_DIR", ROOT / "memory")
MEMORY_SEED = env_path("HQ_MEMORY_SEED_DIR", ROOT / "memory-seed")
CLIENTS = env_path("HQ_CLIENTS_DIR", ROOT / "clients")
INVENTORY = env_path("HQ_INVENTORY_DIR", ROOT / "inventory")
TEAM = env_path("HQ_TEAM_DIR", ROOT / "team")
GROWTH = env_path("HQ_GROWTH_DIR", ROOT / "growth")
OPS = env_path("HQ_OPS_DIR", ROOT / "ops")

SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]{0,95}")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
OPEN_Q = re.compile(r"^\s*[*-] \[ \]", re.M)
DONE_Q = re.compile(r"^\s*[*-] \[[xX]\]", re.M)
STAGES = ["lead", "researching", "package ready", "proposal sent", "negotiating", "won", "lost"]
# which ledger spaces each page shows; tests/test_spaces.py checks every space has a page
SPACE_PAGES = {"hq": "/", "clients": "/clients", "inventory": "/inventory", "team": "/team",
               "growth": "/growth", "growth-research": "/growth", "ops": "/ops"}
SPACE_LABELS = {"hq": "HQ", "clients": "Clients", "inventory": "Inventory", "team": "Team", "growth": "Growth",
                "growth-research": "Growth / Research", "ops": "Ops"}


# ---------------------------------------------------------------- reading files

def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    fields: dict[str, str] = {}
    for line in (match.group(1).splitlines() if match else []):
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
    return fields


def live_or_example(live: Path, example: Path) -> tuple[Path | None, bool]:
    if live.exists():
        return live, False
    if example.exists():
        return example, True
    return None, True


def md_table(text: str) -> list[list[str]]:
    """The first Markdown table in text, as rows of cells, without the header and separator."""
    rows, seen_sep = [], False
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            if seen_sep and rows:
                break
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            seen_sep = True
            continue
        if seen_sep:
            rows.append(cells)
    return rows


def read_csv_rows(path: Path | None) -> list[dict[str, str]]:
    if not path or not path.exists():
        return []
    try:
        return list(csv.DictReader(io.StringIO(read_text(path))))
    except csv.Error:
        return []


def run_json(cmd: list[str], timeout: float = 8) -> Any:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def agents() -> list[dict[str, str]]:
    result = run_json([str(ROOT / "scripts" / "hq"), "list", "--json"])
    return result if isinstance(result, list) else []


def ledger(limit: int = 300) -> list[dict[str, Any]]:
    result = run_json([sys.executable, str(ROOT / "scripts" / "ledger"), "recent", "--limit", str(limit), "--json"])
    return result if isinstance(result, list) else []


def approvals() -> list[dict[str, str]]:
    items = []
    for path in sorted(APPROVALS.glob("*.md")) if APPROVALS.is_dir() else []:
        if path.name.lower() == "readme.md":
            continue
        meta = frontmatter(read_text(path))
        if meta.get("status", "waiting") == "waiting":
            items.append({"file": f"approvals/{path.name}", "title": meta.get("title", path.stem),
                          "from": meta.get("from", ""), "kind": meta.get("kind", ""),
                          "asked": meta.get("asked", ""), "client": meta.get("client", "")})
    return items


# ---------------------------------------------------------------- clients

def client_profile(slug: str) -> dict[str, Any]:
    folder = CLIENTS / slug
    meta = frontmatter(read_text(folder / "profile.md"))
    questions = read_text(folder / "kb" / "questions.md")
    onboarding = read_text(folder / "onboarding.md")
    return {
        "slug": slug, "exists": folder.is_dir(), "meta": meta,
        "open_questions": len(OPEN_Q.findall(questions)),
        "questions": [re.sub(r"^\s*[*-] \[ \]\s*", "", l) for l in questions.splitlines() if OPEN_Q.match(l)],
        "onboarding_done": len(DONE_Q.findall(onboarding)),
        "onboarding_total": len(DONE_Q.findall(onboarding)) + len(OPEN_Q.findall(onboarding)),
        "sample": meta.get("sample", "").lower() == "true",
    }


def clients() -> dict[str, Any]:
    path, sample = live_or_example(CLIENTS / "INDEX.md", CLIENTS / "INDEX.example.md")
    rows, listed = [], set()
    for cells in md_table(read_text(path)) if path else []:
        cells += [""] * (6 - len(cells))
        link = re.match(r"\[([^\]]+)\]\(([^)/]+)/", cells[0])
        name, slug = (link.group(1), link.group(2)) if link else (cells[0], "")
        if slug and not SLUG.fullmatch(slug):
            slug = ""
        prof = client_profile(slug) if slug else None
        meta = prof["meta"] if prof else {}
        listed.add(slug)
        rows.append({
            "name": name, "slug": slug, "platform": meta.get("platforms") or cells[1],
            "services": meta.get("services") or cells[2], "status": meta.get("status") or cells[3],
            "va_lead": meta.get("va_lead") or cells[4], "next_action": meta.get("next_action") or cells[5],
            "open_questions": prof["open_questions"] if prof else 0,
            "sample": sample or bool(prof and prof["sample"]),
        })
    for folder in sorted(CLIENTS.iterdir()) if CLIENTS.is_dir() else []:
        slug = folder.name
        if folder.is_dir() and SLUG.fullmatch(slug) and slug not in listed and (folder / "profile.md").exists():
            prof = client_profile(slug)
            meta = prof["meta"]
            rows.append({"name": meta.get("name", slug), "slug": slug, "platform": meta.get("platforms", ""),
                         "services": meta.get("services", ""), "status": meta.get("status", ""),
                         "va_lead": meta.get("va_lead", ""), "next_action": "Add this client to clients/INDEX.md",
                         "open_questions": prof["open_questions"], "sample": prof["sample"]})
    return {"sample": sample, "source": str(path.relative_to(ROOT)) if path and path.is_relative_to(ROOT) else
            (path.name if path else ""), "rows": rows}


# ---------------------------------------------------------------- inventory

def inventory(now: datetime) -> dict[str, Any]:
    live = (INVENTORY / "master" / "master.csv").exists()
    root = INVENTORY if live else INVENTORY / "examples"
    master = read_csv_rows(root / "master" / "master.csv")
    processed = read_csv_rows(root / "master" / "processed.csv")
    done_sources = {Path(p.get("source_file", "")).name for p in processed}
    drop = INVENTORY / "drop"
    waiting = sorted(p.name for p in drop.iterdir() if p.is_file() and p.name not in ("README.md", ".gitkeep")
                     and not p.name.startswith(".") and p.name not in done_sources) if drop.is_dir() else []

    week_ago = now - timedelta(days=7)
    recent_ids = set()
    for p in processed:
        try:
            when = datetime.fromisoformat(p.get("processed_at", ""))
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if when >= week_ago or not live:  # the sample is always "this week"
            recent_ids.add((p.get("invoice_id"), p.get("supplier")))
    by_client: dict[str, dict[str, int]] = {}
    for r in master:
        if (r.get("invoice_id"), r.get("supplier")) not in recent_ids:
            continue
        slot = by_client.setdefault(r.get("client") or "(no client yet)", {"ready": 0, "needs_review": 0, "qty": 0})
        ready = r.get("status") == "ready"
        slot["ready" if ready else "needs_review"] += 1
        try:
            slot["qty"] += int(r.get("qty") or 0) if ready else 0
        except ValueError:
            pass

    held = []
    for path in sorted((root / "review").glob("*.csv")) if (root / "review").is_dir() else []:
        for r in read_csv_rows(path):
            held.append({**r, "file": path.name})
    sheets = []
    for path in (root / "clients").glob("*/sheets/*.csv") if (root / "clients").is_dir() else []:
        lines = max(len(read_text(path).strip().splitlines()) - 1, 0)
        sheets.append({"client": path.parent.parent.name, "file": path.name, "lines": lines,
                       "path": str(path.relative_to(INVENTORY))})
    sheets.sort(key=lambda s: s["file"], reverse=True)
    return {"sample": not live, "drop_waiting": waiting, "invoices_this_week": len(recent_ids),
            "by_client": by_client, "held": held, "sheets": sheets[:20], "master_lines": len(master)}


# ---------------------------------------------------------------- team, growth, ops

def team(client_rows: list[dict[str, Any]]) -> dict[str, Any]:
    path, sample = live_or_example(TEAM / "roster.csv", TEAM / "roster.example.csv")
    roster = read_csv_rows(path)
    coverage: dict[str, list[str]] = {}
    for person in roster:
        for slug in [c.strip() for c in (person.get("clients") or "").split(";") if c.strip()]:
            coverage.setdefault(slug, []).append(person.get("name", ""))
    gaps = [c["slug"] or c["name"] for c in client_rows if (c["slug"] or c["name"]) not in coverage
            and c["status"] not in ("ended", "paused")]
    qa_path, qa_sample = live_or_example(TEAM / "qa" / "qa-log.csv", TEAM / "qa" / "qa-log.example.csv")
    return {"sample": sample, "roster": roster, "coverage": coverage, "gaps": gaps,
            "qa": read_csv_rows(qa_path)[-10:], "qa_sample": qa_sample}


def number(text: str) -> float:
    try:
        return float(re.sub(r"[^0-9.]", "", text) or 0)
    except ValueError:
        return 0.0


def growth() -> dict[str, Any]:
    path, sample = live_or_example(GROWTH / "pipeline.md", GROWTH / "pipeline.example.md")
    rows = []
    for cells in md_table(read_text(path)) if path else []:
        cells += [""] * (5 - len(cells))
        rows.append({"prospect": cells[0], "stage": cells[1].lower(), "value": number(cells[2]),
                     "next_step": cells[3], "owner": cells[4]})
    stages = {s: {"count": 0, "value": 0.0} for s in STAGES}
    for r in rows:
        slot = stages.setdefault(r["stage"] or "lead", {"count": 0, "value": 0.0})
        slot["count"] += 1
        slot["value"] += r["value"]
    open_value = sum(v["value"] for s, v in stages.items() if s not in ("won", "lost"))
    return {"sample": sample, "rows": rows, "stages": stages, "open_value": open_value}


def ops() -> dict[str, Any]:
    path, sample = live_or_example(OPS / "billing.csv", OPS / "billing.example.csv")
    tools = [{"tool": c[0], "for": c[1] if len(c) > 1 else "", "owner": c[2] if len(c) > 2 else "",
              "renews": c[4] if len(c) > 4 else ""} for c in md_table(read_text(OPS / "tools.md"))]
    return {"sample": sample, "billing": read_csv_rows(path), "tools": tools}


# ---------------------------------------------------------------- memory

def memory_dir() -> tuple[Path, bool]:
    if MEMORY.is_dir() and (MEMORY / "MEMORY.md").exists():
        return MEMORY, False
    return MEMORY_SEED, True


def memories() -> dict[str, Any]:
    root, starter = memory_dir()
    items = []
    for path in sorted(root.glob("*.md")) if root.is_dir() else []:
        if path.name == "MEMORY.md" or not SAFE_NAME.fullmatch(path.name):
            continue
        meta = frontmatter(read_text(path))
        items.append({"file": path.name, "name": meta.get("name", path.stem), "description": meta.get("description", ""),
                      "type": meta.get("type", ""), "space": meta.get("space", ""), "client": meta.get("client", "")})
    return {"starter": starter, "items": items}


def memory_file(name: str) -> tuple[str, str] | None:
    if not SAFE_NAME.fullmatch(name) or ".." in name or not name.endswith(".md"):
        return None
    root = memory_dir()[0]
    try:
        resolved = (root / name).resolve()
    except OSError:
        return None
    if not resolved.is_file() or not resolved.is_relative_to(root.resolve()):
        return None
    return name, read_text(resolved)


# ---------------------------------------------------------------- state

def state(now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    jobs = ledger()
    per_space: dict[str, dict[str, int]] = {s: {"open": 0, "done": 0, "failed": 0} for s in SPACE_LABELS}
    for j in jobs:
        slot = per_space.setdefault(j.get("space") or "hq", {"open": 0, "done": 0, "failed": 0})
        status = j.get("status", "")
        slot["done" if status == "done" else "failed" if status in ("failed", "abandoned") else "open"] += 1
    c = clients()
    return {"agents": agents(), "approvals": approvals(), "ledger": jobs, "per_space": per_space,
            "clients": c, "inventory": inventory(now), "team": team(c["rows"]), "growth": growth(),
            "ops": ops(), "memory": memories()}


# ---------------------------------------------------------------- html

def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def money(value: Any) -> str:
    try:
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "n/a"


def sample_tag(flag: Any) -> str:
    return '<span class="tag">SAMPLE</span>' if flag else ""


def pill(text: str, cls: str = "") -> str:
    return f'<span class="pill {esc(cls or text.replace(" ", "_"))}">{esc(text)}</span>' if text else ""


NAV = [("/", "Overview"), ("/clients", "Clients"), ("/inventory", "Inventory"), ("/team", "Team"),
       ("/growth", "Growth"), ("/ops", "Ops"), ("/memory", "Memory"), ("/ledger", "Ledger")]

CSS = """
:root { --bg:#f5f7f8; --card:#fff; --ink:#303030; --muted:#66757d; --line:#e1e8eb; --accent:#E34949;
  --slate:#5C7988; --sky:#A1D4DC; --link:#9F1D22; --ok:#2f8a5f; --warn:#c98a1b; --bad:#c23b3b;
  --okbg:#dcefe4; --okink:#1f5c3f; --badbg:#f8dcdc; --badink:#7a2020; --warnbg:#f7ebd2; --warnink:#6e4c0f; --skybg:#e3f3f6; }
@media (prefers-color-scheme: dark) { :root { --bg:#161a1c; --card:#1f2528; --ink:#eef2f3; --muted:#9aa9b0;
  --line:#33403f; --accent:#f06a6a; --slate:#8fb0c0; --link:#f0a0a3; --okbg:#1d3a2c; --okink:#a7dcbd;
  --badbg:#46252a; --badink:#f2b3b3; --warnbg:#3f3220; --warnink:#f0d29a; --skybg:#1d3236; } }
* { box-sizing:border-box }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 Montserrat, "Helvetica Neue", Arial, sans-serif }
header { padding:18px 24px 6px; display:flex; align-items:baseline; gap:12px; flex-wrap:wrap }
h1 { margin:0; font-size:20px; letter-spacing:.08em; text-transform:uppercase }
h1 span { background:var(--accent); color:#fff; border-radius:99px; padding:1px 10px; margin-left:4px }
nav { display:flex; gap:6px; flex-wrap:wrap; padding:6px 24px 0 }
nav a { color:var(--ink); text-decoration:none; padding:5px 12px; border-radius:99px; border:1px solid var(--line);
  background:var(--card); font-size:13px; letter-spacing:.04em; text-transform:uppercase }
nav a.on { background:var(--slate); border-color:var(--slate); color:#fff }
main { display:grid; gap:16px; padding:16px 24px 32px; grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr)) }
section { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px; min-width:0 }
h2 { margin:0 0 10px; font-size:13px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted) }
h3 { margin:14px 0 6px; font-size:15px }
a { color:var(--link) } a:hover { color:var(--slate) }
.scroll { overflow-x:auto }
table { width:100%; border-collapse:collapse } td, th { padding:6px; border-top:1px solid var(--line); vertical-align:top }
th { text-align:left; font-size:12px; color:var(--muted); font-weight:600; white-space:nowrap }
td.n, th.n { text-align:right; white-space:nowrap }
.muted { color:var(--muted) } code { font-size:12px }
.big { display:flex; gap:22px; flex-wrap:wrap; margin-bottom:8px } .big div b { display:block; font-size:26px }
.dot { display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; background:var(--muted) }
.dot.working { background:var(--warn) } .dot.idle, .dot.done { background:var(--ok) } .dot.blocked { background:var(--bad) }
.pill { font-size:12px; padding:1px 8px; border-radius:99px; background:var(--line); white-space:nowrap }
.pill.done, .pill.ready, .pill.active, .pill.won, .pill.pass { background:var(--okbg); color:var(--okink) }
.pill.failed, .pill.blocked, .pill.needs_review, .pill.lost, .pill.gap { background:var(--badbg); color:var(--badink) }
.pill.waiting_approval, .pill.onboarding, .pill.proposal_sent, .pill.package_ready, .pill.fixed { background:var(--warnbg); color:var(--warnink) }
.pill.running, .pill.dispatched, .pill.researching, .pill.negotiating { background:var(--skybg) }
.tag { font-size:11px; background:var(--warn); color:#fff; padding:1px 6px; border-radius:4px; margin-left:6px;
  letter-spacing:0; text-transform:none }
ul { margin:0; padding-left:18px } li { margin:6px 0 }
.wide { grid-column:1/-1 }
.spaces { display:grid; gap:10px; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)) }
.space { border:1px solid var(--line); border-radius:12px; padding:12px; text-decoration:none; color:var(--ink) }
.space b { display:block; font-size:22px }
.filters { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px }
.filters a { font-size:13px; padding:2px 10px; border:1px solid var(--line); border-radius:99px; text-decoration:none }
.filters a.on { background:var(--sky); color:#303030; border-color:var(--sky) }
pre.doc { white-space:pre-wrap; overflow-wrap:anywhere; font:14px/1.55 ui-monospace, monospace; margin:0 }
@media (max-width:600px) { header, nav { padding-left:16px; padding-right:16px } main { padding:12px 16px 28px } }
"""


def shell(title: str, path: str, body: str, refresh: bool = True) -> str:
    nav = "".join(f'<a href="{href}"{" class=on" if href == path else ""}>{esc(label)}</a>' for href, label in NAV)
    meta = '<meta http-equiv="refresh" content="30">' if refresh else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta}<title>{esc(title)} | ThinkSocial HQ</title>
<style>{CSS}</style></head><body>
<header><h1>ThinkSocial <span>HQ</span></h1><span class="muted">The agency's agent desk. Internal to ThinkSocial.</span></header>
<nav>{nav}</nav>
<main>
{body}
</main></body></html>"""


def table(head: list[tuple[str, str]], rows: list[str], empty: str) -> str:
    th = "".join(f'<th class="{cls}">{esc(label)}</th>' for label, cls in head)
    body = "".join(rows) or f'<tr><td colspan="{len(head)}" class="muted">{empty}</td></tr>'
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def job_rows(jobs: list[dict[str, Any]], show_space: bool = True) -> list[str]:
    out = []
    for j in jobs:
        where = esc(SPACE_LABELS.get(j.get("space", "hq"), j.get("space", "")))
        if j.get("client"):
            where += f' / <a href="/client/{esc(j["client"])}">{esc(j["client"])}</a>'
        out.append(f'<tr><td class="muted">{esc(str(j.get("updated", ""))[5:16].replace("T", " "))}</td>'
                   + (f"<td>{where}</td>" if show_space else "")
                   + f'<td>{esc(j.get("agent"))}</td><td>{pill(str(j.get("status", "")))}</td>'
                   f'<td>{esc(j.get("title"))}<br><span class="muted">{esc(j.get("outcome", ""))}</span></td></tr>')
    return out


def jobs_table(jobs: list[dict[str, Any]], show_space: bool = True, empty: str = "No work recorded yet.") -> str:
    head = [("Updated", "")] + ([("Space", "")] if show_space else []) + [("Agent", ""), ("Status", ""), ("Job", "")]
    return table(head, job_rows(jobs, show_space), empty)


def space_work(s: dict[str, Any], spaces: list[str]) -> str:
    jobs = [j for j in s["ledger"] if (j.get("space") or "hq") in spaces][:15]
    names = " and ".join(SPACE_LABELS[x] for x in spaces)
    link = "/ledger?" + urlencode({"space": spaces[0]})
    return (f'<section class="wide" id="work"><h2>Work in {esc(names)} (ledger)</h2>'
            f'{jobs_table(jobs, show_space=len(spaces) > 1, empty="Nothing recorded in this space yet.")}'
            f'<p class="muted">Recorded with <code>scripts/ledger start</code> from this space\'s folder. '
            f'<a href="{link}">All of it</a></p></section>')


def overview_page(s: dict[str, Any]) -> str:
    agent_rows = "".join(
        f'<tr><td>{esc(a.get("name"))}</td><td><span class="dot {esc(a.get("state"))}"></span>{esc(a.get("state"))}</td>'
        f'<td class="muted">{esc(a.get("detail"))}</td></tr>' for a in s["agents"]
    ) or '<tr><td colspan="3" class="muted">No agents running. Start them with <code>scripts/hq start</code>.</td></tr>'
    approval_rows = "".join(
        f'<li><b>{esc(a["title"])}</b><br><span class="muted">{esc(a["from"])} {esc(a["kind"])} {esc(a["client"])} '
        f'{esc(a["asked"])} <code>{esc(a["file"])}</code></span></li>' for a in s["approvals"]
    ) or '<li class="muted">Nothing is waiting on you.</li>'
    cards = []
    for space, label in SPACE_LABELS.items():
        if space == "growth-research":
            continue
        counts = s["per_space"].get(space, {})
        if space == "growth":
            r = s["per_space"].get("growth-research", {})
            counts = {k: counts.get(k, 0) + r.get(k, 0) for k in ("open", "done", "failed")}
        cards.append(f'<a class="space" href="{SPACE_PAGES[space]}"><span class="muted">{esc(label)}</span>'
                     f'<b>{counts.get("open", 0)}</b><span class="muted">open, {counts.get("done", 0)} done'
                     f'{", " + str(counts["failed"]) + " failed" if counts.get("failed") else ""}</span></a>')
    inv, c = s["inventory"], s["clients"]
    body = f"""<section><h2>Waiting on Desiree</h2><ul>{approval_rows}</ul></section>
<section><h2>Agents</h2><table>{agent_rows}</table></section>
<section><h2>At a glance</h2><div class="big">
<div><b>{len(c["rows"])}</b><span class="muted">clients {sample_tag(c["sample"])}</span></div>
<div><b>{len(inv["drop_waiting"])}</b><span class="muted">invoices to read</span></div>
<div><b>{len(inv["held"])}</b><span class="muted">lines held {sample_tag(inv["sample"])}</span></div>
<div><b>{money(s["growth"]["open_value"])}</b><span class="muted">open pipeline {sample_tag(s["growth"]["sample"])}</span></div>
</div></section>
<section class="wide"><h2>Work per space</h2><div class="spaces">{"".join(cards)}</div></section>
{space_work(s, ["hq"])}
<section class="wide"><h2>Recent work, every space</h2>{jobs_table(s["ledger"][:12])}</section>"""
    return shell("Overview", "/", body)


def clients_page(s: dict[str, Any]) -> str:
    c = s["clients"]
    rows = []
    for r in c["rows"]:
        name = f'<a href="/client/{esc(r["slug"])}">{esc(r["name"])}</a>' if r["slug"] else esc(r["name"])
        q = f'<b>{r["open_questions"]}</b>' if r["open_questions"] else "0"
        rows.append(f'<tr><td>{name}{sample_tag(r["sample"])}</td><td>{esc(r["platform"])}</td>'
                    f'<td>{esc(r["services"])}</td><td>{pill(r["status"])}</td><td>{esc(r["va_lead"])}</td>'
                    f'<td class="n">{q}</td><td>{esc(r["next_action"])}</td></tr>')
    body = f"""<section class="wide"><h2>Clients {sample_tag(c["sample"])}</h2>
{table([("Client", ""), ("Platform", ""), ("Services", ""), ("Status", ""), ("VA lead", ""), ("Open KB questions", "n"),
        ("Next action", "")], rows, "No clients yet. Run <code>scripts/new-client &lt;slug&gt;</code>.")}
<p class="muted">From <code>{esc(c["source"])}</code> and each client's <code>profile.md</code>. Open KB questions are the
unticked lines in <code>kb/questions.md</code>.</p></section>
{space_work(s, ["clients"])}"""
    return shell("Clients", "/clients", body)


def client_page(s: dict[str, Any], slug: str) -> str | None:
    if not SLUG.fullmatch(slug) or not (CLIENTS / slug / "profile.md").is_file():
        return None
    prof = client_profile(slug)
    m = prof["meta"]
    fields = [("Status", pill(m.get("status", ""))), ("Platforms", esc(m.get("platforms"))),
              ("Services", esc(m.get("services"))), ("Plan", esc(m.get("plan"))), ("Start date", esc(m.get("start_date"))),
              ("VA lead", esc(m.get("va_lead"))), ("Holding replies", esc(m.get("holding_replies", "no"))),
              ("Next action", esc(m.get("next_action")))]
    facts = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in fields)
    questions = "".join(f"<li>{esc(q)}</li>" for q in prof["questions"]) or '<li class="muted">No open questions.</li>'
    jobs = [j for j in s["ledger"] if j.get("client") == slug]
    sheets = [x for x in s["inventory"]["sheets"] if x["client"] == slug]
    sheet_rows = "".join(f'<li><code>{esc(x["path"])}</code> {x["lines"]} lines</li>' for x in sheets) \
        or '<li class="muted">No sheets yet.</li>'
    body = f"""<section><h2>{esc(m.get("name", slug))} {sample_tag(prof["sample"])}</h2><table>{facts}</table>
<p class="muted">Onboarding {prof["onboarding_done"]} of {prof["onboarding_total"]} done.
Folder <code>clients/{esc(slug)}/</code></p></section>
<section><h2>Open questions for the owner</h2><ul>{questions}</ul></section>
<section><h2>Inventory sheets {sample_tag(s["inventory"]["sample"])}</h2><ul>{sheet_rows}</ul></section>
<section class="wide"><h2>This client's ledger</h2>{jobs_table(jobs, empty="Nothing recorded for this client yet.")}
<p class="muted">Same view in the terminal: <code>scripts/ledger view --client {esc(slug)}</code></p></section>"""
    return shell(m.get("name", slug), "/clients", body)


def inventory_page(s: dict[str, Any]) -> str:
    inv = s["inventory"]
    drop = "".join(f"<li><code>{esc(n)}</code></li>" for n in inv["drop_waiting"]) \
        or '<li class="muted">Nothing waiting in <code>inventory/drop/</code>.</li>'
    by_client = [f'<tr><td>{esc(k)}</td><td class="n">{v["ready"]}</td><td class="n">{v["needs_review"]}</td>'
                 f'<td class="n">{v["qty"]}</td></tr>' for k, v in sorted(inv["by_client"].items())]
    held = [f'<tr><td><code>{esc(h["file"])}</code></td><td>{esc(h.get("client") or "none")}</td><td>{esc(h.get("sku"))}</td>'
            f'<td>{esc(h.get("item"))}</td><td class="n">{esc(h.get("qty"))}</td><td class="n">{esc(h.get("confidence"))}</td>'
            f'<td>{esc(h.get("reason"))}</td></tr>' for h in inv["held"]]
    sheets = [f'<tr><td>{esc(x["client"])}</td><td><code>{esc(x["file"])}</code></td><td class="n">{x["lines"]}</td></tr>'
              for x in inv["sheets"]]
    tag = sample_tag(inv["sample"])
    body = f"""<section><h2>Invoices not read yet</h2><div class="big"><div><b>{len(inv["drop_waiting"])}</b>
<span class="muted">in drop/</span></div></div><ul>{drop}</ul><p class="muted">Run <code>/inventory-run</code> in HQ.</p></section>
<section><h2>This week by client {tag}</h2>
{table([("Client", ""), ("Lines ready", "n"), ("Held", "n"), ("Units ready", "n")], by_client, "No invoices read this week.")}
<p class="muted">{inv["invoices_this_week"]} invoices read in the last 7 days; {inv["master_lines"]} lines in the master sheet.</p></section>
<section class="wide"><h2>Lines held for a person {tag}</h2>
{table([("Review file", ""), ("Client", ""), ("SKU", ""), ("Item", ""), ("Qty", "n"), ("Confidence", "n"), ("Why", "")],
       held, "Nothing held. Every line read cleanly.")}
<p class="muted">Check each against the invoice image, then move the file to <code>inventory/review/done/</code>
(<code>team/sops/inventory-review.md</code>).</p></section>
<section class="wide"><h2>Sheets ready {tag}</h2>
{table([("Client", ""), ("Sheet", ""), ("Lines", "n")], sheets, "No sheets yet.")}
<p class="muted">Each sheet copies the column order of that client's last sheet. Sheets are never overwritten.</p></section>
{space_work(s, ["inventory"])}"""
    return shell("Inventory", "/inventory", body)


def team_page(s: dict[str, Any]) -> str:
    t = s["team"]
    roster = [f'<tr><td>{esc(p.get("name"))}</td><td>{esc(p.get("role"))}</td><td>{esc(p.get("clients"))}</td>'
              f'<td class="n">{esc(p.get("hours"))}</td><td>{esc(p.get("tools_access"))}</td>'
              f'<td>{esc(p.get("start_date"))}</td></tr>' for p in t["roster"]]
    cover = [f'<tr><td>{esc(k)}</td><td>{esc(", ".join(v))}</td></tr>' for k, v in sorted(t["coverage"].items())]
    cover += [f'<tr><td>{esc(g)}</td><td>{pill("no VA assigned", "gap")}</td></tr>' for g in t["gaps"]]
    qa = [f'<tr><td>{esc(q.get("date"))}</td><td>{esc(q.get("va"))}</td><td>{esc(q.get("client"))}</td>'
          f'<td>{esc(q.get("item"))}</td><td>{pill(q.get("result", ""))}</td></tr>' for q in t["qa"]]
    body = f"""<section class="wide"><h2>Roster {sample_tag(t["sample"])}</h2>
{table([("Name", ""), ("Role", ""), ("Clients", ""), ("Hours", "n"), ("Tools", ""), ("Started", "")], roster,
       "No roster yet. Copy <code>team/roster.example.csv</code> to <code>team/roster.csv</code>.")}</section>
<section><h2>Who covers which client {sample_tag(t["sample"])}</h2>{table([("Client", ""), ("VAs", "")], cover, "No clients.")}</section>
<section><h2>QA log {sample_tag(t["qa_sample"])}</h2>{table([("Date", ""), ("VA", ""), ("Client", ""), ("Item", ""), ("Result", "")], qa,
       "No spot checks yet.")}</section>
{space_work(s, ["team"])}"""
    return shell("Team", "/team", body)


def growth_page(s: dict[str, Any]) -> str:
    g = s["growth"]
    stage_rows = [f'<tr><td>{pill(k)}</td><td class="n">{v["count"]}</td><td class="n">{money(v["value"])}</td></tr>'
                  for k, v in g["stages"].items() if v["count"]]
    rows = [f'<tr><td>{esc(r["prospect"])}</td><td>{pill(r["stage"])}</td><td class="n">{money(r["value"])}</td>'
            f'<td>{esc(r["next_step"])}</td><td>{esc(r["owner"])}</td></tr>' for r in g["rows"]]
    tag = sample_tag(g["sample"])
    body = f"""<section><h2>Pipeline by stage {tag}</h2><div class="big"><div><b>{money(g["open_value"])}</b>
<span class="muted">open monthly value</span></div><div><b>{len(g["rows"])}</b><span class="muted">prospects</span></div></div>
{table([("Stage", ""), ("Prospects", "n"), ("Value", "n")], stage_rows, "Empty pipeline.")}</section>
<section class="wide"><h2>Every prospect {tag}</h2>
{table([("Prospect", ""), ("Stage", ""), ("Value", "n"), ("Next step", ""), ("Owner", "")], rows,
       "No prospects. Drop a store link into <code>/pipeline</code>.")}
<p class="muted">From <code>growth/pipeline.md</code>. Outreach drafts in <code>growth/outreach/</code> are never sent by an agent.</p></section>
{space_work(s, ["growth", "growth-research"])}"""
    return shell("Growth", "/growth", body)


def ops_page(s: dict[str, Any]) -> str:
    o = s["ops"]
    tools = [f'<tr><td>{esc(t["tool"])}</td><td>{esc(t["for"])}</td><td>{esc(t["owner"])}</td><td>{esc(t["renews"])}</td></tr>'
             for t in o["tools"]]
    bills = [f'<tr><td>{esc(b.get("client"))}</td><td>{esc(b.get("plan"))}</td><td class="n">{money(b.get("monthly_price"))}</td>'
             f'<td>{esc(b.get("last_invoice"))}</td><td>{pill(b.get("status", ""))}</td></tr>' for b in o["billing"]]
    body = f"""<section class="wide"><h2>Billing tracker {sample_tag(o["sample"])}</h2>
{table([("Client", ""), ("Plan", ""), ("Monthly", "n"), ("Last invoice", ""), ("Status", "")], bills, "No billing rows.")}</section>
<section class="wide"><h2>Tool stack</h2>{table([("Tool", ""), ("For", ""), ("Owner", ""), ("Renews", "")], tools, "No tools listed.")}
<p class="muted">Logins live in 1Password, never here (<code>ops/vault-policy.md</code>).</p></section>
{space_work(s, ["ops"])}"""
    return shell("Ops", "/ops", body)


def memory_page(s: dict[str, Any]) -> str:
    mem = s["memory"]
    tag = '<span class="tag">STARTER</span>' if mem["starter"] else ""
    lines = [f'<tr><td><a href="/memory/{esc(m["file"])}">{esc(m["name"])}</a></td><td>{esc(m["type"])}</td>'
             f'<td>{esc(m["space"])}</td><td>{esc(m["client"])}</td><td>{esc(m["description"])}</td></tr>'
             for m in mem["items"]]
    note = ("These are the starter memories in <code>memory-seed/</code>. Run <code>./setup.sh</code> "
            "to copy them into <code>memory/</code>." if mem["starter"] else
            "Read only. Teach the agents with <code>/remember</code> in HQ.")
    body = f"""<section class="wide"><h2>Memory {tag}</h2>
{table([("Name", ""), ("Type", ""), ("Space", ""), ("Client", ""), ("Description", "")], lines, "No memories yet.")}
<p class="muted">{note} Each space's <code>CLAUDE.md</code> lists the memories tagged to it.</p></section>"""
    return shell("Memory", "/memory", body)


def memory_doc_page(name: str, text: str) -> str:
    body = (f'<section class="wide"><h2>{esc(name)}</h2><pre class="doc">{esc(text)}</pre>'
            f'<p><a href="/memory">All memories</a></p></section>')
    return shell(name, "/memory", body, refresh=False)


def ledger_page(s: dict[str, Any], query: dict[str, list[str]]) -> str:
    space = (query.get("space") or [""])[0]
    client = (query.get("client") or [""])[0]
    jobs = [j for j in s["ledger"] if (not space or (j.get("space") or "hq") == space)
            and (not client or j.get("client") == client)]
    links = [f'<a href="/ledger"{" class=on" if not space and not client else ""}>All</a>']
    links += [f'<a href="/ledger?space={k}"{" class=on" if k == space else ""}>{esc(v)}</a>' for k, v in SPACE_LABELS.items()]
    what = f" for {SPACE_LABELS.get(space, space)}" if space else (f" for {client}" if client else "")
    body = f"""<section class="wide"><h2>Ledger{esc(what)}</h2><div class="filters">{"".join(links)}</div>
{jobs_table(jobs, empty="No jobs match.")}
<p class="muted">Records are in <code>work/</code>. Each job carries its space and folder, and its client when it has one.</p></section>"""
    return shell("Ledger", "/ledger", body)


# ---------------------------------------------------------------- server

PAGES = {"/": overview_page, "/index.html": overview_page, "/clients": clients_page, "/inventory": inventory_page,
         "/team": team_page, "/growth": growth_page, "/ops": ops_page, "/memory": memory_page}


class Handler(BaseHTTPRequestHandler):
    def send(self, body: bytes, kind: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        url = urlsplit(self.path)
        path = url.path
        parts = [unquote(p) for p in path.split("/")[1:]]
        if path.startswith("/api/state"):
            self.send(json.dumps(state(), default=str).encode(), "application/json")
        elif path in PAGES:
            self.send(PAGES[path](state()).encode(), "text/html; charset=utf-8")
        elif path == "/ledger":
            self.send(ledger_page(state(), parse_qs(url.query)).encode(), "text/html; charset=utf-8")
        elif len(parts) == 2 and parts[0] == "client":
            page = client_page(state(), parts[1])
            if page is None:
                self.send_error(404)
                return
            self.send(page.encode(), "text/html; charset=utf-8")
        elif len(parts) == 2 and parts[0] == "memory":
            doc = memory_file(parts[1])
            if not doc:
                self.send_error(404)
                return
            self.send(memory_doc_page(*doc).encode(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def log_message(self, *args: Any) -> None:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="ThinkSocial HQ dashboard")
    parser.add_argument("--port", type=int, default=int(os.environ.get("HQ_DASHBOARD_PORT", 8765)))
    parser.add_argument("--once", action="store_true", help="print the data as JSON and exit")
    args = parser.parse_args()
    if args.once:
        print(json.dumps(state(), indent=2, default=str))
        return 0
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"ThinkSocial HQ dashboard: http://localhost:{args.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
