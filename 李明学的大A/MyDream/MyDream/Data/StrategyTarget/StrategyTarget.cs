using NPOI.HSSF.Record;
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
        public List<StrategyTargetItem> DataTwice = new List<StrategyTargetItem>();

        public void Init()
        {
            Data3.Clear();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var last_date = TradingDates.Dates.Last();

                var record_1 = ZZ5001D.Instance[stock_code!]![last_date];
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 1, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 2, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 3, true);

                if (record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;
                if (record_3.Volume < record_2.Volume && record_2.Volume < record_1.Volume &&
                    record_3.IsUp && record_2.IsUp && record_1.IsUp &&
                    record_2.IsRed && record_1.IsRed &&
                    record_3.Low < record_2.Low && record_2.Low < record_1.Low &&
                    record_3.High < record_2.High && record_2.High < record_1.High &&
                    !record_3.IsTop && !record_2.IsTop && !record_1.IsTop)
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

            Data31.Clear();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var last_date = TradingDates.Dates.Last();

                var record_1 = ZZ5001D.Instance[stock_code!]![last_date];
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 1, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 2, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 3, true);
                var record_5 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 4, true);

                if (record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;
                if (record_4.Volume < record_3.Volume && record_3.Volume < record_2.Volume && record_2.Volume > record_1.Volume &&
                    record_4.Low < record_3.Low && record_3.Low < record_2.Low &&
                    record_4.High < record_3.High && record_3.High < record_2.High &&
                    !record_4.IsTop && !record_3.IsTop && !record_2.IsTop && !record_1.IsBottom &&
                    record_4.IsUp && record_3.IsUp && record_2.IsUp && record_1.IsDown &&
                    record_3.IsRed && record_2.IsRed && record_1.IsGreen)
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
                    Data31.Add(StrategyTarget_item);
                }
            }

            DataTop.Clear();
            int range = 20;
            for (int i = TradingDates.Dates.Count - range; i < TradingDates.Dates.Count; i++)
            {
                var items = Strategy.Instance.Data[TradingDates.Dates[i]];
                foreach (var item in items)
                {
                    var record_1 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 1);
                    var record_2 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 2);
                    var record_3 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 3);
                    var record_4 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 4);
                    var record_5 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 5);
                    var record_6 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 5);
                    var record_7 = ZZ5001D.Instance.PreRecord(item.StockCode!, TradingDates.Dates.Last(), 5);
                    if (record_7 == null || record_6 == null || record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;

                    var ma5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                    var pre_ma5 = (record_2.Close + record_3.Close + record_4.Close + record_5.Close + record_6.Close) / 5.0;
                    var pre_pre_ma5 = (record_3.Close + record_4.Close + record_5.Close + record_6.Close + record_7.Close) / 5.0;
                    if ((record_1!.IsTop || record_2!.IsTop || record_3!.IsTop || record_4!.IsTop) &&
                        record_1.Close > ma5 && record_2.Close > pre_ma5 && record_3.Close > pre_pre_ma5)
                    {
                        StrategyTargetItem target_item = new StrategyTargetItem();
                        target_item.StockName = item.StockName;
                        target_item.StockCode = item.StockCode;
                        DataTop.Add(target_item);
                    }
                }
            }

            DataTwice.Clear();
            range = 10;
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var last_date = TradingDates.Dates.Last();

                var record_1 = ZZ5001D.Instance[stock_code!]![last_date];
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 1, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 2, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 3, true);
                var record_5 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 4, true);
                var record_6 = ZZ5001D.Instance.PreRecord(stock_code, last_date, 5, true);

                if (record_6 == null || record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;

                var ma5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                var pre_ma5 = (record_2.Close + record_3.Close + record_4.Close + record_5.Close + record_6.Close) / 5.0;
                if (record_2.Volume < record_1.Volume &&
                    record_1.IsRed && record_1.IsUp &&
                    record_2.Low < record_1.Low &&
                    record_2.High < record_1.High &&
                    !record_2.IsBottom && !record_2.IsTop && !record_1.IsTop && !record_1.IsBottom &&
                    record_2.Open > pre_ma5 && record_2.Close > pre_ma5 && record_1.Open > ma5 && record_1.Close > ma5)
                {
                    for (int i = TradingDates.Dates.Count - range; i < TradingDates.Dates.Count - 3; i++)
                    {
                        var items = Strategy.Instance.Data[TradingDates.Dates[i]];
                        foreach (var item in items)
                        {
                            if (item.StockCode == stock_code)
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
                                DataTwice.Add(StrategyTarget_item);
                                break;
                            }
                        }
                    }
                }
            }
        }
    }
}
