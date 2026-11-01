"""경제콩 본문 카드 이미지 (가로 1080, 세로는 내용에 맞춤, JPG) — 차트(chart.py)와 같은 경제신문 스타일.
AI 사진 대신 쓰는 '사람이 만든 티 나는' 정보 이미지: 표, 요약 카드, 구조도, 비교, 타임라인, 핵심 숫자.
숫자·사실은 반드시 출처에서 확인한 값만. 의사 지칭은 짧은 문구 규칙(일반의/전공의)을 따른다.

사용: python3 tools/cards.py spec.json   (spec은 객체 하나 또는 배열, 저장소 루트에서 실행)
공통 키: out, type, title(결론형 한 줄, 25자 이내), sub(선택), source(선택, "출처: ..." → "자료: ..."로 표시)
type별 키
  summary   : points ["한 줄", "한 줄", "한 줄"]          (오늘 결론 3줄 카드. 2~4개)
  table     : columns ["구분","2025","2026"], rows [["매출","1,000","1,200"],...], highlight_row 1(선택, 0부터)
              (행 8개 이하, 열 5개 이하. 숫자 열은 자동 오른쪽 정렬)
  flow      : steps [{"label":"임상 1상","desc":"안전성 확인 · 수십 명"}, ...]   (3~6단계, 위→아래 화살표)
  compare   : left {"name":"장비","items":["한 번 팔면 끝", ...]}, right {"name":"소모품","items":[...]}, win "right"(선택: 강조할 쪽)
  timeline  : events [{"date":"2026.9","text":"노바티스와 계약"}, ...], highlight 2(선택)   (3~7개)
  stat      : stats [{"label":"52주 고점 대비","value":"-61%","note":"10/30 종가 기준"}, ...]  (2~4개, 첫 번째가 빨강)
"""
import html, json, os, sys, tempfile
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "fonts")
E = lambda s: html.escape(str(s))

CSS = f"""
@font-face{{font-family:NG;src:url('file://{FD}/NanumGothic-Regular.ttf')}}
@font-face{{font-family:NG;font-weight:700;src:url('file://{FD}/NanumGothic-Bold.ttf')}}
@font-face{{font-family:NG;font-weight:800;src:url('file://{FD}/NanumGothic-ExtraBold.ttf')}}
@font-face{{font-family:DH;src:url('file://{FD}/DoHyeon-Regular.ttf')}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1080px;background:#f6f3ee;font-family:NG,'Noto Sans CJK KR',sans-serif;color:#111}}
.wrap{{padding:54px 60px 40px}}
.rule{{height:10px;background:#111;margin-bottom:30px}}
h1{{font-family:DH,sans-serif;font-weight:400;font-size:54px;line-height:1.2;letter-spacing:-0.5px}}
.sub{{font-size:22px;color:#555;margin-top:12px}}
.body{{margin-top:40px}}
.foot{{margin-top:44px;border-top:2px solid #999;padding-top:16px;display:flex;justify-content:space-between;align-items:center}}
.src{{font-size:17px;color:#666}} .mark{{font-family:DH;font-size:26px;color:#2ea028}}
.red{{color:#c8102e}}
/* summary */
.pt{{display:flex;gap:22px;align-items:flex-start;padding:26px 0;border-bottom:1px solid #d8d3ca}}
.pt:last-child{{border-bottom:none}}
.num{{font-family:DH;font-size:48px;color:#c8102e;width:56px;flex:none;line-height:1}}
.pt p{{font-size:31px;font-weight:700;line-height:1.45}}
.pt:first-child p{{background:linear-gradient(transparent 58%,#fff59d 58%);display:inline}}
/* table */
table{{width:100%;border-collapse:collapse;font-size:27px}}
th{{background:#111;color:#fff;font-weight:700;padding:18px 16px;text-align:left}}
td{{padding:18px 16px;border-bottom:1px solid #d3cec4;background:#fbf9f5}}
tr:nth-child(even) td{{background:#f1ede6}}
td.n,th.n{{text-align:right;font-variant-numeric:tabular-nums}}
tr.hi td{{background:#fbe3e6;color:#c8102e;font-weight:800}}
td:first-child{{font-weight:700}}
/* flow */
.step{{background:#fff;border:2px solid #222;padding:22px 28px;display:flex;gap:24px;align-items:center}}
.step .lb{{font-family:DH;font-size:36px;min-width:230px}}
.step .ds{{font-size:25px;color:#444;line-height:1.4}}
.step.last{{background:#c8102e;border-color:#c8102e;color:#fff}} .step.last .ds{{color:#fde8ea}}
.arrow{{text-align:center;font-size:34px;color:#888;line-height:1;padding:8px 0}}
/* compare */
.cmp{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
.col{{background:#fff;border:2px solid #bbb}}
.col h2{{font-family:DH;font-weight:400;font-size:40px;padding:20px 26px;background:#9a9a9a;color:#fff}}
.col.win{{border-color:#c8102e}} .col.win h2{{background:#c8102e}}
.col li{{list-style:none;font-size:27px;line-height:1.4;padding:18px 26px;border-top:1px solid #e3ded5}}
.col li:first-child{{border-top:none}}
/* timeline */
.tl{{position:relative;padding-left:44px}}
.tl:before{{content:'';position:absolute;left:13px;top:10px;bottom:10px;width:4px;background:#bbb}}
.ev{{position:relative;padding:16px 0 22px}}
.ev:before{{content:'';position:absolute;left:-41px;top:22px;width:22px;height:22px;border-radius:50%;background:#9a9a9a;border:4px solid #f6f3ee}}
.ev .d{{font-family:DH;font-size:30px;color:#666}} .ev .t{{font-size:29px;font-weight:700;margin-top:4px;line-height:1.4}}
.ev.hi:before{{background:#c8102e}} .ev.hi .d,.ev.hi .t{{color:#c8102e}}
/* stat */
.stats{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.st{{background:#fff;border-top:8px solid #9a9a9a;padding:26px 28px 24px}}
.st:first-child{{border-top-color:#c8102e}}
.st .l{{font-size:24px;color:#555;font-weight:700}} .st .v{{font-family:DH;font-size:72px;margin-top:8px;line-height:1.1}}
.st:first-child .v{{color:#c8102e}} .st .no{{font-size:20px;color:#777;margin-top:6px}}
"""

