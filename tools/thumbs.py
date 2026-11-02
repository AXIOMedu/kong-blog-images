"""경제콩 썸네일 생성기 (1080x1080 JPG)

주의: 썸네일은 프롤로그 그리드(약 350px)로 줄어들어 보인다. 문구는 짧게.
홈판(홈피드)·메인 경제판은 약 16:9로 가운데만 잘라 보여준다 → 글자·핵심은 전부 세로 236~844px 안전영역 안에 둔다(모든 스타일 적용됨).
기본은 P(실사진+짧은 글자띠). 실사진(또는 PD 로고)을 못 구했을 때만 A/B/C 카드형.
  A: kicker 15자 이내, big은 숫자 위주 6자 이내, line2 10자 이내, chart labels는 각 2~3글자(길면 줄여서). foot은 더 이상 표시하지 않음(출처는 본문 차트에).

사용: python3 tools/thumbs.py spec.json
spec.json 예시
  A 실적 카드형(딥):  {"style":"A","out":"2026-11-01/deep_thumb.jpg","kicker":"일라이 릴리 3분기 실적",
                     "big":"매출 +40%","line2":"비만약 하나로 바뀐 회사","color":"#d52b1e",
                     "chart":{"labels":["21","22","23","24","25"],"values":[28,28,34,45,63]},
                     "foot":"연간 매출, 십억 달러 · 2026.10.31 기준"}
  B 형광 박스형(이슈): {"style":"B","out":"...","tag":"오늘의 이슈","l1":"임상 3상 발표 D-7",
                     "l2":"주가는 왜 먼저 빠질까?","sub":"한 줄 부제","chart":{"values":[...]}}  (chart 생략 가능)
  공통(선택) "logo": "2026-11-02/us_logo.png" — photos.py --logo로 받은 퍼블릭 도메인 로고만. 흰 상자에 원본 그대로 얹음.
  P 실사진형(기본): {"style":"P","out":"...","photo":"2026-11-03/us_p1.jpg","tag":"미국주식","head":"배당 64년 연속","sub":"존슨앤존슨이 버틴 비결"}
                     photo = photos.py get으로 받은 로컬 파일(필수, hotlink 주소 불가 — 썸네일 복사 버튼이 로컬 이미지만 됨).
                     사진이 없고 PD 로고만 있으면 "photo" 대신 "logo":"...png","bg":"#1f4e8c" → 색 배경에 로고를 크게(인텔 로고 타일처럼).
                     head 6~11자(숫자 하나 넣기), sub 16자 이내(선택), tag 6자 이내(선택).
                     CC BY·CC BY-SA 사진이면 본문 첫 줄(썸네일 바로 아래)에 credit 캡션 필수.
  C 텍스트 카드(기초): {"style":"C","out":"...","series":"주식공부 #1","l1":"PER이 낮으면","l2":"정말 싼 걸까?",
                     "sub":"제약사 예시로 3분 만에 이해하기","color":"#1f6feb"}
"""
import io, json, sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

FD = "/usr/share/fonts/opentype/noto/"
def font(s, w="Black"): return ImageFont.truetype(f"{FD}NotoSansCJK-{w}.ttc", s, index=1)
W = H = 1080
def rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def fit(d, t, size, maxw, w="Black"):
    f = font(size, w)
    while d.textlength(t, font=f) > maxw and size > 24: size -= 3; f = font(size, w)
    return f

def bars(labels, values, w, h, color):
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    cols = ["#c9ced6"] * (len(values) - 1) + [color]
    ax.bar(labels, values, color=cols, width=0.62)
    for s in ax.spines.values(): s.set_visible(False)
    ax.tick_params(colors="#374151", labelsize=30, length=0); ax.set_yticks([])
    for l in ax.get_xticklabels(): l.set_fontproperties(matplotlib.font_manager.FontProperties(fname=f"{FD}NotoSansCJK-Bold.ttc", size=30))
    fig.tight_layout(pad=0.4); buf = io.BytesIO(); fig.savefig(buf, format="png"); plt.close(fig)
    return Image.open(buf).convert("RGB")

