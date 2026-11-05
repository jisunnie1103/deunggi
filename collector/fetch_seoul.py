"""Collect one contract month of MOLIT apartment sale records for every Seoul district."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from collector.browser_export import write_seoul_export
from collector.fetch_molit import service_key_from_env
from collector.molit_collector import MolitApartmentTradeCollector


SEOUL_DISTRICTS = {
    "11110": "종로구", "11140": "중구", "11170": "용산구", "11200": "성동구", "11215": "광진구",
    "11230": "동대문구", "11260": "중랑구", "11290": "성북구", "11305": "강북구", "11320": "도봉구",
    "11350": "노원구", "11380": "은평구", "11410": "서대문구", "11440": "마포구", "11470": "양천구",
    "11500": "강서구", "11530": "구로구", "11545": "금천구", "11560": "영등포구", "11590": "동작구",
    "11620": "관악구", "11650": "서초구", "11680": "강남구", "11710": "송파구", "11740": "강동구",
}


def collect_seoul_month(*, deal_ymd: str, collector_factory: Callable[[str], MolitApartmentTradeCollector]) -> dict[str, list[dict]]:
    """Collect each Seoul district independently so failures identify their district."""
    return {
        lawd_cd: collector_factory(lawd_cd).fetch_month(lawd_cd=lawd_cd, deal_ymd=deal_ymd)
        for lawd_cd in SEOUL_DISTRICTS
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect a contract month for all 25 Seoul districts.")
    parser.add_argument("--deal-ymd", required=True, help="contract month in YYYYMM format")
    parser.add_argument("--output-dir", default="data/raw", help="directory for the normalized JSON export")
    args = parser.parse_args()

    service_key = service_key_from_env()
    results = collect_seoul_month(
        deal_ymd=args.deal_ymd,
        collector_factory=lambda _lawd_cd: MolitApartmentTradeCollector(service_key),
    )
    districts = [
        {"lawd_cd": code, "district": SEOUL_DISTRICTS[code], "count": len(trades), "trades": trades}
        for code, trades in results.items()
    ]
    payload = {
        "source": "국토교통부_아파트 매매 실거래가 자료 (data.go.kr 15126469)",
        "scope": "서울특별시 25개 자치구",
        "deal_ymd": args.deal_ymd,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "district_count": len(districts),
        "count": sum(district["count"] for district in districts),
        "districts": districts,
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"molit_apt_trade_seoul_{args.deal_ymd}.json"
    write_seoul_export(payload, output)
    print(f"Collected {payload['count']} records across {len(districts)} Seoul districts → {output}")


if __name__ == "__main__":
    main()
