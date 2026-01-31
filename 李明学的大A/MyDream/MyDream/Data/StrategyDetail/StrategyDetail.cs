using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    internal class StrategyDetail
    {
        private const int RANDOM_COUNT = 100;

        private static StrategyDetail? _instance = null;
        public static StrategyDetail Instance { get => _instance == null ? _instance = new StrategyDetail() : _instance; }
        public List<StrategyDetailItem> Data1 = new List<StrategyDetailItem>();
        public List<StrategyDetailItem> Data2 = new List<StrategyDetailItem>();
        public List<StrategyDetailItem> Data3 = new List<StrategyDetailItem>();
        public List<StrategyDetailItem> DataVWAP = new List<StrategyDetailItem>();

        public void Update()
        {
            UpdateStrategyDetail1();
            UpdateStrategyDetail2();
            UpdateStrategyDetail3();
            UpdateStrategyDetailVWAP();
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

        private void UpdateStrategyDetail3()
        {
            Data3.Clear();
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
                    if (strategy_items.Count == 1) {
                        ratio = GetRatio(strategy_items[0]);
                    } else if (strategy_items.Count == 2) {
                        ratio = (GetRatio(strategy_items[0]) + GetRatio(strategy_items[1])) / 2.0;
                    } else {
                        int random_index1 = new Random().Next(strategy_items.Count);
                        int random_index2 = 0;
                        do
                        {
                            random_index2 = new Random().Next(strategy_items.Count);
                        } while (random_index2 == random_index1);
                        int random_index3 = 0;
                        do
                        {
                            random_index3 = new Random().Next(strategy_items.Count);
                        } while (random_index3 == random_index1 || random_index3 == random_index2);

                        ratio = (GetRatio(strategy_items[random_index1]) + GetRatio(strategy_items[random_index2]) + GetRatio(strategy_items[random_index3])) / 3.0;
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
                Data3.Add(detail_item);
            }
            StrategyDetailItem detail_total = new StrategyDetailItem();
            detail_total.ID = "TOTAL";
            double total_ratio_2024 = 0.0;
            double total_ratio_2025 = 0.0;
            double total_ratio_2026 = 0.0;
            foreach (var detail_item in Data3)
            {
                total_ratio_2024 += double.Parse(detail_item.Detail2024!.TrimEnd('%')) / 100.0;
                total_ratio_2025 += double.Parse(detail_item.Detail2025!.TrimEnd('%')) / 100.0;
                total_ratio_2026 += double.Parse(detail_item.Detail2026!.TrimEnd('%')) / 100.0;
            }
            detail_total.Detail2024 = (total_ratio_2024 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2025 = (total_ratio_2025 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2026 = (total_ratio_2026 / RANDOM_COUNT).ToString("P2");
            Data3.Insert(0, detail_total);
        }

        private void UpdateStrategyDetailVWAP()
        {
            DataVWAP.Clear();
            foreach (var i in Enumerable.Range(0, RANDOM_COUNT))
            {
                double ratio_2024 = 1.0;
                double ratio_2025 = 1.0;
                double ratio_2026 = 1.0;
                foreach (var date in TradingDates.Dates)
                {
                    var strategy_items = Strategy.Instance.Data[date];
                    if (strategy_items.Count == 0) continue;

                    int max_index = -1;
                    double max_vwap = -10000;
                    foreach (var strategy_item in strategy_items)
                    {
                        var record = ZZ5001D.Instance[strategy_item.StockCode!]![date];
                        var record_1 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 1);
                        var record_2 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 2);
                        var record_3 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 3);
                        var record_4 = ZZ5001D.Instance.PreRecord(strategy_item.StockCode!, date, 4);
                        if (record == null || record_1 == null || record_2 == null || record_3 == null || record_4 == null) continue;
                        double total_value = GetPrice(record_1) * record_1.Volume + GetPrice(record_2) * record_2.Volume + GetPrice(record_3) * record_3.Volume + GetPrice(record_4) * record_4.Volume;
                        double total_value_low = GetLow(record_1) * record_1.Volume + GetLow(record_2) * record_2.Volume + GetLow(record_3) * record_3.Volume + GetLow(record_4) * record_4.Volume;
                        double total_volume = record_1.Volume + record_2.Volume + record_3.Volume + record_4.Volume;
                        double vwap = total_value / total_volume;
                        double vwap_low = total_value_low / total_volume;

                        vwap = (vwap - record_1.Close) / record_1.Close * 100.0;

                        if (vwap > max_vwap)
                        {
                            max_vwap = vwap;
                            max_index = strategy_items.IndexOf(strategy_item);
                        }
                    }

                    if (max_index == -1) continue;

                    var ratio = GetRatio(strategy_items[max_index]);

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
            detail_total.Detail2024 = (total_ratio_2024 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2025 = (total_ratio_2025 / RANDOM_COUNT).ToString("P2");
            detail_total.Detail2026 = (total_ratio_2026 / RANDOM_COUNT).ToString("P2");
            DataVWAP.Insert(0, detail_total);
        }

        private double GetRatio(StrategyItem item)
        {
            var value = double.Parse(item.HighRatio);
            return value;
        }

        private double GetPrice(Record1DItem? item)
        {
            return item!.High;
        }

        private double GetLow(Record1DItem? item)
        {
            return item!.Low;
        }
    }
}
