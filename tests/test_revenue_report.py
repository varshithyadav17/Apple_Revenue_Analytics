import csv
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("revenue", ROOT / "apple_financial_report.py")
revenue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(revenue)


class RevenueReportTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.folder = Path(self.sandbox.name)
        for path in (ROOT / "data").iterdir():
            shutil.copy(path, self.folder / path.name)

    def tearDown(self):
        self.sandbox.cleanup()

    def products(self):
        return revenue.read_revenue(self.folder / "apple_product_revenue.csv", "Category", revenue.PRODUCTS)

    def alter_csv(self, operation):
        path = self.folder / "apple_product_revenue.csv"
        with path.open(newline="") as handle:
            rows = list(csv.reader(handle))
        operation(rows)
        with path.open("w", newline="") as handle:
            csv.writer(handle).writerows(rows)

    def test_both_views_reconcile_to_reported_controls(self):
        source = json.loads((self.folder / "apple_sources.json").read_text())
        controls = {p["year"]: p["reported_net_sales_usd_m"] for p in source["periods"]}
        regional = revenue.read_revenue(self.folder / "apple_regional_revenue.csv", "Region", revenue.REGIONS)
        self.assertEqual(revenue.totals_and_check(self.products(), controls, "Products"), controls)
        self.assertEqual(revenue.totals_and_check(regional, controls, "Regions"), controls)

    def test_services_growth_and_wearables_decline(self):
        rows = self.products()
        totals = {y: sum(r[y] for r in rows) for y in revenue.YEARS}
        metrics = {r["name"]: r for r in revenue.build_metrics(rows, totals, "Product")}
        self.assertEqual(metrics["Services"]["FY2025_change_USD_M"], 12989)
        self.assertAlmostEqual(metrics["Services"]["FY2025_share_of_net_growth"], 12989 / 25126)
        self.assertLess(metrics["Wearables, Home and Accessories"]["FY2025_share_of_net_growth"], 0)

    def test_zero_prior_revenue_is_unavailable(self):
        row = {"name": "New category", 2023: 0, 2024: 0, 2025: 100}
        result = revenue.build_metrics([row], {2023: 1000, 2024: 1000, 2025: 1100}, "Product")[0]
        self.assertIsNone(result["FY2025_yoy"])
        self.assertEqual(revenue.format_percent(result["FY2025_yoy"]), "N/A")

    def test_missing_category_is_rejected(self):
        self.alter_csv(lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, "missing"):
            self.products()

    def test_duplicate_category_is_rejected(self):
        self.alter_csv(lambda rows: rows[2].__setitem__(0, rows[1][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.products()

    def test_blank_and_nonnumeric_amounts_are_rejected(self):
        for amount in ["", "unknown", "1.5", "-10"]:
            with self.subTest(amount=amount):
                self.alter_csv(lambda rows: rows[1].__setitem__(1, amount))
                with self.assertRaisesRegex(ValueError, "nonnegative integer"):
                    self.products()

    def test_wrong_total_stops_run_before_output(self):
        self.alter_csv(lambda rows: rows[1].__setitem__(3, str(int(rows[1][3]) + 1)))
        output = self.folder / "report-output"
        result = subprocess.run([sys.executable, str(ROOT / "apple_financial_report.py"), "--input-dir", str(self.folder), "--output-dir", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("reported control", result.stderr)
        self.assertFalse(output.exists())

    def test_cli_generates_report_and_metrics(self):
        output = self.folder / "reports"
        result = subprocess.run([sys.executable, str(ROOT / "apple_financial_report.py"), "--input-dir", str(self.folder), "--output-dir", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = (output / "apple_revenue_review.md").read_text(encoding="utf-8")
        self.assertIn("51.7%", report)
        self.assertIn("| FY2023 | 383.3 | N/A |", report)
        with (output / "apple_revenue_metrics.csv").open() as handle:
            self.assertEqual(len(list(csv.DictReader(handle))), 10)


if __name__ == "__main__":
    unittest.main()
