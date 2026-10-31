/** @OnlyCurrentDoc */
// Import the two CSVs as tabs named Product CSV and Regional CSV, then run
// buildAppleRevenueSummary. Source columns and reported controls are FY2023–FY2025.
const APPLE_YEARS = [2023, 2024, 2025];
const APPLE_TOTALS = [383285, 391035, 416161];
const APPLE_PRODUCTS = ['iPhone', 'Mac', 'iPad', 'Wearables, Home and Accessories', 'Services'];
const APPLE_REGIONS = ['Americas', 'Europe', 'Greater China', 'Japan', 'Rest of Asia Pacific'];

function onOpen() {
  SpreadsheetApp.getUi().createMenu('Apple review')
    .addItem('Build revenue summary', 'buildAppleRevenueSummary').addToUi();
}

function readAppleInput(ss, name, firstHeader, expected) {
  const sheet = ss.getSheetByName(name);
  if (!sheet) throw new Error('Import the CSV into a tab named ' + name);
  const values = sheet.getDataRange().getValues();
  const headers = [firstHeader].concat(APPLE_YEARS.map(year => 'FY' + year + '_USD_M'));
  if (values[0].length !== headers.length || headers.some((header, i) => values[0][i] !== header)) {
    throw new Error(name + ': expected headers ' + headers.join(', '));
  }
  const seen = new Set();
  const totals = [0, 0, 0];
  const records = [];
  values.slice(1).forEach((row, index) => {
    if (row.every(value => value === '')) return;
    const label = String(row[0]).trim();
    if (expected.indexOf(label) === -1 || seen.has(label)) {
      throw new Error(name + ': unknown or duplicate category ' + label);
    }
    const amounts = row.slice(1).map((value, col) => {
      if (value === '' || typeof value === 'boolean' || !/^\d+$/.test(String(value))) {
        throw new Error(name + ': invalid FY' + APPLE_YEARS[col] + ' value for ' + label);
      }
      const amount = Number(value);
      if (!Number.isSafeInteger(amount) || amount < 0) throw new Error(name + ': invalid amount for ' + label);
      totals[col] += amount;
      return amount;
    });
    records.push({label: label, sourceRow: index + 2, amounts: amounts});
    seen.add(label);
  });
  if (seen.size !== expected.length) throw new Error(name + ': missing categories');
  totals.forEach((total, i) => {
    if (total !== APPLE_TOTALS[i]) throw new Error(name + ': FY' + APPLE_YEARS[i] + ' does not reconcile to reported sales');
  });
  return records;
}

function buildAppleRevenueSummary() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  // Validate both inputs before creating or clearing the output.
  const products = readAppleInput(ss, 'Product CSV', 'Category', APPLE_PRODUCTS);
  const regions = readAppleInput(ss, 'Regional CSV', 'Region', APPLE_REGIONS);
  const out = ss.getSheetByName('Automated Summary') || ss.insertSheet('Automated Summary');
  out.getCharts().forEach(chart => out.removeChart(chart));
  out.clear();
  out.setConditionalFormatRules([]);
  out.setHiddenGridlines(true);
  out.getRange('A1:G34').setFontFamily('Arial').setFontSize(11).setVerticalAlignment('middle');
  out.getRange('A1').setValue('Apple Inc. annual revenue review').setFontSize(16).setFontWeight('bold');
  out.getRange('A2').setValue('FY2023–FY2025. Net sales in USD millions. Golla Varshith.');
  out.getRange('A4:D4').setValues([['Fiscal year', 'Net sales ($M)', 'YoY growth', 'Services share']]);
  const servicesRow = products.find(row => row.label === 'Services').sourceRow;
  const productRows = products.map(row => row.sourceRow);
  const annualRows = ['B', 'C', 'D'].map((sourceCol, i) => {
    const targetRow = i + 5;
    const sum = productRows.map(row => "'Product CSV'!" + sourceCol + row).join(',');
    return [
      'FY' + APPLE_YEARS[i],
      '=SUM(' + sum + ')',
      i === 0 ? 'N/A' : '=B' + targetRow + '/B' + (targetRow - 1) + '-1',
      "='Product CSV'!" + sourceCol + servicesRow + '/B' + targetRow,
    ];
  });
  out.getRange('A5:D7').setValues(annualRows);
  out.getRange('B5:B7').setNumberFormat('#,##0');
  out.getRange('C5:D7').setNumberFormat('0.0%;(0.0%);"–"');
  out.getRange('A9').setValue('FY2023 has 53 weeks; FY2024 and FY2025 have 52. FY2023 YoY requires FY2022.');

  const writeSection = (startRow, label, sourceName, records) => {
    out.getRange(startRow, 1).setValue(label).setFontWeight('bold');
    out.getRange(startRow + 1, 1, 1, 6).setValues([['Name', 'FY2025 ($M)', 'Change ($M)', 'YoY', 'Share of sales', 'Share of net growth']]);
    // Order by the original reported table. Each result uses its named input tab.
    const formulas = records.map((record, index) => {
      const r = startRow + 2 + index;
      const source = "'" + sourceName + "'!";
      const prior = source + 'C' + record.sourceRow;
      return [
        '=' + source + 'A' + record.sourceRow,
        '=' + source + 'D' + record.sourceRow,
        '=B' + r + '-' + prior,
        '=IF(' + prior + '=0,"N/A",B' + r + '/' + prior + '-1)',
        '=B' + r + '/$B$7',
        '=C' + r + '/($B$7-$B$6)',
      ];
    });
    out.getRange(startRow + 2, 1, records.length, 6).setFormulas(formulas);
    out.getRange(startRow + 2, 2, records.length, 2).setNumberFormat('#,##0;(#,##0);"–"');
    out.getRange(startRow + 2, 4, records.length, 3).setNumberFormat('0.0%;(0.0%);"–"');
  };
  writeSection(11, 'Product categories', 'Product CSV', products);
  writeSection(20, 'Regions', 'Regional CSV', regions);
  ['A4:D4', 'A12:F12', 'A21:F21'].forEach(range => {
    out.getRange(range).setBackground('#F3F6FA').setFontColor('#202632').setFontWeight('bold').setWrap(true);
  });
  out.setRowHeights(1, 34, 24);
  out.setRowHeight(12, 38);
  out.setRowHeight(21, 38);
  out.setColumnWidth(1, 290);
  out.setColumnWidths(2, 5, 145);
  out.setColumnWidth(7, 24);
  out.setColumnWidths(8, 5, 100);
  out.getRange('A29').setValue('Share of net growth = category or regional change / consolidated change. The two views must not be added.');
  out.getRange('A30').setValue('Source: Apple FY2025 Form 10-K, pp. 21–23 and 29.');
  out.getRange('A31').setValue('https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm');
  out.getRange('A33').setValue('Static reported inputs. This function calculates and formats the review; it does not fetch new filings.');
  const chart = out.newChart().setChartType(Charts.ChartType.LINE)
    .addRange(out.getRange('A4:B7')).setNumHeaders(1).setPosition(4, 6, 0, 0)
    .setOption('title', 'Annual net sales (USD millions)')
    .setOption('legend', {position: 'none'}).setOption('colors', ['#2463B5'])
    .setOption('width', 420).setOption('height', 165).build();
  out.insertChart(chart);
  const negatives = SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(0)
    .setFontColor('#AE3B39').setRanges([out.getRange('C13:F17'), out.getRange('C22:F26')]).build();
  out.setConditionalFormatRules([negatives]);
  ss.setActiveSheet(out);
}
