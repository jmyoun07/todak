/* 서버로 나가는 글자만 따로 본다 — 성함·생년월일·병원 이름이 밖으로 나가면 안 된다. (ES5)
   native.js 에서 파서 구간과 HIRA 의 '조회 글자 만들기'(normKey·pickRevive)만 잘라 내 돌린다.
   실제 조회(fetch)는 하지 않는다 — 무엇을 물으려 했는지 글자만 떠 본다.
   쓰는 법:  node outbound.js [native.js 경로] */
var fs = require('fs'), path = require('path');
var NATIVE = process.argv[2] || 'C:/Users/rudtn/todak-app/www/js/native.js';
var src = fs.readFileSync(NATIVE, 'utf8');
var a = src.indexOf('    var SKIP_LINE =');
var b = src.indexOf('    return { parseMeds: parseMeds, formKind: formKind');
var h0 = src.indexOf('    var NAME_TAIL = /(님|씨|귀하)$/;');
var h1 = src.indexOf('    /* meds(사진에서 읽은 약) · lines(읽은 글줄 전부)');
if (a < 0 || b < 0 || h0 < 0 || h1 < 0) { console.error('native.js 에서 구간을 못 찾았습니다.'); process.exit(2); }
var glue = '\nvar MAX_REVIVE = 12;\nvar OCRP = { stripDose: stripDose, formKind: formKind, looksLikeName: looksLikeName, rowDoseOf: rowDoseOf };\n';
var mod = { exports: {} };
new Function('module', src.slice(a, b) + glue + src.slice(h0, h1) +
  '\nmodule.exports = { parseMeds: parseMeds, pickRevive: pickRevive, normKey: normKey };')(mod);
var M = mod.exports;

var F = require(path.join(__dirname, 'fixtures.js')).FIXTURES;
/* 밖으로 나가면 안 되는 글자 — 글자본에 쓰인 더미 성함·상호·진료과. 실제 환자 정보는 한 건도 쓰지 않았다 */
var BAD = ['김영자', '박순자', '이정숙', '홍길동', '최영산', '박현정', '남궁민정', '황보라정', '이정액', '정미환',
           '김미정', '이수정', '삼성어린이소아과', '삼성정형외과', '삼성내과', '조이팜약국', '필독약국', '터울병원',
           '500312', '19500312', '1950', '1970'];
var fail = [], lines = 0;
F.forEach(function (c) {
  var meds = M.parseMeds(c.items, c.band || 8);
  var rev = M.pickRevive(c.items, meds);
  var keys = [];
  meds.forEach(function (m) { var k = M.normKey(m.name); if (k.length >= 2 && keys.indexOf(k) < 0) keys.push(k); });
  rev.forEach(function (v) { if (keys.indexOf(v.ck) < 0) keys.push(v.ck); });
  lines += keys.length;
  var hit = [];
  keys.forEach(function (k) {
    BAD.forEach(function (w) { if (k.indexOf(M.normKey(w)) >= 0 && hit.indexOf(k) < 0) hit.push(k + ' ← ' + w); });
  });
  if (hit.length) fail.push(c.id + ' ' + c.form + '\n      나간 글자: ' + hit.join(' , '));
  console.log((hit.length ? 'LEAK' : 'OK  ') + '  [' + c.id + '] ' + (keys.length ? keys.join(' , ') : '(조회 없음)'));
});
console.log('\n글자본 ' + F.length + '개 · 서버로 나간 글자 ' + lines + '개 · 새어 나간 것 ' + fail.length + '개');
if (fail.length) { console.log('\n새어 나감:\n  ' + fail.join('\n  ')); process.exit(1); }
