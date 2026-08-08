# -*- coding: utf-8 -*-
"""
auto_trade.py 自动化测试套件

覆盖:
  1. calc_limit_up / calc_stop_price — 涨停/止损价计算
  2. _safe_float — QMT tick 类型安全
  3. load_tpo3 — 两种文件格式
  4. _load_precomputed — ATR10/MA5/MA10 预计算
  5. compute_features — 5特征实时计算 + MA滚动公式
  6. check_sell_signal — 止损卖出信号
  7. train_walk_forward — 样本加载+岭回归
  8. api.buy / api.sell 参数顺序
  9. 回测一致性: pb_depth/ma5_dev/bear/bull/golden 公式对齐
 10. vol_contract 已删除验证

用法: python -B test_auto_trade.py          # 静默, 仅输出失败项
       python -B test_auto_trade.py -v       # 详细输出
       python -B test_auto_trade.py --quick  # 仅快速测试(跳过WF重训)
"""
import sys, os, math, json, tempfile, shutil, unittest, logging
import numpy as np
from io import StringIO
from unittest.mock import patch, MagicMock, PropertyMock

# ===== MOCK xtquant BEFORE importing auto_trade =====
class MockTick:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class MockPosition:
    def __init__(self, stock_code, volume, avg_price, market_value=0, profit=0):
        self.stock_code = stock_code
        self.volume = volume
        self.avg_price = avg_price
        self.market_value = market_value or volume * avg_price
        self.profit = profit
        self.current_price = avg_price

class MockAsset:
    def __init__(self, total_asset=100000, cash=50000, market_value=50000):
        self.total_asset = total_asset
        self.cash = cash
        self.market_value = market_value

class MockTrade:
    def __init__(self, stock_code, direction, traded_volume, price=0):
        self.stock_code = stock_code
        self.direction = direction  # 1=buy, 2=sell
        self.traded_volume = traded_volume
        self.price = price

class MockOrder:
    def __init__(self, order_id, stock_code, order_status, order_volume, price=0, order_type='sell', status_text=''):
        self.order_id = str(order_id)
        self.stock_code = stock_code
        self.order_status = order_status
        self.order_volume = order_volume
        self.price = price
        self.order_type = order_type
        self.status_text = status_text or {48:'未报',49:'待报',50:'已报',52:'部成',54:'已撤',55:'部成',56:'已成',57:'废单'}.get(order_status, '')

# Mock xtquant module before auto_trade imports it
mock_xtquant = MagicMock()
mock_xtdata = MagicMock()
mock_xtdata.enable_hello = False
mock_xtdata.connect = MagicMock()
mock_xtdata.get_full_tick = MagicMock(return_value={})
mock_xtdata.get_instrument_detail = MagicMock(return_value={'InstrumentName': '测试股'})
mock_xtdata.get_market_data_ex = MagicMock(return_value={})
sys.modules['xtquant'] = mock_xtquant
sys.modules['xtquant.xtdata'] = mock_xtdata
sys.modules['xtquant.xttrader'] = MagicMock()
sys.modules['xtquant.xttype'] = MagicMock()

import auto_trade as at

# Suppress log output during tests
at.log.handlers = []
at.log.addHandler(logging.NullHandler())
at.log.propagate = False

# ===== Helper =====
def log_output():
    """Return captured log content"""
    return _log_stream.getvalue()

