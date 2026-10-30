#!/usr/bin/env python3
"""Turn one extracted supplier invoice (JSON) into master sheet rows and per client preference sheets.

  python3 tools/invoice_to_rows.py extracted/INV-1001.json [more.json ...]
  python3 tools/invoice_to_rows.py --root /some/inventory --json extracted/INV-1001.json

What it does, per invoice:
  1. Checks every line: a line with confidence under the threshold (default 0.85), no client,
     more than one possible client, or a missing SKU, item or whole number quantity is held for review.
  2. Attributes each line to a client: the line's own "client", else the invoice's "client", else the
     rules in rules/<slug>.json (sku_map beats sku_prefixes beats item_keywords beats suppliers).
  3. Writes clients/<slug>/sheets/<date>-<invoice_id>.csv for each client with ready lines, in that
     client's preference format. When clients/<slug>/last/ holds a previous sheet, the new sheet copies
     its column order exactly, so the person opening it sees the sheet they always get.
  4. Writes review/<invoice_id>.csv with every held line and the reason.
  5. Appends every line to master/master.csv and records the invoice in master/processed.csv.

It never overwrites a file. An invoice already in the master sheet is skipped, so stock is never
counted twice. It never talks to a store. Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MASTER_COLUMNS = ["invoice_id", "supplier", "date", "client", "sku", "item", "qty", "unit_cost", "status"]
PROCESSED_COLUMNS = ["invoice_id", "supplier", "source_file", "processed_at", "lines", "ready", "needs_review"]
REVIEW_COLUMNS = ["invoice_id", "supplier", "date", "client", "sku", "item", "qty", "unit_cost", "confidence",
                  "reason", "note"]
FIELDS = {"invoice_id", "supplier", "date", "client", "sku", "client_sku", "item", "qty", "unit_cost",
          "line_total", "blank"}
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,62}")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")
DEFAULT_ROOT = Path(__file__).resolve().parent.parent


class InvoiceError(Exception):
    pass


# ------------------------------------------------------------------ reading

def load_invoice(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvoiceError(f"{path}: cannot read: {error}") from error
    for key in ("invoice_id", "supplier", "date", "lines"):
        if not data.get(key):
            raise InvoiceError(f"{path}: missing {key}")
    if not SAFE_ID.fullmatch(str(data["invoice_id"])):
        raise InvoiceError(f"{path}: invoice_id must be letters, numbers, dot, dash or underscore")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data["date"])):
        raise InvoiceError(f"{path}: date must be YYYY-MM-DD")
    if not isinstance(data["lines"], list):
        raise InvoiceError(f"{path}: lines must be a list")
    return data


def load_rules(root: Path) -> dict[str, dict[str, Any]]:
    rules = {}
    for path in sorted((root / "rules").glob("*.json")):
        if path.stem.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        slug = data.get("client") or path.stem
        if not SLUG.fullmatch(slug):
            raise InvoiceError(f"{path}: client must be a slug")
        rules[slug] = data
    return rules


def load_preference(root: Path, slug: str) -> dict[str, Any]:
    path = root / "clients" / slug / "preference.json"
    if not path.exists():
        return {"columns": [{"header": c, "field": c} for c in
                            ("item", "sku", "client_sku", "qty", "unit_cost", "invoice_id", "supplier", "date")]}
    pref = json.loads(path.read_text(encoding="utf-8"))
    for col in pref.get("columns", []):
        if col.get("field") not in FIELDS:
            raise InvoiceError(f"{path}: unknown field {col.get('field')!r} (use one of {sorted(FIELDS)})")
    return pref


def last_sheet_header(root: Path, slug: str) -> tuple[list[str] | None, str]:
    folder = root / "clients" / slug / "last"
    sheets = sorted(folder.glob("*.csv")) if folder.is_dir() else []
    if not sheets:
        return None, ""
    with sheets[-1].open(newline="", encoding="utf-8-sig") as handle:
        header = next(csv.reader(handle), None)
    return ([h.strip() for h in header] if header else None), sheets[-1].name


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


# ------------------------------------------------------------------ deciding

def attribute(line: dict[str, Any], invoice: dict[str, Any], rules: dict[str, dict[str, Any]]) -> tuple[str, str]:
    """(client slug or "", reason when it could not decide)."""
    explicit = str(line.get("client") or invoice.get("client") or "").strip()
    if explicit:
        return (explicit, "") if SLUG.fullmatch(explicit) else ("", f"client {explicit!r} is not a slug")
    sku = str(line.get("sku") or "").strip().upper()
    item = str(line.get("item") or "").lower()
    supplier = str(invoice.get("supplier") or "").strip().lower()
    levels: list[set[str]] = [set(), set(), set(), set()]
    for slug, rule in rules.items():
        if sku and sku in {k.upper() for k in rule.get("sku_map", {})}:
            levels[0].add(slug)
        if sku and any(sku.startswith(p.upper()) for p in rule.get("sku_prefixes", []) if p):
            levels[1].add(slug)
        if item and any(k.lower() in item for k in rule.get("item_keywords", []) if k):
            levels[2].add(slug)
        if supplier and supplier in {s.lower() for s in rule.get("suppliers", [])}:
            levels[3].add(slug)
    for found in levels:
        if len(found) == 1:
            return next(iter(found)), ""
        if len(found) > 1:
            return "", "matches more than one client: " + ", ".join(sorted(found))
    return "", "no rule matches this line"


def whole_number(value: Any) -> int | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() and number > 0 else None


def money(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def decide(invoice: dict[str, Any], rules: dict[str, dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    rows = []
    for raw in invoice["lines"]:
        line = raw if isinstance(raw, dict) else {}
        client, why = attribute(line, invoice, rules)
        reasons = [why] if why else []
        try:
            confidence = float(line.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence < threshold:
            reasons.append(f"low confidence {confidence:.2f}")
        qty = whole_number(line.get("qty"))
        if qty is None:
            reasons.append("quantity is not a whole number above zero")
        if not str(line.get("sku") or "").strip():
            reasons.append("no SKU")
        if not str(line.get("item") or "").strip():
            reasons.append("no item name")
        sku = str(line.get("sku") or "").strip()
        sku_map = {k.upper(): v for k, v in rules.get(client, {}).get("sku_map", {}).items()}
        unit = money(line.get("unit_cost"))
        rows.append({
            "invoice_id": invoice["invoice_id"], "supplier": invoice["supplier"], "date": invoice["date"],
            "client": client, "sku": sku, "client_sku": sku_map.get(sku.upper(), ""),
            "item": str(line.get("item") or "").strip(),
            "qty": qty if qty is not None else str(line.get("qty", "")), "unit_cost": unit,
            "line_total": f"{qty * float(unit):.2f}" if qty is not None and unit else "", "blank": "",
            "confidence": f"{confidence:.2f}", "note": str(line.get("note") or ""),
            "status": "needs_review" if reasons else "ready", "reason": "; ".join(reasons),
        })
    return rows


def sheet_columns(pref: dict[str, Any], last: list[str] | None) -> tuple[list[tuple[str, str]], list[str]]:
    """[(header, field)] for the new sheet, and warnings. The last sheet's header order wins."""
    mapping = {c["header"].strip().lower(): c["field"] for c in pref.get("columns", [])}
    if not last:
        return [(c["header"], c["field"]) for c in pref.get("columns", [])], []
    columns, warnings = [], []
    for header in last:
        field = mapping.get(header.lower())
        if field is None:
            warnings.append(f"last sheet column {header!r} has no field in preference.json; left blank")
            field = "blank"
        columns.append((header, field))
    dropped = [c["header"] for c in pref.get("columns", []) if c["header"].strip().lower() not in
               {h.lower() for h in last}]
    if dropped:
        warnings.append("not in the last sheet, so left out: " + ", ".join(dropped))
    return columns, warnings


