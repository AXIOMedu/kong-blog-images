"""Gemini(나노 바나나)로 블로그용 사진 생성 → 로컬 JPG 저장. thumbs.py P 스타일의 "photo"나 본문 이미지로 그대로 쓴다.

키: 환경변수 GEMINI_API_KEY (노션 '도구 설정 (API 키)' 페이지에서 읽어 export. 키 값은 글·노션 본문·커밋·로그에 절대 쓰지 말 것).
모델: 환경변수 GEMINI_IMAGE_MODEL 이 있으면 그것, 없으면 gemini-3.1-flash-lite-image(가장 저렴) → gemini-3.1-flash-image(512px, 장당 약 $0.045) 순서.
비용 규칙: 하루 최대 2장(경제콩·멘토콩 홈판형 글 썸네일 사진만). 나머지 글은 photos.py 무료 사진·표지 카드·H 스타일.

사용:
  python3 tools/gen_image.py spec.json
  spec.json = [{"prompt":"영양제 통 여러 개가 놓인 부엌 식탁, 아침 햇살", "out":"2026-11-17/p3_photo.jpg", "aspect":"1:1"}, ...]
  aspect: 1:1(썸네일 기본) / 4:5(카드) / 16:9(본문 가로) / 9:16(클립)

규칙(프롬프트에 자동으로 덧붙음, 그래도 직접 지킬 것):
  - 실존 인물·연예인·정치인 얼굴, 실제 회사 로고·브랜드 제품·약 포장, 실제 병원 간판 금지.
  - 엑스레이·검사지·처방전·공시 문서·차트처럼 '진짜 자료'로 오해될 이미지 금지(차트는 chart.py로 실데이터만).
  - 이미지 안 글자 금지(글자는 thumbs.py가 얹는다).
  - 쓴 이미지 아래 캡션 끝에 "(AI 생성 이미지)"를 붙인다.
실패(키 없음·차단·거부)하면 종료코드 1과 사유를 출력 → photos.py 실사진이나 thumbs.py H 스타일로 대체.
"""
import base64, io, json, os, sys, urllib.request, urllib.error
from PIL import Image

MODELS = ["gemini-3.1-flash-lite-image", "gemini-3.1-flash-image"]  # 비용 순(2026-11-16 사용자: 싸게). flash-image는 512px로만
GUARD = (" Style: natural editorial photograph, realistic lighting, shallow depth of field, Korean everyday setting when relevant."
         " Strictly no text, letters, numbers, captions or watermarks in the image. No logos, no brand names, no real product packaging."
         " No identifiable real or famous people; if people appear, show them from behind, hands only, or out of focus."
         " Not a medical document, X-ray, chart, prescription or screenshot.")

def call(model, prompt, aspect, ver):
    size = "512" if model == "gemini-3.1-flash-image" else None
    url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt + GUARD}]}],
            "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect, **({"imageSize": size} if size else {})}}}
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    for part in (d.get("candidates") or [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part: return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("이미지 없음: " + json.dumps(d.get("promptFeedback") or d.get("candidates", [{}])[0].get("finishReason"), ensure_ascii=False))

def gen(s):
    last = ""
    models = [os.environ["GEMINI_IMAGE_MODEL"]] if os.environ.get("GEMINI_IMAGE_MODEL") else MODELS
    for model in models:
        for ver in ("v1", "v1beta"):
            try:
                raw = call(model, s["prompt"], s.get("aspect", "1:1"), ver)
                os.makedirs(os.path.dirname(s["out"]) or ".", exist_ok=True)
                Image.open(io.BytesIO(raw)).convert("RGB").save(s["out"], quality=88)
                return model
            except urllib.error.HTTPError as e:
                last = f"{model}/{ver} HTTP {e.code}: {e.read()[:200].decode('utf-8', 'ignore')}"
                if e.code in (400, 401, 403, 429): break  # 키·요청·한도 문제: 같은 모델 다른 버전 시도 무의미
            except Exception as e:
                last = f"{model}/{ver} {e}"
    raise RuntimeError(last)

def _clean(v): return (v or "").strip().strip("()").strip().strip("'\"")
for _k in ("GEMINI_API_KEY", "GEMINI_IMAGE_MODEL"):
    if _k in os.environ: os.environ[_k] = _clean(os.environ[_k])
if os.environ.get("GEMINI_IMAGE_MODEL", "").startswith("비워두면"): os.environ.pop("GEMINI_IMAGE_MODEL")

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("실패: GEMINI_API_KEY 환경변수 없음"); sys.exit(1)
    spec = json.load(open(sys.argv[1])); spec = spec if isinstance(spec, list) else [spec]
    bad = 0
    for s in spec:
        try: print(s["out"], "←", gen(s))
        except Exception as e: bad += 1; print("실패:", s["out"], e)
    sys.exit(1 if bad else 0)