def isnum(s):
    if str(s).strip() in ("-", "–", ""): return True
    t = str(s).replace(",", "").replace("%", "").replace("원", "").replace("억", "").replace("조", "").replace("배", "").replace("+", "").replace("-", "").replace(".", "").replace("~", "").strip()
    return t.isdigit()

def body(s):
    t = s["type"]
    if t == "summary":
        return "".join(f"<div class='pt'><div class='num'>{i + 1}</div><p>{E(p)}</p></div>" for i, p in enumerate(s["points"]))
    if t == "table":
        cols, rows, hi = s["columns"], s["rows"], s.get("highlight_row", -1)
        numc = [all(isnum(r[j]) for r in rows) for j in range(len(cols))]
        h = "".join(f"<th class='{'n' if numc[j] and j else ''}'>{E(c)}</th>" for j, c in enumerate(cols))
        b = "".join("<tr class='%s'>" % ("hi" if i == hi else "") + "".join(f"<td class='{'n' if numc[j] and j else ''}'>{E(c)}</td>" for j, c in enumerate(r)) + "</tr>" for i, r in enumerate(rows))
        return f"<table><tr>{h}</tr>{b}</table>"
    if t == "flow":
        st = s["steps"]; out = []
        for i, x in enumerate(st):
            out.append(f"<div class='step{' last' if i == len(st) - 1 else ''}'><div class='lb'>{E(x['label'])}</div><div class='ds'>{E(x.get('desc', ''))}</div></div>")
            if i < len(st) - 1: out.append("<div class='arrow'>▼</div>")
        return "".join(out)
    if t == "compare":
        w = s.get("win")
        def col(k): c = s[k]; return f"<div class='col{' win' if w == k else ''}'><h2>{E(c['name'])}</h2><ul>" + "".join(f"<li>{E(i)}</li>" for i in c["items"]) + "</ul></div>"
        return f"<div class='cmp'>{col('left')}{col('right')}</div>"
    if t == "timeline":
        hi = s.get("highlight", -1)
        return "<div class='tl'>" + "".join(f"<div class='ev{' hi' if i == hi else ''}'><div class='d'>{E(e['date'])}</div><div class='t'>{E(e['text'])}</div></div>" for i, e in enumerate(s["events"])) + "</div>"
    if t == "stat":
        return "<div class='stats'>" + "".join(f"<div class='st'><div class='l'>{E(x['label'])}</div><div class='v'>{E(x['value'])}</div><div class='no'>{E(x.get('note', ''))}</div></div>" for x in s["stats"]) + "</div>"
    raise ValueError(t)

def page(s):
    src = s.get("source", "").strip()
    if src.startswith("출처:"): src = "자료:" + src[3:]
    sub = f"<div class='sub'>{E(s['sub'])}</div>" if s.get("sub") else ""
    return (f"<!doctype html><meta charset='utf-8'><style>{CSS}</style><div class='wrap'><div class='rule'></div>"
            f"<h1>{E(s['title'])}</h1>{sub}<div class='body'>{body(s)}</div>"
            f"<div class='foot'><span class='src'>{E(src)}</span><span class='mark'>경제콩</span></div></div>")

def render(specs):
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1080, "height": 800}, device_scale_factor=1)
        for s in specs:
            with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
                f.write(page(s)); path = f.name
            pg.goto("file://" + path); pg.wait_for_timeout(150)
            h = pg.evaluate("document.querySelector('.wrap').getBoundingClientRect().height")
            pg.set_viewport_size({"width": 1080, "height": int(max(h, 560))})
            os.makedirs(os.path.dirname(os.path.abspath(s["out"])), exist_ok=True)
            pg.screenshot(path=s["out"], type="jpeg", quality=90, full_page=True); os.unlink(path); print(s["out"])
        b.close()

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    render(spec if isinstance(spec, list) else [spec])
