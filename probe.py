#!/usr/bin/env python3
"""수급 데이터 대체 소스 탐색용 (일회성 2차). 다음 금융 투자자 API의 세부 항목·과거 깊이 확인."""
import urllib.request, json
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
H = {"User-Agent": UA, "Accept": "application/json", "Referer": "https://finance.daum.net/domestic/kospi"}
B = "https://finance.daum.net/api/investor/KOSPI/days"
C = [
 B + "?perPage=3&page=1&detail=true",
 B + "?perPage=3&page=1&details=true",
 B + "?perPage=3&page=1&isDetail=true",
 B + "?perPage=3&page=1&fieldName=details",
 "https://finance.daum.net/api/investor/KOSPI/days/details?perPage=3&page=1",
 B + "?perPage=100&page=1",
 B + "?perPage=100&page=60",
 B + "?perPage=100&page=200",
 "https://finance.daum.net/api/investor/days?symbolCode=KOSPI&perPage=3&page=1",
 "https://finance.daum.net/api/market_index/days?market=KOSPI&perPage=3&page=1",
 "https://finance.daum.net/api/investor/KOSPI/times?perPage=3&page=1",
]
for url in C:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=20) as r:
            t = r.read().decode("utf-8", "replace")
            try:
                j = json.loads(t)
                d = j.get("data") or []
                info = {"n": len(d), "first": d[0] if d else None, "last_date": d[-1].get("date") if d else None, "keys": list(j.keys())}
                print(f"[{r.status}] {url}\n   {json.dumps(info, ensure_ascii=False)[:900]}\n")
            except Exception:
                print(f"[{r.status}] {url}\n   {t[:300]!r}\n")
    except Exception as e:  # noqa
        print(f"[ERR] {url}: {e}\n")
#!/usr/bin/env python3
"""수급 데이터 대체 소스 탐색용 (일회성). 각 후보 주소의 응답 코드와 앞부분만 출력한다."""
import urllib.request, urllib.parse, ssl, json
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
C = [
 ("GET", "https://m.stock.naver.com/api/index/KOSPI/integration", None, {}),
 ("GET", "https://m.stock.naver.com/api/index/KOSPI/investorTrend", None, {}),
 ("GET", "https://m.stock.naver.com/api/index/KOSPI/trend?pageSize=10&page=1", None, {}),
 ("GET", "https://m.stock.naver.com/front-api/index/investor/trend?indexCode=KOSPI", None, {}),
 ("GET", "https://finance.naver.com/sise/sise_trans_style.naver?sosok=01", None, {}),
 ("GET", "https://finance.naver.com/sise/investorDealTrendTime.naver?bizdate=20261007&sosok=01", None, {}),
 ("GET", "https://finance.daum.net/api/investor/KOSPI/days?perPage=10&page=1", None, {"Referer": "https://finance.daum.net/domestic/kospi"}),
 ("GET", "https://finance.daum.net/api/market_index/investor/days?market=KOSPI&perPage=10", None, {"Referer": "https://finance.daum.net/domestic/kospi"}),
 ("POST", "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
  {"bld": "dbms/MDC/STAT/standard/MDCSTAT02201", "locale": "ko_KR", "inqTpCd": "2", "trdVolVal": "2", "askBid": "3",
   "mktId": "STK", "strtDd": "20260901", "endDd": "20261007", "etf": "EF", "etn": "EN", "elw": "EW", "detailView": "1"},
  {"Referer": "https://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020301"}),
 ("GET", "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS&cosd=2026-09-01", None, {}),
 ("GET", "https://fchart.stock.naver.com/sise.nhn?symbol=KOSPI&timeframe=day&count=5&requestType=0", None, {}),
 ("GET", "https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc", None, {}),
]
for m, url, data, hdr in C:
    try:
        body = urllib.parse.urlencode(data).encode() if data else None
        req = urllib.request.Request(url, data=body, method=m, headers={"User-Agent": UA, "Accept": "*/*", **hdr})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
            ct = r.headers.get("Content-Type", "")
            enc = "euc-kr" if "euc-kr" in ct.lower() else "utf-8"
            txt = raw.decode(enc, "replace")
            print(f"[{r.status}] {url} ({len(raw)}B, {ct})\n   {txt[:400]!r}\n")
    except Exception as e:  # noqa
        print(f"[ERR] {url}: {e}\n")
