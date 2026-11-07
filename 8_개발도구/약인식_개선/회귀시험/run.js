/* native.js 에서 파서 구간만 잘라내 돌린다 — 앱을 켜지 않고 회귀를 잡는다.
   잘라내는 구간은 SKIP_LINE 정의부터 parseMeds 끝까지.
   항목에 meds 가 있으면 찾은 약 목록 전체를 비교하고(순서 무관, '' 는 하나도 없어야 함), 없으면 expect 로 본다.
   band 가 있으면 그 값으로, 없으면 8 로 돌린다. */
var fs = require('fs'), path = require('path');
var NATIVE = process.argv[2] || 'C:/Users/rudtn/todak-app/www/js/native.js';
var src = fs.readFileSync(NATIVE, 'utf8');
var a = src.indexOf('    var SKIP_LINE =');
var b = src.indexOf("return { name: n.name, times: n.times, days: n.days, kind: n.kind || '' };");
if (a < 0 || b < 0) { console.error('native.js 에서 파서 구간을 못 찾았습니다.'); process.exit(2); }
b = src.indexOf('\n    }', src.indexOf('}', b)) + '\n    }'.length;
var mod = { exports: {} };
new Function('module', src.slice(a, b) + '\nmodule.exports = { parseMeds: parseMeds, findCols: findCols };')(mod);
var parseMeds = mod.exports.parseMeds;

function listOf(s) {
  return String(s).split('|').map(function (x) { return x.replace(/\s+/g, ''); }).filter(Boolean).sort().join(' | ');
}
var F = require(path.join(__dirname, 'fixtures.js')).FIXTURES;
var pass = 0, fail = [];
F.forEach(function (c) {
  var r = parseMeds(c.items, c.band || 8);
  var got = r.length ? r.map(function (m) { return m.name + '=' + m.times + 'x' + m.days; }).join(' | ') : '(약을 못 찾음)';
  var ok, want;
  if (typeof c.meds === 'string') {
    want = c.meds ? listOf(c.meds) : '(약을 못 찾음)';
    ok = (r.length ? listOf(got) : '(약을 못 찾음)') === want;
  } else {
    want = c.expect;
    ok = c.expect === '0x0'
      ? (r.length > 0 && r.every(function (m) { return !m.times && !m.days; }))
      : r.some(function (m) { return m.times + 'x' + m.days === c.expect; });
  }
  if (ok) pass++; else fail.push(c.id + ' ' + c.form + '\n      기대 ' + want + ' → 실제 ' + got);
  console.log((ok ? 'PASS' : 'FAIL') + '  [' + c.id + '] ' + c.form + '  (' + c.share + ')');
  if (!ok) console.log('        기대 ' + want + '  →  ' + got);
});
console.log('\n' + pass + '/' + F.length + ' 통과');
if (fail.length) { console.log('\n실패:\n  ' + fail.join('\n  ')); process.exit(1); }
