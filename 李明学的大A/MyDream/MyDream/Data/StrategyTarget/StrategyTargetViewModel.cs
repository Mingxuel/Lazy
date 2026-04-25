using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Win32;
using MyDream;
using NPOI.HSSF.Record;
using NPOI.SS.Formula.Functions;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Diagnostics.Eventing.Reader;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        [ObservableProperty]
        private string slope = string.Empty;

        [ObservableProperty]
        private string slopeRatio = string.Empty;

        [ObservableProperty]
        private ObservableCollection<StrategyTargetItem> strategyTarget3Data = new ObservableCollection<StrategyTargetItem>();

        private int strategyTarget3DataIndex = -1;
        public int StrategyTarget3DataIndex
        {
            get => strategyTarget3DataIndex;
            set
            {
                strategyTarget3DataIndex = value;
                OnPropertyChanged();
                UpdateRecordsStrategyTarget3();
            }
        }

        [ObservableProperty]
        private ObservableCollection<StrategyTargetItem> strategyTarget31Data = new ObservableCollection<StrategyTargetItem>();

        private int strategyTarget31DataIndex = -1;
        public int StrategyTarget31DataIndex
        {
            get => strategyTarget31DataIndex;
            set
            {
                strategyTarget31DataIndex = value;
                OnPropertyChanged();
                UpdateRecordsStrategyTarget31();
            }
        }

        [ObservableProperty]
        private List<Record1DItem> strategyTargetKRecords = new List<Record1DItem>();

        private Dictionary<string, Record1DItem> RealRecords = new Dictionary<string, Record1DItem>();

        private void UpdateDataStrategyTarget()
        {
            StrategyTarget3Data.Clear();
            StrategyTarget31Data.Clear();

            StrategyTarget.Instance.Init();

            foreach (var item in StrategyTarget.Instance.Data3)
            {
                StrategyTarget3Data.Add(item);
            }

            foreach (var item in StrategyTarget.Instance.Data31)
            {
                StrategyTarget31Data.Add(item);
            }
        }

        private void UpdateRecordsStrategyTarget3()
        {
            if (StrategyTarget3DataIndex == -1) return;

            List<Record1DItem?> records = new List<Record1DItem?>();
            string stock_code = StrategyTarget3Data[StrategyTarget3DataIndex].StockCode!;
            int count = ZZ5001D.Instance[stock_code]!.Data!.Count;
            for (int i = 0; i <= count; i++)
            {
                if (i == count)
                {
                    if (RealRecords.Keys.Contains(stock_code)) records.Add(RealRecords[stock_code]);
                    break;
                }
                records.Add(ZZ5001D.Instance[stock_code]!.Data![i]);
            }
            StrategyTargetKRecords = records!;
        }

        private void UpdateRecordsStrategyTarget31()
        {
            if (StrategyTarget31DataIndex == -1) return;

            List<Record1DItem?> records = new List<Record1DItem?>();
            string stock_code = StrategyTarget31Data[StrategyTarget31DataIndex].StockCode!;
            int count = ZZ5001D.Instance[stock_code]!.Data!.Count;
            for (int i = 0; i <= count; i++)
            {
                if (i == count)
                {
                    if (RealRecords.Keys.Contains(stock_code)) records.Add(RealRecords[stock_code]);
                    break;
                }
                records.Add(ZZ5001D.Instance[stock_code]!.Data![i]);
            }
            StrategyTargetKRecords = records!;
        }

        [RelayCommand]
        private void StrategyListSyncClick()
        {
            string tpo3 = string.Empty;
            foreach (var data in StrategyTarget3Data)
            {
                string stock_code = data!.StockCode!.Replace(".SH", "").Replace(".SZ", "");
                tpo3 += FormatTHSLine(stock_code);
            }
            if (!string.IsNullOrEmpty(tpo3) && tpo3.Last() == '\n') tpo3 = tpo3.Remove(tpo3.Count() - 1);

            string tpo31 = string.Empty;
            foreach (var data in StrategyTarget31Data)
            {
                string stock_code = data!.StockCode!.Replace(".SH", "").Replace(".SZ", "");
                tpo31 += FormatTHSLine(stock_code);
            }
            if (!string.IsNullOrEmpty(tpo31) && tpo31.Last() == '\n') tpo31 = tpo31.Remove(tpo31.Count() - 1);

            string history = string.Empty;
            string? select_date = StrategyTradingDatesIndex != -1 ? StrategyTradingDates[StrategyTradingDatesIndex] : null;

            if (select_date != null)
            {
                string year = select_date.Substring(0, 4);
                foreach(var trading_date in TradingDates.Dates)
                {
                    if (trading_date.StartsWith(year))
                    {
                        var dates = Strategy.Instance.Data[trading_date];
                        foreach (var item in dates)
                        {
                            string stock_code = item.StockCode!.Replace(".SH", "").Replace(".SZ", "");
                            history += FormatTHSLine(stock_code);
                        }
                    }
                }
            }

            string file_content = File.ReadAllText(APath.GetTHSStrategyFileOrigin());
            file_content = file_content.Replace("===TPO3===", tpo3).Replace("===TPO31===", tpo31).Replace("===GOOD===", history);
            File.WriteAllText(APath.GetTHSStrategyFileTarget(), file_content);
        }

        private string FormatTHSLine(string code)
        {
            if (code.StartsWith("00")) return string.Format("    <security market=\"USZA\" code=\"{0}\" />\n", code);
            if (code.StartsWith("60")) return string.Format("    <security market=\"USHA\" code=\"{0}\" />\n", code);

            return "";
        }

        private void RealTimeCallback(object? sender, System.Timers.ElapsedEventArgs e)
        {
            try
            {
                var lines = File.ReadAllLines(APath.GetRuntime());
                foreach (var line in lines)
                {
                    if (line.Trim().Length < 50) continue;
                    var data = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                    if (data.Length >= 10)
                    {
                        string stock_code = data[0];
                        double open = double.Parse(data[2]);
                        double high = double.Parse(data[3]);
                        double low = double.Parse(data[4]);
                        double close = double.Parse(data[5]);
                        int volume = (int)double.Parse(data[6]);
                        double amount = double.Parse(data[7]);
                        double settlement_price = double.Parse(data[8]);
                        double open_interest = double.Parse(data[9]);
                        double pre_close = 0.0;
                        Record1DItem record_item = new Record1DItem(DateTimeOffset.Now.ToUnixTimeMilliseconds(), open, high, low, close, volume, amount, settlement_price, open_interest, pre_close, 0.0);
                        lock (RealRecords)
                        {
                            RealRecords[stock_code] = record_item;
                        }
                    }
                }

                var collection3 = new ObservableCollection<StrategyTargetItem>();
                foreach (var data in StrategyTarget3Data)
                {
                    List<Record1DItem?> records = new List<Record1DItem?>();
                    int count = ZZ5001D.Instance[data!.StockCode!]!.Data!.Count;
                    for (int i = 0; i <= count; i++)
                    {
                        if (i == count)
                        {
                            if (RealRecords.Keys.Contains(data!.StockCode!)) records.Add(RealRecords[data!.StockCode!]);
                            break;
                        }
                        records.Add(ZZ5001D.Instance[data!.StockCode!]!.Data![i]);
                    }

                    double total_high = records[records.Count - 1]!.High * records[records.Count - 1]!.Volume +
                                        records[records.Count - 2]!.High * records[records.Count - 2]!.Volume +
                                        records[records.Count - 3]!.High * records[records.Count - 3]!.Volume +
                                        records[records.Count - 4]!.High * records[records.Count - 4]!.Volume;
                    double total_close = records[records.Count - 1]!.Close * records[records.Count - 1]!.Volume +
                                        records[records.Count - 2]!.Close * records[records.Count - 2]!.Volume +
                                        records[records.Count - 3]!.Close * records[records.Count - 3]!.Volume +
                                        records[records.Count - 4]!.Close * records[records.Count - 4]!.Volume;
                    double total_volume = records[records.Count - 1]!.Volume + records[records.Count - 2]!.Volume + records[records.Count - 3]!.Volume + records[records.Count - 4]!.Volume;

                    double m5 = (records[records.Count - 1]!.Close + records[records.Count - 2]!.Close + records[records.Count - 3]!.Close + records[records.Count - 4]!.Close + records[records.Count - 5]!.Close) / 5.0;
                    double pre_m5 = (records[records.Count - 2]!.Close + records[records.Count - 3]!.Close + records[records.Count - 4]!.Close + records[records.Count - 5]!.Close + records[records.Count - 6]!.Close) / 5.0;
                    double pre_pre_m5 = (records[records.Count - 3]!.Close + records[records.Count - 4]!.Close + records[records.Count - 5]!.Close + records[records.Count - 6]!.Close + records[records.Count - 7]!.Close) / 5.0;

                        if (records[records.Count - 3]!.Volume < records[records.Count - 2]!.Volume && records[records.Count - 2]!.Volume > records[records.Count - 1]!.Volume && records[records.Count - 3]!.Volume < records[records.Count - 1]!.Volume &&
                        records[records.Count - 3]!.Low < records[records.Count - 2]!.Low && records[records.Count - 2]!.Low < records[records.Count - 1]!.Low &&
                        records[records.Count - 3]!.High < records[records.Count - 2]!.High && records[records.Count - 2]!.High < records[records.Count - 1]!.High &&
                        records[records.Count - 3]!.Ratio < records[records.Count - 2]!.Ratio &&
                        !records[records.Count - 3]!.IsTop && !records[records.Count - 2]!.IsTop && !records[records.Count - 1]!.IsTop &&
                        records[records.Count - 3]!.IsUp && records[records.Count - 2]!.IsUp && records[records.Count - 1]!.IsUp &&
                        records[records.Count - 3]!.IsRed && records[records.Count - 2]!.IsRed && records[records.Count - 1]!.IsRed &&
                        m5 > pre_m5 && pre_m5 > pre_pre_m5)
                    {
                        data.Flag = "Y";
                    }
                    else
                    {
                        data.Flag = "N";
                    }

                    collection3.Add(data);
                }
                StrategyTarget3Data = collection3;
                /*
                                    var collection31 = new ObservableCollection<StrategyTargetItem>();
                                    foreach (var data in StrategyTarget31Data)
                                    {
                                        List<Record1DItem?> records = new List<Record1DItem?>();
                                        int count = ZZ5001D.Instance[data!.StockCode!]!.Data!.Count;
                                        for (int i = 0; i <= count; i++)
                                        {
                                            if (i == count)
                                            {
                                                if (RealRecords.Keys.Contains(data!.StockCode!)) records.Add(RealRecords[data!.StockCode!]);
                                                break;
                                            }
                                            records.Add(ZZ5001D.Instance[data!.StockCode!]!.Data![i]);
                                        }

                                        double total_high = records[records.Count - 1]!.High * records[records.Count - 1]!.Volume +
                                                            records[records.Count - 2]!.High * records[records.Count - 2]!.Volume +
                                                            records[records.Count - 3]!.High * records[records.Count - 3]!.Volume +
                                                            records[records.Count - 4]!.High * records[records.Count - 4]!.Volume +
                                                            records[records.Count - 5]!.High * records[records.Count - 5]!.Volume;
                                        double total_close = records[records.Count - 1]!.Close * records[records.Count - 1]!.Volume +
                                                            records[records.Count - 2]!.Close * records[records.Count - 2]!.Volume +
                                                            records[records.Count - 3]!.Close * records[records.Count - 3]!.Volume +
                                                            records[records.Count - 4]!.Close * records[records.Count - 4]!.Volume +
                                                            records[records.Count - 5]!.Close * records[records.Count - 5]!.Volume;
                                        double total_volume = records[records.Count - 1]!.Volume + records[records.Count - 2]!.Volume + records[records.Count - 3]!.Volume + records[records.Count - 4]!.Volume + records[records.Count - 5]!.Volume;

                                        data.VWAPHigh = (((total_high / total_volume) - records[records.Count - 1]!.Close) / records[records.Count - 1]!.Close).ToString("P2");
                                        data.VWAPAll = (((total_high / total_volume) + (total_close / total_volume) - records[records.Count - 1]!.Close * 2) / records[records.Count - 1]!.Close).ToString("P2");
                                        if (total_high / total_volume > records[records.Count - 1]!.High) {
                                            data.Flag = "H>H";
                                        } else if (total_high / total_volume > records[records.Count - 1]!.Close) {
                                            data.Flag = "H>C";
                                        } else if (total_close / total_volume > records[records.Count - 1]!.Close){
                                            data.Flag = "C>C";
                                        } else {
                                            data.Flag = "";
                                        }
                                        collection31.Add(data);
                                    }
                                    StrategyTarget31Data = collection31;

                                    var collectiontop = new ObservableCollection<StrategyTargetItem>();
                                    foreach (var data in StrategyTargetTopData)
                                    {
                                        List<Record1DItem?> records = new List<Record1DItem?>();
                                        int count = ZZ5001D.Instance[data!.StockCode!]!.Data!.Count;
                                        for (int i = 0; i <= count; i++)
                                        {
                                            if (i == count)
                                            {
                                                if (RealRecords.Keys.Contains(data!.StockCode!)) records.Add(RealRecords[data!.StockCode!]);
                                                break;
                                            }
                                            records.Add(ZZ5001D.Instance[data!.StockCode!]!.Data![i]);
                                        }

                                        double total_high = records[records.Count - 1]!.High * records[records.Count - 1]!.Volume +
                                                            records[records.Count - 2]!.High * records[records.Count - 2]!.Volume +
                                                            records[records.Count - 3]!.High * records[records.Count - 3]!.Volume +
                                                            records[records.Count - 4]!.High * records[records.Count - 4]!.Volume;
                                        double total_close = records[records.Count - 1]!.Close * records[records.Count - 1]!.Volume +
                                                            records[records.Count - 2]!.Close * records[records.Count - 2]!.Volume +
                                                            records[records.Count - 3]!.Close * records[records.Count - 3]!.Volume +
                                                            records[records.Count - 4]!.Close * records[records.Count - 4]!.Volume;
                                        double total_volume = records[records.Count - 1]!.Volume + records[records.Count - 2]!.Volume + records[records.Count - 3]!.Volume + records[records.Count - 4]!.Volume;

                                        data.VWAPHigh = (((total_high / total_volume) - records[records.Count - 1]!.Close) / records[records.Count - 1]!.Close * 100).ToString("00.00%");
                                        data.VWAPAll = (((total_high / total_volume) + (total_close / total_volume) - records[records.Count - 1]!.Close * 2) / records[records.Count - 1]!.Close * 100).ToString("00.00%");
                                        collectiontop.Add(data);
                                    }
                                    StrategyTargetTopData = collectiontop;
                                });*/
            }
            catch
            {

            }
        }
    }
}
