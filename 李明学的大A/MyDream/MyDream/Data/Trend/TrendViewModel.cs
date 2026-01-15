using CommunityToolkit.Mvvm;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using Org.BouncyCastle.Asn1.Cms;
using OxyPlot;
using OxyPlot.Series;
using OxyPlot.Wpf;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using WinRT;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        [ObservableProperty]
        private List<Record1DItem> trendKRecords = new List<Record1DItem>();

        [ObservableProperty]
        private ObservableCollection<TrendItem> trendData = new ObservableCollection<TrendItem>();

        [ObservableProperty]
        private ObservableCollection<string> trendStockCodes = new ObservableCollection<string>();

        [ObservableProperty]
        private ObservableCollection<string> trendBeginDate = new ObservableCollection<string>();

        [ObservableProperty]
        private ObservableCollection<string> trendEndDate = new ObservableCollection<string>();

        private int trendDataIndex = -1;
        public int TrendDataIndex
        {
            get => trendDataIndex;
            set
            {
                if (trendDataIndex != value)
                {
                    trendDataIndex = value;
                    OnPropertyChanged();
                    UpdateKRecordsTrend();
                }
            }
        }

        [ObservableProperty]
        private int trendStockCodeIndex = -1;

        [ObservableProperty]
        private int trendBeginDateIndex = -1;

        [ObservableProperty]
        private int trendEndDateIndex = -1;

        [RelayCommand]
        private void AddTrendClick()
        {
            var trend_item = new TrendItem();
            trend_item.Index = Trend.Instance.Data.Count();
            trend_item.StockName = TrendStockCodes[TrendStockCodeIndex];
            foreach(var data in ZZ500.Data)
            {
                if (trend_item.StockName == data.StockName)
                {
                    trend_item.StockCode = data.StockCode;
                    break;
                }
            }
            trend_item.BeginDate = TrendBeginDate[TrendBeginDateIndex];
            trend_item.EndDate = TrendEndDate[TrendEndDateIndex];
            Trend.Instance.Data.Add(trend_item.Index, trend_item);
            Trend.Instance.WriteToConfig();
            UpdateDataTrend();
        }

        [RelayCommand]
        private void DeleteTrendClick(TrendItem item)
        {
            Trend.Instance.Data.Remove(item.Index);
            Trend.Instance.WriteToConfig();
            UpdateDataTrend();
        }

        private void UpdateDataTrend()
        {
            Trend.Instance.Init();
            TrendData.Clear();
            foreach(var data in Trend.Instance.Data.Values)
            {
                TrendData.Add(data);
            }

            TrendStockCodes.Clear();
            foreach(var data in ZZ500.Data)
            {
                TrendStockCodes.Add(data.StockName!);
            }

            TrendBeginDate.Clear();
            TrendEndDate.Clear();
            foreach(var date in TradingDates.Dates)
            {
                TrendBeginDate.Add(date);
                TrendEndDate.Add(date);
            }
        }

        private void UpdateKRecordsTrend()
        {
            if (TrendDataIndex == -1) return;

            TrendKRecords = ZZ5001D.Instance[TrendData[TrendDataIndex].StockCode!]!.Data!;
        }
    }
}
