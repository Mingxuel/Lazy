using CommunityToolkit.Mvvm.ComponentModel;
using MathNet.Numerics;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        [ObservableProperty]
        private ObservableCollection<StrategyDetailItem> strategyDetail1 = new ObservableCollection<StrategyDetailItem>();

        [ObservableProperty]
        private ObservableCollection<StrategyDetailItem> strategyDetail2 = new ObservableCollection<StrategyDetailItem>();

        [ObservableProperty]
        private ObservableCollection<StrategyDetailItem> strategyDetailVWAP = new ObservableCollection<StrategyDetailItem>();

        [ObservableProperty]
        private ObservableCollection<StrategyDetailVWAPTicketItem> strategyDetailVWAPTickets = new ObservableCollection<StrategyDetailVWAPTicketItem>();

        private int strategyDetailVWAPTicketsIndex = -1;
        public int StrategyDetailVWAPTicketsIndex
        {
            get => strategyDetailVWAPTicketsIndex;
            set
            {
                if (strategyDetailVWAPTicketsIndex != value)
                {
                    strategyDetailVWAPTicketsIndex = value;
                    OnPropertyChanged();
                    if (value != -1) UpdateStrategyDetailVWAPTickets();
                }
            }
        }

        [ObservableProperty]
        private List<Record1DItem> strategyDetailKRecords = new List<Record1DItem>();

        private void UpdateStrategyDetail()
        {
            StrategyDetail.Instance.Update();

            StrategyDetail1.Clear();
            foreach (var item in StrategyDetail.Instance.Data1)
            {
                StrategyDetail1.Add(item);
            }

            StrategyDetail2.Clear();
            foreach (var item in StrategyDetail.Instance.Data2)
            {
                StrategyDetail2.Add(item);
            }

            StrategyDetailVWAP.Clear();
            foreach (var item in StrategyDetail.Instance.DataVWAP)
            {
                StrategyDetailVWAP.Add(item);
            }

            StrategyDetailVWAPTickets.Clear();
            foreach (var item in StrategyDetail.Instance.DataVWAPTickets)
            {
                StrategyDetailVWAPTickets.Insert(0, item);
            }
        }

        private void UpdateStrategyDetailVWAPTickets()
        {
            if (StrategyDetailVWAPTicketsIndex == -1) return;

            List<string> selected_dates = new List<string>();

            for (int i = 4; i != 0; i--)
            {
                var date = TradingDates.PreDate(StrategyDetailVWAPTickets[StrategyDetailVWAPTicketsIndex].Date!, i);
                selected_dates.Add(date!);
            }

            List<Record1DItem> records = new List<Record1DItem>();
            List<Record5MItem> records_5m = new List<Record5MItem>();
            foreach (var selected_date in selected_dates)
            {
                var recor = ZZ5005M.Instance.Read(StrategyDetailVWAPTickets[StrategyDetailVWAPTicketsIndex].StockCode, selected_date)!;
                foreach (var item in recor)
                {
                    item.Time = selected_date! + item.Time;
                    records_5m.Add(item);
                }
            }

            foreach (var record in records_5m)
            {
                var datetime = DateTime.ParseExact(record.Time, "yyyyMMddHHmmss", System.Globalization.CultureInfo.InvariantCulture);
                long seconds = new DateTimeOffset(datetime).ToUnixTimeSeconds() * 1000;
                Record1DItem item = new Record1DItem(seconds, record.Open, record.High, record.Low, record.Close, record.Volume, record.Amount, 0.0, 0.0, 0.0, 0.0);
                records.Add(item);
            }

            foreach (var item in ZZ5001D.Instance[StrategyDetailVWAPTickets[StrategyDetailVWAPTicketsIndex].StockCode!]!.Data!)
            {

            }

            StrategyDetailKRecords = records;
        }
    }
}
