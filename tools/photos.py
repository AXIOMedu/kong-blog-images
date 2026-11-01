"""경제콩 실사진·로고 가져오기 — 저작권 안전한 출처만 (라이선스 자동 필터)

출처 2곳
  1) Wikimedia Commons: 특정 제품·장비·건물·현미경 사진, 회사 로고. 퍼블릭 도메인 / CC0 / CC BY / CC BY-SA 만 허용
     (NC·ND·비자유 라이선스 자동 제외). 이 환경 IP가 자주 429(요청 제한)를 받으므로 느리게 재시도하고,
     그래도 실패하면 포기하고 다른 이미지로 대체한다(글 작성을 막지 말 것).
  2) Pexels: 연구실·병원·약·돈 같은 일반 실사 스톡. 무료 상업 이용 가능. 환경변수 PEXELS_KEY 필요.
규칙
  - 실존 인물(CEO·정치인·연예인 등) 얼굴이 식별되는 사진은 쓰지 않는다. 'personality rights' 표시 파일은 자동 제외.
  - 받은 뒤 반드시 이미지를 직접 열어 보고, 글과 무관하거나 워터마크·다른 회사 로고가 박혀 있으면 버린다.
  - 로고(--logo): 퍼블릭 도메인 표시(단순 글자 로고 등)만. 회사를 '가리키는' 용도로만, 원본 그대로(변형·재채색 금지),
    협찬·제휴처럼 보이는 배치 금지. 썸네일엔 thumbs.py의 "logo" 키(파일 경로)로 넣는다. 국내 회사 로고는 대부분 없음 → 없으면 생략.
  - 본문에 사진을 넣으면 바로 아래 캡션 <p>에 출력된 credit을 그대로 넣는다(예: "▲ 다빈치 수술 로봇 (사진: 홍길동 / Wikimedia Commons / CC BY-SA 4.0)").
  - get이 다운로드에 실패하면 JSON에 "hotlink"(원본 이미지 주소)를 준다 → body에 <img src='그 https 주소'>로 넣으면
    네이버에 붙여넣을 때 네이버가 직접 가져간다(발행함 미리보기엔 회색 자리로 보임).

사용(저장소 루트에서, 영문 검색어가 결과가 훨씬 많다)
  python3 tools/photos.py search "da Vinci surgical system" [-n 6]
  python3 tools/photos.py search "Pfizer logo" --logo
  python3 tools/photos.py get "File:New Da Vinci Xi.jpg" 2026-11-02/us_p1.jpg
  python3 tools/photos.py get "File:Pfizer (2021).svg" 2026-11-02/us_logo.png --logo
  python3 tools/photos.py pexels "laboratory pipette" [-n 6]               # 후보(JSON)
  python3 tools/photos.py pexels-get <photo_id> 2026-11-02/issue1_p1.jpg
"""
import argparse, html, io, json, os, re, subprocess, sys, time, urllib.parse
from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
UA = "kong-blog-images/1.0 (https://github.com/AXIOMedu/kong-blog-images)"
OK_LIC = re.compile(r"^(public domain|pd\b|pd-|cc0|cc[- ]by(-sa)?[- ]?\d|cc[- ]by(-sa)?$)", re.I)
BAD_LIC = re.compile(r"\b(nc|nd)\b|non-?commercial|no ?deriv|fair use|non-?free", re.I)
WAITS = [10, 30, 60, 90]  # 429면 이만큼 쉬고 재시도(총 약 3분)

class Fail(Exception): pass

def fetch(url, headers=()):
    # 파이썬 HTTP 라이브러리는 Wikimedia가 더 자주 막아서 curl 사용
    code = b"0"
    for w in WAITS + [None]:
        cmd = ["curl", "-sS", "-L", "-m", "60", "-A", UA, "-w", "\n%{http_code}"]
        for h in headers: cmd += ["-H", h]
        r = subprocess.run(cmd + [url], capture_output=True)
        body, code = r.stdout.rsplit(b"\n", 1) if b"\n" in r.stdout else (r.stdout, b"0")
        if code.strip() == b"200": return body
        if w is None or code.strip() not in (b"429", b"503", b"0"): break
        time.sleep(w)
    raise Fail(f"{code.decode().strip()} {url}")

def call(params):
    return json.loads(fetch(f"{API}?{urllib.parse.urlencode({**params, 'format': 'json'})}"))

def strip(s): return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

def thumb(url, mime, w, size=1280):
    # API에 썸네일 생성을 시키면 429가 잦아서 표준 경로로 직접 만든다
    url = (url or "").split("?")[0]
    m = re.match(r"(https://upload\.wikimedia\.org/wikipedia/commons)/(\w/\w\w)/(.+)$", url)
    if not m: return url
    base, h, name = m.groups()
    if (mime or "").endswith("svg+xml"): return f"{base}/thumb/{h}/{name}/{size}px-{name}.png"
    if (w or 0) > size: return f"{base}/thumb/{h}/{name}/{size}px-{name}"
    return url

