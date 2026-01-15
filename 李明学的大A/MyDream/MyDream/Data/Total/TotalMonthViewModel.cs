using CommunityToolkit.Mvvm.ComponentModel;
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
        private ObservableCollection<TotalMonthItem> totalMonth2024 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private ObservableCollection<TotalMonthItem> totalMonth2025 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private ObservableCollection<TotalMonthItem> totalMonth2026 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private ObservableCollection<TotalMonthItem> totalMonth2027 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private ObservableCollection<TotalMonthItem> totalMonth2028 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private ObservableCollection<TotalMonthItem> totalMonth2029 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private ObservableCollection<TotalMonthItem> totalMonth2030 = new ObservableCollection<TotalMonthItem>();

        [ObservableProperty]
        private string closeRatio2024 = "";

        [ObservableProperty]
        private string openRatio2024 = "";

        [ObservableProperty]
        private string highRatio2024 = "";

        [ObservableProperty]
        private string closeRatioPlan2024 = "";

        [ObservableProperty]
        private string openRatioPlan2024 = "";

        [ObservableProperty]
        private string highRatioPlan2024 = "";

        [ObservableProperty]
        private string closeRatio2025 = "";

        [ObservableProperty]
        private string openRatio2025 = "";

        [ObservableProperty]
        private string highRatio2025 = "";

        [ObservableProperty]
        private string closeRatioPlan2025 = "";

        [ObservableProperty]
        private string openRatioPlan2025 = "";

        [ObservableProperty]
        private string highRatioPlan2025 = "";

        [ObservableProperty]
        private string closeRatio2026 = "";

        [ObservableProperty]
        private string openRatio2026 = "";

        [ObservableProperty]
        private string highRatio2026 = "";

        [ObservableProperty]
        private string closeRatioPlan2026 = "";

        [ObservableProperty]
        private string openRatioPlan2026 = "";

        [ObservableProperty]
        private string highRatioPlan2026 = "";

        [ObservableProperty]
        private string closeRatio2027 = "";

        [ObservableProperty]
        private string openRatio2027 = "";

        [ObservableProperty]
        private string highRatio2027 = "";

        [ObservableProperty]
        private string closeRatioPlan2027 = "";

        [ObservableProperty]
        private string openRatioPlan2027 = "";

        [ObservableProperty]
        private string highRatioPlan2027 = "";

        [ObservableProperty]
        private string closeRatio2028 = "";

        [ObservableProperty]
        private string openRatio2028 = "";

        [ObservableProperty]
        private string highRatio2028 = "";

        [ObservableProperty]
        private string closeRatioPlan2028 = "";

        [ObservableProperty]
        private string openRatioPlan2028 = "";

        [ObservableProperty]
        private string highRatioPlan2028 = "";

        [ObservableProperty]
        private string closeRatio2029 = "";

        [ObservableProperty]
        private string openRatio2029 = "";

        [ObservableProperty]
        private string highRatio2029 = "";

        [ObservableProperty]
        private string closeRatioPlan2029 = "";

        [ObservableProperty]
        private string openRatioPlan2029 = "";

        [ObservableProperty]
        private string highRatioPlan2029 = "";

        [ObservableProperty]
        private string closeRatio2030 = "";

        [ObservableProperty]
        private string openRatio2030 = "";

        [ObservableProperty]
        private string highRatio2030 = "";

        [ObservableProperty]
        private string closeRatioPlan2030 = "";

        [ObservableProperty]
        private string openRatioPlan2030 = "";

        [ObservableProperty]
        private string highRatioPlan2030 = "";

        private void UpdateTotalMonth()
        {
            TotalMonth2024.Clear();
            TotalMonth2025.Clear();
            TotalMonth2026.Clear();
            TotalMonth2027.Clear();
            TotalMonth2028.Clear();
            TotalMonth2029.Clear();
            TotalMonth2030.Clear();
            for (int i = 0; i < 12; i++)
            {
                TotalMonth2024.Add(new TotalMonthItem());
                TotalMonth2025.Add(new TotalMonthItem());
                TotalMonth2026.Add(new TotalMonthItem());
                TotalMonth2027.Add(new TotalMonthItem());
                TotalMonth2028.Add(new TotalMonthItem());
                TotalMonth2029.Add(new TotalMonthItem());
                TotalMonth2030.Add(new TotalMonthItem());
            }

            int pre_year = 2024;
            int pre_month = 1;
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
            int update_count = 0;
            foreach (var data in Strategy.Instance.Data)
            {
                string date = data.Key.Substring(0, 6);
                int date_year = int.Parse(date!.Substring(0, 4));
                int date_month = int.Parse(date!.Substring(4, 2));

                if (date_year != pre_year || date_month != pre_month)
                {
                    total_count = 0;
                    close_final_ratio = 1.0;
                    close_win_count = 0;
                    open_final_ratio = 1.0;
                    open_win_count = 0;
                    high_final_ratio = 1.0;
                    high_win_count = 0;
                    total_per_count = 0;
                    total_per_close_win = 0;
                    total_per_high_win = 0;
                    total_per_open_win = 0;
                    pre_year = date_year;
                    pre_month = date_month;
                }

                update_count++;

                double close_total_ratio = 0.0;
                double open_total_ratio = 0.0;
                double high_total_ratio = 0.0;
                foreach (var item in data.Value)
                {
                    close_total_ratio += double.Parse(item.CloseRatio!);
                    open_total_ratio += double.Parse(item.OpenRatio!);
                    high_total_ratio += double.Parse(item.HighRatio!);

                    total_per_count++;
                    if (double.Parse(item.CloseRatio!) >= 0.0) total_per_close_win++;
                    if (double.Parse(item.OpenRatio!) >= 0.0) total_per_open_win++;
                    if (double.Parse(item.HighRatio!) >= 0.0) total_per_high_win++;
                }

                if (data.Value.Count != 0)
                {
                    double close_avg_ratio = close_total_ratio / data.Value.Count / 100.0;
                    double open_avg_ratio = open_total_ratio / data.Value.Count / 100.0;
                    double high_avg_ratio = high_total_ratio / data.Value.Count / 100.0;
                    close_final_ratio = close_final_ratio * (1 + close_avg_ratio);
                    open_final_ratio = open_final_ratio * (1 + open_avg_ratio);
                    high_final_ratio = high_final_ratio * (1 + high_avg_ratio);

                    total_count += 1;
                    if (close_total_ratio >= 0.0) close_win_count += 1;
                    if (open_total_ratio >= 0.0) open_win_count += 1;
                    if (high_total_ratio >= 0.0) high_win_count += 1;
                }

                switch (date_year)
                {
                    case 2024:
                        TotalMonth2024[date_month - 1].Month = date_month.ToString();
                        TotalMonth2024[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2024[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2024[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2024[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2024[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2024[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2024[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2024[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2024[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2024[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2024[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                    case 2025:
                        TotalMonth2025[date_month - 1].Month = date_month.ToString();
                        TotalMonth2025[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2025[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2025[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2025[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2025[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2025[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2025[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2025[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2025[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2025[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2025[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                    case 2026:
                        TotalMonth2026[date_month - 1].Month = date_month.ToString();
                        TotalMonth2026[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2026[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2026[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2026[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2026[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2026[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2026[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2026[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2026[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2026[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2026[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                    case 2027:
                        TotalMonth2027[date_month - 1].Month = date_month.ToString();
                        TotalMonth2027[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2027[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2027[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2027[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2027[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2027[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2027[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2027[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2027[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2027[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2027[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                    case 2028:
                        TotalMonth2028[date_month - 1].Month = date_month.ToString();
                        TotalMonth2028[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2028[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2028[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2028[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2028[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2028[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2028[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2028[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2028[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2028[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2028[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                    case 2029:
                        TotalMonth2029[date_month - 1].Month = date_month.ToString();
                        TotalMonth2029[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2029[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2029[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2029[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2029[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2029[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2029[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2029[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2029[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2029[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2029[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                    case 2030:
                        TotalMonth2030[date_month - 1].Month = date_month.ToString();
                        TotalMonth2030[date_month - 1].SellCount = (int)total_count;
                        TotalMonth2030[date_month - 1].PerSellCount = total_per_count;
                        TotalMonth2030[date_month - 1].CloseWin = (close_win_count / total_count).ToString("P2");
                        TotalMonth2030[date_month - 1].PerCloseWin = (total_per_close_win / (double)total_per_count).ToString("P2");
                        TotalMonth2030[date_month - 1].CloseRatio = close_final_ratio.ToString("P2");
                        TotalMonth2030[date_month - 1].OpenWin = (open_win_count / total_count).ToString("P2");
                        TotalMonth2030[date_month - 1].PerOpenWin = (total_per_open_win / (double)total_per_count).ToString("P2");
                        TotalMonth2030[date_month - 1].OpenRatio = open_final_ratio.ToString("P2");
                        TotalMonth2030[date_month - 1].HighWin = (high_win_count / total_count).ToString("P2");
                        TotalMonth2030[date_month - 1].PerHighWin = (total_per_high_win / (double)total_per_count).ToString("P2");
                        TotalMonth2030[date_month - 1].HighRatio = high_final_ratio.ToString("P2");
                        break;
                }
            }

            double close_ratio = 1.0;
            double open_ratio = 1.0;
            double high_ratio = 1.0;
            double close_plan_ratio = 1.0;
            double open_plan_ratio = 1.0;
            double high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2024)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2024 = close_ratio.ToString("P2");
            OpenRatio2024 = open_ratio.ToString("P2");
            HighRatio2024 = high_ratio.ToString("P2");
            CloseRatioPlan2024 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2024 = open_plan_ratio.ToString("P2");
            HighRatioPlan2024 = high_plan_ratio.ToString("P2");

            close_ratio = 1.0;
            open_ratio = 1.0;
            high_ratio = 1.0;
            close_plan_ratio = 1.0;
            open_plan_ratio = 1.0;
            high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2025)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2025 = close_ratio.ToString("P2");
            OpenRatio2025 = open_ratio.ToString("P2");
            HighRatio2025 = high_ratio.ToString("P2");
            CloseRatioPlan2025 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2025 = open_plan_ratio.ToString("P2");
            HighRatioPlan2025 = high_plan_ratio.ToString("P2");

            close_ratio = 1.0;
            open_ratio = 1.0;
            high_ratio = 1.0;
            close_plan_ratio = 1.0;
            open_plan_ratio = 1.0;
            high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2026)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2026 = close_ratio.ToString("P2");
            OpenRatio2026 = open_ratio.ToString("P2");
            HighRatio2026 = high_ratio.ToString("P2");
            CloseRatioPlan2026 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2026 = open_plan_ratio.ToString("P2");
            HighRatioPlan2026 = high_plan_ratio.ToString("P2");

            close_ratio = 1.0;
            open_ratio = 1.0;
            high_ratio = 1.0;
            close_plan_ratio = 1.0;
            open_plan_ratio = 1.0;
            high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2027)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2027 = close_ratio.ToString("P2");
            OpenRatio2027 = open_ratio.ToString("P2");
            HighRatio2027 = high_ratio.ToString("P2");
            CloseRatioPlan2027 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2027 = open_plan_ratio.ToString("P2");
            HighRatioPlan2027 = high_plan_ratio.ToString("P2");

            close_ratio = 1.0;
            open_ratio = 1.0;
            high_ratio = 1.0;
            close_plan_ratio = 1.0;
            open_plan_ratio = 1.0;
            high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2028)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2028 = close_ratio.ToString("P2");
            OpenRatio2028 = open_ratio.ToString("P2");
            HighRatio2028 = high_ratio.ToString("P2");
            CloseRatioPlan2028 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2028 = open_plan_ratio.ToString("P2");
            HighRatioPlan2028 = high_plan_ratio.ToString("P2");

            close_ratio = 1.0;
            open_ratio = 1.0;
            high_ratio = 1.0;
            close_plan_ratio = 1.0;
            open_plan_ratio = 1.0;
            high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2029)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2029 = close_ratio.ToString("P2");
            OpenRatio2029 = open_ratio.ToString("P2");
            HighRatio2029 = high_ratio.ToString("P2");
            CloseRatioPlan2029 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2029 = open_plan_ratio.ToString("P2");
            HighRatioPlan2029 = high_plan_ratio.ToString("P2");

            close_ratio = 1.0;
            open_ratio = 1.0;
            high_ratio = 1.0;
            close_plan_ratio = 1.0;
            open_plan_ratio = 1.0;
            high_plan_ratio = 1.0;
            foreach (var item in TotalMonth2030)
            {
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_ratio *= double.Parse(item.CloseRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_ratio *= double.Parse(item.OpenRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_ratio *= double.Parse(item.HighRatio.Replace("%", "")) / 100.0;
                if (!string.IsNullOrEmpty(item.CloseRatio)) close_plan_ratio *= ((double.Parse(item.CloseRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.OpenRatio)) open_plan_ratio *= ((double.Parse(item.OpenRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
                if (!string.IsNullOrEmpty(item.HighRatio)) high_plan_ratio *= ((double.Parse(item.HighRatio.Replace("%", "")) - 100.0) * Constants.PlanRatio + 100.0) / 100.0;
            }
            CloseRatio2030 = close_ratio.ToString("P2");
            OpenRatio2030 = open_ratio.ToString("P2");
            HighRatio2030 = high_ratio.ToString("P2");
            CloseRatioPlan2030 = close_plan_ratio.ToString("P2");
            OpenRatioPlan2030 = open_plan_ratio.ToString("P2");
            HighRatioPlan2030 = high_plan_ratio.ToString("P2");
        }
    }
}