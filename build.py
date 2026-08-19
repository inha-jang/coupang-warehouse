#!/usr/bin/env python3
"""facilities.csv 를 읽어 template.html 에 주입하고 tracker.html 을 만듭니다.

    python3 build.py                        # 기본 경로 사용
    python3 build.py 내데이터.csv 결과.html

CSV 열: name, type, address, sido, sigungu, lat, lng, opened, note, source_url
  - type 은 풀필먼트센터 / 서브허브 / 캠프 / 기타 중 하나여야 합니다.
  - sido, sigungu 를 비워 두면 address 앞부분에서 자동으로 채웁니다.
  - lat, lng 가 비어 있으면 표에는 나오지만 지도에는 표시되지 않습니다.
"""
import csv, json, re, sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "facilities.csv"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "tracker.html"
TPL = HERE / "template.html"

VALID = {"풀필먼트센터", "서브FC", "서브허브", "캠프", "기타"}
# 흔한 표기 흔들림을 정규화합니다.
ALIAS = {
    "풀필먼트 센터": "풀필먼트센터", "fc": "풀필먼트센터", "FC": "풀필먼트센터",
    "물류센터": "풀필먼트센터", "풀필먼트": "풀필먼트센터",
    "서브 허브": "서브허브", "subhub": "서브허브", "sub-hub": "서브허브", "허브": "서브허브",
    "서브 FC": "서브FC", "sub fc": "서브FC", "sub-fc": "서브FC", "subfc": "서브FC", "sr-fc": "서브FC",
    "배송캠프": "캠프", "camp": "캠프",
    "기타시설": "기타", "기타 시설": "기타", "": "기타",
}

SIDO_FULL = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "광주광역시", "대전": "대전광역시", "울산": "울산광역시", "세종": "세종특별자치시",
    "경기": "경기도", "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}


def norm_type(v):
    v = (v or "").strip()
    if v in VALID:
        return v
    return ALIAS.get(v, ALIAS.get(v.lower(), "기타"))


def split_addr(addr):
    """주소 문자열에서 시도 / 시군구를 뽑아냅니다."""
    parts = (addr or "").split()
    if not parts:
        return "", ""
    sido = parts[0]
    for short, full in SIDO_FULL.items():
        if sido.startswith(short):
            sido = full
            break
    sigungu = ""
    for p in parts[1:3]:
        if re.search(r"(시|군|구)$", p):
            sigungu = p
            break
    return sido, sigungu


def num(v):
    try:
        return round(float(str(v).strip()), 6)
    except (TypeError, ValueError):
        return None


rows, problems = [], []
with SRC.open(encoding="utf-8-sig", newline="") as f:
    for i, r in enumerate(csv.DictReader(f), start=2):
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        if not r.get("name"):
            continue
        raw_type = r.get("type", "")
        t = norm_type(raw_type)
        if raw_type and raw_type not in VALID and t == "기타":
            problems.append(f"  {i}행 '{r['name']}': 유형 '{raw_type}' 을 알 수 없어 기타로 넣었습니다")
        sido, sigungu = r.get("sido"), r.get("sigungu")
        if not sido or not sigungu:
            a, b = split_addr(r.get("address", ""))
            sido, sigungu = sido or a, sigungu or b
        lat, lng = num(r.get("lat")), num(r.get("lng"))
        if lat is None or lng is None:
            problems.append(f"  {i}행 '{r['name']}': 좌표가 없어 지도에서 빠집니다")
        rows.append({
            "name": r["name"], "type": t, "address": r.get("address", ""),
            "region": r.get("region", ""), "sido": sido, "sigungu": sigungu,
            "lat": lat, "lng": lng, "precision": r.get("precision", ""), "matched": r.get("matched", ""),
            "note": r.get("note", ""), "source_url": r.get("source_url", ""),
        })

ORDER = ["풀필먼트센터", "서브FC", "서브허브", "캠프", "기타"]
rows.sort(key=lambda x: (ORDER.index(x["type"]), x["name"]))

counts = {t: sum(1 for r in rows if r["type"] == t) for t in ORDER}
mapped = sum(1 for r in rows if r["lat"] is not None)
meta = {
    "built": date.today().isoformat(),
    "note": ("총 " + str(len(rows)) + "개 시설 — "
             + ", ".join(f"{t} {n}개" for t, n in counts.items()) + ". "
             f"이 중 {mapped}개가 지도에 표시됩니다. 좌표는 행정구역 중심점 기준의 임시값이며 "
             f"실제 부지와 차이가 있습니다. 원본 목록 기준일: 풀필먼트 센터 2026-08-18, 나머지 2026-07-13."),
}

html = TPL.read_text(encoding="utf-8")
html = html.replace("/*__DATA__*/[]", json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
html = html.replace('/*__META__*/{built:"", note:""}', json.dumps(meta, ensure_ascii=False))
OUT.write_text(html, encoding="utf-8")

print(f"{OUT} 생성 — 시설 {len(rows)}개, 지도 표시 {mapped}개")
for t, n in counts.items():
    print(f"  {t}: {n}")
if problems:
    print(f"\n확인이 필요한 행 {len(problems)}건:")
    print("\n".join(problems[:30]))
    if len(problems) > 30:
        print(f"  … 외 {len(problems) - 30}건")
