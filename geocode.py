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
import csv, os, sys, time, urllib.parse, urllib.request
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


def lookup(name, address):
    """주소 검색 → 실패 시 키워드 검색."""
    if address:
        docs = call("search/address.json", query=address, size=1)
        if docs:
            return float(docs[0]["y"]), float(docs[0]["x"]), "주소"
        # 도로명 상세(동·호수 등)를 떼고 재시도
        trimmed = " ".join(address.split()[:4])
        if trimmed != address:
            docs = call("search/address.json", query=trimmed, size=1)
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"]), "주소(축약)"
    docs = call("search/keyword.json", query=f"{name} {address}".strip(), size=1)
    if docs:
        return float(docs[0]["y"]), float(docs[0]["x"]), "키워드"
    return None, None, None


rows = list(csv.DictReader(PATH.open(encoding="utf-8-sig", newline="")))
cols = list(rows[0].keys()) if rows else []
for c in ("lat", "lng"):
    if c not in cols:
        cols.append(c)

done = failed = skipped = 0
for r in rows:
    approx = (r.get("precision") or "").strip() in ("읍면동", "시군구")
    if (r.get("lat") or "").strip() and (r.get("lng") or "").strip() and not approx:
        skipped += 1        # 이미 정확한 좌표가 있는 행
        continue
    name, addr = (r.get("name") or "").strip(), (r.get("address") or "").strip()
    if not (name or addr):
        continue
    try:
        lat, lng, how = lookup(name, addr)
    except Exception as e:
        print(f"  ! {name}: 요청 실패 {e}")
        lat = lng = how = None
    if lat:
        r["lat"], r["lng"] = f"{lat:.6f}", f"{lng:.6f}"
        if "precision" in r:
            r["precision"] = ""
        done += 1
        print(f"  ✓ {name} ({how})")
    else:
        failed += 1
        print(f"  ✗ {name} — 찾지 못함: {addr}")
    time.sleep(0.12)   # 호출 간격을 둡니다

with PATH.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print(f"\n{PATH} 갱신 — 성공 {done}, 실패 {failed}, 건너뜀 {skipped}")
if failed:
    print("실패한 행은 카카오맵에서 직접 찾아 lat, lng 를 손으로 채워 넣으면 됩니다.")
