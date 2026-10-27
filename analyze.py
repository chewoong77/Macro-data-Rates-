"""최신 금리/WTI 데이터와 웹 검색(지정학 뉴스, Fed 발언)으로 Claude가 다음 FOMC 결정을 추정해 data/analysis.json에 저장한다.
사용: ANTHROPIC_API_KEY 환경변수 설정 후 `python analyze.py`. 키가 없으면 조용히 건너뛴다."""
import csv, json, os, re, sys, urllib.error, urllib.request
from datetime import datetime, timezone

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")

PROMPT = """Today (UTC): {today}

Latest daily data (FRED). US Treasury yields in %, WTI crude in USD/bbl:
[YIELDS]
{yields}
[WTI]
{oil}

Task:
1. Use web search to find (a) the next FOMC meeting date and recent Fed communications / market expectations, and (b) current geopolitical news that matters for oil and rates.
2. Judge whether the Fed's NEXT rate decision is most likely Hike, Cut, or Hold.
3. Reply with ONLY this JSON (no other text):
{{"decision":"Hike|Cut|Hold","next_meeting":"YYYY-MM-DD or 확인 불가","evidence":[exactly 10 strings],"sources":[{{"title":"...","url":"..."}}]}}

Rules: write evidence in Korean, one sentence each, each tied to the data above or a specific news item. Use only the data above and search results. Never invent numbers or dates; if something cannot be verified, say 확인 불가."""


def tail(name, n=10):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return []
    with open(p, newline="") as f:
        rows = list(csv.reader(f))
    return rows[:1] + rows[-n:] if len(rows) > 1 else []


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("ANTHROPIC_API_KEY 없음: 분석을 건너뜀")
        return
    y, o = tail("yields.csv"), tail("oil.csv")
    if not y or not o:
        print("데이터 부족: 분석을 건너뜀")
        return
    prompt = PROMPT.format(today=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                           yields="\n".join(",".join(r) for r in y), oil="\n".join(",".join(r) for r in o))
    body = {"model": MODEL, "max_tokens": 3000,
            "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"API 오류 {e.code}: {e.read().decode()[:500]}")
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    m = re.search(r'\{\s*"decision"', text)
    if not m:
        sys.exit("응답에서 JSON을 못 찾음: " + text[:300])
    res = json.JSONDecoder().raw_decode(text[m.start():])[0]
    if res.get("decision") not in ("Hike", "Cut", "Hold"):
        sys.exit("decision 값이 이상함: " + str(res.get("decision")))
    out = {"decision": res["decision"], "next_meeting": str(res.get("next_meeting", "")),
           "evidence": [str(x) for x in res.get("evidence", [])][:10],
           "sources": [s for s in res.get("sources", []) if isinstance(s, dict)][:8],
           "data_as_of": y[-1][0], "model": MODEL,
           "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    with open(os.path.join(DATA, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("analysis.json 저장:", out["decision"])


if __name__ == "__main__":
    main()
