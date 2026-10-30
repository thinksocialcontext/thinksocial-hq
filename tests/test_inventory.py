"""Tests for inventory/tools/invoice_to_rows.py on fake invoices, in a temp inventory folder."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "inventory" / "tools" / "invoice_to_rows.py"
FIX = ROOT / "tests" / "fixtures" / "invoices"
MASTER_HEADER = ["invoice_id", "supplier", "date", "client", "sku", "item", "qty", "unit_cost", "status"]


def rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


class InvoiceToRowsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "rules").mkdir()
        (self.root / "rules" / "alpha-shop.json").write_text(json.dumps({
            "client": "alpha-shop", "sku_map": {"FW1-DRESS-RED-M": "ALP-1001-M"}, "sku_prefixes": ["ALP-", "SHARED-"],
            "suppliers": ["Fake Wholesale One"]}))
        (self.root / "rules" / "beta-shop.json").write_text(json.dumps({
            "client": "beta-shop", "sku_prefixes": ["BET-", "SHARED-", "FW1-"], "item_keywords": ["mystery nothing"]}))
        (self.root / "rules" / "_template.json").write_text(json.dumps({"client": "x", "sku_prefixes": ["ZZZ-"]}))
        alpha = self.root / "clients" / "alpha-shop"
        (alpha / "last").mkdir(parents=True)
        (alpha / "preference.json").write_text(json.dumps({"columns": [
            {"header": "Item", "field": "item"}, {"header": "Store SKU", "field": "client_sku"},
            {"header": "Qty", "field": "qty"}, {"header": "Cost", "field": "unit_cost"},
            {"header": "Supplier", "field": "supplier"}], "sort_by": ["item"]}))
        (alpha / "last" / "2026-09-01-old.csv").write_text("Qty,Item,Store SKU,Bin,Cost\n1,Old thing,ALP-1,A1,2.00\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *invoices, ok=True):
        out = subprocess.run([sys.executable, str(TOOL), "--root", str(self.root), "--json", *map(str, invoices)],
                             capture_output=True, text=True)
        if ok:
            self.assertEqual(out.returncode, 0, out.stderr)
        return out

    def test_attribution_review_and_sheets(self):
        result = json.loads(self.run_tool(FIX / "fake-a.json").stdout)[0]
        master = rows(self.root / "master" / "master.csv")
        self.assertEqual(master[0], MASTER_HEADER)
        by_sku = {r[4]: r for r in master[1:]}
        self.assertEqual(len(by_sku), 7)
        # sku_map beats beta's FW1- prefix
        self.assertEqual(by_sku["FW1-DRESS-RED-M"][3], "alpha-shop")
        self.assertEqual(by_sku["FW1-DRESS-RED-M"][8], "ready")
        self.assertEqual(by_sku["ALP-HAT-01"][3], "alpha-shop")
        self.assertEqual(by_sku["BET-SOCK-02"][3], "beta-shop")
        # two clients claim SHARED-, so a person decides
        self.assertEqual((by_sku["SHARED-01"][3], by_sku["SHARED-01"][8]), ("", "needs_review"))
        # low confidence is held even though beta's FW1- prefix claims it
        self.assertEqual(by_sku["FW1-BAG-TAN"][8], "needs_review")
        # only the supplier rule matches (the weakest level); the _template rules file is ignored
        self.assertEqual((by_sku["ZZZ-999"][3], by_sku["ZZZ-999"][8]), ("alpha-shop", "ready"))
        # 2.5 pins is not a quantity
        self.assertEqual(by_sku["ALP-PIN-07"][8], "needs_review")

        review = {r["sku"]: r for r in csv.DictReader((self.root / "review" / "T-100.csv").read_text().splitlines())}
        self.assertEqual(set(review), {"FW1-BAG-TAN", "SHARED-01", "ALP-PIN-07"})
        self.assertIn("low confidence 0.40", review["FW1-BAG-TAN"]["reason"])
        self.assertEqual(review["FW1-BAG-TAN"]["note"], "torn corner")
        self.assertIn("more than one client", review["SHARED-01"]["reason"])
        self.assertIn("whole number", review["ALP-PIN-07"]["reason"])
        self.assertEqual((result["ready"], result["needs_review"]), (4, 3))

    def test_no_rule_goes_to_review(self):
        inv = self.root / "c.json"
        inv.write_text(json.dumps({"invoice_id": "T-300", "supplier": "Nobody We Know", "date": "2026-10-22",
                                   "lines": [{"sku": "ZZZ-1", "item": "Thing", "qty": 1, "unit_cost": 1, "confidence": 1}]}))
        self.run_tool(inv)
        review = list(csv.DictReader((self.root / "review" / "T-300.csv").read_text().splitlines()))
        self.assertEqual(review[0]["reason"], "no rule matches this line")
        self.assertFalse((self.root / "clients" / "alpha-shop" / "sheets").exists())

    def test_new_sheet_matches_the_last_sheet(self):
        result = json.loads(self.run_tool(FIX / "fake-a.json").stdout)[0]
        sheet = rows(self.root / "clients" / "alpha-shop" / "sheets" / "2026-10-20-T-100.csv")
        self.assertEqual(sheet[0], ["Qty", "Item", "Store SKU", "Bin", "Cost"])  # the last sheet's order, exactly
        self.assertEqual(sheet[1:], [["3", "Bucket Hat", "", "", "7.50"], ["1", "Mystery Item", "", "", "3.00"],
                                     ["5", "Wrap Dress Red M", "ALP-1001-M", "", "18.00"]])  # sorted by item
        self.assertEqual(result["matched_last"], {"clients/alpha-shop/sheets/2026-10-20-T-100.csv": "2026-09-01-old.csv"})
        self.assertTrue(any("'Bin'" in w for w in result["warnings"]))
        self.assertTrue(any("Supplier" in w for w in result["warnings"]))
        # no preference and no last sheet: the default columns
        beta = rows(self.root / "clients" / "beta-shop" / "sheets" / "2026-10-20-T-100.csv")
        self.assertEqual(beta[0][:4], ["item", "sku", "client_sku", "qty"])
        self.assertEqual(len(beta), 2)

    def test_invoice_level_client(self):
        self.run_tool(FIX / "fake-b.json")
        sheet = rows(self.root / "clients" / "beta-shop" / "sheets" / "2026-10-21-T-200.csv")
        self.assertEqual(sheet[1][0], "Silk Scarf")
        self.assertFalse((self.root / "review" / "T-200.csv").exists())

    def test_same_invoice_twice_counts_once(self):
        self.run_tool(FIX / "fake-a.json")
        before = (self.root / "master" / "master.csv").read_text()
        again = json.loads(self.run_tool(FIX / "fake-a.json").stdout)[0]
        self.assertEqual(again["skipped"], "already in the master sheet")
        self.assertEqual((self.root / "master" / "master.csv").read_text(), before)
        self.assertEqual(len(rows(self.root / "master" / "processed.csv")), 2)

    def test_never_overwrites_a_sheet(self):
        sheet = self.root / "clients" / "beta-shop" / "sheets" / "2026-10-21-T-200.csv"
        sheet.parent.mkdir(parents=True)
        sheet.write_text("someone's earlier sheet\n")
        out = self.run_tool(FIX / "fake-b.json", ok=False)
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("never overwritten", out.stderr)
        self.assertEqual(sheet.read_text(), "someone's earlier sheet\n")
        self.assertFalse((self.root / "master" / "master.csv").exists())  # nothing half written

    def test_rejects_a_bad_invoice(self):
        bad = self.root / "bad.json"
        bad.write_text(json.dumps({"invoice_id": "../../x", "supplier": "S", "date": "2026-10-01", "lines": []}))
        out = self.run_tool(bad, ok=False)
        self.assertNotEqual(out.returncode, 0)
        bad.write_text(json.dumps({"invoice_id": "X1", "supplier": "S", "date": "Oct 1", "lines": [{}]}))
        self.assertNotEqual(self.run_tool(bad, ok=False).returncode, 0)

    def test_committed_examples_are_reproducible(self):
        """inventory/examples/ is exactly what the tool makes from the fake example invoices."""
        import shutil
        shutil.rmtree(self.root / "rules")
        shutil.rmtree(self.root / "clients")
        shutil.copytree(ROOT / "inventory" / "rules", self.root / "rules")
        shutil.copytree(ROOT / "inventory" / "clients" / "example-boutique", self.root / "clients" / "example-boutique",
                        ignore=shutil.ignore_patterns("sheets"))
        ex = ROOT / "inventory" / "examples"
        self.run_tool(ex / "extracted" / "INV-EX-1001.json", ex / "extracted" / "INV-EX-1002.json")
        for rel in ("master/master.csv", "review/INV-EX-1001.csv", "review/INV-EX-1002.csv",
                    "clients/example-boutique/sheets/2026-10-26-INV-EX-1001.csv",
                    "clients/example-boutique/sheets/2026-10-27-INV-EX-1002.csv"):
            self.assertEqual((self.root / rel).read_text(), (ex / rel).read_text(), rel)


if __name__ == "__main__":
    unittest.main()
