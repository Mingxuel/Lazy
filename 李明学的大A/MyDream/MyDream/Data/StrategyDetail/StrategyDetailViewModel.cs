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
        private ObservableCollection<StrategyDetailItem> strategyDetail3 = new ObservableCollection<StrategyDetailItem>();

        [ObservableProperty]
        private ObservableCollection<StrategyDetailItem> strategyDetailVWAP = new ObservableCollection<StrategyDetailItem>();

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

            StrategyDetail3.Clear();
            foreach (var item in StrategyDetail.Instance.Data3)
            {
                StrategyDetail3.Add(item);
            }

            StrategyDetailVWAP.Clear();
            foreach (var item in StrategyDetail.Instance.DataVWAP)
            {
                StrategyDetailVWAP.Add(item);
            }
        }
    }
}
