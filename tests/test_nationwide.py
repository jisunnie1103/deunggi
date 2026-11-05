"""Offline regression checks; generated fixtures are never production data."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from collector.fetch_nationwide import collect_month, parse_registry
from collector.molit_collector import MolitApartmentTradeCollector


class NationwideTests(unittest.TestCase):
    def test_registry_excludes_inactive_and_parent_cities(self):
        rows = ['법정동코드\t법정동명\t폐지여부']
        # Enough synthetic leaf districts to exercise completeness validation.
        for province in range(11, 27):
            for district in range(100, 115):
                rows.append(f'{province:02}{district:03}00000\t시도{province} 구{district}\t존재')
        rows += ['4111000000\t경기도 수원시\t존재',
                 '4111100000\t경기도 수원시 장안구\t존재',
                 '4111300000\t경기도 수원시 권선구\t존재',
                 '2811000000\t인천광역시 중구\t폐지',
                 '1168010100\t서울특별시 강남구 역삼동\t존재']
        registry = parse_registry('\n'.join(rows))
        codes = {d['lawd_cd'] for d in registry}
        self.assertNotIn('41110', codes)
        self.assertNotIn('28110', codes)
        self.assertIn('41111', codes)
        self.assertIn('41113', codes)
        self.assertEqual(next(d['full_name'] for d in registry if d['lawd_cd']=='41111'), '경기도 수원시 장안구')

    def test_incomplete_registry_rejected(self):
        with self.assertRaises(ValueError):
            parse_registry('1111000000\t서울특별시 종로구\t존재')

    @patch('collector.fetch_nationwide.time.sleep')
    def test_failures_are_unknown_not_zero_and_resume_retries_them(self, _sleep):
        registry = [{'lawd_cd': c, 'province_code': c[:2], 'province': n, 'district': '테스트구', 'full_name': n+' 테스트구'}
                    for c,n in [('11110','서울특별시'),('26110','부산광역시')]]
        client = Mock()
        client.fetch_month.side_effect = [[], RuntimeError('fail'),RuntimeError('fail'),RuntimeError('fail')]
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory)/'checkpoint.json'
            result = collect_month(registry, '202610', client, checkpoint)
            self.assertEqual(result['collection_status'], 'partial')
            self.assertEqual(result['collected_district_count'], 1)
            self.assertEqual(result['districts'][0]['collection_status'], 'complete')
            self.assertEqual(result['districts'][1]['collection_status'], 'failed')
            client.fetch_month.reset_mock(side_effect=True)
            client.fetch_month.return_value = []
            result = collect_month(registry,'202610',client,checkpoint)
            client.fetch_month.assert_called_once_with(lawd_cd='26110',deal_ymd='202610')
            self.assertEqual(result['collection_status'],'complete')

    def test_malformed_response_cannot_be_saved_as_no_transactions(self):
        client = MolitApartmentTradeCollector('test', fetch_bytes=lambda _: b'<response><header><resultCode>000</resultCode></header></response>')
        with self.assertRaisesRegex(RuntimeError, 'body missing'):
            client.fetch_month(lawd_cd='11110',deal_ymd='202610')

    def test_incomplete_page_is_failure(self):
        xml=b'<response><header><resultCode>000</resultCode></header><body><totalCount>2</totalCount><items/></body></response>'
        with self.assertRaisesRegex(RuntimeError, 'pagination'):
            MolitApartmentTradeCollector('test',fetch_bytes=lambda _:xml).fetch_month(lawd_cd='11110',deal_ymd='202610')


if __name__ == '__main__':
    unittest.main()
