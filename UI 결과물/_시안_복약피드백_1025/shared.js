/* 시안 공통 — 55 오늘의 복약 · 56 복약 설정이 같은 창을 연다 */
(function () {
  var SLOTS = ['아침', '점심', '저녁', '자기전'];
  var LBL = { '아침': '아침', '점심': '점심', '저녁': '저녁', '자기전': '자기 전' };
  var IC = { '아침': '🌅', '점심': '☀️', '저녁': '🌆', '자기전': '🌙' };
  var TM = { '아침': '오전 8:00', '점심': '오후 1:00', '저녁': '오후 7:00', '자기전': '오후 10:00' };
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function screen() { return $('.screen'); }
  function sortSlots(sl) { return SLOTS.filter(function (s) { return sl.indexOf(s) > -1; }); }
  function whenTxt(sl) { return sortSlots(sl).map(function (s) { return LBL[s]; }).join('·'); }

  var toastT = null;
  function toast(t) {
    var el = $('.toast9');
    if (!el) { el = document.createElement('div'); el.className = 'toast9'; screen().appendChild(el); }
    el.textContent = t; el.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(function () { el.classList.remove('on'); }, 1800);
  }

  /* ── 약 목록 고치기 (순서·드시는 시간) ──
     o = { items: [{ id, name, slots }], onSave(order, slotsById, changedIds) }
     순서: 약 이름 쪽(≡ + 이름)을 꾹 누르면 카드가 들리고, 끌어서 놓을 자리로 옮긴다.
           마우스는 4px 움직이면, 손가락은 0.22초 누르고 있거나 움직이면 들린다.
     드시는 시간: 아래 네 칸을 누른다. 하나는 꼭 남는다. */
  function openSheet(o) {
    var tmp = o.items.map(function (it) {
      return { id: it.id, name: it.name, was: sortSlots(it.slots), slots: sortSlots(it.slots) };
    });
    var moved = null;
    var dim = document.createElement('div');
    dim.className = 'pk-dim';
    dim.innerHTML = '<div class="pk-sheet" role="dialog" aria-label="약 목록 고치기">'
      + '<div class="pk-title">약 목록 고치기</div>'
      + '<div class="pk-sub">순서는 약 이름을 꾹 눌러 끌어 옮기고,<br>드시는 시간은 아래 칸을 눌러 바꿔요.</div>'
      + '<button type="button" class="btn btn-outline btn-sm btn-block ro-auto">드시는 시간 순서로 한 번에 정리</button>'
      + '<div class="pk-list ro-list"></div>'
      + '<p class="tiny muted ro-foot">드시는 시간을 바꾸면 <b>오늘부터</b> 그렇게 보여요.<br>새로 고른 시간의 알림은 복약 설정에서 바꿀 수 있어요.</p>'
      + '<div class="pk-acts"><button type="button" class="pk-cancel">취소</button><button type="button" class="pk-ok">저장</button></div>'
      + '</div>';
    screen().appendChild(dim);
    var list = $('.ro-list', dim);

    function paint() {
      list.innerHTML = '';
      tmp.forEach(function (m, i) {
        var r = document.createElement('div');
        r.className = 'ro-row' + (m.id === moved ? ' is-moved' : '');
        var chg = m.slots.join() !== m.was.join();
        r.innerHTML = '<div class="ro-grip" role="button" tabindex="0" aria-roledescription="끌어 옮기기" aria-label="'
          + m.name + ' · ' + (i + 1) + '번째 · 꾹 눌러 끌어 옮기기">'
          + '<span class="ro-handle" aria-hidden="true"></span><span class="ro-nm">' + m.name + '</span></div>'
          + '<div class="when-grid when-grid--sm">' + SLOTS.map(function (s) {
              var on = m.slots.indexOf(s) > -1;
              return '<span class="chip' + (on ? ' chip--on' : '') + '" role="checkbox" tabindex="0" aria-checked="' + on
                + '" aria-label="' + m.name + ' ' + LBL[s] + '" data-i="' + i + '" data-slot="' + s + '">' + LBL[s] + '</span>';
            }).join('') + '</div>'
          + (chg ? '<div class="ro-chg">' + whenTxt(m.was) + ' → <b>' + whenTxt(m.slots) + '</b> · 오늘부터</div>' : '');
        list.appendChild(r);
      });
    }

    /* ── 끌어 옮기기 ── */
    var drag = null;
    function lift() {
      if (!drag || drag.on) return;
      drag.on = true;
      drag.row.classList.add('is-drag');
      list.classList.add('is-dragging');
      if (drag.pid !== -1) try { if (navigator.vibrate) navigator.vibrate(10); } catch (eV) {}   /* 안드로이드: 잡혔다는 짧은 떨림 */
    }
    list.addEventListener('pointerdown', function (ev) {
      var grip = ev.target.closest && ev.target.closest('.ro-grip');
      if (!grip) return;
      if (ev.pointerType === 'mouse' && ev.button !== 0) return;
      var rows = $$('.ro-row', list), row = grip.closest('.ro-row'), idx = rows.indexOf(row);
      drag = { row: row, rows: rows, idx: idx, target: idx, y0: ev.clientY, on: false, pid: ev.pointerId,
               rects: rows.map(function (x) { return x.getBoundingClientRect(); }) };
      try { grip.setPointerCapture(ev.pointerId); } catch (eP) {}
      if (ev.pointerType !== 'mouse') drag.timer = setTimeout(lift, 220);
      ev.preventDefault();
    });
    list.addEventListener('pointermove', function (ev) {
      if (!drag || ev.pointerId !== drag.pid) return;
      var dy = ev.clientY - drag.y0;
      if (!drag.on) { if (Math.abs(dy) > 4) lift(); else return; }
      follow(dy);
    });
    function follow(dy) {
      var me = drag.rects[drag.idx], first = drag.rects[0], last = drag.rects[drag.rects.length - 1];
      dy = Math.max(first.top - me.top, Math.min(last.bottom - me.bottom, dy));
      drag.row.style.transform = 'translateY(' + dy + 'px) scale(1.02)';
      var c = me.top + me.height / 2 + dy, t = drag.idx;
      drag.rects.forEach(function (rc, i) {
        var mid = rc.top + rc.height / 2;
        if (i < drag.idx && c < mid && i < t) t = i;
        if (i > drag.idx && c > mid && i > t) t = i;
      });
      drag.target = t;
      var h = me.height + 8;
      drag.rows.forEach(function (rw, i) {
        if (i === drag.idx) return;
        var s = 0;
        if (drag.idx < t && i > drag.idx && i <= t) s = -h;
        if (drag.idx > t && i < drag.idx && i >= t) s = h;
        rw.style.transform = s ? 'translateY(' + s + 'px)' : '';
      });
    }
    function drop() {
      if (!drag) return;
      clearTimeout(drag.timer);
      var d = drag; drag = null;
      list.classList.remove('is-dragging');
      if (!d.on) return;
      if (d.target !== d.idx) {
        var it = tmp.splice(d.idx, 1)[0];
        tmp.splice(d.target, 0, it);
        moved = it.id;
      }
      paint();
    }
    list.addEventListener('pointerup', drop);
    list.addEventListener('pointercancel', drop);

    /* ── 드시는 시간 칸 ── */
    list.addEventListener('click', function (ev) {
      var ch = ev.target.closest && ev.target.closest('.chip[data-slot]');
      if (!ch) return;
      var m = tmp[+ch.getAttribute('data-i')], s = ch.getAttribute('data-slot'), k = m.slots.indexOf(s);
      if (k > -1) {
        if (m.slots.length === 1) return toast('드시는 시간을 하나 이상\n골라 주세요');
        m.slots.splice(k, 1);
      } else m.slots = sortSlots(m.slots.concat([s]));
      paint();
    });

    $('.ro-auto', dim).addEventListener('click', function () {
      var first = function (m) { return SLOTS.indexOf(m.slots[0]); };
      tmp = tmp.map(function (m, i) { return [m, i]; })
        .sort(function (a, b) { return (first(a[0]) - first(b[0])) || (a[1] - b[1]); })
        .map(function (x) { return x[0]; });
      moved = null; paint();
      toast('아침 약부터 차례로 놓았어요');
    });
    function close() { if (dim.parentNode) dim.parentNode.removeChild(dim); }
    $('.pk-cancel', dim).addEventListener('click', close);
    dim.addEventListener('click', function (ev) { if (ev.target === dim) close(); });
    $('.pk-ok', dim).addEventListener('click', function () {
      var slots = {}, changed = [];
      tmp.forEach(function (m) { slots[m.id] = m.slots.slice(); if (m.slots.join() !== m.was.join()) changed.push(m.id); });
      close();
      o.onSave(tmp.map(function (m) { return m.id; }), slots, changed);
    });
    paint();
    return {
      /* 시안 그림용: 한 줄을 옮긴 모습 / 드시는 시간을 바꾼 모습을 미리 만들어 둔다 */
      demo: function (from, to, slotI, addSlot, delSlot) {
        if (from != null) { var it = tmp.splice(from, 1)[0]; tmp.splice(to, 0, it); moved = it.id; }
        if (slotI != null) {
          var m = tmp[slotI];
          if (delSlot) m.slots = m.slots.filter(function (x) { return x !== delSlot; });
          if (addSlot) m.slots = sortSlots(m.slots.concat([addSlot]));
        }
        paint();
      },
      /* 시안 그림용: idx 번째 약을 잡아 dy 만큼 끌어 올린 순간 */
      lift: function (idx, dy) {
        var rows = $$('.ro-row', list);
        drag = { row: rows[idx], rows: rows, idx: idx, target: idx, y0: 0, on: false, pid: -1,
                 rects: rows.map(function (x) { return x.getBoundingClientRect(); }) };
        lift();
        follow(dy);
      }
    };
  }

  window.TDP = { SLOTS: SLOTS, LBL: LBL, IC: IC, TM: TM, toast: toast, whenTxt: whenTxt, sortSlots: sortSlots, openSheet: openSheet };
})();
