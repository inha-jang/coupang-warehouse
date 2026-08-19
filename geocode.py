#!/usr/bin/env python3
"""주소를 위경도로 바꿔 CSV 의 lat, lng 열을 채웁니다. (카카오 로컬 API)

준비
  1. https://developers.kakao.com 에서 앱을 만들고 REST API 키를 받습니다. (무료)
  2. 키를 환경변수에 넣습니다.
        export KAKAO_KEY="여기에_REST_API_키"

실행
        python3 geocode.py                     # facilities.csv 를 그 자리에서 갱신
        python3 geocode.py 내데이터.csv

동작
  - lat, lng 가 이미 채워진 행은 건너뜁니다. 여러 번 돌려도 안전합니다.
  - 주소 검색이 실패하면 키워드 검색(시설명 + 주소)으로 한 번 더 시도합니다.
  - 그래도 실패하면 lat, lng 를 비워 두고 마지막에 목록으로 보여 줍니다.
"""
import csv, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

KEY = os.environ.get("KAKAO_KEY", "").strip()
if not KEY:
    sys.exit("KAKAO_KEY 환경변수가 없습니다. export KAKAO_KEY=\"...\" 후 다시 실행하세요.")

PATH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "facilities.csv"
HEADERS = {"Authorization": f"KakaoAK {KEY}"}


def call(endpoint, **params):
    url = f"https://dapi.kakao.com/v2/local/{endpoint}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as r:
        import json
        return json.load(r).get("documents", [])


FLOOR = re.compile(r"^(지하\s*)?[BbGg]?\d+([-~]\d+)?\s*(층|[Ff])$")
UNIT  = re.compile(r"^([A-Za-z]|제?\d+)\s*(동|호|블럭|블록|게이트|코어|도크|Dock|dock)$")


def clean(address):
    """층·호수·건물 안내 같은 꼬리를 떼어 주소만 남깁니다.
    괄호 안 설명과 쉼표 뒤 내용은 카카오 주소 검색이 못 읽는 경우가 많습니다."""
    a = re.sub(r"\([^)]*\)", " ", address)      # 괄호 설명 제거
    a = a.split(",")[0]                          # 쉼표 뒤 층·동 정보 제거
    toks = a.split()
    while toks and (FLOOR.match(toks[-1]) or UNIT.match(toks[-1])):
        toks.pop()
    return " ".join(toks).strip()


def lookup(name, address):
    """되돌려주는 세 번째 값이 '어떻게 찾았는지' 입니다.
    이 값에 따라 precision 열이 달라지고, 페이지에서 검증 대상으로 표시됩니다."""
    if address:
        cleaned = clean(address)
        # 1) 층·호수만 떼고 주소 그대로 조회 — 이것만 정확한 좌표로 인정합니다
        for q in ([address, cleaned] if cleaned != address else [address]):
            docs = call("search/address.json", query=q, size=1)
            if docs:
                d = docs[0]
                return float(d["y"]), float(d["x"]), "", d.get("address_name", "")
        # 2) 뒤에서부터 한 토큰씩 잘라 가며 재시도 — 넓은 지역으로 밀릴 수 있습니다
        toks = cleaned.split()
        for n in range(len(toks) - 1, 2, -1):
            docs = call("search/address.json", query=" ".join(toks[:n]), size=1)
            if docs:
                d = docs[0]
                return float(d["y"]), float(d["x"]), "축약주소", d.get("address_name", "")
    # 3) 시설명으로 장소 검색 — 엉뚱한 곳이 잡힐 수 있습니다
    docs = call("search/keyword.json", query=f"{name} {clean(address)}".strip(), size=1)
    if docs:
        d = docs[0]
        return float(d["y"]), float(d["x"]), "키워드", d.get("road_address_name") or d.get("address_name", "")
    return None, None, None, None


rows = list(csv.DictReader(PATH.open(encoding="utf-8-sig", newline="")))
cols = list(rows[0].keys()) if rows else []
for c in ("lat", "lng", "precision", "matched"):
    if c not in cols:
        cols.append(c)

done = failed = skipped = shaky = 0
for r in rows:
    approx = (r.get("precision") or "").strip() in ("읍면동", "시군구")
    if (r.get("lat") or "").strip() and (r.get("lng") or "").strip() and not approx:
        skipped += 1        # 이미 정확한 좌표가 있는 행
        continue
    name, addr = (r.get("name") or "").strip(), (r.get("address") or "").strip()
    if not (name or addr):
        continue
    try:
        lat, lng, how, matched = lookup(name, addr)
    except Exception as e:
        print(f"  ! {name}: 요청 실패 {e}")
        lat = lng = how = matched = None
    if lat:
        r["lat"], r["lng"] = f"{lat:.6f}", f"{lng:.6f}"
        r["precision"] = how
        r["matched"] = matched or ""
        if how:
            shaky += 1
            print(f"  ~ {name} — {how}로 찾음. 확인 필요 → {matched}")
        else:
            done += 1
    else:
        r["precision"] = "실패"
        failed += 1
        print(f"  ✗ {name} — 찾지 못함: {addr}")
    time.sleep(0.12)   # 호출 간격을 둡니다

with PATH.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print(f"\n{PATH} 갱신 — 정확 {done}, 확인 필요 {shaky}, 실패 {failed}, 건너뜀 {skipped}")
if shaky:
    print("'~' 표시는 주소를 그대로 찾지 못해 축약하거나 시설명으로 찾은 것입니다.")
    print("페이지의 좌표 필터에서 '확인 필요' 를 골라 한 번씩 살펴보세요.")
if failed:
    print("실패한 행은 카카오맵에서 직접 찾아 lat, lng 를 손으로 채워 넣으면 됩니다.")