def dark_line(values, w, h, color="#ff4d4f"):
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
    x = range(len(values)); lo = min(values) * 0.85
    ax.plot(x, values, color=color, lw=7); ax.fill_between(x, values, lo, color=color, alpha=.22)
    ax.grid(color="#30363d", lw=1); ax.set_xticks([]); ax.set_yticks([]); ax.set_ylim(lo, max(values) * 1.05)
    for s in ax.spines.values(): s.set_visible(False)
    fig.tight_layout(pad=0); buf = io.BytesIO(); fig.savefig(buf, format="png", facecolor="#0d1117"); plt.close(fig)
    return Image.open(buf).convert("RGB").resize((w, h))

def put_logo(img, path, box):
    # box=(x0,y0,x1,y1) 안에 비율 유지로 맞추고 흰 둥근 상자 위에 원본 그대로 얹는다(변형·재채색 없음)
    if not path: return
    try: lg = Image.open(path).convert("RGBA")
    except Exception: return
    x0, y0, x1, y1 = box; pad = 14
    lg.thumbnail((x1 - x0 - 2 * pad, y1 - y0 - 2 * pad))
    w, h = lg.size[0] + 2 * pad, lg.size[1] + 2 * pad
    d = ImageDraw.Draw(img); d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 14, fill=(255, 255, 255))
    img.paste(lg, (x0 + pad, y0 + pad), lg)
    return x0 + w

def mark(d, dark=True, y=H - 56):
    d.text((W - 150, y), "경제콩", font=font(34), fill=(120, 230, 90) if dark else (46, 160, 40))

def style_a(s):
    # 그리드(약 350px)로 줄어도 읽히게: 큰 글씨 3덩어리 + 굵은 막대만. 출처는 본문에.
    c = rgb(s.get("color", "#d52b1e"))
    img = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 340], fill=c)  # 색 띠는 위로 넓게, 글자는 안전영역(236~)부터
    right = put_logo(img, s.get("logo"), (36, 236, 330, 330)) if s.get("logo") else None
    if right:  # 로고가 있으면 kicker는 로고 오른쪽에 왼쪽 정렬
        f = fit(d, s["kicker"], 64, W - right - 60); d.text((right + 30, 248), s["kicker"], font=f, fill=(255, 255, 255))
    else:
        f = fit(d, s["kicker"], 72, W - 100); d.text(((W - d.textlength(s["kicker"], font=f)) / 2, 240), s["kicker"], font=f, fill=(255, 255, 255))
    f = fit(d, s["big"], 200, W - 100); d.text(((W - d.textlength(s["big"], font=f)) / 2, 350), s["big"], font=f, fill=c)
    f = fit(d, s["line2"], 96, W - 100); d.text(((W - d.textlength(s["line2"], font=f)) / 2, 600), s["line2"], font=f, fill=(20, 20, 20))
    ch = s.get("chart")
    if ch: img.paste(bars(ch["labels"], ch["values"], 960, 320, s.get("color", "#d52b1e")), (60, 740))  # 막대는 장식(아래가 잘려도 됨)
    mark(d, dark=False); return img

def style_b(s):
    vals = (s.get("chart") or {}).get("values")
    if not vals:
        random.seed(len(s["l1"])); v = 100; vals = []
        for _ in range(14): v += random.randint(-12, 14); vals.append(v)
    img = dark_line(vals, W, H).filter(ImageFilter.GaussianBlur(1.5)).convert("RGBA")
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 100)); img.alpha_composite(sh); d = ImageDraw.Draw(img)
    f = font(40, "Bold"); tw = d.textlength(s.get("tag", "오늘의 이슈"), font=f)
    d.rounded_rectangle([60, 300, 60 + tw + 44, 365], 10, fill=(55, 60, 70)); d.text((82, 306), s.get("tag", "오늘의 이슈"), font=f, fill=(255, 255, 255))
    for i, (t, col, bg) in enumerate([(s["l1"], (20, 20, 20), (255, 221, 0)), (s.get("l2", ""), (255, 255, 255), (0, 0, 0))]):
        if not t: continue
        f = fit(d, t, 104, W - 160); tw = d.textlength(t, font=f); y = 390 + i * 150
        d.rectangle([60, y, 60 + tw + 40, y + 132], fill=bg); d.text((80, y + 6), t, font=f, fill=col)
    if s.get("sub"): d.text((64, 710), s["sub"], font=fit(d, s["sub"], 48, W - 140, "Bold"), fill=(235, 238, 242))
    if s.get("logo"): put_logo(img, s["logo"], (W - 360, 250, W - 60, 365))
    mark(d, y=770); return img.convert("RGB")

