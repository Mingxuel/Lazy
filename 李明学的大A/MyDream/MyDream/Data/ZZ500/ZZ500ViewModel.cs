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
using System.Linq;
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
        private ObservableCollection<StockCodesListItem> zZ500Data = new ObservableCollection<StockCodesListItem>();

        private int zZ500DataIndex = -1;
        public int ZZ500DataIndex
        {
            get => zZ500DataIndex;
            set
            {
                if (zZ500DataIndex != value)
                {
                    zZ500DataIndex = value;
                    OnPropertyChanged();
                    UpdateKRecordsZZ500();
                }
            }
        }

        [ObservableProperty]
        private List<Record1DItem> zZ500KRecords = new List<Record1DItem>();

        private void UpdateDataZZ500()
        {
            ZZ500Data.Clear();
            foreach (var data in ZZ500.Data)
            {
                StockCodesListItem item = new StockCodesListItem();
                item.StockCode = data.StockCode!;
                item.StockName = data.StockName!;
                ZZ500Data.Add(item);
            }
        }

        private void UpdateKRecordsZZ500()
        {
            if (ZZ500DataIndex == -1) return;

            ZZ500KRecords = ZZ5001D.Instance[ZZ500Data[ZZ500DataIndex].StockCode!]!.Data!;
        }
    }
}