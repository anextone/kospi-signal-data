#!/usr/bin/env python3
"""코스피 폭락 신호용 원본 데이터 수집기 (GitHub Actions에서 실행, 표준 라이브러리만 사용)

수집 대상 (모두 공개, 인증키 불필요)
  data/kospi_index.csv   코스피 지수 일별 시가·고가·저가·종가·거래량   네이버 금융 차트(KRX 지수 원값)
  data/flows.csv         코스피 투자자별 순매수(억원)                    네이버 금융 투자자별 매매동향
  data/fred_<ID>.csv     DEXKOUS(원/달러), DCOILBRENTEU(브렌트), DGS10(미 10년물), VIXCLS(VIX)   FRED
  data/lev_etf.csv       삼성전자·SK하이닉스 단일종목 레버리지 ETF 시가총액 합계(억원) 일별 스냅샷   네이버 금융 ETF 목록
  data/status.json       소스별 성공 여부·마지막 날짜·오류

환경변수
  BACKFILL_START=YYYY-MM-DD   투자자 수급을 이 날짜까지 과거로 채움(수동 실행 때만). 비우면 최근 분만 갱신.
"""
import csv, datetime as dt, io, json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
KST = dt.timezone(dt.timedelta(hours=9))
status = {"run_at": dt.datetime.now(KST).isoformat(timespec="seconds"), "sources": {}}


def get(url, enc="utf-8", referer=None, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, **({"Referer": referer} if referer else {})})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode(enc, "replace")
        except Exception as e:  # noqa
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"{url}: {last}")


def write_csv(path, header, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def record(name, fn):
    try:
        info = fn() or {}
        status["sources"][name] = {"ok": True, **info}
    except Exception as e:  # noqa
        status["sources"][name] = {"ok": False, "error": str(e)[:300]}
        print(f"[실패] {name}: {e}", file=sys.stderr)


# ---- 1. 코스피 지수 (네이버 차트 XML, 전체 이력 1회 요청) --------------------
def kospi_index():
    xml = get("https://fchart.stock.naver.com/sise.nhn?symbol=KOSPI&timeframe=day&count=8000&requestType=0", enc="euc-kr")
    items = re.findall(r'<item data="([^"]+)"', xml)
    rows = []
    for it in items:
        p = it.split("|")
        if len(p) < 6:
            continue
        d = p[0]
        rows.append([f"{d[:4]}-{d[4:6]}-{d[6:8]}", p[1], p[2], p[3], p[4], p[5]])
    if len(rows) < 100:
        raise RuntimeError(f"행 수가 너무 적음({len(rows)}) — 응답 형식 변경 의심")
    rows.sort()
    write_csv(os.path.join(DATA, "kospi_index.csv"), ["date", "open", "high", "low", "close", "volume"], rows)
    return {"last_date": rows[-1][0], "first_date": rows[0][0], "rows": len(rows)}


# ---- 2. 투자자별 순매수 (네이버, 페이지당 10영업일) ------------------------
FLOW_COLS = ["date", "individual", "foreign", "institution", "fin_invest", "insurance", "trust", "bank",
             "other_fin", "pension", "other_corp"]
ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{2})$")


def flow_page(bizdate):
    html = get(f"https://finance.naver.com/sise/investorDealTrendDay.naver?bizdate={bizdate}&sosok=01", enc="euc-kr",
               referer="https://finance.naver.com/sise/sise_deal_rank.naver")
    out = []
    for tr in ROW_RE.findall(html):
        cells = [TAG_RE.sub("", c).replace("&nbsp;", " ").strip() for c in CELL_RE.findall(tr)]
        if len(cells) < len(FLOW_COLS):
            continue
        m = DATE_RE.match(cells[0])
        if not m:
            continue
        rec = {"date": f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"}
        for i, c in enumerate(FLOW_COLS[1:], start=1):
            try:
                rec[c] = int(cells[i].replace(",", ""))
            except ValueError:
                rec[c] = 0
        out.append(rec)
    return out


def flows():
    path = os.path.join(DATA, "flows.csv")
    have = {r["date"]: r for r in read_csv(path)}
    start = os.environ.get("BACKFILL_START", "").strip()
    target = start or (max(have) if have else (dt.date.today() - dt.timedelta(days=400)).isoformat())
    cur = dt.datetime.now(KST).date()
    pages = 0
    while pages < 3000:
        rows = flow_page(cur.strftime("%Y%m%d"))
        pages += 1
        if not rows:
            break
        for r in rows:
            have[r["date"]] = r  # 다시 받은 날은 최신 값으로 덮어씀(잠정치 보정)
        oldest = min(r["date"] for r in rows)
        if oldest <= target:
            break
        cur = dt.date.fromisoformat(oldest) - dt.timedelta(days=1)
        time.sleep(0.4)
    rows = [[have[d][c] for c in FLOW_COLS] for d in sorted(have)]
    write_csv(path, FLOW_COLS, rows)
    return {"last_date": rows[-1][0] if rows else None, "first_date": rows[0][0] if rows else None, "rows": len(rows), "pages": pages}


# ---- 3. FRED ---------------------------------------------------------------
def fred(sid):
    def run():
        txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}")
        rd = list(csv.reader(io.StringIO(txt)))
        hdr, body = rd[0], rd[1:]
        body = [r for r in body if len(r) == 2 and r[1] not in (".", "")]
        if len(body) < 50:
            raise RuntimeError(f"행 수가 너무 적음({len(body)})")
        write_csv(os.path.join(DATA, f"fred_{sid}.csv"), ["date", "value"], body)
        return {"last_date": body[-1][0], "rows": len(body)}
    return run


# ---- 4. 단일종목 레버리지 ETF 스냅샷 ----------------------------------------
LEV_RE = re.compile(r"(삼성전자|SK하이닉스|하이닉스).*(레버리지|2X|2x)")


def lev_etf():
    txt = get("https://finance.naver.com/api/sise/etfItemList.nhn?etfType=0&targetColumn=market_sum&sortOrder=desc", enc="euc-kr")
    js = json.loads(txt)
    items = js.get("result", {}).get("etfItemList", [])
    if not items:
        raise RuntimeError("ETF 목록이 비어 있음 — 응답 형식 변경 의심")
    hit = [it for it in items if LEV_RE.search(it.get("itemname", "")) and "인버스" not in it.get("itemname", "")]
    total = sum(float(it.get("marketSum") or 0) for it in hit)  # 억원
    today = dt.datetime.now(KST).date().isoformat()
    path = os.path.join(DATA, "lev_etf.csv")
    old = {r["date"]: r for r in read_csv(path)}
    old[today] = {"date": today, "count": len(hit), "total_marcap_eok": round(total, 1),
                  "items": ";".join(f"{it.get('itemcode')}:{it.get('itemname')}:{it.get('marketSum')}" for it in hit)}
    rows = [[old[d]["date"], old[d]["count"], old[d]["total_marcap_eok"], old[d]["items"]] for d in sorted(old)]
    write_csv(path, ["date", "count", "total_marcap_eok", "items"], rows)
    return {"last_date": today, "count": len(hit), "total_marcap_eok": round(total, 1)}


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    record("kospi_index", kospi_index)
    record("flows", flows)
    for sid in ("DEXKOUS", "DCOILBRENTEU", "DGS10", "VIXCLS"):
        record(f"fred_{sid}", fred(sid))
    record("lev_etf", lev_etf)
    with open(os.path.join(DATA, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    print(json.dumps(status, ensure_ascii=False, indent=1))
    if not any(v.get("ok") for v in status["sources"].values()):
        sys.exit(1)
