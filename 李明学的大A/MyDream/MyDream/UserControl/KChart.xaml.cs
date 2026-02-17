using CommunityToolkit.Mvvm.ComponentModel;
using Newtonsoft.Json;
using NPOI.POIFS.Storage;
using OxyPlot;
using OxyPlot.Axes;
using OxyPlot.Series;
using OxyPlot.Wpf;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

namespace MyDream
{
    /// <summary>
    /// KChart.xaml 的交互逻辑
    /// </summary>
    public partial class KChart : UserControl
    {
        public KChart()
        {
            InitializeComponent();
            InitializeWebView();
        }

        private async void InitializeWebView()
        {
            await webView.EnsureCoreWebView2Async(null);
            string html = System.IO.Path.GetFullPath("../../../Resources/amcharts5/examples/md-main/index.html");
            webView.CoreWebView2.Navigate(new Uri(html).AbsoluteUri);
        }

        public static readonly DependencyProperty KRecordsProperty =
            DependencyProperty.Register(
                nameof(KRecords),
                typeof(List<Record1DItem>),
                typeof(KChart),
                new PropertyMetadata(null, OnKRecordsChangedAsync));

        public List<Record1DItem> KRecords
        {
            get => (List<Record1DItem>)GetValue(KRecordsProperty);
            set => SetValue(KRecordsProperty, value);
        }

        private async static void OnKRecordsChangedAsync(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            try
            {
                List<Record1DItem> records = new List<Record1DItem>();
                var temps = (List<Record1DItem>)((KChart)d).GetValue(KRecordsProperty);
                foreach (var temp in temps)
                {
                    if (temp != null) records.Add(temp);
                }

                if (records.Count == 0) return;

                string jsonData = JsonConvert.SerializeObject(records);
                if (((KChart)d).webView.CoreWebView2 != null)
                    await ((KChart)d).webView.CoreWebView2.ExecuteScriptAsync(@$"window.AppInterface.setData1D({jsonData})");
            }
            catch
            {

            }
        }
    }
}
