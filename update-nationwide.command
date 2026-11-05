#!/bin/zsh
cd "${0:A:h}" || exit 1
printf '전국 아파트 실거래가 수집 · 계약월 (예: 202610): '
read trade_month
python3 -m collector.fetch_nationwide --deal-ymd "$trade_month" --output-dir data "$@"
result=$?
printf '\n완료 후 브라우저를 새로고침하세요. 종료하려면 Enter를 누르세요.\n'
read
exit "$result"
