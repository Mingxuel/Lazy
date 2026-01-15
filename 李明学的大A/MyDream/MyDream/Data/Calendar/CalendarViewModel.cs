using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using MyDream;
using NPOI.SS.Formula.Functions;
using NPOI.XSSF.Streaming.Values;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        [ObservableProperty]
        private ObservableCollection<CalendarItem> calendarDatas = new ObservableCollection<CalendarItem>();

        [ObservableProperty]
        private int calendarYear = 0;

        [ObservableProperty]
        private int calendarMonth = 0;

        private int last_year = 0;
        private int last_month = 0;

        [RelayCommand]
        private void CalenderYearMinusClick()
        {
            if (CalendarYear > 2024) CalendarYear--;

            UpdateCalendar();
        }

        [RelayCommand]
        private void CalenderYearPlusClick()
        {
            if (CalendarYear < last_year) CalendarYear++;

            UpdateCalendar();
        }

        [RelayCommand]
        private void CalenderMonthMinusClick()
        {
            if (CalendarMonth > 1) CalendarMonth--;

            UpdateCalendar();
        }

        [RelayCommand]
        private void CalenderMonthPlusClick()
        {
            if (CalendarYear == last_year && CalendarMonth == last_month) return;

            if (CalendarMonth < 12) CalendarMonth++;

            UpdateCalendar();
        }

        private void UpdateCalendarDate()
        {
            var date = TradingDates.Dates.Last();
            string year = date!.Substring(0, 4);
            string month = date!.Substring(4, 2);
            CalendarYear = int.Parse(year);
            CalendarMonth = int.Parse(month);
            last_year = CalendarYear;
            last_month = CalendarMonth;
        }

        private void UpdateCalendar()
        {
            CalendarDatas.Clear();

            foreach(var data in Strategy.Instance.Data)
            {
                if (int.Parse(data.Key.Substring(0, 4)) == CalendarYear && int.Parse(data.Key.Substring(4, 2)) == CalendarMonth)
                {
                    double close_ratio = 0.0;
                    double open_ratio = 0.0;
                    double high_ratio = 0.0;
                    foreach (var item in  data.Value)
                    {
                        close_ratio += double.Parse(item.CloseRatio!);
                        open_ratio += double.Parse(item.OpenRatio!);
                        high_ratio += double.Parse(item.HighRatio!);
                    }
                    if (data.Value.Count != 0)
                    {
                        close_ratio = close_ratio / (double)data.Value.Count / 100.0;
                        if (data.Value.Count != 0) open_ratio = open_ratio / (double)data.Value.Count / 100.0;
                        if (data.Value.Count != 0) high_ratio = high_ratio / (double)data.Value.Count / 100.0;

                        CalendarItem calendar_item = new CalendarItem();
                        calendar_item.Day = data.Key.Substring(6, 2);
                        calendar_item.CloseRatio = close_ratio.ToString("P2");
                        calendar_item.OpenRatio = open_ratio.ToString("P2");
                        calendar_item.HighRatio = high_ratio.ToString("P2");
                        CalendarDatas.Add(calendar_item);
                    }
                    else
                    {
                        CalendarItem calendar_item = new CalendarItem();
                        calendar_item.Day = data.Key.Substring(6, 2);
                        calendar_item.CloseRatio = "-";
                        calendar_item.OpenRatio = "-";
                        calendar_item.HighRatio = "-";
                        CalendarDatas.Add(calendar_item);
                    }
                }
            }
        }
    }
}
