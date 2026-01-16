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
using System.Configuration;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        private System.Timers.Timer? _real_timer;

        [ObservableProperty]
        private string? output = null;

        [ObservableProperty]
        private EPage kPage = EPage.Main;

        [ObservableProperty]
        private bool sZ200IsSelected = false;

        [ObservableProperty]
        private bool zZ500IsSelected = false;

        public BoardViewModel()
        {
            //默认选择ZZ500
            SZ200IsSelected = true;
        }

        [RelayCommand]
        private async Task UpdateDataClick()
        {
            if (MessageBox.Show("确定要更新所有数据吗?", "更新数据", MessageBoxButton.YesNo, MessageBoxImage.Question) == MessageBoxResult.Yes)
            {
                List<string> stock_codes = new List<string>();
                string file_zz500 = APath.GetZZ500TicketsConfig();
                foreach (var line in File.ReadLines(file_zz500))
                {
                    if (!string.IsNullOrEmpty(line.Trim())) stock_codes.Add(line.Trim());
                }
                string file_sz200 = APath.GetSZ200TicketsConfig();
                foreach (var line in File.ReadLines(file_sz200))
                {
                    if (!string.IsNullOrEmpty(line.Trim()) && !stock_codes.Contains(line.Trim()))
                    {
                        stock_codes.Add(line.Trim());
                    }
                }
                stock_codes.Sort();
                string target_file = APath.GetTicketsConfig();
                File.WriteAllLines(target_file, stock_codes);

                //更新交易日数据
                Output = await CallPythonAPI.UpdateTradingDatesAsync();
                //下载1D数据
                Output += await CallPythonAPI.DownloadHistory1DAsync();
                //更新1D数据
                Output += await CallPythonAPI.UpdateHistory1DAsync();
                //下载1M数据
                //Output += await CallPythonAPI.DownloadHistory1MAsync();
                //更新1M数据
                //Output += await CallPythonAPI.UpdateHistory1MAsync();
            }
        }

        [RelayCommand]
        private void ClearTPOClick()
        {
            var directory = APath.GetStrategy();
            foreach (var filePath in Directory.EnumerateFiles(directory))
            {
                var fileInfo = new FileInfo(filePath);
                File.Delete(filePath);
            }
        }

        [RelayCommand]
        private void UpdateTPOClick()
        {
            Strategy.Instance.StrategyType = EStrategy.ThreePlusOne;
            UpdateStrategy();
        }

        [RelayCommand]
        private void ClearTestingClick()
        {
            var directory = APath.GetTesting();
            foreach (var filePath in Directory.EnumerateFiles(directory))
            {
                var fileInfo = new FileInfo(filePath);
                File.Delete(filePath);
            }
        }

        [RelayCommand]
        private void UpdateTestingClick()
        {
            Strategy.Instance.StrategyType = EStrategy.Testing;
            UpdateStrategy();
        }

        [RelayCommand]
        private void RuntimeClick()
        {
            List<string> stock_codes = new List<string>();
            foreach ( var data in StrategyTarget.Instance.Data3)
            {
                stock_codes.Add(data.StockCode!);
            }
            foreach (var data in StrategyTarget.Instance.Data31)
            {
                stock_codes.Add(data.StockCode!);
            }

            if (stock_codes.Count > 0) CallPythonAPI.RunAsync(stock_codes);

            _real_timer = new System.Timers.Timer();
            _real_timer.Interval = 3000;
            _real_timer.Elapsed += RealTimeCallback;
            _real_timer.Start();
        }

        private void UpdateStrategy()
        {
            //更新ZZ500数据
            Output = "更新ZZ500数据\n";
            ZZ500.ReadFromXlsx(ZZ500IsSelected);
            ZZ500.WriteToConfig(ZZ500IsSelected);
            //更新板块
            Output += "更新板块\n";
            Industry.InitData(ZZ500IsSelected);
            Industry.WriteDataToConfig();
            //更新概念
            Output += "更新概念\n";
            Concepts.InitData(ZZ500IsSelected);
            Concepts.WriteDataToConfig();

            //初始化数据类
            //初始化交易日数据
            TradingDates.Init();
            TradingTimes.Init();
            //初始化ZZ500股票代码
            ZZ500StockCodes.Init(ZZ500IsSelected);
            //初始化ZZ500股票代码
            ZZ5001D.Instance.Init();
            //初始化ZZ500股票代码
            ZZ5001M.Instance.Init();
            //初始化趋势数据
            Trend.Instance.Init();

            UpdateDataZZ500();
            UpdateDataTrend();
            UpdateDataStrategy();
            UpdateDataStrategyTarget();
            UpdateTotalMonth();
            UpdateCalendarDate();
            UpdateCalendar();
            UpdateDistributionDate();
            UpdateDistribution();

            //UpdateBurn();
        }
    }
}
