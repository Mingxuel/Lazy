using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Microsoft.Win32;
using MyDream;
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
        private ObservableCollection<StrategyTargetItem> strategyTarget2Data = new ObservableCollection<StrategyTargetItem>();

        private int strategyTarget2DataIndex = -1;
        public int StrategyTarget2DataIndex
        {
            get => strategyTarget2DataIndex;
            set
            {
                strategyTarget2DataIndex = value;
                OnPropertyChanged();
                UpdateRecordsStrategyTarget2();
            }
        }

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
        private ObservableCollection<StrategyTargetItem> strategyTargetTopData = new ObservableCollection<StrategyTargetItem>();

        private int strategyTargetTopDataIndex = -1;
        public int StrategyTargetTopDataIndex
        {
            get => strategyTargetTopDataIndex;
            set
            {
                strategyTargetTopDataIndex = value;
                OnPropertyChanged();
                UpdateRecordsStrategyTargetTop();
            }
        }

        [ObservableProperty]
        private ObservableCollection<StrategyTargetItem> strategyTargetTopHistoryData = new ObservableCollection<StrategyTargetItem>();

        private int strategyTargetTopHistoryDataIndex = -1;
        public int StrategyTargetTopHistoryDataIndex
        {
            get => strategyTargetTopHistoryDataIndex;
            set
            {
                strategyTargetTopHistoryDataIndex = value;
                OnPropertyChanged();
                UpdateRecordsStrategyTargetTopHistory();
            }
        }

        [ObservableProperty]
        private List<Record1DItem> strategyTargetKRecords = new List<Record1DItem>();

        private Dictionary<string, Record1DItem> RealRecords = new Dictionary<string, Record1DItem>();

        private void UpdateDataStrategyTarget()
        {
            StrategyTarget2Data.Clear();
            StrategyTarget3Data.Clear();
            StrategyTarget31Data.Clear();
            StrategyTargetTopData.Clear();
            StrategyTargetTopHistoryData.Clear();

            StrategyTarget.Instance.Init();

            foreach (var item in StrategyTarget.Instance.Data2)
            {
                StrategyTarget2Data.Add(item);
            }

            foreach (var item in StrategyTarget.Instance.Data3)
            {
                StrategyTarget3Data.Add(item);
            }

            foreach (var item in StrategyTarget.Instance.Data31)
            {
                StrategyTarget31Data.Add(item);
            }

            foreach (var item in StrategyTarget.Instance.DataTop)
            {
                StrategyTargetTopData.Add(item);
            }

            foreach (var item in StrategyTarget.Instance.DataTopHistory)
            {
                StrategyTargetTopHistoryData.Add(item);
            }
        }

        private void UpdateRecordsStrategyTarget2()
        {
            if (StrategyTarget2DataIndex == -1) return;

            List<Record1DItem?> records = new List<Record1DItem?>();
            string stock_code = StrategyTarget2Data[StrategyTarget2DataIndex].StockCode!;
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

        private void UpdateRecordsStrategyTargetTop()
        {
            if (StrategyTargetTopDataIndex == -1) return;

            List<Record1DItem?> records = new List<Record1DItem?>();
            string stock_code = StrategyTargetTopData[StrategyTargetTopDataIndex].StockCode!;
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

        private void UpdateRecordsStrategyTargetTopHistory()
        {
            if (StrategyTargetTopDataIndex == -1) return;

            List<Record1DItem?> records = new List<Record1DItem?>();
            string stock_code = StrategyTargetTopHistoryData[StrategyTargetTopHistoryDataIndex].StockCode!;
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
            string tpo2 = string.Empty;
            foreach (var data in StrategyTarget2Data)
            {
                string stock_code = data!.StockCode!.Replace(".SH", "").Replace(".SZ", "");
                tpo2 += FormatTHSLine(stock_code);
            }
            if (!string.IsNullOrEmpty(tpo2) && tpo2.Last() == '\n') tpo2 = tpo2.Remove(tpo2.Count() - 1);

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

            string top = string.Empty;
            foreach (var data in StrategyTargetTopData)
            {
                string stock_code = data!.StockCode!.Replace(".SH", "").Replace(".SZ", "");
                top += FormatTHSLine(stock_code);
            }
            if (!string.IsNullOrEmpty(top) && top.Last() == '\n') top = top.Remove(top.Count() - 1);

            string top_history = string.Empty;
            foreach (var data in StrategyTargetTopHistoryData)
            {
                string stock_code = data!.StockCode!.Replace(".SH", "").Replace(".SZ", "");
                top_history += FormatTHSLine(stock_code);
            }
            if (!string.IsNullOrEmpty(top_history) && top_history.Last() == '\n') top_history = top_history.Remove(top_history.Count() - 1);

            string file_content = File.ReadAllText(APath.GetTHSStrategyFileOrigin());
            //file_content = file_content.Replace("===TPO2===", tpo2).Replace("===TPO3===", tpo3).Replace("===TPO31===", tpo31).Replace("===TOP===", top).Replace("===TOPHISTORY===", top_history);
            file_content = file_content.Replace("===TPO3===", tpo3).Replace("===TPO31===", tpo31).Replace("===TOP===", top);
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

/*                Application.Current.Dispatcher.Invoke(() =>
                {
                    var collection2 = new ObservableCollection<StrategyTargetItem>();
                    foreach (var data in StrategyTarget2Data)
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

                        data.VWAPHigh = (((total_high / total_volume) - records[records.Count - 1]!.Close) / records[records.Count - 1]!.Close).ToString("00.00%");
                        data.VWAPAll = (((total_high / total_volume) + (total_close / total_volume) - records[records.Count - 1]!.Close * 2) / records[records.Count - 1]!.Close).ToString("00.00%");

                        double ma5 = (records[records.Count - 1]!.Close + records[records.Count - 2]!.Close + records[records.Count - 3]!.Close + records[records.Count - 4]!.Close + records[records.Count - 5]!.Close) / 5.0;

                        records[records.Count - 1]!.PreClose = records[records.Count - 2]!.Close;
                        if (records[records.Count - 1]!.Volume > records[records.Count - 2]!.Volume &&
                            records[records.Count - 1]!.IsRed &&
                            records[records.Count - 1]!.IsUp &&
                            !records[records.Count - 1]!.IsTop &&
                            records[records.Count - 1]!.Close > ma5)
                        {
                            data.Flag = "Y";
                        }
                        else
                        {
                            data.Flag = "N";
                        }

                        collection2.Add(data);
                    }
                    StrategyTarget2Data = collection2;
*/
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

                        data.VWAPHigh = (((total_high / total_volume) - records[records.Count - 1]!.Close) / records[records.Count - 1]!.Close).ToString("00.00%");
                        data.VWAPAll = (((total_high / total_volume) + (total_close / total_volume) - records[records.Count - 1]!.Close * 2) / records[records.Count - 1]!.Close).ToString("00.00%");

                        double ma5 = (records[records.Count - 1]!.Close + records[records.Count - 2]!.Close + records[records.Count - 3]!.Close + records[records.Count - 4]!.Close + records[records.Count - 5]!.Close) / 5.0;

                        records[records.Count - 1]!.PreClose = records[records.Count - 2]!.Close;
                        if (records[records.Count - 1]!.Volume < records[records.Count - 2]!.Volume &&
                            records[records.Count - 1]!.IsDown &&
                            !records[records.Count - 1]!.IsBottom &&
                            records[records.Count - 1]!.Close > ma5 &&
                            double.Parse(data.VWAPAll.Replace("%", "")) > Constants.MinVWAP)
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
            catch{

            }
        }
    }
}
