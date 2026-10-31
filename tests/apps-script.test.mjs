import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
function csvRows(text) {
  return text.trim().split(/\r?\n/).map((line,index)=>{
    const fields=[];let current='',quoted=false;
    for(let i=0;i<line.length;i++) {
      const char=line[i];
      if(char==='"') {
        if(quoted&&line[i+1]==='"'){current+='"';i++;}else quoted=!quoted;
      }else if(char===','&&!quoted){fields.push(current);current='';}else current+=char;
    }
    fields.push(current);
    return index===0?fields:[fields[0],...fields.slice(1).map(Number)];
  });
}
const source={
  product:csvRows(fs.readFileSync(path.join(root,'data/apple_product_revenue.csv'),'utf8')),
  regional:csvRows(fs.readFileSync(path.join(root,'data/apple_regional_revenue.csv'),'utf8')),
};
const copy=value=>JSON.parse(JSON.stringify(value));
let raw=copy(source);
const cells=new Map();let charts=[],clears=0;
const address=(row,col)=>String.fromCharCode(64+col)+row;
function range(...args) {
  let row,col;
  if(typeof args[0]==='string') {
    const match=/^([A-Z]+)(\d+)/.exec(args[0]);
    row=Number(match[2]);col=[...match[1]].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0);
  }else [row,col]=args;
  const result=new Proxy({}, {get:(_,method)=>(value)=>{
    if(method==='setValues'||method==='setFormulas') {
      value.forEach((values,r)=>values.forEach((v,c)=>cells.set(address(row+r,col+c),v)));
    }else if(method==='setValue'||method==='setFormula')cells.set(address(row,col),value);
    return result;
  }});
  return result;
}
const output={
  getRange:range,
  getCharts:()=>charts.slice(),
  removeChart:chart=>{charts=charts.filter(item=>item!==chart);},
  insertChart:chart=>{charts.push(chart);},
  clear:()=>{clears++;cells.clear();},
  newChart:()=>{
    const builder=new Proxy({}, {get:(_,key)=>key==='build'?()=>({chart:true}):()=>builder});return builder;
  },
};
for(const method of ['setConditionalFormatRules','setHiddenGridlines','setRowHeights','setRowHeight','setColumnWidth','setColumnWidths'])output[method]=()=>output;
const spreadsheet={
  getSheetByName:name=>name==='Product CSV'?{getDataRange:()=>({getValues:()=>raw.product})}:
    name==='Regional CSV'?{getDataRange:()=>({getValues:()=>raw.regional})}:
      name==='Automated Summary'?output:null,
  setActiveSheet:()=>{},
};
const rule=new Proxy({}, {get:(_,name)=>name==='build'?()=>({rule:true}):()=>rule});
const context={SpreadsheetApp:{getActiveSpreadsheet:()=>spreadsheet,newConditionalFormatRule:()=>rule},Charts:{ChartType:{LINE:'LINE'}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,'apps-script/Code.gs'),'utf8'),context);

context.buildAppleRevenueSummary();
assert.equal(cells.get('C5'),'N/A');
assert.equal(cells.get('D5'),"='Product CSV'!B6/B5");
assert.equal(cells.get('C13'),"=B13-'Product CSV'!C2");
assert.equal(cells.get('D24'),'=IF(\'Regional CSV\'!C4=0,"N/A",B24/\'Regional CSV\'!C4-1)');
assert.equal(cells.get('F17'),'=C17/($B$7-$B$6)');
assert.deepEqual(raw,source);
context.buildAppleRevenueSummary();
assert.equal(charts.length,1,'A repeat run should replace the chart');

for(const change of [
  data=>data.product.pop(),
  data=>data.product[2][0]=data.product[1][0],
  data=>data.product[1][1]='',
  data=>data.product[1][3]+=1,
  data=>data.regional[1][3]+=1,
]) {
  raw=copy(source);change(raw);const previousClears=clears;
  assert.throws(()=>context.buildAppleRevenueSummary());
  assert.equal(clears,previousClears,'Invalid inputs must not clear the output');
}
console.log('Apps Script checks passed: formulas, repeat runs, source preservation and five invalid-input cases.');
