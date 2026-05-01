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

        public void Init()
        {
            UpdateData3();
            UpdateData31();
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

                if (record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;
                if (record_3.Volume < record_2.Volume && record_2.Volume < record_1.Volume &&
                    record_2.High < record_1.High &&
                    !record_3.IsTop && record_2.IsTop && !record_1.IsTop &&
                    record_1.IsUp)
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
                    StrategyTarget_item.Score = ZZ5005M.Instance.GetScore(stock_code, last_date);
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

                if (record_4.Volume < record_3.Volume && record_3.Volume < record_2.Volume && record_2.Volume > record_1.Volume &&
                    record_3.High < record_2.High &&
                    !record_4.IsTop && record_3.IsTop && !record_2.IsTop && !record_1.IsBottom &&
                    record_2.IsUp && record_1.IsDown &&
                    record_1.Close > m5)
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
                    double vwap_high = record_1.High * record_1.Volume + record_2.High * record_2.Volume + record_3.High * record_3.Volume;
                    double vwap_close = record_1.Close * record_1.Volume + record_2.Close * record_2.Volume + record_3.Close * record_3.Volume;
                    double vwap_volume = record_1.Volume + record_2.Volume + record_3.Volume;
                    StrategyTarget_item.Score = ZZ5005M.Instance.GetScore(stock_code, last_date!);
                    Data31.Add(StrategyTarget_item);
                }
            }
        }
    }
}
