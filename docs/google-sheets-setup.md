# Google Sheets setup

This example uses a spreadsheet-bound Apps Script. It reads two named input tabs and creates one output tab.

1. Create a Google spreadsheet.
2. Import `data/apple_product_revenue.csv` into a new tab named **Product CSV**.
3. Import `data/apple_regional_revenue.csv` into another tab named **Regional CSV**.
4. Keep the CSV headers in row 1. Do not add a title row or an extra column.
5. Open **Extensions → Apps Script**, replace the initial code with `apps-script/Code.gs`, and save.
6. Select **buildAppleRevenueSummary** and run it. Complete Google's authorization prompt for the spreadsheet operations.
7. Return to the spreadsheet. **Automated Summary** will contain the results. Reloading the spreadsheet also adds the **Apple review → Build revenue summary** menu.

## Expected results

| Metric | Result |
| --- | ---: |
| FY2023 sales, USD millions | 383,285 |
| FY2024 sales, USD millions | 391,035 |
| FY2025 sales, USD millions | 416,161 |
| FY2023 YoY | N/A |
| FY2025 YoY | 6.4% |
| FY2025 Services share | 26.2% |
| FY2025 Services contribution to net growth | 51.7% |

Product and regional tables each contain five rows. A line chart shows annual consolidated sales. Running the function again rebuilds the output tab and its chart.

The script validates both input tabs before clearing the output. Missing or duplicate categories, incorrect headers, nonnumeric amounts and totals that do not reconcile stop the run. The function only changes `Automated Summary`; source tabs are read as inputs.

## Troubleshooting

| Message or behaviour | Check |
| --- | --- |
| Import the CSV into a tab named… | Tab names must match `Product CSV` and `Regional CSV` exactly. |
| Expected headers… | Import the complete CSV, beginning in A1, without extra columns. |
| Unknown or duplicate category | Check for repeated rows or changed category names. |
| Invalid FY… value | Amounts must be whole numeric values, without currency symbols or blank cells. |
| Does not reconcile to reported sales | Restore the reported amounts from the CSV before running again. |
| Apple review menu is missing | Save the script and reload the spreadsheet, or run the main function from the editor. |

Financial inputs are a fixed FY2023–FY2025 extract. The function does not download filings or send email.

API references: [Range](https://developers.google.com/apps-script/reference/spreadsheet/range), [Sheet](https://developers.google.com/apps-script/reference/spreadsheet/sheet), and [custom menus](https://developers.google.com/apps-script/guides/menus).
