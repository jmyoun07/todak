"""Markdown -> docx 변환 (토닥 사용설명서용)
사용: python 8_개발도구/_md_to_docx.py <입력.md> [출력.docx]

watch(당봄케어) 의 md_to_docx_cli.py 를 가져와 제목색만 토닥(#9E2E54)으로 바꾸고,
한 줄에 그림 여러 장을 좌우로 놓는 문법을 더했다(당봄은 docx 를 나중에 고치는 스크립트로 했다).

서식 기준: 당봄 합병증 프로그램(DB-care) 사용설명서 / 토닥 문서.
Word 기본 스타일(Title·제목1·제목2·목록)만 쓰고, 표는 얇은 실선에 머리행만 회색 음영.
색 채운 머리행, 행 교대음영, 제목 밑줄·좌측 컬러바 같은 장식은 쓰지 않는다.

추가 문법
  @cover 제품명|문서종류|버전|날짜     표지 블록
  @toc                                 '##' 제목을 모아 차례 생성
  @pagebreak                           쪽 나눔
  ![캡션](이미지경로)                  그림 + "그림 N-M. 캡션" 캡션 (앱 화면: 검은 실선 테두리)
  ![캡션|nb](경로)                     테두리 없이 (안내 카드처럼 앱 화면이 아닌 그림)
  ![캡션|w=15](경로)                   폭 지정(cm)
  ![가](a) ![나](b) [![다](c)]         한 줄에 2~3장 → 테두리 없는 표로 좌우 배치
                                       (한 화면을 위아래로 나눈 그림만 묶는다)
  > [!주의] 내용  /  > [!참고] 내용    1x1 표 박스 (회색 음영)
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor

SRC = Path(sys.argv[1])
DST = Path(sys.argv[2]) if len(sys.argv) > 2 else SRC.with_suffix(".docx")

KOREAN_FONT = "맑은 고딕"
BODY_PT = 10.5
TABLE_PT = 10
CAPTION_PT = 9.5
HEAD_COLOR = RGBColor(0x9E, 0x2E, 0x54)      # 토닥 --primary-dark
SUBHEAD_COLOR = RGBColor(0x9E, 0x2E, 0x54)
MUTED = RGBColor(0x59, 0x59, 0x59)
TABLE_HEAD_FILL = "EDEDED"
BOX_FILL = "EDEDED"
IMG_WIDTH_CM = 6.5      # 앱 화면 한 장 (당봄은 7.5 — 토닥은 화면이 많아 빈 쪽이 생겨 줄임)
IMG_MAX_H_CM = 15.0     # 이보다 길면 폭을 줄인다
IMG_MAX_H_WIDE = 21.0   # 폭을 직접 준 그림(안내 카드 등)의 높이 한도

doc = Document()
sec = doc.sections[0]
sec.top_margin = sec.bottom_margin = Cm(2.3)
sec.left_margin = sec.right_margin = Cm(2.3)


def set_font(obj, name=KOREAN_FONT):
    el = obj.element if hasattr(obj, "element") else obj._element
    rPr = el.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rFonts.set(qn(attr), name)


normal = doc.styles["Normal"]
normal.font.name = KOREAN_FONT
normal.font.size = Pt(BODY_PT)
set_font(normal)
normal.paragraph_format.space_after = Pt(6)

title_st = doc.styles["Title"]
title_st.font.name = KOREAN_FONT
title_st.font.size = Pt(24)
title_st.font.bold = True
title_st.font.color.rgb = HEAD_COLOR
set_font(title_st)
title_st.paragraph_format.space_after = Pt(6)
# Word 기본 Title 스타일에 딸린 파란 밑줄(pBdr)을 뺀다 — 제목 밑줄은 쓰지 않는 서식
_tp = title_st.element.find(qn("w:pPr"))
if _tp is not None:
    for _b in _tp.findall(qn("w:pBdr")):
        _tp.remove(_b)

h1 = doc.styles["Heading 1"]
h1.font.name = KOREAN_FONT
h1.font.size = Pt(14)
h1.font.bold = True
h1.font.color.rgb = HEAD_COLOR
set_font(h1)
h1.paragraph_format.space_before = Pt(16)
h1.paragraph_format.space_after = Pt(6)

h2 = doc.styles["Heading 2"]
h2.font.name = KOREAN_FONT
h2.font.size = Pt(11.5)
h2.font.bold = True
h2.font.color.rgb = SUBHEAD_COLOR
set_font(h2)
h2.paragraph_format.space_before = Pt(10)
h2.paragraph_format.space_after = Pt(4)

for sname in ("List Bullet", "List Number"):
    s = doc.styles[sname]
    s.font.name = KOREAN_FONT
    s.font.size = Pt(BODY_PT)
    set_font(s)
    s.paragraph_format.space_after = Pt(4)

INLINE_RE = re.compile(r"(\*\*[^*\n]+\*\*|`[^`\n]+`)")


def emit_inline(p, text, *, color=None, size=None, bold_all=False):
    def add(t, bold=False, mono=False):
        if not t:
            return
        r = p.add_run(t)
        r.bold = bold or bold_all
        if color:
            r.font.color.rgb = color
        if size:
            r.font.size = Pt(size)
        set_font(r, "Consolas" if mono else KOREAN_FONT)

    pos = 0
    for m in INLINE_RE.finditer(text):
        add(text[pos:m.start()])
        seg = m.group(0)
        if seg.startswith("**"):
            add(seg[2:-2], bold=True)
        else:
            add(seg[1:-1], mono=True)
        pos = m.end()
    add(text[pos:])


def fill_cell(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tcPr.append(shd)


def thin_borders(table):
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:color"), "auto")
        borders.append(el)
    table._tbl.tblPr.append(borders)


def col_widths(headers, rows, total=16.4, min_cm=2.6):
    """칸 폭을 글자 수에 맞춘다(긴 칸이 넓게). 같은 폭으로 나누면 짧은 '항목' 칸이 반을 차지한다."""
    n = len(headers)
    need = []
    for i in range(n):
        cells = [headers[i]] + [r[i] for r in rows]
        need.append(min(max(len(re.sub(r"\*\*|`", "", c)) for c in cells), 60))
    raw = [max(x, 4) for x in need]
    s = float(sum(raw))
    w = [max(min_cm, total * x / s) for x in raw]
    k = total / sum(w)
    return [Cm(x * k) for x in w]


def add_table(headers, aligns, rows):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    thin_borders(t)
    t.autofit = False
    for r_ in t.rows:
        for c_, wd in zip(r_.cells, col_widths(headers, rows)):
            c_.width = wd
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        fill_cell(cell, TABLE_HEAD_FILL)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(2)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER if aligns[i] == "center" else WD_ALIGN_PARAGRAPH.LEFT
        emit_inline(p, h.strip(), size=TABLE_PT, bold_all=True)
    keep = len(rows) <= 12      # 짧은 표는 한 쪽에 모은다(줄마다 다음 줄과 같이)
    for c in t.rows[0].cells:
        c.paragraphs[0].paragraph_format.keep_with_next = True
    for ri, row in enumerate(rows):
        for i, val in enumerate(row):
            cell = t.rows[ri + 1].cells[i]
            cell.text = ""
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(2)
            if keep and ri < len(rows) - 1:
                p.paragraph_format.keep_with_next = True
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if aligns[i] == "center" else WD_ALIGN_PARAGRAPH.LEFT
            emit_inline(p, val.strip(), size=TABLE_PT)
    doc.add_paragraph()


def add_box(label, body_lines):
    t = doc.add_table(rows=1, cols=1)
    thin_borders(t)
    cell = t.rows[0].cells[0]
    cell.text = ""
    fill_cell(cell, BOX_FILL)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    emit_inline(p, label, size=TABLE_PT, bold_all=True)
    for line in body_lines:
        bp = cell.add_paragraph()
        bp.paragraph_format.space_after = Pt(2)
        emit_inline(bp, line, size=TABLE_PT)
    doc.add_paragraph()


def _list_abstract_id():
    """List Number 스타일이 쓰는 abstractNumId."""
    numbering = doc.part.numbering_part.element
    st = doc.styles["List Number"].element
    nid = st.find(qn("w:pPr")).find(qn("w:numPr")).find(qn("w:numId")).get(qn("w:val"))
    for x in numbering.findall(qn("w:num")):
        if x.get(qn("w:numId")) == nid:
            return x.find(qn("w:abstractNumId")).get(qn("w:val"))
    return "0"


def new_num_id():
    """1 부터 다시 시작하는 번호 목록을 하나 만든다."""
    numbering = doc.part.numbering_part.element
    ids = [int(x.get(qn("w:numId"))) for x in numbering.findall(qn("w:num"))]
    new = (max(ids) if ids else 0) + 1
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(new))
    a = OxmlElement("w:abstractNumId")
    a.set(qn("w:val"), _list_abstract_id())
    num.append(a)
    ov = OxmlElement("w:lvlOverride")
    ov.set(qn("w:ilvl"), "0")
    so = OxmlElement("w:startOverride")
    so.set(qn("w:val"), "1")
    ov.append(so)
    num.append(ov)
    numbering.append(num)
    return new


def set_num(p, num_id):
    pPr = p._p.get_or_add_pPr()
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        numPr = OxmlElement("w:numPr")
        pPr.append(numPr)
    for tag in ("w:ilvl", "w:numId"):
        e = numPr.find(qn(tag))
        if e is not None:
            numPr.remove(e)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    nid = OxmlElement("w:numId")
    nid.set(qn("w:val"), str(num_id))
    numPr.append(ilvl)
    numPr.append(nid)


def pic_border(shape):
    """앱 화면 그림에 검은 실선 테두리."""
    inline = shape._inline
    spPr = inline.find(".//" + qn("pic:spPr"))
    spPr.append(parse_xml('<a:ln %s><a:solidFill><a:schemeClr val="tx1"/>'
                          '</a:solidFill></a:ln>' % nsdecls("a")))
    ee = inline.find(qn("wp:effectExtent"))
    if ee is not None:
        for k in ("l", "t", "r", "b"):
            ee.set(k, "19050")


def _fit(path, width_cm, max_h=None):
    from PIL import Image
    img = Image.open(path)
    ratio = img.height / img.width
    if max_h is None:
        max_h = IMG_MAX_H_WIDE if width_cm else IMG_MAX_H_CM
    w = width_cm or IMG_WIDTH_CM
    h = w * ratio
    if h > max_h:
        h = max_h
        w = h / ratio
    return w, h


def add_image(path, caption, chapter, fignum, width_cm=None, border=True):
    w, h = _fit(path, width_cm)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    shape = p.add_run().add_picture(str(path), width=Cm(w), height=Cm(h))
    if border:
        pic_border(shape)
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(10)
    emit_inline(cap, "그림 %d-%d. %s" % (chapter, fignum, caption), color=MUTED, size=CAPTION_PT)


USABLE_CM = 16.4                 # 본문 폭 (A4 - 좌우 여백 2.3cm)
ROW_IMG_W = {2: 6.5, 3: 5.0}     # 당봄은 7.5 / 5.2


def add_image_row(items, chapter, start_fignum):
    """한 화면을 나눈 그림 2~3장을 테두리 없는 표에 좌우로 — 캡션은 그림 아래 같은 칸에."""
    from docx.enum.table import WD_TABLE_ALIGNMENT
    cols = len(items)
    t = doc.add_table(rows=1, cols=cols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tblPr = t._tbl.tblPr
    st = tblPr.find(qn("w:tblStyle"))
    if st is not None:
        tblPr.remove(st)
    tblPr.append(parse_xml('<w:tblCellMar %s><w:left w:w="0" w:type="dxa"/>'
                           '<w:right w:w="0" w:type="dxa"/></w:tblCellMar>' % nsdecls("w")))
    col_w = Cm(USABLE_CM / cols)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))     # 그림과 캡션이 쪽 사이에서 갈리지 않게
    for k, (cap, path, wcm, border) in enumerate(items):
        cell = t.rows[0].cells[k]
        cell.width = col_w
        cell.vertical_alignment = WD_ALIGN_VERTICAL.TOP
        w, h = _fit(path, wcm or ROW_IMG_W.get(cols, 5.0), IMG_MAX_H_CM)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        shape = p.add_run().add_picture(str(path), width=Cm(w), height=Cm(h))
        if border:
            pic_border(shape)
        cp = cell.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_after = Pt(8)
        emit_inline(cp, "그림 %d-%d. %s" % (chapter, start_fignum + k, cap), color=MUTED, size=CAPTION_PT)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


IMG_RE = re.compile(r"!\[(.*?)\]\((.*?)\)")


def parse_img(alt, path):
    parts = alt.split("|")
    cap, wcm, border = parts[0].strip(), None, True
    for fl in (x.strip() for x in parts[1:]):
        if fl.startswith("w="):
            wcm = float(fl[2:])
        elif fl == "nb":
            border = False
    return cap, SRC.parent / path, wcm, border


lines = SRC.read_text(encoding="utf-8").splitlines()
toc_items = [re.match(r"^##\s+(\d+\..*)$", ln.strip()).group(1)
             for ln in lines if re.match(r"^##\s+\d+\.", ln.strip())]

chapter = 0
fignum = 0
cur_num = None
i = 0
while i < len(lines):
    line = lines[i].strip()

    if not line or line == "---":
        i += 1
        continue

    if line.startswith("@cover"):
        parts = [x.strip() for x in line[len("@cover"):].strip().split("|")]
        for n, part in enumerate(parts):
            if n == 0:
                p = doc.add_paragraph(style="Title")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(90)
                p.paragraph_format.space_after = Pt(4)
                emit_inline(p, part)
            elif n == 1:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(60)
                emit_inline(p, part, size=16, bold_all=True, color=SUBHEAD_COLOR)
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after = Pt(2)
                emit_inline(p, part, size=11, color=MUTED)
        i += 1
        continue

    if line == "@toc":
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        emit_inline(p, "차례", size=14, bold_all=True, color=HEAD_COLOR)
        for item in toc_items:
            tp = doc.add_paragraph()
            tp.paragraph_format.left_indent = Pt(12)
            tp.paragraph_format.space_after = Pt(2)
            emit_inline(tp, item)
        i += 1
        continue

    if line == "@pagebreak":
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        i += 1
        continue

    if line.startswith("!["):
        imgs = IMG_RE.findall(line)
        if len(imgs) >= 2 and IMG_RE.sub("", line).strip() == "":
            items = [parse_img(a, b) for a, b in imgs]
            add_image_row(items, chapter, fignum + 1)
            fignum += len(items)
            i += 1
            continue
        m = re.match(r"^!\[(.*?)\]\((.*?)\)$", line)
        if m:
            fignum += 1
            cap, path, wcm, border = parse_img(m.group(1), m.group(2))
            add_image(path, cap, chapter, fignum, wcm, border)
            i += 1
            continue

    m = re.match(r"^(#{1,4})\s+(.*)$", line)
    if m:
        level, text = len(m.group(1)), m.group(2)
        if level == 1:
            p = doc.add_paragraph(style="Title")
            emit_inline(p, text)
        elif level == 2:
            num = re.match(r"^(\d+)\.", text)
            if num:
                chapter = int(num.group(1))
                fignum = 0
            p = doc.add_paragraph(style="Heading 1")
            emit_inline(p, text)
        else:
            p = doc.add_paragraph(style="Heading 2")
            emit_inline(p, text)
        i += 1
        continue

    if line.startswith(">"):
        first = line[1:].strip()
        mb = re.match(r"^\[!(주의|참고)\]\s*(.*)$", first)
        body = []
        if mb:
            label = mb.group(1)
            if mb.group(2):
                body.append(mb.group(2))
        else:
            label = None
            body = [first]
        i += 1
        while i < len(lines) and lines[i].strip().startswith(">"):
            body.append(lines[i].strip()[1:].strip())
            i += 1
        if label:
            add_box(label, body)
        else:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Pt(14)
            for n, q in enumerate(body):
                if n:
                    p.add_run().add_break()
                emit_inline(p, q, color=MUTED)
        continue

    if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|\-]+\|?\s*$", lines[i + 1]):
        headers = [c.strip() for c in line.strip("|").split("|")]
        aligns = ["center" if a.strip().startswith(":") and a.strip().endswith(":") else "left"
                  for a in lines[i + 1].strip().strip("|").split("|")]
        aligns += ["left"] * (len(headers) - len(aligns))
        rows, j = [], i + 2
        while j < len(lines) and "|" in lines[j] and lines[j].strip():
            cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
            cells += [""] * (len(headers) - len(cells))
            rows.append(cells[:len(headers)])
            j += 1
        add_table(headers, aligns, rows)
        i = j
        continue

    m = re.match(r"^(\d+)\.\s+(.*)$", line)
    if m:
        if m.group(1) == "1" or cur_num is None:
            cur_num = new_num_id()
        p = doc.add_paragraph(style="List Number")
        set_num(p, cur_num)
        emit_inline(p, m.group(2))
        i += 1
        while i < len(lines) and lines[i].startswith("   ") and not re.match(r"^\s*\d+\.\s", lines[i]):
            sub = lines[i].strip().lstrip("-").strip()
            if sub:
                sp = doc.add_paragraph(style="List Bullet")
                sp.paragraph_format.left_indent = Pt(36)
                emit_inline(sp, sub)
            i += 1
        continue

    m = re.match(r"^[-*]\s+(.*)$", line)
    if m:
        p = doc.add_paragraph(style="List Bullet")
        emit_inline(p, m.group(1))
        i += 1
        continue

    p = doc.add_paragraph()
    emit_inline(p, line)
    i += 1

# 문서 끝이 표면 그 뒤 빈 문단이 다음 쪽으로 넘어가 빈 쪽이 생긴다 — 1pt 로 줄인다
last = doc.paragraphs[-1]
if not last.text.strip():
    last.paragraph_format.space_after = Pt(0)
    last.paragraph_format.space_before = Pt(0)
    from docx.enum.text import WD_LINE_SPACING
    last.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    last.paragraph_format.line_spacing = Pt(1)

doc.save(str(DST))
print("OK: %s (%s bytes)" % (DST.name, format(DST.stat().st_size, ",")))
