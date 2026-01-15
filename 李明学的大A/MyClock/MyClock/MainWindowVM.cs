using CommunityToolkit.Mvvm.ComponentModel;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;
using System.Windows.Threading;
using System;
using System.Diagnostics;

namespace MyClock
{
    public partial class MainWindowVM : ObservableObject
    {
        private int pre_minute = -1;
        private System.Windows.Threading.DispatcherTimer _timer;

        [ObservableProperty]
        private string hour = "00";

        [ObservableProperty]
        private string minute = "00";

        [ObservableProperty]
        private string second = "00";

        [ObservableProperty]
        private double fontSize = 30;

        [ObservableProperty]
        private Brush foreground = new SolidColorBrush(Color.FromRgb(255, 128, 0));

        [ObservableProperty]
        public int targetCount = 0;

        [ObservableProperty]
        private ObservableCollection<ProcessItem> processItems = new ObservableCollection<ProcessItem>();

        public MainWindowVM()
        {
            _timer = new System.Windows.Threading.DispatcherTimer
            {
                Interval = TimeSpan.FromMilliseconds(1000)
            };

            _timer.Tick += (s, e) =>
            {
                Application.Current.Dispatcher.Invoke(() => {
                    CallTimer();
                }, DispatcherPriority.Send);
            };

            _timer.Start();
        }

        private void CallTimer()
        {
            var now = DateTime.Now;
            Hour = now.Hour.ToString("D2");
            Minute = now.Minute.ToString("D2");
            Second = now.Second.ToString("D2");

            DateTime start_time = now.Date.AddHours(09).AddMinutes(14);
            TimeSpan diff = now - start_time;
            TargetCount = (int)diff.TotalMinutes;
            if (pre_minute != TargetCount && TargetCount >= 1 && TargetCount <= 345)
            {
                UpdateProcess();
            }
            else if (pre_minute != TargetCount)
            {
                Foreground = Brushes.White;
            }
            if (pre_minute != TargetCount) pre_minute = TargetCount;
        }

        public void UpdateProcess()
        {
            ProcessItems.Clear();
            for (int i = 1; i <= 345; i++)
            {
                var status = 1;
                if (i <= TargetCount && (i <= 10 || i >= 343))
                {
                    status = 3;
                    Foreground = new SolidColorBrush(Color.FromRgb(255, 0, 0));
                }
                else if (i <= TargetCount && ((i > 15 && i <= 135) || (i > 225)))
                {
                    status = 2;
                    Foreground = Brushes.White;
                }
                else
                {
                    Foreground = new SolidColorBrush(Color.FromRgb(255, 128, 0));
                }

                ProcessItems.Add(new ProcessItem
                {
                    Id = i + 1, IsSolid = status
                });
            }
        }
    }
}