def style_c(s):
    c = rgb(s.get("color", "#1f6feb"))
    bgc = tuple(int(255 - (255 - x) * 0.10) for x in c)
    img = Image.new("RGB", (W, H), bgc); d = ImageDraw.Draw(img)
    d.rectangle([50, 50, W - 50, H - 50], outline=c, width=8)
    f = font(44, "Bold"); tw = d.textlength(s["series"], font=f)
    d.rounded_rectangle([(W - tw) / 2 - 30, 245, (W + tw) / 2 + 30, 317], 36, fill=c)
    d.text(((W - tw) / 2, 251), s["series"], font=f, fill=(255, 255, 255))
    for i, (t, col) in enumerate([(s["l1"], (25, 25, 25)), (s.get("l2", ""), c)]):
        if not t: continue
        f = fit(d, t, 120, W - 180); tw = d.textlength(t, font=f)
        d.text(((W - tw) / 2, 350 + i * 155), t, font=f, fill=col)
    if s.get("sub"):
        f = fit(d, s["sub"], 48, W - 200, "Bold"); tw = d.textlength(s["sub"], font=f)
        d.text(((W - tw) / 2, 700), s["sub"], font=f, fill=(70, 75, 85))
    if s.get("logo"): put_logo(img, s["logo"], (80, 880, 400, 990))
    mark(d, dark=False, y=H - 130); return img

def cover(im, w, h):
    r = max(w / im.width, h / im.height); im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def style_p(s):
    # 홈판 경제판처럼 실사진이 주인공. 글자는 안전영역 아래쪽 띠 하나에만.
    if s.get("photo"):
        img = cover(Image.open(s["photo"]).convert("RGB"), W, H)
    else:  # PD 로고 타일: 색 배경 + 로고 크게(원본 그대로)
        img = Image.new("RGB", (W, H), rgb(s.get("bg", "#1f4e8c")))
        lg = Image.open(s["logo"]).convert("RGBA"); lg.thumbnail((640, 220))
        pad = 40; bw, bh = lg.width + 2 * pad, lg.height + 2 * pad; x0, y0 = (W - bw) // 2, 250 + (300 - bh) // 2 if bh < 300 else 250
        ImageDraw.Draw(img).rounded_rectangle([x0, y0, x0 + bw, y0 + bh], 28, fill=(255, 255, 255))
        img.paste(lg, (x0 + pad, y0 + pad), lg)
    img = img.convert("RGBA")
    grad = Image.new("L", (1, H)); [grad.putpixel((0, y), int(max(0, min(1, (y - 380) / 300)) * 200)) for y in range(H)]
    img.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, H), 0)] * 3 + [grad.resize((W, H))]))
    d = ImageDraw.Draw(img); y = 600
    if s.get("tag"):
        f = font(38, "Bold"); tw = d.textlength(s["tag"], font=f)
        d.rounded_rectangle([60, y - 72, 60 + tw + 40, y - 14], 8, fill=(255, 221, 0)); d.text((80, y - 69), s["tag"], font=f, fill=(20, 20, 20))
    f = fit(d, s["head"], 112, W - 120); d.text((60, y), s["head"], font=f, fill=(255, 255, 255))
    if s.get("sub"): d.text((62, y + 140), s["sub"], font=fit(d, s["sub"], 50, W - 300, "Bold"), fill=(235, 238, 242))
    mark(d, y=y + 150); return img.convert("RGB")

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    for s in (spec if isinstance(spec, list) else [spec]):
        img = {"A": style_a, "B": style_b, "C": style_c, "P": style_p}[s["style"]](s)
        img.convert("RGB").save(s["out"], quality=88); print(s["out"])
