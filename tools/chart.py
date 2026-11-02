"""경제콩 본문 차트 — 경제신문 인포그래픽 스타일 (1200x750 JPG). 숫자는 반드시 출처에서 확인한 값만.

스타일 규칙(사용자 확정 2026-11-01, "B 스타일 통일"):
  - title은 '결론 문장'으로 쓴다. 예) "신규 개원 10곳 중 8곳은 '피부과'"  (X "진료과목별 신규 개원 수")
  - sub에는 무엇을 언제 기준으로 셌는지 한 줄. unit이 있으면 sub 뒤에 붙는다.
  - 강조 막대/선은 1개만 빨강, 나머지는 회색. highlight로 인덱스 지정(기본: bar=마지막, hbar=최댓값).
  - y축 눈금 없음. 값은 막대/점 옆에 직접 표기.

사용: python3 tools/chart.py spec.json   (spec은 객체 하나 또는 배열)
spec 예시:
  {"out":"2026-11-01/deep_1.jpg","type":"bar|line|hbar",
   "title":"비만약 하나로 매출이 두 배","sub":"일라이 릴리 연간 매출","unit":"십억 달러",
   "labels":["2021","2022"],"series":[{"name":"매출","values":[28.3,28.5]}],
   "source":"출처: 일라이 릴리 IR · 2026.10.31 기준","highlight":1,"suffix":"곳"}
  - suffix: 값 뒤에 붙일 글자(예 "곳","%","명"). 생략 가능.
  - 시리즈가 2개 이상이면 첫 시리즈가 빨강, 나머지는 진회색/회색/남색 + 상단 범례.
"""
import json, os, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "fonts")
NOTO = "/usr/share/fonts/opentype/noto/"
def fp(name, fallback):
    p = os.path.join(FD, name)
    return FontProperties(fname=p if os.path.exists(p) else NOTO + fallback)
NG = fp("NanumGothic-Regular.ttf", "NotoSansCJK-Regular.ttc")
NGB = fp("NanumGothic-Bold.ttf", "NotoSansCJK-Bold.ttc")
DH = fp("DoHyeon-Regular.ttf", "NotoSansCJK-Black.ttc")

BG, INK, SUB, GRAY, ACC, GREEN = "#f6f3ee", "#111111", "#555555", "#9a9a9a", "#c8102e", "#2ea028"
MULTI = [ACC, "#444444", "#9a9a9a", "#1c4e80", "#b08a3e"]

def num(v, suffix=""):
    s = f"{v:,.1f}" if isinstance(v, float) and v != int(v) else f"{int(v):,}"
    return s + suffix

def fit_size(fig, text, fprop, size, maxw_frac):
    r = fig.canvas.get_renderer()
    while size > 20:
        t = fig.text(0, 0, text, fontproperties=fprop, fontsize=size); w = t.get_window_extent(r).width; t.remove()
        if w <= fig.bbox.width * maxw_frac: break
        size -= 2
    return size

