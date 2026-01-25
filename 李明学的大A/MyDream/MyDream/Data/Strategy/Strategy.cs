using NPOI.SS.Util;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Shapes;

namespace MyDream
{
    internal class Strategy
    {
        private static Strategy? _instance = null;
        public static Strategy Instance { get => _instance == null ? _instance = new Strategy() : _instance; }
        public Dictionary<string, List<StrategyItem>> Data = new Dictionary<string, List<StrategyItem>>();
        public EStrategy StrategyType = EStrategy.ThreePlusOne;

        public void Init()
        {
            Data.Clear();

            foreach (var trading_date in TradingDates.Dates)
            {
                Data[trading_date] = new List<StrategyItem>();

                string? file = null;
                switch(StrategyType)
                {
                    case EStrategy.ThreePlusOne:
                        file = APath.GetStrategy() + trading_date;
                        break;
                    case EStrategy.Testing:
                        file = APath.GetTesting() + trading_date;
                        break;
                    default:
                        file = APath.GetStrategy() + trading_date;
                        break;
                }

                if (File.Exists(file))
                {
                    foreach (var line in File.ReadLines(file))
                    {
                        if (!string.IsNullOrEmpty(line.Trim()))
                        {
                            StrategyItem strategy_item = new StrategyItem();
                            var items = line.Split("|");
                            strategy_item.StockName = items[0];
                            strategy_item.StockCode = items[1];
                            strategy_item.Date = items[2];
                            strategy_item.Open = double.Parse(items[3].Trim());
                            strategy_item.High = double.Parse(items[4].Trim());
                            strategy_item.Low = double.Parse(items[5].Trim());
                            strategy_item.Close = double.Parse(items[6].Trim());
                            strategy_item.CloseRatio = items[7];
                            strategy_item.HighRatio = items[8];
                            strategy_item.OpenRatio = items[9];
                            strategy_item.PreCloseRatio = items[10];
                            strategy_item.PreHighRatio = items[11];
                            strategy_item.PreOpenRatio = items[12];
                            Data[trading_date].Add(strategy_item);
                        }
                    }
                }
                else
                {
                    switch (StrategyType)
                    {
                        case EStrategy.ThreePlusOne:
                            UpdateTPO(file, trading_date);
                            break;
                        case EStrategy.Testing:
                            UpdateTesting(file, trading_date);
                            break;
                        default:
                            UpdateTPO(file, trading_date);
                            break;
                    }
                }
            }
        }

