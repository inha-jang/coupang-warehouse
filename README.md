# 쿠팡 물류 네트워크 지도

전국 쿠팡 물류시설 288곳의 위치와 목록입니다. 배경지도는 OpenStreetMap을 씁니다.

**지도 보기 →** `https://<깃허브아이디>.github.io/<저장소이름>/`

| 유형 | 개수 | 표식 |
|---|---:|---|
| 풀필먼트 센터 | 88 | 빨강 사각형 |
| 서브FC | 32 | 보라 마름모 |
| 서브허브 | 51 | 주황 삼각형 |
| 캠프 | 114 | 청록 원 |
| 기타 시설 | 3 | 회색 십자 |

## 파일 구조

```
index.html        공개되는 페이지 (build.py 가 자동 생성)
facilities.csv    원본 데이터. 수정은 여기서만
template.html     페이지 디자인과 기능
build.py          facilities.csv + template.html → index.html
geocode.py        주소 → 좌표 (카카오 로컬 API)
geocode_osm.py    주소 → 좌표 (Nominatim, API 키 불필요)
```

## 데이터 고치는 법

깃허브 웹에서 `facilities.csv` 를 열어 연필 아이콘으로 수정하고 커밋하면 끝입니다.
GitHub Actions 가 `index.html` 을 다시 만들어 커밋하므로 로컬에서 아무것도 돌릴 필요가 없습니다.
1~2분 뒤 페이지에 반영됩니다.

로컬에서 작업하실 때는 이렇게 합니다.

```bash
python3 build.py facilities.csv index.html
```

### CSV 열

| 열 | 설명 |
|---|---|
| `name` | 시설명 |
| `type` | `풀필먼트센터` / `서브FC` / `서브허브` / `캠프` / `기타` |
| `address` | 주소 |
| `region` | 원본 목록의 권역 구분 |
| `sido`, `sigungu` | 비워 두면 주소에서 자동으로 채워집니다 |
| `lat`, `lng` | 위경도. 비어 있으면 표에만 나옵니다 |
| `precision` | 좌표 정밀도. 비어 있으면 정확한 좌표로 취급 |
| `note` | 비고 |
| `source_url` | 출처 링크. 넣으면 팝업에 표시됩니다 |

엑셀로 편집하실 때는 **CSV UTF-8** 로 저장하세요. 일반 CSV 는 한글이 깨집니다.

## 좌표 정밀도

`precision` 열이 좌표의 출처를 나타냅니다.

- **(빈칸)** — 지오코딩으로 얻은 실제 부지 좌표
- **읍면동** — 읍면동 중심점. 수백 m 오차
- **시군구** — 시군구 중심점. 수 km 오차
- **주소없음** — 원본에 주소가 없어 지도에서 제외

정확한 좌표로 바꾸는 방법은 두 가지입니다.

**브라우저에서 (터미널 불필요)**

1. [카카오 개발자센터](https://developers.kakao.com) 로그인 → 내 애플리케이션 → 애플리케이션 추가하기
2. 만든 앱을 열고 **요약 정보 → 앱 키**에서 `REST API 키` 를 복사
3. 이 저장소의 **Settings → Secrets and variables → Actions → New repository secret**
   이름은 `KAKAO_KEY`, 값은 복사한 키
4. **Actions 탭 → 좌표 채우기 → Run workflow**

2~3분 뒤 `facilities.csv` 와 `index.html` 이 자동으로 갱신됩니다.
카카오 키 없이 진행하려면 Run workflow 에서 `nominatim` 을 고르면 됩니다(적중률은 낮습니다).

**로컬에서**

```bash
export KAKAO_KEY="발급받은_키"
python3 geocode.py
python3 build.py facilities.csv index.html
```

두 방법 모두 임시 좌표(`precision` 이 읍면동·시군구인 행)만 다시 조회하고,
성공한 행은 `precision` 이 비워져 정확한 좌표로 표시됩니다.
찾지 못한 주소는 임시 좌표를 그대로 두고 실행 로그에 목록으로 남습니다.

## 같은 건물에 있는 시설

같은 주소를 쓰는 시설이 53곳 120개 있습니다. 표식이 겹쳐 가려지지 않도록
같은 좌표의 시설들을 65~150m 간격의 작은 원으로 흩어 놓았습니다.
지도를 확대하면 하나씩 구분되며, CSV 의 좌표값 자체는 원래대로입니다.

## 출처와 라이선스

- 배경지도 © [OpenStreetMap](https://www.openstreetmap.org/copyright) 기여자, 타일 © [CARTO](https://carto.com/attributions)
- 시설 목록은 공개된 자료를 정리한 것이며 쿠팡과 무관합니다
- 오류 제보는 Issues 로 남겨 주세요