def info(title_list):
    r = call({"action": "query", "titles": "|".join(title_list), "prop": "imageinfo",
              "iiprop": "url|extmetadata|size|mime",
              "iiextmetadatafilter": "LicenseShortName|UsageTerms|NonFree|Restrictions|Artist|ImageDescription"})
    out = []
    for p in r.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]; m = ii.get("extmetadata", {})
        g = lambda k: strip(m.get(k, {}).get("value", ""))
        out.append({"title": p.get("title"), "license": g("LicenseShortName"), "usage_terms": g("UsageTerms"),
                    "nonfree": g("NonFree"), "restrictions": g("Restrictions"), "artist": g("Artist")[:80] or "작성자 미상",
                    "desc": g("ImageDescription")[:160], "w": ii.get("width"), "h": ii.get("height"), "mime": ii.get("mime"),
                    "thumb": thumb(ii.get("url"), ii.get("mime"), ii.get("width")), "page": ii.get("descriptionurl")})
    return out

def allowed(x, logo=False):
    lic = x["license"] or x["usage_terms"]
    if not (x["mime"] or "").startswith("image/"): return False
    if not lic or BAD_LIC.search(lic) or x["nonfree"].lower() == "true": return False
    if logo:
        is_logo = "logo" in (x["title"] or "").lower() or "trademark" in x["restrictions"].lower()
        return is_logo and bool(re.match(r"^(public domain|pd|cc0)", lic, re.I))
    if not OK_LIC.search(lic): return False
    if "personality" in x["restrictions"].lower(): return False
    if (x["w"] or 0) < 500 and not (x["mime"] or "").endswith("svg+xml"): return False
    return True

def search(q, n=6, logo=False):
    r = call({"action": "query", "list": "search", "srsearch": q, "srnamespace": 6, "srlimit": 12})
    titles = [s["title"] for s in r.get("query", {}).get("search", [])]
    if not titles: return []
    time.sleep(2)
    return [x for x in info(titles) if allowed(x, logo)][:n]

def save(raw, out):
    im = Image.open(io.BytesIO(raw))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA"); bg = Image.new("RGB", im.size, (255, 255, 255)); bg.paste(im, mask=im.split()[-1]); im = bg
    im = im.convert("RGB")
    if max(im.size) > 1600: im.thumbnail((1600, 1600))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    im.save(out) if out.lower().endswith(".png") else im.save(out, quality=88)

def get(title, out, logo=False):
    x = info([title])[0]
    if not allowed(x, logo): raise Fail(f"라이선스 조건 불충족: {x['license']} {x['restrictions']}")
    cr = f"사진: {x['artist']} / Wikimedia Commons / {x['license'] or x['usage_terms']}"
    try:
        save(fetch(x["thumb"]), out); res = {"out": out}
    except Fail as e:
        res = {"out": None, "hotlink": x["thumb"], "note": f"다운로드 실패({e}) — hotlink 주소를 body img src로 직접 사용 가능"}
    print(json.dumps({**res, "credit": cr, "page": x["page"], "license": x["license"]}, ensure_ascii=False))

def pexels(q, n=6):
    key = os.environ.get("PEXELS_KEY")
    if not key: raise Fail("PEXELS_KEY 환경변수 없음")
    r = json.loads(fetch(f"https://api.pexels.com/v1/search?{urllib.parse.urlencode({'query': q, 'per_page': n})}", [f"Authorization: {key}"]))
    return [{"id": p["id"], "alt": p.get("alt"), "photographer": p["photographer"], "w": p["width"], "h": p["height"],
             "src": p["src"]["large2x"], "page": p["url"]} for p in r.get("photos", [])]

def pexels_get(pid, out):
    key = os.environ.get("PEXELS_KEY")
    p = json.loads(fetch(f"https://api.pexels.com/v1/photos/{pid}", [f"Authorization: {key}"]))
    save(fetch(p["src"]["large2x"]), out)
    print(json.dumps({"out": out, "credit": f"사진: {p['photographer']} / Pexels", "page": p["url"]}, ensure_ascii=False))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["search", "get", "pexels", "pexels-get"]); ap.add_argument("a"); ap.add_argument("b", nargs="?")
    ap.add_argument("-n", type=int, default=6); ap.add_argument("--logo", action="store_true"); o = ap.parse_args()
    try:
        if o.cmd == "search": print(json.dumps(search(o.a, o.n, o.logo), ensure_ascii=False, indent=1))
        elif o.cmd == "get": get(o.a, o.b, o.logo)
        elif o.cmd == "pexels": print(json.dumps(pexels(o.a, o.n), ensure_ascii=False, indent=1))
        else: pexels_get(o.a, o.b)
    except Fail as e:
        print(json.dumps({"error": str(e), "hint": "Wikimedia 요청 제한일 수 있음. 몇 분 뒤 1번만 다시 시도하고, 안 되면 사진 없이 카드·차트로 대체"}, ensure_ascii=False)); sys.exit(1)