def sort_rows(rows: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: tuple(str(r.get(k, "")).lower() for k in keys)) if keys else rows


# ------------------------------------------------------------------ writing

def write_new(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    """Create a CSV. Refuses if the file already exists: a sheet is never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = path.open("x", newline="", encoding="utf-8")
    except FileExistsError as error:
        raise InvoiceError(f"{path} already exists; sheets are never overwritten") from error
    with handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def append(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    if not new:
        with path.open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle), [])
        if header != columns:
            raise InvoiceError(f"{path} has columns {header}, expected {columns}")
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        if new:
            writer.writeheader()
        writer.writerows(rows)


def process(path: Path, root: Path, threshold: float, now: str | None = None) -> dict[str, Any]:
    invoice = load_invoice(path)
    master = root / "master" / "master.csv"
    seen = {(r["invoice_id"], r["supplier"]) for r in read_csv(master)}
    if (invoice["invoice_id"], invoice["supplier"]) in seen:
        return {"invoice_id": invoice["invoice_id"], "skipped": "already in the master sheet", "sheets": [],
                "review": "", "ready": 0, "needs_review": 0, "warnings": []}
    rules = load_rules(root)
    rows = decide(invoice, rules, threshold)
    ready = [r for r in rows if r["status"] == "ready"]
    held = [r for r in rows if r["status"] == "needs_review"]

    # plan every file first, so nothing is half written when one would collide
    plans, warnings = [], []
    for slug in sorted({r["client"] for r in ready}):
        pref = load_preference(root, slug)
        last, last_name = last_sheet_header(root, slug)
        columns, notes = sheet_columns(pref, last)
        warnings += [f"{slug}: {n}" for n in notes]
        mine = sort_rows([r for r in ready if r["client"] == slug], pref.get("sort_by", []))
        out = root / "clients" / slug / "sheets" / f"{invoice['date']}-{invoice['invoice_id']}.csv"
        plans.append((out, [h for h, _ in columns], [[r.get(f, "") for _, f in columns] for r in mine], last_name))
    review = root / "review" / f"{invoice['invoice_id']}.csv"
    for out in [p[0] for p in plans] + ([review] if held else []):
        if out.exists():
            raise InvoiceError(f"{out} already exists; sheets are never overwritten")

    for out, header, body, _ in plans:
        write_new(out, header, body)
    if held:
        write_new(review, REVIEW_COLUMNS, [[r.get(c, "") for c in REVIEW_COLUMNS] for r in held])
    append(master, MASTER_COLUMNS, rows)
    append(root / "master" / "processed.csv", PROCESSED_COLUMNS, [{
        "invoice_id": invoice["invoice_id"], "supplier": invoice["supplier"],
        "source_file": invoice.get("source_file", ""), "lines": len(rows), "ready": len(ready),
        "needs_review": len(held),
        "processed_at": now or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")}])
    return {"invoice_id": invoice["invoice_id"], "skipped": "", "ready": len(ready), "needs_review": len(held),
            "sheets": [str(p[0].relative_to(root)) for p in plans],
            "matched_last": {str(p[0].relative_to(root)): p[3] for p in plans if p[3]},
            "review": str(review.relative_to(root)) if held else "", "warnings": warnings}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extracted invoice JSON to master sheet and preference sheets")
    parser.add_argument("invoices", nargs="+", type=Path)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="the inventory folder (default: inventory/)")
    parser.add_argument("--threshold", type=float, default=0.85, help="lines under this confidence go to review")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    results, failed = [], False
    for path in args.invoices:
        try:
            results.append(process(path, args.root, args.threshold))
        except (InvoiceError, OSError, json.JSONDecodeError) as error:
            print(f"invoice_to_rows: {error}", file=sys.stderr)
            failed = True
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if r["skipped"]:
                print(f"{r['invoice_id']}: skipped, {r['skipped']}")
                continue
            print(f"{r['invoice_id']}: {r['ready']} ready, {r['needs_review']} held for review")
            for sheet in r["sheets"]:
                print(f"  sheet  {sheet}")
            if r["review"]:
                print(f"  review {r['review']}")
            for warning in r["warnings"]:
                print(f"  note   {warning}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
