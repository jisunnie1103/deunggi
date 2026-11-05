"""Collect national apartment trades using current official legal district codes.

Run: python3 -m collector.fetch_nationwide --deal-ymd 202610 --output-dir data
Successful districts are checkpointed; retry resumes only unfinished districts.
Use --refresh to re-fetch completed districts when updating a contract month.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import os
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from collector.browser_export import write_seoul_export
from collector.fetch_molit import service_key_from_env
from collector.molit_collector import MolitApartmentTradeCollector

CODE_URL = 'https://www.code.go.kr/etc/codeFullDown.do'


def load_dotenv(path: Path) -> None:
    """Read only the API setting, without executing shell or printing secrets."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        key, sep, value = line.strip().removeprefix('export ').partition('=')
        if sep and key.strip() == 'MOLIT_SERVICE_KEY':
            os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def parse_registry(text: str) -> list[dict]:
    codes = {}
    for row in csv.reader(io.StringIO(text), delimiter='\t'):
        if len(row) < 3:
            continue
        code, name, status = (part.strip() for part in row[:3])
        if len(code) != 10 or not code.isdigit() or status != '존재':
            continue
        if code[5:] != '00000' or code[2:5] == '000':
            continue
        parts = name.split()
        if len(parts) < 2:
            continue
        codes[code[:5]] = {'lawd_cd': code[:5], 'province_code': code[:2],
                             'province': parts[0], 'district': ' '.join(parts[1:]),
                             'full_name': name}
    # Municipal cities with non-autonomous wards: collect the leaf ward, not both.
    result = [value for code, value in codes.items()
              if not (code.endswith('0') and any(other != code and other[:4] == code[:4]
                                                for other in codes))]
    provinces = {d['province_code'] for d in result}
    if len(result) < 200 or len(provinces) < 16:
        raise ValueError('Incomplete official district registry; existing dataset retained')
    return sorted(result, key=lambda d: d['lawd_cd'])


def download_registry() -> list[dict]:
    body = urlencode({'codeseId': '법정동코드'}).encode()
    request = Request(CODE_URL, data=body, headers={'User-Agent': 'Mozilla/5.0'})
    with urlopen(request, timeout=30) as response:
        content = response.read()
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            name = next(n for n in archive.namelist() if n.lower().endswith('.txt'))
            content = archive.read(name)
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            return parse_registry(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise ValueError('Could not decode official district registry')


def collect_month(registry, deal_ymd, collector, checkpoint, refresh=False):
    previous = json.loads(checkpoint.read_text()) if checkpoint.exists() and not refresh else {}
    if previous.get('deal_ymd') != deal_ymd:
        previous = {'deal_ymd': deal_ymd, 'districts': {}}
    results = previous['districts']
    for index, district in enumerate(registry, 1):
        code = district['lawd_cd']
        if results.get(code, {}).get('collection_status') == 'complete':
            continue
        trades, success = [], False
        for attempt in range(3):
            try:
                trades = collector.fetch_month(lawd_cd=code, deal_ymd=deal_ymd)
                success = True
                break
            except Exception:
                # API URLs contain credentials: never print exceptions or request URLs.
                if attempt < 2:
                    time.sleep(2 ** attempt)
        results[code] = {**district, 'trades': trades, 'count': len(trades),
                         'collection_status': 'complete' if success else 'failed',
                         'collected_at': datetime.now(timezone.utc).isoformat() if success else None}
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        temp = checkpoint.with_suffix('.tmp')
        temp.write_text(json.dumps(previous, ensure_ascii=False))
        temp.replace(checkpoint)
        print(f"[{index}/{len(registry)}] {district['full_name']}: "
              + (f'{len(trades)} records' if success else 'failed; retry on next run'), flush=True)
        time.sleep(.15)
    districts = [results[d['lawd_cd']] for d in registry]
    complete = sum(d['collection_status'] == 'complete' for d in districts)
    return {'source': '국토교통부_아파트 매매 실거래가 자료 (data.go.kr 15126469)',
            'scope': '전국 시·군·구', 'deal_ymd': deal_ymd,
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'collection_status': 'complete' if complete == len(districts) else 'partial',
            'district_count': len(districts), 'collected_district_count': complete,
            'count': sum(d['count'] for d in districts), 'districts': districts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deal-ymd', required=True)
    parser.add_argument('--output-dir', default='data')
    parser.add_argument('--registry-file', type=Path, help='Official full legal-code TSV (optional)')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    MolitApartmentTradeCollector._validate('11110', args.deal_ymd)
    datetime.strptime(args.deal_ymd, '%Y%m')
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    collector = MolitApartmentTradeCollector(service_key_from_env())
    output_dir = Path(args.output_dir)
    try:
        if args.registry_file:
            content = args.registry_file.read_bytes()
            try:
                text = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = content.decode('cp949')
            registry = parse_registry(text)
        else:
            registry = download_registry()
    except Exception:
        raise SystemExit('Official district download failed. Check network or pass --registry-file with the official code.go.kr TSV. Existing transaction data retained.')
    checkpoint = output_dir / 'checkpoints' / f'nationwide_{args.deal_ymd}.json'
    payload = collect_month(registry, args.deal_ymd, collector, checkpoint, args.refresh)
    if not payload['collected_district_count']:
        raise SystemExit('No district collected successfully. Existing transaction data retained.')
    output = output_dir / 'molit_apt_trade_nationwide.json'
    write_seoul_export(payload, output)
    print(f"Saved {payload['count']} transactions; "
          f"{payload['collected_district_count']}/{payload['district_count']} districts complete.")
    if payload['collection_status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
