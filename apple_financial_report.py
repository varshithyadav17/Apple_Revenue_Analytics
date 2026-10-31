"""Validate Apple's FY2023–FY2025 revenue extracts and build a comparison report."""

import argparse
import csv
import json
from pathlib import Path
import sys

YEARS = (2023, 2024, 2025)
PRODUCTS = {"iPhone", "Mac", "iPad", "Wearables, Home and Accessories", "Services"}
REGIONS = {"Americas", "Europe", "Greater China", "Japan", "Rest of Asia Pacific"}


def read_revenue(path, label, expected):
    fields = [label] + [f"FY{year}_USD_M" for year in YEARS]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError(f"{path.name}: expected columns {', '.join(fields)}")
        records = []
        seen = set()
        for line, source in enumerate(reader, start=2):
            name = (source.get(label) or "").strip()
            if name not in expected or name in seen:
                raise ValueError(f"{path.name}:{line}: unknown or duplicate {label}: {name}")
            if None in source:
                raise ValueError(f"{path.name}:{line}: unexpected extra fields")
            record = {"name": name}
            for year, field in zip(YEARS, fields[1:]):
                raw = (source.get(field) or "").strip()
                if not raw.isascii() or not raw.isdigit():
                    raise ValueError(f"{path.name}:{line}: {field} must be a nonnegative integer")
                record[year] = int(raw)
            records.append(record)
            seen.add(name)
    if seen != expected:
        raise ValueError(f"{path.name}: missing {', '.join(sorted(expected - seen))}")
    return records


def totals_and_check(records, controls, label):
    totals = {year: sum(record[year] for record in records) for year in YEARS}
    for year in YEARS:
        if totals[year] != controls[year]:
            raise ValueError(
                f"{label} FY{year} totals {totals[year]:,}; "
                f"reported control is {controls[year]:,} USD millions"
            )
    return totals


def build_metrics(records, totals, view):
    net_change = totals[2025] - totals[2024]
    result = []
    for record in records:
        change = record[2025] - record[2024]
        result.append({
            "view": view,
            "name": record["name"],
            "FY2023_USD_M": record[2023],
            "FY2024_USD_M": record[2024],
            "FY2025_USD_M": record[2025],
            "FY2025_change_USD_M": change,
            "FY2025_yoy": record[2025] / record[2024] - 1 if record[2024] else None,
            "FY2025_share": record[2025] / totals[2025] if totals[2025] else None,
            "FY2025_share_of_net_growth": change / net_change if net_change else None,
        })
    return sorted(result, key=lambda row: row["FY2025_change_USD_M"], reverse=True)


def format_percent(value):
    return "N/A" if value is None else f"{value:.1%}"


def build_report(product_metrics, region_metrics, totals, source):
    products = {row["name"]: row for row in product_metrics}
    regions = {row["name"]: row for row in region_metrics}
    services = products["Services"]
    china = regions["Greater China"]
    share_change = (services["FY2025_share"] - services["FY2024_USD_M"] / totals[2024]) * 100
    lines = [
        "# Apple Inc. revenue review",
        "",
        "FY2023–FY2025. Annual reported net sales. Golla Varshith.",
        "",
        f"FY2025 revenue was **${totals[2025] / 1000:.1f}B**, up "
        f"**{totals[2025] / totals[2024] - 1:.1%}** from FY2024.",
        "",
        f"- Services added ${services['FY2025_change_USD_M'] / 1000:.1f}B, "
        f"accounting for {format_percent(services['FY2025_share_of_net_growth'])} of the net increase.",
        f"- Services represented {services['FY2025_share']:.1%} of revenue, "
        f"a {share_change:+.1f} percentage-point change from FY2024. "
        f"iPhone remained the largest category at {products['iPhone']['FY2025_share']:.1%}.",
        f"- Greater China YoY: {format_percent(china['FY2025_yoy'])}. "
        f"Wearables, Home and Accessories YoY: "
        f"{format_percent(products['Wearables, Home and Accessories']['FY2025_yoy'])}.",
        "",
        "## Annual totals",
        "",
        "| Fiscal year | Net sales ($B) | YoY growth |",
        "| --- | ---: | ---: |",
    ]
    for year in YEARS:
        growth = None if year == 2023 else totals[year] / totals[year - 1] - 1
        lines.append(f"| FY{year} | {totals[year] / 1000:.1f} | {format_percent(growth)} |")
    for title, rows in [("Product categories", product_metrics), ("Regions", region_metrics)]:
        lines += ["", f"## {title}", "", "| Name | FY2025 ($B) | Change ($B) | YoY | Share of sales | Share of net growth |",
                  "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for row in rows:
            lines.append(
                f"| {row['name']} | {row['FY2025_USD_M'] / 1000:.1f} | "
                f"{row['FY2025_change_USD_M'] / 1000:+.1f} | {format_percent(row['FY2025_yoy'])} | "
                f"{format_percent(row['FY2025_share'])} | {format_percent(row['FY2025_share_of_net_growth'])} |"
            )
    lines += [
        "", "## Method", "",
        "YoY = current revenue / prior revenue − 1. Revenue share = category or regional revenue / total sales. "
        "Share of net growth = category or regional FY2025 change / consolidated FY2025 change. "
        "Product and regional tables are two views of the same revenue; they must not be added together.",
        "", "Each extract reconciles independently to reported consolidated revenue in all three years. "
        "FY2023 contains 53 weeks, compared with 52 weeks in FY2024 and FY2025. "
        "FY2023 YoY is unavailable because FY2022 is outside this extract. "
        "No adjustment has been made for the extra week, currency, inflation or product mix.",
        "", "These figures describe revenue, not customer retention, unit sales or profitability. "
        "The extracts are a manually collected historical snapshot; running this script does not fetch new filings.",
        "", f"Source: [Apple FY2025 Form 10-K]({source['url']}), pp. 21–23 and 29.", "",
    ]
    return "\n".join(lines)


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=base / "data")
    parser.add_argument("--output-dir", type=Path, default=base / "reports")
    parser.add_argument("--check-only", action="store_true", help="Validate extracts without writing reports")
    args = parser.parse_args()
    try:
        source = json.loads((args.input_dir / "apple_sources.json").read_text(encoding="utf-8"))
        controls = {period["year"]: period["reported_net_sales_usd_m"] for period in source["periods"]}
        if set(controls) != set(YEARS) or any(not isinstance(v, int) or v <= 0 for v in controls.values()):
            raise ValueError("apple_sources.json: invalid reported controls for FY2023–FY2025")
        products = read_revenue(args.input_dir / "apple_product_revenue.csv", "Category", PRODUCTS)
        regions = read_revenue(args.input_dir / "apple_regional_revenue.csv", "Region", REGIONS)
        totals = totals_and_check(products, controls, "Products")
        totals_and_check(regions, controls, "Regions")
        if args.check_only:
            print("Both revenue extracts reconcile to Apple's reported totals for FY2023, FY2024 and FY2025.")
            return 0
        product_metrics = build_metrics(products, totals, "Product")
        region_metrics = build_metrics(regions, totals, "Region")
        report = build_report(product_metrics, region_metrics, totals, source)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "apple_revenue_review.md").write_text(report, encoding="utf-8")
        with (args.output_dir / "apple_revenue_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
            rows = product_metrics + region_metrics
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(report)
        print(f"Reports saved in {args.output_dir.resolve()}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Revenue report failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
