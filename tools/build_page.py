"""경제콩 발행함 페이지(HTML) 생성.

사용: python3 tools/build_page.py posts.json out.html
posts.json:
{"date":"2026-11-01","sha":"<이미지가 들어간 커밋 SHA>",
 "posts":[{"type":"딥|기초|이슈","title":"...","tags":"#태그1 #태그2 ...",
           "gpt_prompt":"(딥글만, 사진 배경용 GPT 프롬프트)",
           "body":"<img src='2026-11-01/deep_thumb.jpg'><p>...</p><h3>소제목</h3><p><span class='hl'>형광펜</span></p>..."}]}
post에 "keyword":"메인 키워드", "sub_keywords":["서브1","서브2"] 를 넣으면 발행함에 표시됨.
post에 "category":"네이버 카테고리 경로"(예: "헬스케어 투자 > 헬스케어 이슈")를 넣으면 발행함에 표시됨.
body 규칙: p, h3, b, br, a, img(src=저장소 상대경로), span(class) 만 사용.
  형광펜: hl(노랑·핵심 결론) / hl-g(연두·보조 포인트) / hl-b(하늘·정의·개념) / hl-p(분홍·반전·주의)
  글자색: red(핵심 숫자·리스크) / blue(제품명·회사명·용어 첫 등장)
- 미리보기: 이미지를 data URI로 박아 넣음 (아티팩트는 외부 이미지를 못 띄움)
- 복사용: 소제목·'한 줄 정리' 앞에 빈 줄 자동 삽입. 본문 맨 끝에 '#태그 #태그' 줄 자동 추가(띄어쓰기 제거). 이미지는 raw.githubusercontent.com/<sha> 주소, 형광펜·가운데 정렬은 인라인 스타일 (네이버 붙여넣기 호환)
"""
import base64, html, json, re, sys, os

REPO = "AXIOMedu/kong-blog-images"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STYLES = {"hl": "background-color:#fff59d", "hl-g": "background-color:#d9f7be", "hl-b": "background-color:#cfe8ff",
          "hl-p": "background-color:#ffd6e7", "red": "color:#e03131", "blue": "color:#1c6dd0"}

def tag_line(tags):
    ts = [t.replace(" ", "") for t in re.split(r"[#,\s]*#", " " + tags) if t.strip()]
    return " ".join("#" + t.strip("#,") for t in ts if t.strip("#,"))

def to_naver(body, sha, tags=""):
    body = re.sub(r"<img[^>]*>", "", body, count=1)  # 썸네일은 '썸네일 복사' 버튼으로 따로 붙여넣음(대표 사진 지정용)
    if not sha:  # 업로드 실패 시: 복사본에서 이미지 제외(미리보기에서 우클릭 복사)
        body = re.sub(r"<img[^>]*>", "", body)
    b = re.sub(r"<img[^>]*src=['\"]([^'\"]+)['\"][^>]*>",
               lambda m: f'<p style="text-align:center"><img src="https://raw.githubusercontent.com/{REPO}/{sha}/{m.group(1)}" style="max-width:100%"></p>', body)
    for cls, style in STYLES.items():
        b = re.sub(rf"<span class=['\"]{cls}['\"]>", f'<span style="{style}">', b)
    b = re.sub(r"<p>", '<p style="text-align:center">', b)
    BLANK = '<p style="text-align:center"><br></p>'
    b = re.sub(r"<p style=\"text-align:center\"><b>한 줄 정리</b></p>", BLANK + r'<p style="text-align:center"><b>한 줄 정리</b></p>', b)
    b = re.sub(r"<h3>(.*?)</h3>", BLANK + r'<p style="text-align:center"><b><span style="font-size:19px">\1</span></b></p>', b, flags=re.S)
    if tags.strip():  # 본문 맨 끝 해시태그 줄: 네이버가 본문 #태그를 태그로 자동 등록하는지 사용자 테스트용
        b += BLANK + f'<p style="text-align:center">{html.escape(tag_line(tags))}</p>'
    return b

