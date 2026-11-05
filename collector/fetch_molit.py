"""Command-line collector for a single MOLIT apartment trade month.

Example:
  MOLIT_SERVICE_KEY='...' python3 -m collector.fetch_molit --lawd-cd 11680 --deal-ymd 202604
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from collector.molit_collector import MolitApartmentTradeCollector


def service_key_from_env() -> str:
    key = os.environ.get("MOLIT_SERVICE_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "MOLIT_SERVICE_KEY is missing. Set the public data portal Decoding key before collecting."
        )
    return key


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect MOLIT apartment sale records for one district/month.")
    parser.add_argument("--lawd-cd", required=True, help="five-digit legal district code, e.g. 11680 (Gangnam-gu)")
    parser.add_argument("--deal-ymd", required=True, help="contract month in YYYYMM format")
    parser.add_argument("--output-dir", default="data/raw", help="directory for the raw normalized JSON export")
    args = parser.parse_args()

    trades = MolitApartmentTradeCollector(service_key_from_env()).fetch_month(
        lawd_cd=args.lawd_cd,
        deal_ymd=args.deal_ymd,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"molit_apt_trade_{args.lawd_cd}_{args.deal_ymd}.json"
    payload = {
        "source": "국토교통부_아파트 매매 실거래가 자료 (data.go.kr 15126469)",
        "lawd_cd": args.lawd_cd,
        "deal_ymd": args.deal_ymd,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "count": len(trades),
        "trades": trades,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Collected {len(trades)} records → {output}")


if __name__ == "__main__":
    main()
