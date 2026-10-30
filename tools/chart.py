"""경제콩 본문 차트 (1200x750 JPG). 숫자는 반드시 출처에서 확인한 값만.

사용: python3 tools/chart.py spec.json
spec 예시: {"out":"2026-11-01/deep_1.jpg","type":"bar|line|hbar","title":"일라이 릴리 연간 매출",
            "labels":["2021","2022"],"series":[{"name":"매출","values":[28.3,28.5]}],
            "unit":"십억 달러","source":"출처: 일라이 릴리 IR · 2026.10.31 기준","highlight_last":true}
"""
import json, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

FD = "/usr/share/fonts/opentype/noto/"
B = FontProperties(fname=f"{FD}NotoSansCJK-Bold.ttc"); R = FontProperties(fname=f"{FD}NotoSansCJK-Regular.ttc")
PAL = ["#2f6fdf", "#e0533d", "#2aa36b", "#8a5cf6", "#d99a1e"]

def draw(s):
    fig, ax = plt.subplots(figsize=(12, 7.5), dpi=100)
    labels, series, t = s["labels"], s["series"], s.get("type", "bar")
    n = len(series); x = range(len(labels))
    for i, se in enumerate(series):
        col = PAL[i % len(PAL)]; v = se["values"]
        if t == "line":
            ax.plot(list(x), v, color=col, lw=4, marker="o", ms=8, label=se.get("name"))
            ax.annotate(f"{v[-1]:,}", (len(v) - 1, v[-1]), textcoords="offset points", xytext=(0, 12), ha="center", fontproperties=B, fontsize=15, color=col)
        elif t == "hbar":
            cols = [col] * len(v)
            ax.barh(labels, v, color=cols, height=0.6)
            for j, val in enumerate(v): ax.text(val, j, f" {val:,}", va="center", fontproperties=B, fontsize=15)
        else:
            w = 0.7 / n; off = [k + (i - (n - 1) / 2) * w for k in x]
            cols = [col] * len(v)
            if n == 1 and s.get("highlight_last", True): cols = ["#b9c2cf"] * (len(v) - 1) + [col]
            ax.bar(off, v, width=w, color=cols, label=se.get("name"))
            for xo, val in zip(off, v): ax.text(xo, val, f"{val:,}", ha="center", va="bottom", fontproperties=B, fontsize=14)
    if t != "hbar": ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontproperties=R, fontsize=15)
    else:
        for l in ax.get_yticklabels(): l.set_fontproperties(R); l.set_fontsize(15)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
    ax.spines["left"].set_color("#cfd5dd"); ax.spines["bottom"].set_color("#cfd5dd")
    ax.tick_params(colors="#4b5563", length=0); ax.grid(axis="x" if t == "hbar" else "y", color="#eef1f5")
    ax.set_axisbelow(True)
    ax.set_title(s["title"], fontproperties=B, fontsize=24, loc="left", pad=18, color="#111827")
    if s.get("unit"): ax.text(1, 1.01, f"단위: {s['unit']}", transform=ax.transAxes, fontproperties=R, fontsize=13, color="#6b7280", va="bottom", ha="right")
    if n > 1: ax.legend(prop=R, frameon=False, fontsize=14)
    fig.text(0.01, 0.01, s.get("source", ""), fontproperties=R, fontsize=12, color="#6b7280")
    fig.text(0.99, 0.01, "경제콩", fontproperties=B, fontsize=14, color="#2ea028", ha="right")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(s["out"], dpi=100, pil_kwargs={"quality": 88}); plt.close(fig)
    print(s["out"])

if __name__ == "__main__":
    spec = json.load(open(sys.argv[1]))
    for s in (spec if isinstance(spec, list) else [spec]): draw(s)