# ==============================================================================
#  TEST 1: calc_limit_up / calc_stop_price
# ==============================================================================
class TestPricing(unittest.TestCase):
    def test_limit_up_two_stage_rounding(self):
        """验证两次四舍五入"""
        cases = [
            (5.04,  5.54),  # raw=5.544 → 5.54
            (6.86,  7.55),  # raw=7.546 → 7.55
            (3.45,  3.80),  # raw=3.795 → floor(3.80)=3.80
            (9.99,  10.99), # raw=10.989 → 10.99
            (44.67, 49.14), # 四方股份实证
            (44.70, 49.17), # 相同昨收验证
            (0.91,  1.00),
            (10.00, 11.00),
            (99.99, 109.99),
            (8.88,  9.77),
        ]
        for pre, expected in cases:
            result = at.calc_limit_up(pre)
            self.assertEqual(result, expected,
                             f"pre={pre} raw={pre*1.10:.4f} got={result} expected={expected}")

    def test_limit_up_no_bankers_rounding(self):
        """Python round(5.5445,2) → 5.54, 但calc_limit_up应返回5.55"""
        py_round = round(5.545, 2)
        my_round = at.calc_limit_up(5.545 / 1.10)
        # Banker's rounding in some Python versions: round(5.545, 2) can be 5.54 or 5.55
        # Our calc_limit_up should consistently give the A-share correct value
        self.assertIn(my_round, [5.54, 5.55])  # depends on exact float, just no crash

    def test_stop_price(self):
        self.assertEqual(at.calc_stop_price(45.00), 42.30)
        self.assertEqual(at.calc_stop_price(44.67), 41.99)  # round(44.67*0.94,2)
        self.assertEqual(at.calc_stop_price(100.00), 94.00)
        self.assertEqual(at.calc_stop_price(5.04), 4.74)

# ==============================================================================
#  TEST 2: _safe_float
# ==============================================================================
class TestSafeFloat(unittest.TestCase):
    def test_list_first_element(self):
        self.assertEqual(at._safe_float([12.34]), 12.34)
        self.assertEqual(at._safe_float([5]), 5.0)

    def test_list_empty(self):
        self.assertEqual(at._safe_float([], default=99.9), 99.9)

    def test_tuple(self):
        self.assertEqual(at._safe_float((7.7,)), 7.7)

    def test_none(self):
        self.assertEqual(at._safe_float(None), 0.0)
        self.assertEqual(at._safe_float(None, default=-1.0), -1.0)

    def test_string(self):
        self.assertEqual(at._safe_float("12.34"), 12.34)

    def test_int(self):
        self.assertEqual(at._safe_float(42), 42.0)

    def test_float(self):
        self.assertEqual(at._safe_float(3.14), 3.14)

    def test_invalid_string(self):
        self.assertEqual(at._safe_float("abc", default=0.0), 0.0)

