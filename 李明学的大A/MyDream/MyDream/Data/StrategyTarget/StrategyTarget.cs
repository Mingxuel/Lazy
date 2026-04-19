using NPOI.HSSF.Record;
using NPOI.HSSF.Record.Chart;
using NPOI.SS.Util;
using OxyPlot.Series;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Shapes;

namespace MyDream
{
    internal class StrategyTarget
    {
        private static StrategyTarget? _instance = null;
        public static StrategyTarget Instance { get => _instance == null ? _instance = new StrategyTarget() : _instance; }
        public List<StrategyTargetItem> Data3 = new List<StrategyTargetItem>();
        public List<StrategyTargetItem> Data31 = new List<StrategyTargetItem>();
        public List<StrategyTargetItem> DataTop = new List<StrategyTargetItem>();
        public List<StrategyTargetItem> DataHis = new List<StrategyTargetItem>();

        public void Init()
        {
            UpdateData3();
            UpdateData31();
            UpdateDataTop();
            UpdateDataHis();
        }

        private void UpdateData3()
        {
            Data3.Clear();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var last_date = TradingDates.Dates.Last();

                var record_1 = ZZ5001D.Instance[stock_code!]![last_date];
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 1, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 2, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 3, true);
                var record_5 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 4, true);
                var record_6 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 5, true);
                var record_7 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 6, true);
                var record_8 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 7, true);

                if (record_8 == null || record_7 == null || record_6 == null || record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;

                var pre_pre_pre_m5 = (record_4.Close + record_5.Close + record_6.Close + record_7.Close + record_8.Close) / 5.0;
                var pre_pre_m5 = (record_3.Close + record_4.Close + record_5.Close + record_6.Close + record_7.Close) / 5.0;
                var pre_m5 = (record_2.Close + record_3.Close + record_4.Close + record_5.Close + record_6.Close) / 5.0;
                var m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                var next_m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_1.Close) / 5.0;
                if (record_2.Volume < record_1.Volume &&
                    record_2.Low < record_1.Low &&
                    record_2.High < record_1.High &&
                    !record_2.IsTop && !record_1.IsTop &&
                    record_2.IsUp && record_1.IsUp &&
                    record_2.Ratio < record_1.Ratio &&
                    record_2.IsRed && record_1.IsRed &&
                    m5 > pre_m5)
                {
                    StrategyTargetItem StrategyTarget_item = new StrategyTargetItem();
                    StrategyTarget_item.StockCode = stock_code;
                    foreach (var data in ZZ500.Data)
                    {
                        if (data.StockCode == stock_code)
                        {
                            StrategyTarget_item.StockName = data.StockName;
                        }
                    }
                    Data3.Add(StrategyTarget_item);
                }
            }
        }

        private void UpdateData31()
        {
            Data31.Clear();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var last_date = TradingDates.Dates.Last();

                var record_1 = ZZ5001D.Instance[stock_code!]![last_date];
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 1, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 2, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 3, true);
                var record_5 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 4, true);
                var record_6 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 5, true);
                var record_7 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 6, true);
                var record_8 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 7, true);

                if (record_8 == null || record_7 == null || record_6 == null || record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;

                var pre_pre_pre_m5 = (record_4.Close + record_5.Close + record_6.Close + record_7.Close + record_8.Close) / 5.0;
                var pre_pre_m5 = (record_3.Close + record_4.Close + record_5.Close + record_6.Close + record_7.Close) / 5.0;
                var pre_m5 = (record_2.Close + record_3.Close + record_4.Close + record_5.Close + record_6.Close) / 5.0;
                var m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                var next_m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_1.Close) / 5.0;
                if (record_3.Volume < record_2.Volume && record_2.Volume > record_1.Volume &&
                    record_3.Low < record_2.Low && record_2.Low < record_1.Low &&
                    record_3.High < record_2.High && record_2.High < record_1.High &&
                    !record_3.IsTop && !record_2.IsTop && !record_1.IsTop &&
                    record_3.IsUp && record_2.IsUp && record_1.IsUp &&
                    record_3.Ratio < record_2.Ratio && record_2.Ratio > record_1.Ratio &&
                    record_3.IsRed && record_2.IsRed && record_1.IsRed &&
                    m5 > pre_m5 && pre_m5 > pre_pre_m5)
                {
                    StrategyTargetItem StrategyTarget_item = new StrategyTargetItem();
                    StrategyTarget_item.StockCode = stock_code;
                    foreach (var data in ZZ500.Data)
                    {
                        if (data.StockCode == stock_code)
                        {
                            StrategyTarget_item.StockName = data.StockName;
                        }
                    }
                    double vwap_high = record_1.High * record_1.Volume + record_2.High * record_2.Volume + record_3.High * record_3.Volume + record_4.High * record_4.Volume;
                    double vwap_close = record_1.Close * record_1.Volume + record_2.Close * record_2.Volume + record_3.Close * record_3.Volume + record_4.Close * record_4.Volume;
                    double vwap_volume = record_1.Volume + record_2.Volume + record_3.Volume + record_4.Volume;
                    StrategyTarget_item.VWAPHigh = ((vwap_high / vwap_volume - record_1.Close) / record_1.Close).ToString("P2");
                    StrategyTarget_item.VWAPAll = ((vwap_high / vwap_volume + vwap_close / vwap_volume - record_1.Close * 2) / record_1.Close).ToString("P2");

                    Data31.Add(StrategyTarget_item);
                }
            }
        }

        private void UpdateDataTop()
        {
            DataTop.Clear();
            int range = 12;
            for (int i = TradingDates.Dates.Count - range; i < TradingDates.Dates.Count; i++)
            {
                var items = Strategy.Instance.Data[TradingDates.Dates[i]];
                foreach (var item in items)
                {
                    List<Record1DItem?> records = new List<Record1DItem?>();
                    foreach (int index in Enumerable.Range(0, range))
                    {
                        records.Add(ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), index));
                    }

                    int top_count = 0;
                    foreach (var record in records)
                    {
                        if (record!.IsTop) top_count++;
                    }

                    if (top_count < 1) continue;

                    StrategyTargetItem target_item = new StrategyTargetItem();
                    target_item.StockName = item.StockName;
                    target_item.StockCode = item.StockCode;
                    DataTop.Add(target_item);
                }
            }
        }

        private void UpdateDataHis()
        {
            DataHis.Clear();
            int range = 12;
            var dates = TradingDates.Dates.TakeLast(range);
            foreach (var date in dates)
            {
                var strategy_items = Strategy.Instance.Data[date];
                if (strategy_items.Count == 0) continue;

                int max_index = -1;
                double max_vwap_high = -10000;
                double max_vwap_close = -10000;
                foreach (var strategy_item in strategy_items)
                {
                    var record = ZZ5001D.Instance[strategy_item.StockCode!]![date];
                    var record_1 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 1);
                    var record_2 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 2);
                    var record_3 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 3);
                    var record_4 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 4);
                    if (record == null || record_1 == null || record_2 == null || record_3 == null || record_4 == null) continue;
                    double total_value_high = record_1.High * record_1.Volume + record_2.High * record_2.Volume + record_3.High * record_3.Volume + record_4.High * record_4.Volume;
                    double total_value_close = record_1.Close * record_1.Volume + record_2.Close * record_2.Volume + record_3.Close * record_3.Volume + record_4.Close * record_4.Volume;
                    double total_volume = record_1.Volume + record_2.Volume + record_3.Volume + record_4.Volume;
                    double vwap_high = total_value_high / total_volume;
                    double vwap_close = total_value_close / total_volume;
                    vwap_high = (vwap_high + vwap_close - record_1.Close * 2) / record_1.Close * 100;

                    if (vwap_high > max_vwap_high)
                    {
                        max_vwap_high = vwap_high;
                        max_vwap_close = vwap_close;
                        max_index = strategy_items.IndexOf(strategy_item);
                    }
                }

                if (max_index == -1) continue;

                if (max_vwap_high <= Constants.MinVWAP) continue;

                StrategyTargetItem target_item = new StrategyTargetItem();
                target_item.StockName = strategy_items[max_index].StockName;
                target_item.StockCode = strategy_items[max_index].StockCode;
                DataHis.Add(target_item);
            }
        }
    }
}
