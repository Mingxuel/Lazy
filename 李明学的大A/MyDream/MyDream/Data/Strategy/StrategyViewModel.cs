using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MyDream;
using NPOI.SS.Formula.Functions;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        [ObservableProperty]
        private string strategyPerSellCount = "-";

        [ObservableProperty]
        private string strategySellCloseCount = "-";

        [ObservableProperty]
        private string strategySellCloseWin = "-";

        [ObservableProperty]
        private string strategyPerSellCloseWin = "-";

        [ObservableProperty]
        private string strategySellCloseRatio = "-";

        [ObservableProperty]
        private string strategySellOpenCount = "-";

        [ObservableProperty]
        private string strategySellOpenWin = "-";

        [ObservableProperty]
        private string strategyPerSellOpenWin = "-";

        [ObservableProperty]
        private string strategySellOpenRatio = "-";

        [ObservableProperty]
        private string strategySellHighCount = "-";

        [ObservableProperty]
        private string strategySellHighWin = "-";

        [ObservableProperty]
        private string strategyPerSellHighWin = "-";

        [ObservableProperty]
        private string strategySellHighRatio = "-";

        [ObservableProperty]
        private ObservableCollection<string> strategyTradingDates = new ObservableCollection<string>();

        private int strategyTradingDatesIndex = -1;
        public int StrategyTradingDatesIndex
        {
            get => strategyTradingDatesIndex;
            set
            {
                if (strategyTradingDatesIndex != value)
                {
                    strategyTradingDatesIndex = value;
                    OnPropertyChanged();
                    if (value != -1) UpdateListStrategy();
                }
            }
        }

        [ObservableProperty]
        private ObservableCollection<StrategyItem> strategyData = new ObservableCollection<StrategyItem>();

        private int strategyDataIndex = -1;
        public int StrategyDataIndex
        {
            get => strategyDataIndex;
            set
            {
                if (strategyDataIndex != value)
                {
                    strategyDataIndex = value;
                    OnPropertyChanged();
                    if (value != -1) UpdateRecordsStrategy();
                }
            }
        }

        [ObservableProperty]
        private List<Record1DItem> strategyKRecords = new List<Record1DItem>();

        [ObservableProperty]
        private ObservableCollection<DistributionItem> disCloseData = new ObservableCollection<DistributionItem>();

        [ObservableProperty]
        private ObservableCollection<DistributionItem> disOpenData = new ObservableCollection<DistributionItem>();

        [ObservableProperty]
        private ObservableCollection<DistributionItem> disHighData = new ObservableCollection<DistributionItem>();

        [ObservableProperty]
        private int closeYear = 0;

        [ObservableProperty]
        private int closeMonth = 0;

        [ObservableProperty]
        private int openYear = 0;

        [ObservableProperty]
        private int openMonth = 0;

        [ObservableProperty]
        private int highYear = 0;

        [ObservableProperty]
        private int highMonth = 0;

        private int close_last_year = 0;
        private int close_last_month = 0;
        private int open_last_year = 0;
        private int open_last_month = 0;
        private int high_last_year = 0;
        private int high_last_month = 0;

        [RelayCommand]
        private void CloseYearMinusClick()
        {
            if (CloseYear > 2024) CloseYear--;

            UpdateDistribution();
        }

        [RelayCommand]
        private void CloseYearPlusClick()
        {
            if (CloseYear < close_last_year) CloseYear++;

            UpdateDistribution();
        }

        [RelayCommand]
        private void CloseMonthMinusClick()
        {
            if (CloseMonth > 1) CloseMonth--;

            UpdateDistribution();
        }

        [RelayCommand]
        private void CloseMonthPlusClick()
        {
            if (CloseYear == close_last_year && CloseMonth == close_last_month) return;

            if (CloseMonth < 12) CloseMonth++;

            UpdateDistribution();
        }

        [RelayCommand]
        private void OpenYearMinusClick()
        {
            if (OpenYear > 2024) OpenYear--;

            UpdateDistribution();
        }

        [RelayCommand]
        private void OpenYearPlusClick()
        {
            if (OpenYear < open_last_year) OpenYear++;

            UpdateDistribution();
        }

        [RelayCommand]
        private void OpenMonthMinusClick()
        {
            if (OpenMonth > 1) OpenMonth--;

            UpdateDistribution();
        }

        [RelayCommand]
        private void OpenMonthPlusClick()
        {
            if (OpenYear == open_last_year && OpenMonth == open_last_month) return;

            if (OpenMonth < 12) OpenMonth++;

            UpdateDistribution();
        }

        [RelayCommand]
        private void HighYearMinusClick()
        {
            if (HighYear > 2024) HighYear--;

            UpdateDistribution();
        }

        [RelayCommand]
        private void HighYearPlusClick()
        {
            if (HighYear < high_last_year) HighYear++;

            UpdateDistribution();
        }

        [RelayCommand]
        private void HighMonthMinusClick()
        {
            if (HighMonth > 1) HighMonth--;

            UpdateDistribution();
        }

        [RelayCommand]
        private void HighMonthPlusClick()
        {
            if (HighYear == high_last_year && HighMonth == high_last_month) return;

            if (HighMonth < 12) HighMonth++;

            UpdateDistribution();
        }

        [RelayCommand]
        private void UpClick()
        {
            if (StrategyTradingDatesIndex > 0) StrategyTradingDatesIndex--;
        }

        [RelayCommand]
        private void DownClick()
        {
            if (StrategyTradingDatesIndex < StrategyTradingDates.Count() - 1) StrategyTradingDatesIndex++;
        }

        private void UpdateDataStrategy()
        {
            Strategy.Instance.Init();
            StrategyTradingDates.Clear();
            foreach (var date in TradingDates.Dates)
            {
                StrategyTradingDates.Add(date);
            }

            double total_count = 0;
            double close_final_ratio = 1.0;
            int close_win_count = 0;
            double open_final_ratio = 1.0;
            int open_win_count = 0;
            double high_final_ratio = 1.0;
            int high_win_count = 0;
            int total_per_count = 0;
            int total_per_close_win = 0;
            int total_per_high_win = 0;
            int total_per_open_win = 0;
            foreach (var value in Strategy.Instance.Data.Values)
            {
                double close_total_ratio = 0.0;
                double open_total_ratio = 0.0;
                double high_total_ratio = 0.0;
                foreach (var item in value)
                {
                    close_total_ratio += double.Parse(item.CloseRatio!);
                    open_total_ratio += double.Parse(item.OpenRatio!);
                    high_total_ratio += double.Parse(item.HighRatio!);

                    total_per_count++;
                    if (double.Parse(item.CloseRatio!) >= 0.0) total_per_close_win++;
                    if (double.Parse(item.OpenRatio!) >= 0.0) total_per_open_win++;
                    if (double.Parse(item.HighRatio!) >= 0.0) total_per_high_win++;
                }

                if (value.Count == 0) continue;

                total_count += 1;
                if (close_total_ratio >= 0.0) close_win_count += 1;
                if (open_total_ratio >= 0.0) open_win_count += 1;
                if (high_total_ratio >= 0.0) high_win_count += 1;

                double close_avg_ratio = close_total_ratio / value.Count / 100.0;
                double open_avg_ratio = open_total_ratio / value.Count / 100.0;
                double high_avg_ratio = high_total_ratio / value.Count / 100.0;

                close_final_ratio = close_final_ratio * (1 + close_avg_ratio);
                open_final_ratio = open_final_ratio * (1 + open_avg_ratio);
                high_final_ratio = high_final_ratio * (1 + high_avg_ratio);
            }

            StrategyPerSellCount = total_per_count.ToString();
            StrategySellCloseCount = total_count.ToString();
            StrategySellCloseWin = (close_win_count / total_count).ToString("P2");
            StrategyPerSellCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
            StrategySellCloseRatio = close_final_ratio.ToString("P2");
            StrategySellOpenCount = total_count.ToString();
            StrategySellOpenWin = (open_win_count / total_count).ToString("P2");
            StrategyPerSellOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
            StrategySellOpenRatio = open_final_ratio.ToString("P2");
            StrategySellHighCount = total_count.ToString();
            StrategySellHighWin = (high_win_count / total_count).ToString("P2");
            StrategyPerSellHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
            StrategySellHighRatio = high_final_ratio.ToString("P2");

            StrategyTradingDatesIndex = StrategyTradingDates.Count() - 1;
        }

        private void UpdateListStrategy()
        {
            StrategyData.Clear();
            var items = Strategy.Instance.Data[StrategyTradingDates[StrategyTradingDatesIndex]];
            foreach (var item in items)
            {
                StrategyData.Add(item);
            }
        }

        private void UpdateRecordsStrategy()
        {
            if (StrategyDataIndex == -1) return;

            string selected_date = StrategyTradingDates[StrategyTradingDatesIndex];
/*
            for(int i = 5; i != 0; i--)
            {
                var date = TradingDates.NextDate(selected_date, i);
                if (date == null) continue;
                selected_date = date;
                break;
            }
*/
            for (int i = 1; i < 5; i++)
            {
                var date = TradingDates.PreDate(selected_date, i);
                if (date == null) continue;
                selected_date = date;
                break;
            }

            List<Record1DItem> records = new List<Record1DItem>();
            foreach (var item in ZZ5001D.Instance[StrategyData[StrategyDataIndex].StockCode!]!.Data!)
            {
                if (item == null) continue;
                DateTime unix_epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
                TimeSpan offset = TimeSpan.FromMilliseconds(item!.Date);
                string date = unix_epoch.Add(offset).ToLocalTime().ToString("yyyyMMdd");
                if (selected_date == date)
                {
                    records.Add(item);
                    break;
                }
                records.Add(item);
            }

            StrategyKRecords = records;
        }

        private static long ConvertDateTimeToSeconds(DateTime dateTime)
        {
            DateTime epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            TimeSpan timeSpan = dateTime.ToUniversalTime() - epoch;
            return (long)timeSpan.TotalMilliseconds;
        }

        private void UpdateDistributionDate()
        {
            var date = TradingDates.Dates.Last();
            string year = date!.Substring(0, 4);
            string month = date!.Substring(4, 2);
            close_last_year = open_last_year = high_last_year = CloseYear = OpenYear = HighYear = int.Parse(year);
            close_last_month = open_last_month = high_last_month = CloseMonth = OpenMonth = HighMonth = int.Parse(month);
        }

        private void UpdateDistribution()
        {
            DisCloseData.Clear();
            DisOpenData.Clear();
            DisHighData.Clear();
            for (int i = 0; i < 20; i++)
            {
                string name = string.Format("[{0}%, {1}%]", 9 - i, 10 - i);
                DistributionItem item_close = new DistributionItem();
                item_close.Name = name;
                DisCloseData.Add(item_close);
                DistributionItem item_open = new DistributionItem();
                item_open.Name = name;
                DisOpenData.Add(item_open);
                DistributionItem item_high = new DistributionItem();
                item_high.Name = name;
                DisHighData.Add(item_high);
            }

            foreach (var value in Strategy.Instance.Data)
            {
                int year = int.Parse(value.Key.Substring(0, 4));
                int month = int.Parse(value.Key.Substring(4, 2));
                foreach (var item in value.Value)
                {
                    if (year == CloseYear && month == CloseMonth)
                    {
                        int index = double.Parse(item.CloseRatio!) >= 0.0 ? 9 - (int)double.Parse(item.CloseRatio!) : 10 - (int)double.Parse(item.CloseRatio!);
                        if (index < 0) index = 0;
                        if (index > 19) index = 19;
                        DisCloseData[index].Count += 1;
                    }

                    if (year == OpenYear && month == OpenMonth)
                    {
                        int index = double.Parse(item.OpenRatio!) >= 0.0 ? 9 - (int)double.Parse(item.OpenRatio!) : 10 - (int)double.Parse(item.OpenRatio!);
                        if (index < 0) index = 0;
                        if (index > 19) index = 19;
                        DisOpenData[index].Count += 1;
                    }
                    if (year == HighYear && month == HighMonth)
                    {
                        int index = double.Parse(item.HighRatio!) >= 0.0 ? 9 - (int)double.Parse(item.HighRatio!) : 10 - (int)double.Parse(item.HighRatio!);
                        if (index < 0) index = 0;
                        if (index > 19) index = 19;
                        DisHighData[index].Count += 1;
                    }
                }
            }
        }
    }
}