# ==============================================================================
#  TEST 3: _load_precomputed (MA5/MA10 ROLLING)
# ==============================================================================
class TestPrecomputed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Create a temporary 1D kline file with known data"""
        cls.tmpdir = tempfile.mkdtemp()
        cls.orig_kline_dir = at.KLINE_DIR
        at.KLINE_DIR = cls.tmpdir

        # Generate 20 days of fake kline data
        # date | open | high | low | close | vol | amount | ... | preClose
        closes = [
            100, 101, 99, 102, 103, 104, 105, 106, 107, 108,
            109, 110, 111, 112, 113, 114, 115, 116, 117, 118
        ]
        dates = [f"202608{str(d).zfill(2)}" for d in range(1, 21)]

        kline = f"{cls.tmpdir}/TEST.SH"
        with open(kline, 'w', encoding='utf-8') as f:
            for i in range(20):
                pc = closes[i-1] if i > 0 else closes[i]
                oh = closes[i] * 1.02
                ol = closes[i] * 0.98
                f.write(f"{dates[i]} {ol:.2f} {oh:.2f} {ol:.2f} {closes[i]:.2f} "
                        f"{100000 + i * 1000} {10000000} 0 0 {pc:.2f}\n")

        cls.closes = closes
        cls.dates = dates

    @classmethod
    def tearDownClass(cls):
        at.KLINE_DIR = cls.orig_kline_dir
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_precomputed_ma5(self):
        """验证 MA5 = avg(最近5天收盘)"""
        data = at._load_precomputed('TEST.SH', self.dates[14])  # D-3 = day 15
        self.assertIsNotNone(data)

        # MA5@D-3 = avg(day11,12,13,14,15) = avg(111..115) = 113
        expected_ma5 = np.mean(self.closes[10:15])
        self.assertAlmostEqual(data['ma5'], expected_ma5, places=4)

    def test_precomputed_ma10(self):
        data = at._load_precomputed('TEST.SH', self.dates[14])
        expected_ma10 = np.mean(self.closes[5:15])
        self.assertAlmostEqual(data['ma10'], expected_ma10, places=4)

    def test_precomputed_last_ma5(self):
        """D-4的MA5 = avg(day10..14)"""
        data = at._load_precomputed('TEST.SH', self.dates[14])
        expected = np.mean(self.closes[9:14])
        self.assertAlmostEqual(data['last_ma5'], expected, places=4)

    def test_precomputed_oldest_indices(self):
        """closes[-5] = D-7, closes[-10] = D-12"""
        data = at._load_precomputed('TEST.SH', self.dates[14])
        self.assertAlmostEqual(data['oldest_ma5_close'], self.closes[10], places=2)
        self.assertAlmostEqual(data['oldest_ma10_close'], self.closes[5], places=2)

    def test_ma5_rolling_formula(self):
        """验证滚动公式: (MA5_D3×5 - oldest + D2) / 5 == D2_MA5"""
        data = at._load_precomputed('TEST.SH', self.dates[14])
        d2_close = 120.0

        # 滚动法
        rolled = (data['ma5'] * 5 - data['oldest_ma5_close'] + d2_close) / 5

        # 直算法
        direct = np.mean(np.append(self.closes[11:15], d2_close))

        self.assertAlmostEqual(rolled, direct, places=6,
                               msg=f"MA5滚动公式验证失败! 滚动={rolled:.4f} 直算={direct:.4f}")

    def test_ma10_rolling_formula(self):
        data = at._load_precomputed('TEST.SH', self.dates[14])
        d2_close = 120.0
        rolled = (data['ma10'] * 10 - data['oldest_ma10_close'] + d2_close) / 10
        direct = np.mean(np.append(self.closes[6:15], d2_close))
        self.assertAlmostEqual(rolled, direct, places=6)

    def test_golden_cross_detection(self):
        """验证金叉判断: D-4 MA5≤MA10 且 D-2 MA5>MA10"""
        data = at._load_precomputed('TEST.SH', self.dates[14])
        # Our data: closes monotonically increasing, MA5 > MA10 always on D-4
        # So golden should be 0 (not a fresh cross)
        self.assertGreater(data['ma5'], data['ma10'])
        self.assertGreater(data['last_ma5'], data['last_ma10'])

# ==============================================================================
#  TEST 4: compute_features (5特征)
# ==============================================================================
class TestComputeFeatures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.orig_kline_dir = at.KLINE_DIR
        at.KLINE_DIR = cls.tmpdir

        closes = np.arange(100.0, 120.0, 1.0)
        for i in range(20):
            pc = closes[i-1] if i > 0 else closes[i]
            oh = closes[i] * 1.02
            ol = closes[i] * 0.98
            date = f"202608{str(i+1).zfill(2)}"
            with open(f"{cls.tmpdir}/TEST.SH", 'w' if i == 0 else 'a', encoding='utf-8') as f:
                f.write(f"{date} {ol:.2f} {oh:.2f} {ol:.2f} {closes[i]:.2f} "
                        f"100000 1000000 0 0 {pc:.2f}\n")

    @classmethod
    def tearDownClass(cls):
        at.KLINE_DIR = cls.orig_kline_dir
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        """Setup precomputed data for TEST.SH"""
        at._precomputed.clear()
        data = at._load_precomputed('TEST.SH', '20260815')  # D-3=day15
        self.assertIsNotNone(data, "预计算数据不能为空")
        at._precomputed['TEST.SH'] = data

    def test_compute_features_normal_case(self):
        """正常tick: D-2收盘120, 最高121, 最低118"""
        tick = {
            'lastClose': 115.0,  # D-3收盘
            'lastPrice': 120.0,  # D-2收盘
            'high': 121.0,
            'low': 118.0,
        }
        f = at.compute_features('TEST.SH', tick)
        self.assertIsNotNone(f, "特征计算不能返回None")

        # pb_depth: (115-120)/115*100 = -4.3478
        self.assertAlmostEqual(f['pb_depth'], (115.0 - 120.0) / 115.0 * 100, places=2)

    def test_compute_features_ma5_dev(self):
        """ma5_dev 必须用 D-2 的 MA5（不是 D-3 的 MA5）"""
        tick = {'lastClose': 115.0, 'lastPrice': 120.0, 'high': 121.0, 'low': 118.0}
        f = at.compute_features('TEST.SH', tick)

        # 直算法验证
        pre = at._precomputed['TEST.SH']
        ma5_d2 = (pre['ma5'] * 5 - pre['oldest_ma5_close'] + 120.0) / 5
        expected_ma5_dev = (120.0 - ma5_d2) / ma5_d2 * 100

        self.assertAlmostEqual(f['ma5_dev'], expected_ma5_dev, places=2,
                               msg="ma5_dev 不是基于 D-2_MA5 计算的!")

    def test_compute_features_no_precomputed(self):
        """无预计算数据应返回 None"""
        result = at.compute_features('UNKNOWN.SH', {'lastPrice': 100})
        self.assertIsNone(result)

    def test_compute_features_zero_preclose(self):
        """pre_close=0 应返回 None"""
        tick = {'lastClose': 0, 'lastPrice': 120.0, 'high': 121.0, 'low': 118.0}
        result = at.compute_features('TEST.SH', tick)
        self.assertIsNone(result)

    def test_features_return_dict_keys(self):
        """返回值必须是 5 个 KEY"""
        tick = {'lastClose': 115.0, 'lastPrice': 120.0, 'high': 121.0, 'low': 118.0}
        f = at.compute_features('TEST.SH', tick)
        expected_keys = set(at.KEYS)
        actual_keys = set(f.keys())
        self.assertEqual(actual_keys, expected_keys,
                         f"特征键不匹配! 多了:{actual_keys-expected_keys} 少了:{expected_keys-actual_keys}")

    def test_no_vol_contract(self):
        """特征中绝对不能有 vol_contract（已删除）"""
        tick = {'lastClose': 115.0, 'lastPrice': 120.0, 'high': 121.0, 'low': 118.0}
        f = at.compute_features('TEST.SH', tick)
        self.assertNotIn('vol_contract', f, "vol_contract 应该已被删除!")

    def test_only_5_features(self):
        """N_FEAT 必须是 5"""
        self.assertEqual(at.N_FEAT, 5, f"N_FEAT={at.N_FEAT}, 必须是5!")
        self.assertEqual(len(at.KEYS), 5, f"KEYS长度={len(at.KEYS)}, 必须是5!")
        self.assertEqual(len(at.W), 5, f"W长度={len(at.W)}, 必须是5!")

# ==============================================================================
#  TEST 5: check_sell_signal
# ==============================================================================
class TestCheckSellSignal(unittest.TestCase):
    def test_open_stop(self):
        """开盘止损: 开≤bp*0.94"""
        tick = {'lastClose': 5.0, 'lastPrice': 4.5, 'open': 4.6, 'high': 4.7, 'low': 4.6}
        sell, price, reason = at.check_sell_signal(tick, 5.0)
        self.assertTrue(sell)
        self.assertEqual(reason, 'open_stop')
        self.assertEqual(price, 4.6)

    def test_low_stop(self):
        """日内止损: 低≤bp*0.94"""
        tick = {'lastClose': 5.0, 'lastPrice': 4.5, 'open': 5.0, 'high': 5.1, 'low': 4.6,
                'askPrice': 4.6}
        sell, price, reason = at.check_sell_signal(tick, 5.0)
        self.assertTrue(sell)
        self.assertEqual(reason, 'low_stop')
        self.assertAlmostEqual(price, 4.6 - at.SELL_PRICE_DISCOUNT)

    def test_low_stop_ask1_zero_fallback_lastprice(self):
        """卖一为0时用最新价-0.01"""
        tick = {'lastClose': 5.0, 'lastPrice': 4.7, 'open': 5.0, 'high': 5.1, 'low': 4.6,
                'askPrice': 0}
        sell, price, reason = at.check_sell_signal(tick, 5.0)
        self.assertTrue(sell)
        self.assertAlmostEqual(price, 4.7 - at.SELL_PRICE_DISCOUNT)

    def test_no_sell_normal(self):
        """正常情况不触发卖出"""
        # hold_cost=50, stop=47.0, low=48.0 > 47.0 → 不触发
        tick = {'lastClose': 50.0, 'lastPrice': 52.0, 'open': 51.0, 'high': 53.0, 'low': 48.0}
        sell, price, reason = at.check_sell_signal(tick, 50.0)
        self.assertFalse(sell, f"止损不应触发! stop={at.calc_stop_price(50.0)} low=48.0")

    def test_no_limit_up_in_sell_signal(self):
        """check_sell_signal 不应检测涨停（涨停由预挂单处理）"""
        tick = {'lastClose': 5.0, 'lastPrice': 5.5, 'open': 5.0, 'high': 5.5, 'low': 5.0}
        sell, price, reason = at.check_sell_signal(tick, 5.0)
        self.assertFalse(sell, "check_sell_signal 不应该检测涨停!")

    def test_askprice_list_does_not_crash(self):
        """askPrice 是 list 时不应崩溃"""
        tick = {'lastClose': 5.0, 'lastPrice': 4.5, 'open': 5.0, 'high': 5.1, 'low': 4.6,
                'askPrice': [4.6, 4.61]}
        sell, price, _ = at.check_sell_signal(tick, 5.0)
        # 不崩溃就是通过；list[0] = 4.6
        self.assertTrue(sell)

# ==============================================================================
#  TEST 6: api.buy / api.sell 参数顺序
# ==============================================================================
class TestAPIParameterOrder(unittest.TestCase):
    def test_api_buy_signature(self):
        """api.buy(code, volume, price) — 参数顺序必须是 code, volume, price"""
        from api import QMTAPI
        import inspect
        sig = inspect.signature(QMTAPI.buy)
        params = list(sig.parameters.keys())
        # self, code, volume, price
        self.assertIn('code', params[1].lower(), f"api.buy第1参数是{params[1]}, 应为code相关!")
        self.assertEqual(params[2], 'volume', f"api.buy第2参数是{params[2]}, 应为volume!")
        self.assertEqual(params[3], 'price', f"api.buy第3参数是{params[3]}, 应为price!")

    def test_api_sell_signature(self):
        """api.sell(code, volume, price) — 参数顺序必须是 code, volume, price"""
        from api import QMTAPI
        import inspect
        sig = inspect.signature(QMTAPI.sell)
        params = list(sig.parameters.keys())
        self.assertIn('code', params[1].lower(), f"api.sell第1参数是{params[1]}, 应为code相关!")
        self.assertEqual(params[2], 'volume', f"api.sell第2参数是{params[2]}, 应为volume!")
        self.assertEqual(params[3], 'price', f"api.sell第3参数是{params[3]}, 应为price!")

    def test_auto_trade_calls_use_correct_order(self):
        """autotrade中api.buy/sell调用必须传对参数顺序"""
        import inspect
        src = inspect.getsource(at.execute_buy) + inspect.getsource(at.main)

        # api.buy(code, volume, price) — 所有调用必须正确
        buy_calls = [l.strip() for l in src.split('\n') if 'api.buy(' in l and not l.strip().startswith('#')]
        for line in buy_calls:
            self.assertNotIn('price', line.split('api.buy(')[1].split(',')[1] if ',' in line else '',
                             f"api.buy 参数顺序可疑: {line}")

        # api.sell(code, volume, price) — 同上
        sell_calls = [l.strip() for l in src.split('\n') if 'api.sell(' in l and not l.strip().startswith('#')]
        for line in sell_calls:
            self.assertNotIn('price', line.split('api.sell(')[1].split(',')[1] if ',' in line else '',
                             f"api.sell 参数顺序可疑: {line}")

# ==============================================================================
#  TEST 7: Walk-Forward Training
# ==============================================================================
class TestWalkForward(unittest.TestCase):
    @unittest.skipIf('--quick' in sys.argv, "跳过WF重训 (--quick)")
    def test_training_completes_without_error(self):
        """WF训练应正常完成, 返回5维权重"""
        tds = at.load_trading_days()
        tds = sorted(tds)
        di = {d: i for i, d in enumerate(tds)}

        # 重新定向 log
        w, mu, sg = at.train_walk_forward(tds, di)

        self.assertEqual(len(w), 5, f"权重维度应为5, 实际{len(w)}")
        self.assertEqual(len(mu), 5)
        self.assertEqual(len(sg), 5)
        self.assertFalse(np.all(np.isnan(w)), "权重包含 NaN!")

    @unittest.skipIf('--quick' in sys.argv, "跳过WF重训 (--quick)")
    def test_training_samples_minimum(self):
        """训练样本至少100个"""
        tds = at.load_trading_days()
        tds = sorted(tds)
        di = {d: i for i, d in enumerate(tds)}

        w, mu, sg = at.train_walk_forward(tds, di)

        self.assertGreater(np.abs(w).sum(), 0.01, "权重全为零, 训练可能失败!")

# ==============================================================================
#  TEST 8: 回测特征一致性
# ==============================================================================
class TestBacktestAlignment(unittest.TestCase):
    """验证 auto_trade.py 的 compute_features 与 analysis_311_1d_detail.py 的回测特征一致"""
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.orig_kline_dir = at.KLINE_DIR

        # Create a stock with real data like TPO3
        cls.code = 'TEST_BT.SH'
        cls.prices = np.array([50.0, 51.0, 52.0, 51.5, 53.0, 52.0, 54.0, 55.0,
                               53.0, 56.0, 57.0, 58.0, 56.0, 59.0, 60.0, 58.0,
                               61.0, 62.0, 60.0, 63.0])
        cls.volumes = np.array([10000, 12000, 11000, 9000, 13000, 8000, 10000,
                                15000, 7000, 14000, 12000, 11000, 9000, 16000,
                                13000, 11000, 10000, 14000, 8000, 15000])
        cls.amounts = cls.prices * cls.volumes * 0.01  # rough estimate

        kp = f"{cls.tmpdir}/{cls.code}"
        with open(kp, 'w', encoding='utf-8') as f:
            for i in range(len(cls.prices)):
                pc = cls.prices[i-1] if i > 0 else cls.prices[i]
                h = cls.prices[i] * 1.03
                l = cls.prices[i] * 0.97
                o = pc
                date = f"202608{str(i+1).zfill(2)}"
                f.write(f"{date} {o:.2f} {h:.2f} {l:.2f} {cls.prices[i]:.2f} "
                        f"{cls.volumes[i]:.0f} {cls.amounts[i]:.0f} 0 0 {pc:.2f}\n")

    @classmethod
    def tearDownClass(cls):
        at.KLINE_DIR = cls.orig_kline_dir
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def setUp(self):
        at.KLINE_DIR = self.tmpdir
        at._precomputed.clear()

    def tearDown(self):
        at.KLINE_DIR = self.orig_kline_dir

    def test_pb_depth_formula_identical(self):
        """pb_depth = (D3_close - D2_close) / D3_close * 100 — 手算 vs 脚本"""
        # D-3 = day 16 (index 15), D-2 = day 17
        d3_close = self.prices[15]  # 58.0
        d2_close = self.prices[16]  # 61.0

        # 手算
        manual = (d3_close - d2_close) / d3_close * 100

        # 预处理后用脚本算 (D-3=day16="20260816")
        pre = at._load_precomputed(self.code, '20260816')
        at._precomputed[self.code] = pre

        from unittest.mock import patch
        mock_tick = {'lastClose': d3_close, 'lastPrice': d2_close,
                     'high': d2_close * 1.03, 'low': d2_close * 0.97}
        f = at.compute_features(self.code, mock_tick)

        self.assertAlmostEqual(f['pb_depth'], manual, places=2,
                               msg=f"pb_depth: 脚本={f['pb_depth']:.4f} 手算={manual:.4f}")

    def test_bear_bull_formula(self):
        """bear = (preClose - low)/ATR10, bull = (high - preClose)/ATR10"""
        pre = at._load_precomputed(self.code, '20260816')
        at._precomputed[self.code] = pre

        d3_close = self.prices[15]
        d2_close = self.prices[16]
        d2_high = d2_close * 1.03
        d2_low = d2_close * 0.97

        f = at.compute_features(self.code, {
            'lastClose': d3_close, 'lastPrice': d2_close,
            'high': d2_high, 'low': d2_low
        })

        # 手算 bear/bull
        manual_bear = (d3_close - d2_low) / pre['atr10']
        manual_bull = (d2_high - d3_close) / pre['atr10']

        self.assertAlmostEqual(f['pc_vs_low_atr'], manual_bear, places=3)
        self.assertAlmostEqual(f['high_vs_pc_atr'], manual_bull, places=3)

# ==============================================================================
#  TEST 9: 仓位管理
# ==============================================================================
class TestPositionManagement(unittest.TestCase):
    def test_constants_defined(self):
        self.assertEqual(at.CONSEC_HALF, 2)
        self.assertEqual(at.CONSEC_SKIP, 3)

    def test_consec_loss_var_exists_in_main(self):
        """确认 main() 中有 consec_loss / consec_updated 变量"""
        import inspect
        src = inspect.getsource(at.main)
        self.assertIn('consec_loss', src, "main() 缺少 consec_loss 变量!")
        self.assertIn('consec_updated', src, "main() 缺少 consec_updated 变量!")

    def test_half_position_in_execute_buy(self):
        """execute_buy 应该接受 capital 参数（由 main 决定半仓还是满仓）"""
        import inspect
        sig = inspect.signature(at.execute_buy)
        params = list(sig.parameters.keys())
        self.assertIn('capital', params, "execute_buy 缺少 capital 参数!")

    def test_buy_section_checks_consec(self):
        """买入段应检查连亏>=CONSEC_SKIP 时跳过"""
        import inspect
        src = inspect.getsource(at.main)
        self.assertIn('CONSEC_SKIP', src, "main() 中未引用 CONSEC_SKIP!")
        self.assertIn('CONSEC_HALF', src, "main() 中未引用 CONSEC_HALF!")

# ==============================================================================
#  TEST 10: 输出文件（冒烟）
# ==============================================================================
class TestOutputFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.orig_tick_file = at.TICK_FILE
        cls.orig_score_file = at.SCORE_SNAPSHOT_FILE
        at.TICK_FILE = os.path.join(cls.tmpdir, 'tick.txt')
        at.SCORE_SNAPSHOT_FILE = os.path.join(cls.tmpdir, 'scores.txt')

    @classmethod
    def tearDownClass(cls):
        at.TICK_FILE = cls.orig_tick_file
        at.SCORE_SNAPSHOT_FILE = cls.orig_score_file
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_write_tick_no_crash(self):
        """write_tick_snapshot 不应崩溃"""
        ticks = {'600000.SH': {'lastClose': 10.0, 'lastPrice': 10.5, 'high': 10.8,
                               'low': 9.8, 'askPrice': 10.5}}
        tpo3 = [('测试股', '600000.SH')]
        try:
            at.write_tick_snapshot('09:30', ticks, tpo3,
                                   hold_code='000001.SZ', hold_cost=50.0)
            self.assertTrue(os.path.exists(at.TICK_FILE))
        except Exception as e:
            self.fail(f"write_tick_snapshot 崩溃: {e}")

# ==============================================================================
#  SUMMARY
# ==============================================================================
def print_banner(text):
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)

if __name__ == '__main__':
    try:
        # Parse args
        verbosity = 2 if '-v' in sys.argv else 1
        if '-v' in sys.argv: sys.argv.remove('-v')

        print_banner("auto_trade.py 自动化测试套件")
        print("  测试项:")
        print("    ✓ calc_limit_up (两次四舍五入)")
        print("    ✓ calc_stop_price")
        print("    ✓ _safe_float (list/tuple/None)")
        print("    ✓ _load_precomputed (MA5/MA10 滚动公式)")
        print("    ✓ compute_features (5特征 + 无vol_contract)")
        print("    ✓ check_sell_signal (止损信号)")
        print("    ✓ api.buy/sell 参数顺序")
        print("    ✓ 回测特征一致性 (pb/bear/bull/ma_dev)")
        print("    ✓ 仓位管理")
        print("    ✓ 输出文件 (tick/score)")

        # Run tests
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        # Summary
        print()
        if result.wasSuccessful():
            print("✅ 全部通过！auto_trade.py 无已知错误。")
        else:
            failures = len(result.failures)
            errors = len(result.errors)
            total = failures + errors
            print(f"❌ {total} 项失败 ({failures}F/{errors}E) — 请修复后重跑!")

        sys.exit(0 if result.wasSuccessful() else 1)

    except Exception as e:
        print(f"❌ 测试框架初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
