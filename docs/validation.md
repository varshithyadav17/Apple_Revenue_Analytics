# Validation record

Checked on 31 October 2026.

## Local checks

| Component | Check | Result |
| --- | --- | --- |
| Python | `python -m unittest discover -s tests -v` | 8 tests passed |
| Python CLI | Generate the Markdown review and metrics CSV from the supplied extracts | Completed |
| Input data | Each product and regional extract reconciles to consolidated net sales in all three years | Matched |
| Apps Script | `node tests/apps-script.test.mjs` | Formula references, repeat-run handling, source preservation and five invalid-input cases passed |
| Excel | Source values, formulas, cached results, chart bindings and input-change response | Checked |
| Excel presentation | Four worksheets, two native charts and the Apple logo | Checked |

## Live Google Sheets execution

The script was installed in a spreadsheet containing `Product CSV` and `Regional CSV`, then run from Google's Apps Script editor. It created `Automated Summary` with native formulas, formatting and an annual sales chart.

The final execution log reported **Execution started at 12:46:53 PM** and **Execution completed at 12:46:56 PM**, as displayed in the editor. The spreadsheet was read back through the Google Sheets interface after execution.

| Live result | Expected | Observed |
| --- | ---: | ---: |
| FY2023 net sales ($M) | 383,285 | 383,285 |
| FY2024 net sales ($M) | 391,035 | 391,035 |
| FY2025 net sales ($M) | 416,161 | 416,161 |
| FY2023 YoY | N/A | N/A |
| FY2025 YoY | 6.4% | 6.4% |
| FY2025 Services share | 26.2% | 26.2% |
| Services revenue increase ($M) | 12,989 | 12,989 |
| Services share of net growth | 51.7% | 51.7% |
| Greater China YoY | −3.8% | −3.8% |
| Wearables, Home and Accessories YoY | −3.6% | −3.6% |

The live Services contribution cell used `=C17/($B$7-$B$6)`. No formula-error markers were found in the populated summary range.

A repeat run rebuilt the existing summary and replaced its chart. The final chart was resized and positioned above the product table so it fits within the normal browser view. All three populated tabs were visually inspected at 100% zoom, and the reported source figures remained in the two input tabs.

The bound script project is named **Apple Revenue Analytics**. Its `@OnlyCurrentDoc` annotation limits spreadsheet access to the file where the script is installed. The test spreadsheet remains private to its owner.

## Scope

These checks cover the supplied FY2023–FY2025 extract and the workflow shown in this repository. They do not establish support for later fiscal years or automatic extraction of new filings. A new spreadsheet still requires its owner to authorize the bound script on its first run.
