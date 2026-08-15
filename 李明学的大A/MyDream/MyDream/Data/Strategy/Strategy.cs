using NPOI.HSSF.Record;
using NPOI.HSSF.Record.Aggregates;
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
        public Dictionary<string, List<StrategyItem>> DataD1All = new Dictionary<string, List<StrategyItem>>();
        public Dictionary<string, List<StrategyItem>> DataD1 = new Dictionary<string, List<StrategyItem>>();
        public Dictionary<string, List<StrategyItem>> DataHistory = new Dictionary<string, List<StrategyItem>>();

        public void Init()
        {
            DataD1All.Clear();
            DataD1.Clear();
            DataHistory.Clear();

            foreach (var trading_date in TradingDates.Dates)
            {
                DataD1All[trading_date] = new List<StrategyItem>();
                DataD1[trading_date] = new List<StrategyItem>();
                DataHistory[trading_date] = new List<StrategyItem>();

                string? file_strategy_d1_all = APath.GetStrategyD1All () + trading_date;
                string? file_strategy_d1 = APath.GetStrategyD1() + trading_date;
                string? file_history = APath.GetHistory() + trading_date;

                if (File.Exists(file_strategy_d1_all))
                {
                    foreach (var line in File.ReadLines(file_strategy_d1_all))
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
                            strategy_item.LowRatio = items[9];
                            strategy_item.OpenRatio = items[10];
                            strategy_item.Score = double.Parse(items[11].Trim());
                            DataD1All[trading_date].Add(strategy_item);
                        }
                    }
                }
                else
                {
                    UpdateTPOD1All(file_strategy_d1_all, trading_date);
                }

                if (File.Exists(file_strategy_d1))
                {
                    foreach (var line in File.ReadLines(file_strategy_d1))
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
                            strategy_item.LowRatio = items[9];
                            strategy_item.OpenRatio = items[10];
                            strategy_item.Score = double.Parse(items[11].Trim());
                            DataD1[trading_date].Add(strategy_item);
                        }
                    }
                }
                else
                {
                    UpdateTPOD1(file_strategy_d1, trading_date);
                }

                if (File.Exists(file_history))
                {
                    foreach (var line in File.ReadLines(file_history))
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
                            strategy_item.LowRatio = items[9];
                            strategy_item.OpenRatio = items[10];
                            strategy_item.Score = double.Parse(items[11].Trim());
                            DataHistory[trading_date].Add(strategy_item);
                        }
                    }
                }
                else
                {
                    UpdateHistory(file_history, trading_date);
                }
            }
        }

        private void UpdateTPOD1All(string? file, string? trading_date)
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
                if (record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;
                var m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;
                if (record_4.Volume < record_3.Volume && record_3.Volume < record_2.Volume &&
                    !record_4.IsTop && record_3.IsTop && !record_2.IsTop && !record_2.IsBottom && !record_1.IsTop && !record_1.IsBottom &&
                    record_2.IsUp)
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
                    strategy_item.LowRatio = ((item.Low - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.OpenRatio = ((item.Open - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    double total_high = record_1.High * record_1.Volume + record_2.High * record_2.Volume;
                    double total_close = record_1.Close * record_1.Volume + record_2.Close * record_2.Volume;
                    double total_volume = record_1.Volume + record_2.Volume;
                    string date = TradingDates.PreDate(trading_date!)!;
                    strategy_item.Score = ZZ5005M.Instance.GetScore(stock_code, date);
                    DataD1All[trading_date!].Add(strategy_item);
                    using (StreamWriter writer = new StreamWriter(file!, true))
                    {
                        writer.WriteLine(strategy_item.ToString());
                    }
                }
            }
        }

        private void UpdateTPOD1(string? file, string? trading_date)
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
                if (record_5 == null || record_4 == null || record_3 == null || record_2 == null || record_1 == null) continue;
                var m5 = (record_1.Close + record_2.Close + record_3.Close + record_4.Close + record_5.Close) / 5.0;

                double? volume = 0.0;
                foreach(var data in ZZ500.Data)
                {
                    if (data.StockCode == stock_code)
                    {
                        volume = data.Volume;
                        break;
                    }
                }

                if (record_4.Volume < record_3.Volume && record_3.Volume < record_2.Volume && record_2.Volume > record_1.Volume &&
                    !record_4.IsTop && record_3.IsTop && !record_2.IsTop && !record_2.IsBottom && !record_1.IsTop && !record_1.IsBottom &&
                    record_2.IsUp && record_1.Ratio < 0.03 && volume! * record_2.Close >= Constants.MaxVolume &&
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
                    strategy_item.LowRatio = ((item.Low - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.OpenRatio = ((item.Open - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    double total_high = record_1.High * record_1.Volume + record_2.High * record_2.Volume;
                    double total_close = record_1.Close * record_1.Volume + record_2.Close * record_2.Volume;
                    double total_volume = record_1.Volume + record_2.Volume;
                    string date = TradingDates.PreDate(trading_date!)!;
                    strategy_item.Score = ZZ5005M.Instance.GetScore(stock_code, date);
                    DataD1[trading_date!].Add(strategy_item);
                    using (StreamWriter writer = new StreamWriter(file!, true))
                    {
                        writer.WriteLine(strategy_item.ToString());
                    }
                }
            }
        }

        private void UpdateHistory(string? file, string? trading_date)
        {
            File.Create(file!).Close();
            foreach (var stock_code in ZZ500StockCodes.StockCodes)
            {
                var item = ZZ5001D.Instance.Records[stock_code!]![trading_date!];
                if (item == null) continue;
                var record_1 = item;
                var record_2 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 1, true);
                var record_3 = ZZ5001D.Instance.PreRecord(stock_code, trading_date!, 2, true);
                if (record_3 == null || record_2 == null || record_1 == null) continue;

                if (record_3.Volume < record_2.Volume && record_2.Volume < record_1.Volume &&
                    record_2.High < record_1.High &&
                    !record_3.IsTop && record_2.IsTop && !record_1.IsTop)
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
                    strategy_item.LowRatio = ((item.High - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    strategy_item.OpenRatio = ((item.Open - item.PreClose) / item.PreClose * 100).ToString("00.00");
                    DataHistory[trading_date!].Add(strategy_item);
                    using (StreamWriter writer = new StreamWriter(file!, true))
                    {
                        writer.WriteLine(strategy_item.ToString());
                    }
                }
            }
        }
    }
}
