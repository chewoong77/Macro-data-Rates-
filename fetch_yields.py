"""FRED에서 미국 국채 2/5/10/20/30Y 일별 금리를 받아 data/yields.csv에 누적한다.
사용: FRED_API_KEY 환경변수를 설정하고 `python fetch_yields.py` (외부 패키지 불필요)."""
import csv, json, os, sys, urllib.parse, urllib.request
from datetime import date, timedelta

SERIES = {"y2": "DGS2", "y5": "DGS5", "y10": "DGS10", "y20": "DGS20", "y30": "DGS30"}
KEYS = list(SERIES)
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "yields.csv")
FIRST_RUN_START = "2025-01-01"  # 첫 실행 시 백필 시작일 (MoM 계산용으로 충분한 과거)


def load():
    rows = {}
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, newline="") as f:
            for r in csv.DictReader(f):
                rows[r["date"]] = {k: r.get(k) or "" for k in KEYS}
    return rows


def fetch(series_id, start, key):
    q = urllib.parse.urlencode({"series_id": series_id, "api_key": key,
                                "file_type": "json", "observation_start": start})
    url = "https://api.stlouisfed.org/fred/series/observations?" + q
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    # FRED는 휴장일 값을 "."로 준다 -> 건너뜀
    return {o["date"]: o["value"] for o in data["observations"] if o["value"] not in (".", "")}


def main():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        sys.exit("FRED_API_KEY 환경변수가 없어요.")
    rows = load()
    # 이미 데이터가 있으면 최근 45일만 다시 받아 덮어쓴다 (정정치 반영)
    start = (date.fromisoformat(max(rows)) - timedelta(days=45)).isoformat() if rows else FIRST_RUN_START
    for k, sid in SERIES.items():
        for d, v in fetch(sid, start, key).items():
            rows.setdefault(d, {kk: "" for kk in KEYS})[k] = v
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date"] + KEYS)
        for d in sorted(rows):
            w.writerow([d] + [rows[d][k] for k in KEYS])
    print(f"{len(rows)} rows, latest {max(rows)}")


if __name__ == "__main__":
    main()
