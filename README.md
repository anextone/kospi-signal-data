# kospi-signal-data

코스피 폭락 취약도 계기판(Claude)이 읽는 원본 데이터 저장소입니다. GitHub Actions가 매 영업일 07:20, 19:30(한국시간)에 `collect_official.py`를 실행해 `data/`를 갱신합니다.

| 파일 | 내용 | 원 출처 |
|---|---|---|
| data/kospi_index.csv | 코스피 일별 시가·고가·저가·종가·거래량 | 네이버 금융 차트(KRX 지수) |
| data/flows.csv | 코스피 투자자별 순매수(억원), 연기금 포함 | 네이버 금융 투자자별 매매동향 |
| data/fred_*.csv | 원/달러, 브렌트유, 미 10년물, VIX | FRED |
| data/lev_etf.csv | 삼성전자·SK하이닉스 단일종목 레버리지 ETF 시가총액 합계 | 네이버 금융 ETF 목록 |
| data/status.json | 소스별 성공 여부와 마지막 날짜 | — |

인증키나 비밀번호는 쓰지 않습니다. 과거 수급을 더 채우려면 Actions 탭 → Collect KOSPI signal data → Run workflow에서 `backfill_start`에 날짜를 넣어 실행합니다.
