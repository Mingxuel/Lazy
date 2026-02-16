using NPOI.SS.Formula.Functions;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MyDream
{
    internal class StrategyDetail
    {
        private const int RANDOM_COUNT = 100;

        private static StrategyDetail? _instance = null;
        public static StrategyDetail Instance { get => _instance == null ? _instance = new StrategyDetail() : _instance; }
        public List<StrategyDetailItem> Data1 = new List<StrategyDetailItem>();
        public List<StrategyDetailItem> Data2 = new List<StrategyDetailItem>();
        public List<StrategyDetailItem> DataVWAP = new List<StrategyDetailItem>();
        public List<StrategyDetailVWAPTicketItem> DataVWAPTickets = new List<StrategyDetailVWAPTicketItem>();

        public void Update()
        {
            UpdateStrategyDetail1();
            UpdateStrategyDetail2();
            UpdateStrategyDetailVWAP();
            UpdateStrategyDetailVWAPTickets();
        }

        private void UpdateStrategyDetail1()
        {
            Data1.Clear();
            foreach (var i in Enumerable.Range(0, RANDOM_COUNT))
            {
                double ratio_2024 = 1.0;
                double ratio_2025 = 1.0;
                double ratio_2026 = 1.0;
                foreach (var date in TradingDates.Dates)
                {
                    var strategy_items = Strategy.Instance.Data[date];
                    if (strategy_items.Count == 0) continue;

                    int random_index = new Random().Next(strategy_items.Count);
                    var ratio = GetRatio(strategy_items[random_index]);
                    if (date.StartsWith("2024"))
                        ratio_2024 *= (1 + ratio / 100.0);
                    else if (date.StartsWith("2025"))
                        ratio_2025 *= (1 + ratio / 100.0);
                    else if (date.StartsWith("2026"))
                        ratio_2026 *= (1 + ratio / 100.0);
                }
                StrategyDetailItem detail_item = new StrategyDetailItem();
                detail_item.ID = i.ToString();
                detail_item.Detail2024 = ratio_2024.ToString("P2");
                detail_item.Detail2025 = ratio_2025.ToString("P2");
                detail_item.Detail2026 = ratio_2026.ToString("P2");
                Data1.Add(detail_item);
            }
            StrategyDetailItem detail_total = new StrategyDetailItem();
            detail_total.ID = "TOTAL";
            double total_ratio_2024 = 0.0;
            double total_ratio_2025 = 0.0;
            double total_ratio_2026 = 0.0;
            foreach (var detail_item in Data1)
            {
                total_ratio_2024 += double.Parse(detail_item.Detail2024!.TrimEnd('%')) / 100.0;
                total_ratio_2025 += double.Parse(detail_item.Detail2025!.TrimEnd('%')) / 100.0;
                total_ratio_2026 += double.Parse(detail_item.Detail2026!.TrimEnd('%')) / 100.0;
            }
            detail_total.Detail2024 = (total_ratio_2024 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2025 = (total_ratio_2025 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2026 = (total_ratio_2026 / RANDOM_COUNT).ToString("P2");
            Data1.Insert(0, detail_total);
        }

        private void UpdateStrategyDetail2()
        {
            Data2.Clear();
            foreach (var i in Enumerable.Range(0, RANDOM_COUNT))
            {
                double ratio_2024 = 1.0;
                double ratio_2025 = 1.0;
                double ratio_2026 = 1.0;
                foreach (var date in TradingDates.Dates)
                {
                    var strategy_items = Strategy.Instance.Data[date];
                    if (strategy_items.Count == 0) continue;

                    double ratio = 0.0;
                    if (strategy_items.Count == 1)
                    {
                        ratio = GetRatio(strategy_items[0]);
                    } else {
                        int random_index1 = new Random().Next(strategy_items.Count);
                        int random_index2 = 0;
                        do {
                            random_index2 = new Random().Next(strategy_items.Count);
                        } while (random_index2 == random_index1);
                        ratio = (GetRatio(strategy_items[random_index1]) + GetRatio(strategy_items[random_index2])) / 2.0;
                    }

                    if (date.StartsWith("2024"))
                        ratio_2024 *= (1 + ratio / 100.0);
                    else if (date.StartsWith("2025"))
                        ratio_2025 *= (1 + ratio / 100.0);
                    else if (date.StartsWith("2026"))
                        ratio_2026 *= (1 + ratio / 100.0);
                }
                StrategyDetailItem detail_item = new StrategyDetailItem();
                detail_item.ID = i.ToString();
                detail_item.Detail2024 = ratio_2024.ToString("P2");
                detail_item.Detail2025 = ratio_2025.ToString("P2");
                detail_item.Detail2026 = ratio_2026.ToString("P2");
                Data2.Add(detail_item);
            }
            StrategyDetailItem detail_total = new StrategyDetailItem();
            detail_total.ID = "TOTAL";
            double total_ratio_2024 = 0.0;
            double total_ratio_2025 = 0.0;
            double total_ratio_2026 = 0.0;
            foreach (var detail_item in Data2)
            {
                total_ratio_2024 += double.Parse(detail_item.Detail2024!.TrimEnd('%')) / 100.0;
                total_ratio_2025 += double.Parse(detail_item.Detail2025!.TrimEnd('%')) / 100.0;
                total_ratio_2026 += double.Parse(detail_item.Detail2026!.TrimEnd('%')) / 100.0;
            }
            detail_total.Detail2024 = (total_ratio_2024 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2025 = (total_ratio_2025 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2026 = (total_ratio_2026 / RANDOM_COUNT).ToString("P2");
            Data2.Insert(0, detail_total);
        }

        private void UpdateStrategyDetailVWAP()
        {
            DataVWAP.Clear();
            DataVWAPTickets.Clear();
            foreach (var i in Enumerable.Range(0, 1))
            {
                double ratio_2024 = 1.0;
                double ratio_2025 = 1.0;
                double ratio_2026 = 1.0;
                foreach (var date in TradingDates.Dates)
                {
                    var strategy_items = Strategy.Instance.Data[date];
                    if (strategy_items.Count == 0) continue;

                    int max_index = -1;
                    double max_vwap_high = -10000;
                    double max_vwap_close = -10000;
                    foreach (var strategy_item in strategy_items)
                    {
                        var record = ZZ5001D.Instance[strategy_item.StockCode!]![date];
                        var record_1 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 1);
                        var record_2 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 2);
                        var record_3 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 3);
                        var record_4 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 4);
                        if (record == null || record_1 == null || record_2 == null || record_3 == null || record_4 == null) continue;
                        double total_value_high = record_1.High * record_1.Volume + record_2.High * record_2.Volume + record_3.High * record_3.Volume + record_4.High * record_4.Volume;
                        double total_value_close = record_1.Close * record_1.Volume + record_2.Close * record_2.Volume + record_3.Close * record_3.Volume + record_4.Close * record_4.Volume;
                        double total_volume = record_1.Volume + record_2.Volume + record_3.Volume + record_4.Volume;
                        double vwap_high = total_value_high / total_volume;
                        double vwap_close = total_value_close / total_volume;

                        vwap_high = (vwap_high - record_1.Close) / record_1.Close * 100;
                        vwap_close = (vwap_close - record_1.Close) / record_1.Close * 100;
                        vwap_high = vwap_high + vwap_close;

                        if (vwap_high > max_vwap_high)
                        {
                            max_vwap_high = vwap_high;
                            max_vwap_close = vwap_close;
                            max_index = strategy_items.IndexOf(strategy_item);
                        }
                    }

                    if (max_index == -1) continue;

                    if (max_vwap_high <= Constants.MinVWAP) continue;

                    StrategyDetailVWAPTicketItem ticket_item = new StrategyDetailVWAPTicketItem();
                    ticket_item.Date = date;
                    ticket_item.StockCode = strategy_items[max_index].StockCode;
                    ticket_item.StockName = strategy_items[max_index].StockName;
                    ticket_item.CloseRatio = strategy_items[max_index].CloseRatio;
                    ticket_item.HighRatio = strategy_items[max_index].HighRatio;
                    ticket_item.LowRatio = strategy_items[max_index].LowRatio;
                    ticket_item.OpenRatio = strategy_items[max_index].OpenRatio;
                    ticket_item.VWAPAll = max_vwap_close.ToString("00.00") + "%";
                    ticket_item.VWAPHigh = max_vwap_high.ToString("00.00") + "%";
                    DataVWAPTickets.Add(ticket_item);

                    var ratio = GetM5Ratio(strategy_items[max_index]);
                    if (ratio == null) ratio = GetRatio(strategy_items[max_index]);

                    if (date.StartsWith("2024"))
                        ratio_2024 *= (1 + (double)ratio / 100.0);
                    else if (date.StartsWith("2025"))
                        ratio_2025 *= (1 + (double)ratio / 100.0);
                    else if (date.StartsWith("2026"))
                        ratio_2026 *= (1 + (double)ratio / 100.0);
                }
                StrategyDetailItem detail_item = new StrategyDetailItem();
                detail_item.ID = i.ToString();
                detail_item.Detail2024 = ratio_2024.ToString("P2");
                detail_item.Detail2025 = ratio_2025.ToString("P2");
                detail_item.Detail2026 = ratio_2026.ToString("P2");
                DataVWAP.Add(detail_item);
            }
            StrategyDetailItem detail_total = new StrategyDetailItem();
            detail_total.ID = "TOTAL";
            double total_ratio_2024 = 0.0;
            double total_ratio_2025 = 0.0;
            double total_ratio_2026 = 0.0;
            foreach (var detail_item in DataVWAP)
            {
                total_ratio_2024 += double.Parse(detail_item.Detail2024!.TrimEnd('%')) / 100.0;
                total_ratio_2025 += double.Parse(detail_item.Detail2025!.TrimEnd('%')) / 100.0;
                total_ratio_2026 += double.Parse(detail_item.Detail2026!.TrimEnd('%')) / 100.0;
            }
            detail_total.Detail2024 = (total_ratio_2024 / 1).ToString("P2");
            detail_total.Detail2025 = (total_ratio_2025 / 1).ToString("P2");
            detail_total.Detail2026 = (total_ratio_2026 / 1).ToString("P2");
            DataVWAP.Insert(0, detail_total);
        }

        private void UpdateStrategyDetailVWAPTickets()
        {

        }

        private double GetRatio(StrategyItem item)
        {
            var value = double.Parse(item.CloseRatio);
            return value;
        }

        private double GetPrice(Record1DItem? item)
        {
            return item!.High;
        }

        private double? GetM5Ratio(StrategyItem item)
        {
            var records = ZZ5005M.Instance.Read(item.StockCode, item.Date);

            if (records == null) return null;
            var record_1 = ZZ5001D.Instance.PreRecord(item.StockCode!, item.Date!, 1);
            if (record_1 == null) return null;

            var default_rate = (records?[records.Count - 1].Close / record_1.Close - 1.0) * 100.0;
            if (records?.Count < 47) return default_rate;

            int index = 42;

            var rate = records?.Count > index ? (records?[index].Close / record_1.Close - 1.0) * 100.0 : default_rate;
            return rate;
        }

        private double? Round(double? rate)
        {
            decimal dec_rate = (decimal)rate!;
            decimal dec_result = Math.Round(dec_rate, 3, MidpointRounding.AwayFromZero);
            return (double?)Math.Round(dec_result, 2, MidpointRounding.AwayFromZero);
        }

        private double GetLow(Record1DItem? item)
        {
            return item!.Low;
        }
    }
}