def to_preview(body):
    def emb(m):
        p = os.path.join(ROOT, m.group(1))
        mime = "image/png" if p.endswith(".png") else "image/jpeg"
        data = base64.b64encode(open(p, "rb").read()).decode()
        return f'<img alt="" src="data:{mime};base64,{data}">'
    return re.sub(r"<img[^>]*src=['\"]([^'\"]+)['\"][^>]*>", emb, body)

def build(spec):
    secs, payload = [], []
    for i, p in enumerate(spec["posts"]):
        payload.append({"title": p["title"], "tags": p.get("tags", ""), "html": to_naver(p["body"], spec["sha"], p.get("tags", "")),
                        "gpt": p.get("gpt_prompt", "")})
        cat = f'<p class="cat">카테고리: <b>{html.escape(p["category"])}</b></p>' if p.get("category") else ""
        if p.get("keyword"):
            subs = " · ".join(html.escape(k) for k in p.get("sub_keywords", []))
            cat += f'<p class="cat">메인 키워드: <b>{html.escape(p["keyword"])}</b>' + (f' <span class="subk">/ 서브: {subs}</span>' if subs else "") + '</p>'

        gpt = ""
        if p.get("gpt_prompt"):
            gpt = f'''<details class="gpt"><summary>사진 배경 바꾸고 싶을 때 (GPT 프롬프트)</summary>
<p>{html.escape(p["gpt_prompt"])}</p><button type="button" class="ghost" data-act="gpt" data-i="{i}">프롬프트 복사</button></details>'''
        secs.append(f'''<section class="post" id="p{i}">
<div class="head"><span class="type t{html.escape(p["type"])}">{html.escape(p["type"])}</span>
<h2>{html.escape(p["title"])}</h2></div>
<div class="actions">
<button type="button" data-act="thumb" data-i="{i}">① 썸네일 복사</button>
<button type="button" data-act="body" data-i="{i}">② 본문 복사</button>
<button type="button" class="ghost" data-act="title" data-i="{i}">제목 복사</button>
<button type="button" class="ghost" data-act="tags" data-i="{i}">태그 복사</button>
<span class="status" id="s{i}" role="status"></span></div>
{cat}<p class="tags">{html.escape(p.get("tags", ""))}</p>{gpt}
<article id="a{i}">{to_preview(p["body"])}</article></section>''')
    if not secs:
        secs.append('<section class="post"><article><p>아직 올라온 글이 없어.</p><p>매일 새벽 6시쯤 그날의 딥·기초·이슈 3편이 여기 채워져.</p></article></section>')
    warn = "" if spec.get("sha") else '<p class="warn">오늘은 이미지 업로드가 실패했어. 본문 복사엔 사진이 빠져 있으니, 미리보기 사진을 우클릭 → 이미지 복사로 넣어줘.</p>'
    return TEMPLATE.replace("__WARN__", warn).replace("__DATE__", html.escape(spec["date"])).replace("__SECTIONS__", "\n".join(secs)) \
                   .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))

