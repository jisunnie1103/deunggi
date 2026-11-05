"""Write matching JSON and browser-readable exports of public transaction data."""
from __future__ import annotations

import json
from pathlib import Path


def write_seoul_export(payload: dict, output: Path) -> None:
    """Keep the server JSON and file:// browser data in sync after collection."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    browser_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    browser_json = browser_json.replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    output.with_suffix('.js').write_text(
        '// Public MOLIT transactions; generated from the adjacent JSON file.\n'
        'window.DEUNGGI_LOCAL_DATA=' + browser_json + ';\n', encoding='utf-8'
    )