        private void UpdateTPO(string? file, string? trading_date)
        {
            File.Create(file!).Close();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var item = ZZ5001D.Instance.Records[stock_code!]![trading_date!];
                if (item == null) continue;
                var record_1 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 1, true);
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 2, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 3, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 4, true);
                var record_5 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 5, true);
                var record_6 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 6, true);
                var record_7 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 7, true);
                var record_8 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 8, true);
                if (record_8 == null || record_7 == null || record_6 == null || record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;

                var pre_pre_pre_m5 = (record_4.Close + record_5.Close + record_6.Close + record_7.Close + record_8.Close) / 5.0;
                var pre_pre_m5 = (record_3.Close + record_4.Close + record_5.Close + record_6.Close + record_7.Close) / 5.0;
                var pre_m5 = (record_2.Close + record_3.Close + record_4.Close + record_5.Close + record_6.Close) / 5.0;
                var m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                var next_m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_1.Close) / 5.0;
                if (record_4.Volume < record_3.Volume && record_3.Volume < record_2.Volume && record_2.Volume > record_1.Volume &&
                    record_4.Low < record_3.Low && record_3.Low < record_2.Low &&
                    record_4.High < record_3.High && record_3.High < record_2.High &&
                    !record_4.IsTop && !record_3.IsTop && !record_2.IsTop && !record_1.IsBottom &&
                    record_4.IsUp && record_3.IsUp && record_2.IsUp && record_1.IsDown &&
                    record_4.IsRed && record_3.IsRed && record_2.IsRed &&
                    m5 > pre_m5 && pre_m5 > pre_pre_m5 && pre_pre_m5 > pre_pre_pre_m5 &&
                    record_1.Close > m5)
                {
                    StrategyItem strategy_item = new StrategyItem();
                    strategy_item.StockCode = stock_code;
                    foreach (var data in ZZ500.Data)
                    {
                        if (data.StockCode == stock_code)
                        {
                            strategy_item.StockName = data.StockName;
                        }
                    }
                    strategy_item.Date = trading_date;
                    strategy_item.Open = item.Open;
                    strategy_item.High = item.High;
                    strategy_item.Low = item.Low;
                    strategy_item.Close = item.Close;
                    strategy_item.CloseRatio = ((item.Close - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.HighRatio = ((item.High - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.OpenRatio = ((item.Open - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.PreCloseRatio = ((record_1.Close - record_1.PreClose) / record_1.PreClose * 100).ToString("00.00");
                    strategy_item.PreHighRatio = ((record_1.High - record_1.PreClose) / record_1.PreClose * 100).ToString("00.00");
                    strategy_item.PreOpenRatio = ((record_1.Open - record_1.PreClose) / record_1.PreClose * 100).ToString("00.00");
                    Data[trading_date!].Add(strategy_item);
                    using (StreamWriter writer = new StreamWriter(file!, true))
                    {
                        writer.WriteLine(strategy_item.ToString());
                    }
                }
            }
        }

        private void UpdateTesting(string? file, string? trading_date)
        {
            File.Create(file!).Close();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var item = ZZ5001D.Instance.Records[stock_code!]![trading_date!];
                if (item == null) continue;
                var record_1 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 1, true);
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 2, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 3, true);
                var record_4 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 4, true);
                var record_5 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 5, true);
                var record_6 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 6, true);
                var record_7 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 7, true);
                var record_8 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 8, true);
                var record_9 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 9, true);
                if (record_9 == null || record_8 == null || record_7 == null || record_6 == null || record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;

                var pre_pre_pre_pre_m5 = (record_5.Close + record_6.Close + record_7.Close + record_8.Close + record_9.Close) / 5.0;
                var pre_pre_pre_m5 = (record_4.Close + record_5.Close + record_6.Close + record_7.Close + record_8.Close) / 5.0;
                var pre_pre_m5 = (record_3.Close + record_4.Close + record_5.Close + record_6.Close + record_7.Close) / 5.0;
                var pre_m5 = (record_2.Close + record_3.Close + record_4.Close + record_5.Close + record_6.Close) / 5.0;
                var m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                var next_m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_1.Close) / 5.0;
                if (record_4.Volume < record_3.Volume && record_3.Volume < record_2.Volume && record_2.Volume > record_1.Volume &&
                    record_4.Low < record_3.Low && record_3.Low < record_2.Low &&
                    record_4.High < record_3.High && record_3.High < record_2.High &&
                    !record_4.IsTop && !record_3.IsTop && !record_2.IsTop && !record_1.IsBottom &&
                    record_4.IsUp && record_3.IsUp && record_2.IsUp && record_1.IsDown &&
                    record_4.IsRed && record_3.IsRed && record_2.IsRed && 
                    m5 > pre_m5 && pre_m5 > pre_pre_m5 && pre_pre_m5 > pre_pre_pre_m5 &&
                    record_1.Close > m5)
                {
                    StrategyItem strategy_item = new StrategyItem();
                    strategy_item.StockCode = stock_code;
                    foreach (var data in ZZ500.Data)
                    {
                        if (data.StockCode == stock_code)
                        {
                            strategy_item.StockName = data.StockName;
                        }
                    }
                    strategy_item.Date = trading_date;
                    strategy_item.Open = item.Open;
                    strategy_item.High = item.High;
                    strategy_item.Low = item.Low;
                    strategy_item.Close = item.Close;
                    strategy_item.CloseRatio = ((item.Close - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.HighRatio = ((item.High - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.OpenRatio = ((item.Open - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.PreCloseRatio = ((record_1.Close - record_1.PreClose) / record_1.PreClose * 100).ToString("00.00");
                    strategy_item.PreHighRatio = ((record_1.High - record_1.PreClose) / record_1.PreClose * 100).ToString("00.00");
                    strategy_item.PreOpenRatio = ((record_1.Open - record_1.PreClose) / record_1.PreClose * 100).ToString("00.00");
                    Data[trading_date!].Add(strategy_item);
                    using (StreamWriter writer = new StreamWriter(file!, true))
                    {
                        writer.WriteLine(strategy_item.ToString());
                    }
                }
            }
        }
    }
}