TEMPLATE = r"""<title>경제콩 발행함</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Noto+Sans+KR:wght@400;700;900&display=swap">
<style>
/* 레이아웃: 날짜 머리말 → 글마다 (유형·제목 / 복사 버튼 줄 / 네이버 본문 미리보기) */
:root { --bg:#f3f5ef; --paper:#fff; --ink:#1d2318; --muted:#5f6b57; --bean:#2e9e22; --line:#dfe5d8; --mark:#fff27a; --mark-g:#d9f7be; --mark-b:#cfe8ff; --mark-p:#ffd6e7; --red:#e03131; --blue:#1c6dd0;
  --deep:#c8372d; --basic:#2f6fdf; --issue:#b7791f;
  --display:"Gowun Dodum","Noto Sans KR",system-ui,sans-serif; --body:"Noto Sans KR","Apple SD Gothic Neo",system-ui,sans-serif; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg:#12160f; --paper:#1b2117; --ink:#e8eee2; --muted:#9aa892; --bean:#6fd65a; --line:#2c3527; --mark:#6b6320; --mark-g:#3c5a2a; --mark-b:#24476b; --mark-p:#6b2f48; --red:#ff6b6b; --blue:#74b0ff; --deep:#ff7a6e; --basic:#7aa7ff; --issue:#e2b04a; color-scheme:dark } }
:root[data-theme="dark"] { --bg:#12160f; --paper:#1b2117; --ink:#e8eee2; --muted:#9aa892; --bean:#6fd65a; --line:#2c3527; --mark:#6b6320; --mark-g:#3c5a2a; --mark-b:#24476b; --mark-p:#6b2f48; --red:#ff6b6b; --blue:#74b0ff; --deep:#ff7a6e; --basic:#7aa7ff; --issue:#e2b04a; color-scheme:dark }
body { background:var(--bg); color:var(--ink); font-family:var(--body);
  padding-left:max(16px, env(safe-area-inset-left, 0px)); padding-right:max(16px, env(safe-area-inset-right, 0px)); padding-block:24px 64px; }
.wrap { max-width:760px; margin:0 auto; display:grid; gap:28px; }
header h1 { font-family:var(--display); font-size:1.6rem; margin:0; text-wrap:balance; }
header h1 span { color:var(--bean); }
header p { margin:6px 0 0; color:var(--muted); font-size:.92rem; line-height:1.6; }
nav { display:flex; flex-wrap:wrap; gap:8px; }
nav a { color:var(--ink); text-decoration:none; border:1px solid var(--line); background:var(--paper); border-radius:999px; padding:6px 14px; font-size:.9rem; }
.post { display:grid; gap:12px; min-width:0; }
.head { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }
.head h2 { margin:0; font-size:1.2rem; line-height:1.45; text-wrap:balance; flex:1 1 280px; min-width:0; }
.type { font-weight:700; font-size:.8rem; letter-spacing:.04em; padding:3px 10px; border-radius:6px; color:#fff; }
.t딥 { background:var(--deep); } .t기초 { background:var(--basic); } .t이슈 { background:var(--issue); }
.actions { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
button { font:700 .92rem var(--body); background:var(--bean); color:#fff; border:0; border-radius:8px; padding:10px 16px; cursor:pointer; }
button.ghost { background:transparent; color:var(--ink); border:1px solid var(--line); }
button:focus-visible { outline:3px solid var(--ink); outline-offset:2px; }
.status { font-size:.85rem; color:var(--muted); }
.tags { margin:0; color:var(--muted); font-size:.88rem; line-height:1.6; word-break:keep-all; }
.gpt { background:var(--paper); border:1px dashed var(--line); border-radius:8px; padding:10px 14px; font-size:.88rem; }
.gpt summary { cursor:pointer; color:var(--muted); }
.gpt p { line-height:1.6; }
article { background:var(--paper); border:1px solid var(--line); border-radius:10px; padding:28px clamp(16px,5vw,44px); line-height:1.9; min-width:0; overflow-wrap:anywhere; }
article p { margin:0 0 1.1em; text-align:center; }
article h3 { text-align:center; font-size:1.12rem; margin:1.6em 0 .7em; }
article img { display:block; margin:8px auto 22px; border-radius:4px; }
article .hl { background:var(--mark); } article .hl-g { background:var(--mark-g); } article .hl-b { background:var(--mark-b); } article .hl-p { background:var(--mark-p); }
article .red { color:var(--red); } article .blue { color:var(--blue); }
.cat { margin:0; font-size:.92rem; } .cat b { color:var(--bean); } .subk { color:var(--muted); }
.warn { margin:0; padding:12px 16px; border-radius:8px; background:var(--deep); color:#fff; font-weight:700; line-height:1.6; }
hr { border:0; border-top:1px solid var(--line); margin:8px 0; width:100%; }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; } }
</style>
<div class="wrap">
<header><h1><span>경제콩</span> 발행함 · __DATE__</h1>
<p>① 썸네일 복사 → 네이버 본문 맨 위에 붙여넣기(사진으로 업로드돼서 대표 사진이 됨) → ② 본문 복사 → 그 아래 붙여넣기. 제목은 버튼으로 따로. 태그는 본문 맨 끝 #태그 줄로 같이 들어감(발행 창에 자동으로 안 잡히면 태그 복사 버튼).</p></header>
__WARN__
<nav id="nav"></nav>
__SECTIONS__
</div>
<script>
const DATA = __PAYLOAD__;
const nav = document.getElementById('nav');
document.querySelectorAll('.post').forEach((s, i) => {
  const a = document.createElement('a'); a.href = '#p' + i; a.textContent = s.querySelector('.type').textContent + ' · ' + DATA[i].title.slice(0, 18);
  nav.appendChild(a);
});
function say(i, t) { const el = document.getElementById('s' + i); el.textContent = t; }
async function copyHtml(i) {
  const d = DATA[i];
  try {
    if (!window.ClipboardItem) throw 0;
    await navigator.clipboard.write([new ClipboardItem({
      'text/html': new Blob([d.html], { type: 'text/html' }),
      'text/plain': new Blob([document.getElementById('a' + i).innerText], { type: 'text/plain' }) })]);
    say(i, '본문 복사됨. 네이버에 붙여넣어 줘.');
  } catch (e) {
    const box = document.createElement('div'); box.innerHTML = d.html; box.style.cssText = 'position:fixed;left:-9999px;top:0';
    document.body.appendChild(box);
    const r = document.createRange(); r.selectNodeContents(box); const s = getSelection(); s.removeAllRanges(); s.addRange(r);
    let ok = false; try { ok = document.execCommand('copy'); } catch (_) {}
    if (ok) { s.removeAllRanges(); box.remove(); say(i, '본문 복사됨. 네이버에 붙여넣어 줘.'); }
    else { box.style.cssText = 'position:static'; document.getElementById('p' + i).appendChild(box); say(i, '선택해뒀어. Ctrl+C 눌러줘.'); }
  }
}
async function copyThumb(i) {
  const img = document.querySelector('#a' + i + ' img');
  if (!img) { say(i, '썸네일이 없어.'); return; }
  try {
    if (!window.ClipboardItem) throw 0;
    const blob = new Promise((res, rej) => {
      const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
      c.getContext('2d').drawImage(img, 0, 0); c.toBlob(b => b ? res(b) : rej(0), 'image/png');
    });
    await navigator.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
    say(i, '썸네일 복사됨. 네이버 본문 맨 위에 붙여넣어 줘.');
  } catch (e) { say(i, '복사가 막혔어. 아래 첫 사진을 우클릭 → 이미지 복사로 해줘.'); }
}
async function copyText(i, t, label) {
  try { await navigator.clipboard.writeText(t); say(i, label + ' 복사됨.'); }
  catch (e) { say(i, '복사가 막혔어. 직접 드래그해서 복사해줘.'); }
}
document.addEventListener('click', e => {
  const b = e.target.closest('button[data-act]'); if (!b) return;
  const i = +b.dataset.i, act = b.dataset.act;
  if (act === 'body') copyHtml(i);
  if (act === 'thumb') copyThumb(i);
  if (act === 'title') copyText(i, DATA[i].title, '제목');
  if (act === 'tags') copyText(i, DATA[i].tags, '태그');
  if (act === 'gpt') copyText(i, DATA[i].gpt, '프롬프트');
});
</script>
"""

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    open(sys.argv[2], "w").write(build(spec)); print(sys.argv[2])
