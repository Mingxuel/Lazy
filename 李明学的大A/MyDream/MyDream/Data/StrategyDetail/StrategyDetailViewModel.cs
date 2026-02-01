using CommunityToolkit.Mvvm.ComponentModel;
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
                StrategyDetailVWAPTickets.Add(item);
            }
        }

        private void UpdateStrategyDetailVWAPTickets()
        {
            if (StrategyDetailVWAPTicketsIndex == -1) return;

            string selected_date = StrategyDetailVWAPTickets[StrategyDetailVWAPTicketsIndex].Date!;

            for (int i = 4; i != 0; i--)
            {
                var date = TradingDates.NextDate(selected_date, i);
                if (date == null) continue;
                selected_date = date;
                break;
            }

            List<Record1DItem> records = new List<Record1DItem>();
            foreach (var item in ZZ5001D.Instance[StrategyDetailVWAPTickets[StrategyDetailVWAPTicketsIndex].StockCode!]!.Data!)
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

            StrategyDetailKRecords = records;
        }
    }
}
