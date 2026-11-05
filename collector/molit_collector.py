"""국토교통부 아파트 매매 실거래가 OpenAPI 수집기.

환경변수 MOLIT_SERVICE_KEY에 공공데이터포털 일반 인증키(Decoding)를 넣고 사용한다.
API: 국토교통부_아파트 매매 실거래가 자료 (data.go.kr 15126469)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree as ET


ENDPOINT = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"


@dataclass(frozen=True)
class MolitApartmentTradeCollector:
    service_key: str
    fetch_bytes: Callable[[str], bytes] | None = None

    def fetch_month(self, *, lawd_cd: str, deal_ymd: str) -> list[dict]:
        """Fetch one municipality/month and return normalized KRW apartment trades."""
        self._validate(lawd_cd, deal_ymd)
        page = 1
        trades: list[dict] = []
        total_count: int | None = None

        while total_count is None or len(trades) < total_count:
            root = ET.fromstring(self._fetch(self._url(lawd_cd, deal_ymd, page)))
            self._raise_for_api_error(root)
            body = root.find("body")
            if body is None:
                raise RuntimeError("MOLIT response body missing")
            items = body.find("items")
            records = [] if items is None else list(items.findall("item"))
            trades.extend(self._normalize(item, lawd_cd) for item in records)
            total_count = self._int(self._text(body, "totalCount"))
            if not records:
                if len(trades) < total_count:
                    raise RuntimeError("Incomplete MOLIT pagination")
                break
            page += 1

        return trades

    def _url(self, lawd_cd: str, deal_ymd: str, page: int) -> str:
        query = urlencode({
            "serviceKey": self.service_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "numOfRows": 1000,
            "pageNo": page,
        })
        return f"{ENDPOINT}?{query}"

    def _fetch(self, url: str) -> bytes:
        if self.fetch_bytes:
            return self.fetch_bytes(url)
        with urlopen(url, timeout=30) as response:  # nosec B310: fixed government endpoint
            return response.read()

    @staticmethod
    def _validate(lawd_cd: str, deal_ymd: str) -> None:
        if not (lawd_cd.isdigit() and len(lawd_cd) == 5):
            raise ValueError("lawd_cd must be a five-digit legal district code")
        if not (deal_ymd.isdigit() and len(deal_ymd) == 6):
            raise ValueError("deal_ymd must be YYYYMM")

    @staticmethod
    def _text(parent: ET.Element, name: str) -> str:
        node = parent.find(name)
        return "" if node is None or node.text is None else node.text.strip()

    @classmethod
    def _int(cls, value: str) -> int:
        return int(value.replace(",", "")) if value else 0

    @classmethod
    def _normalize(cls, item: ET.Element, lawd_cd: str) -> dict:
        year = cls._int(cls._text(item, "dealYear"))
        month = cls._int(cls._text(item, "dealMonth"))
        day = cls._int(cls._text(item, "dealDay"))
        registry = cls._text(item, "rgstDate")
        cancellation_date = cls._text(item, "cdealDay")
        cancellation_type = cls._text(item, "cdealType")

        return {
            "lawd_cd": lawd_cd,
            "apartment_name": cls._text(item, "aptNm"),
            "deal_date": date(year, month, day).isoformat(),
            "price_krw": cls._int(cls._text(item, "dealAmount")) * 10_000,
            "area_sqm": float(cls._text(item, "excluUseAr")),
            "floor": cls._int(cls._text(item, "floor")),
            "build_year": cls._int(cls._text(item, "buildYear")),
            "dong": cls._text(item, "umdNm"),
            "jibun": cls._text(item, "jibun"),
            "registry_date": cls._iso_yyyymmdd(registry),
            "cancellation_type": cancellation_type or None,
            "cancellation_date": cls._iso_yyyymmdd(cancellation_date),
            "brokerage_type": cls._text(item, "dealingGbn") or None,
        }

    @classmethod
    def _raise_for_api_error(cls, root: ET.Element) -> None:
        code = cls._text(root, "header/resultCode")
        if code and code != "000":
            raise RuntimeError(f"MOLIT API error {code}: {cls._text(root, 'header/resultMsg')}")

    @staticmethod
    def _iso_yyyymmdd(value: str) -> str | None:
        if len(value) == 8 and value.isdigit():
            return f"{value[:4]}-{value[4:6]}-{value[6:]}"
        return None
