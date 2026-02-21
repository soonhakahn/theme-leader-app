# 테마 주도주 Top10 앱 (MVP)

## 기능
- 종목명 입력 → 관련 테마 자동 추정
- 테마 내 종목 중 **시총 5천억 이상** 필터
- 주도점수 산출:
  - 거래대금(35)
  - 전일 대비 등락률(30)
  - 인기검색 대리지표(네이버 뉴스 노출수, 15)
  - 뉴스 모멘텀(특징주 키워드, 20)
- Top N 테이블 제공
- 종목 선택 시:
  - 캔들 차트
  - 관련 뉴스 제목 표시

## 설치
```bash
cd projects/theme-leader-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 실행
```bash
streamlit run app.py
```

## 비고
- HTS(0186/0181/0198)와 동일한 원천 데이터는 아니므로, 지표는 **근사치**입니다.
- 테마 사전(`THEME_MAP`)은 `app.py` 상단에서 쉽게 확장할 수 있습니다.
- 실무용으로 고도화하려면:
  - 실시간 체결/호가 API
  - 인기검색 원천 데이터 API
  - 테마 분류 DB(증권사/리서치) 연동
  - 백테스트/알림 기능
