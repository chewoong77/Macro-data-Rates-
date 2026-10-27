"""FRED에서 국채금리(2/5/10/20/30Y)와 WTI 원유(DCOILWTICO) 일별 데이터를 받아 data/*.csv에 누적한다.
사용: FRED_API_KEY 환경변수 설정 후 `python fetch_yields.py` (외부 패키지 불필요)."""
import csv, json, os, sys, urllib.parse, urllib.request
from datetime import date, timedelta

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
JOBS = [  # (파일, {열: FRED 시리즈}, 첫 실행 백필 시작일)
    ("yields.csv", {"y2": "DGS2", "y5": "DGS5", "y10": "DGS10", "y20": "DGS20", "y30": "DGS30"}, "2025-01-01"),
    ("oil.csv", {"wti": "DCOILWTICO"}, "2024-01-01"),  # YoY 계산용으로 더 과거부터
]


def fetch(series_id, start, key):
    q = urllib.parse.urlencode({"series_id": series_id, "api_key": key,
                                "file_type": "json", "observation_start": start})
    with urllib.request.urlopen("https://api.stlouisfed.org/fred/series/observations?" + q, timeout=30) as r:
        data = json.load(r)
    return {o["date"]: o["value"] for o in data["observations"] if o["value"] not in (".", "")}


def run(fname, series, first_start, key):
    path, keys, rows = os.path.join(DATA, fname), list(series), {}
    if os.path.exists(path):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                rows[r["date"]] = {k: r.get(k) or "" for k in keys}
    start = (date.fromisoformat(max(rows)) - timedelta(days=45)).isoformat() if rows else first_start
    for k, sid in series.items():
        for d, v in fetch(sid, start, key).items():
            rows.setdefault(d, {kk: "" for kk in keys})[k] = v
    os.makedirs(DATA, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date"] + keys)
        for d in sorted(rows):
            w.writerow([d] + [rows[d][k] for k in keys])
    print(f"{fname}: {len(rows)} rows, latest {max(rows) if rows else '-'}")


if __name__ == "__main__":
    key = os.environ.get("FRED_API_KEY")
    if not key:
        sys.exit("FRED_API_KEY 환경변수가 없어요.")
    for job in JOBS:
        run(*job, key)