def draw(s):
    labels, series, t = s["labels"], s["series"], s.get("type", "bar")
    suf = s.get("suffix", ""); n = len(series)
    fig = plt.figure(figsize=(12, 7.5), dpi=100, facecolor=BG)
    # 머리
    fig.patches.append(Rectangle((0.05, 0.935), 0.9, 0.012, transform=fig.transFigure, color=INK))
    fig.text(0.05, 0.85, s["title"], fontproperties=DH, fontsize=fit_size(fig, s["title"], DH, 40, 0.9), color=INK)
    sub = s.get("sub", "")
    if s.get("unit"): sub = (sub + " · " if sub else "") + f"단위: {s['unit']}"
    if sub: fig.text(0.05, 0.795, sub, fontproperties=NG, fontsize=15, color=SUB)
    if n > 1:
        x0 = 0.95
        for i in reversed(range(n)):
            nm = series[i].get("name", "")
            tx = fig.text(x0, 0.795, nm, fontproperties=NGB, fontsize=14, color=MULTI[i % 5], ha="right")
            w = tx.get_window_extent(fig.canvas.get_renderer()).width / fig.bbox.width
            fig.patches.append(Rectangle((x0 - w - 0.022, 0.8), 0.015, 0.018, transform=fig.transFigure, color=MULTI[i % 5]))
            x0 -= w + 0.045
    # 본문
    left = 0.19 if t == "hbar" else 0.06
    ax = fig.add_axes([left, 0.14, 0.95 - left, 0.58]); ax.set_facecolor(BG)
    for sp in ax.spines.values(): sp.set_visible(False)
    ax.tick_params(length=0)
    allv = [v for se in series for v in se["values"]]; vmax = max(allv); vmin = min(allv)

    if t == "hbar":
        v = series[0]["values"]; y = list(range(len(v)))[::-1]
        hi = s.get("highlight", v.index(max(v)))
        cols = [ACC if i == hi else GRAY for i in range(len(v))]
        ax.barh(y, v, color=cols, height=0.62)
        for yy, val, i in zip(y, v, range(len(v))):
            if val > vmax * 0.35: ax.text(val - vmax * 0.02, yy, num(val, suf), va="center", ha="right", fontproperties=DH, fontsize=24, color="white")
            else: ax.text(val + vmax * 0.015, yy, num(val, suf), va="center", ha="left", fontproperties=DH, fontsize=22, color="#444444")
        ax.set_yticks(y); ax.set_yticklabels(labels, fontproperties=NGB, fontsize=17, color="#222222")
        ax.tick_params(axis="y", pad=12); ax.set_xticks([]); ax.set_xlim(0, vmax * 1.07)
    elif t == "line":
        x = list(range(len(labels)))
        lo = min(0, vmin) if vmin >= 0 and vmin < vmax * 0.4 else vmin - (vmax - vmin) * 0.25
        hi_y = vmax + (vmax - lo) * 0.18
        for yy in ax.get_yticks(): pass
        ax.set_ylim(lo, hi_y)
        for g in [lo + (hi_y - lo) * k / 4 for k in range(1, 4)]: ax.axhline(g, color="#dedad2", lw=1, zorder=0)
        ax.axhline(lo, color="#888888", lw=1.5, zorder=1)
        for i, se in enumerate(series):
            v = se["values"]; col = ACC if n == 1 else MULTI[i % 5]
            ax.plot(x, v, color=col, lw=4 if i == 0 else 3, zorder=3, solid_capstyle="round")
            ax.scatter(x, v, s=70, color=col, zorder=4, edgecolors=BG, linewidths=2)
            idx = range(len(v)) if len(v) <= 7 else sorted({0, len(v) - 1, v.index(max(v)), v.index(min(v))})
            for k in idx:
                ax.annotate(num(v[k], suf), (k, v[k]), textcoords="offset points", xytext=(0, 14), ha="center",
                            fontproperties=DH, fontsize=21 if k == len(v) - 1 else 18, color=col if k == len(v) - 1 or n > 1 else "#444444")
        ax.set_yticks([]); ax.set_xticks(x); ax.set_xticklabels(labels, fontproperties=NGB, fontsize=15, color="#333333")
        ax.set_xlim(-0.4, len(labels) - 0.6)
    else:
        x = list(range(len(labels))); w = 0.62 / n
        for i, se in enumerate(series):
            v = se["values"]; off = [k + (i - (n - 1) / 2) * w for k in x]
            if n == 1:
                hi = s.get("highlight", len(v) - 1)
                cols = [ACC if k == hi else GRAY for k in range(len(v))]
            else: cols = [MULTI[i % 5]] * len(v)
            ax.bar(off, v, width=w * 0.92, color=cols, zorder=2)
            for xo, val, c in zip(off, v, cols):
                ax.text(xo, val + vmax * 0.02, num(val, suf), ha="center", va="bottom", fontproperties=DH,
                        fontsize=22 if n == 1 else 17, color=ACC if c == ACC and n == 1 else "#444444")
        ax.axhline(0, color="#888888", lw=1.5, zorder=3)
        ax.set_yticks([]); ax.set_ylim(min(0, vmin), vmax * 1.15)
        ax.set_xticks(x); ax.set_xticklabels(labels, fontproperties=NGB, fontsize=16, color="#222222")
        ax.tick_params(axis="x", pad=8)
    # 꼬리
    fig.patches.append(Rectangle((0.05, 0.075), 0.9, 0.002, transform=fig.transFigure, color="#999999"))
    src = s.get("source", "").strip()
    if src.startswith("출처:"): src = "자료:" + src[3:]
    fig.text(0.05, 0.035, src, fontproperties=NG, fontsize=12, color="#666666")
    fig.text(0.95, 0.035, s.get("mark", "경제콩"), ha="right", fontproperties=DH, fontsize=17, color=GREEN)
    fig.savefig(s["out"], facecolor=BG, pil_kwargs={"quality": 90}); plt.close(fig)
    print(s["out"])

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    for s in (spec if isinstance(spec, list) else [spec]): draw(s)
