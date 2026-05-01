using NPOI.HSSF.Record;
using NPOI.SS.Formula.Functions;
using Org.BouncyCastle.Tls.Crypto.Impl.BC;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MyDream
{
    internal class StrategyDetail
    {
        private const int RANDOM_COUNT = 10;

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
                    var values = ZZ5005M.Instance.GetM5Ratio(strategy_items[random_index].StockCode!, strategy_items[random_index].Date!);
                    var ratio = (values[1] / values[0] - 1.0) * 100.0;
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
            Data1.Clear();
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
                        var values = ZZ5005M.Instance.GetM5Ratio(strategy_items[0].StockCode!, strategy_items[0].Date!);
                        ratio = (values[1] / values[0] - 1.0) * 100.0;
                    }
                    else
                    {
                        int random_index1 = new Random().Next(strategy_items.Count);
                        int random_index2 = 0;
                        do
                        {
                            random_index2 = new Random().Next(strategy_items.Count);
                        } while (random_index2 == random_index1);
                        var values_1 = ZZ5005M.Instance.GetM5Ratio(strategy_items[random_index1].StockCode!, strategy_items[random_index1].Date!);
                        var values_2 = ZZ5005M.Instance.GetM5Ratio(strategy_items[random_index2].StockCode!, strategy_items[random_index2].Date!);
                        ratio = ((values_1[1] / values_1[0] - 1.0) * 100.0 + (values_2[1] / values_2[0] - 1.0) * 100.0) / 2.0;
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
            Data2.Clear();
            Data2.Insert(0, detail_total);
        }

        private void UpdateStrategyDetailVWAP()
        {
            DataVWAP.Clear();
            DataVWAPTickets.Clear();
            foreach (var i in Enumerable.Range(0, 1))
            {
                int total = 0;
                int win = 0;

                double ratio_2024 = 1.0;
                double ratio_2025 = 1.0;
                double ratio_2026 = 1.0;
                foreach (var date in TradingDates.Dates)
                {
                    var strategy_items = Strategy.Instance.Data[date];
                    if (strategy_items.Count == 0) continue;

                    double ratio = 0.0;
                    double max_score = 0.0;
                    int max_index = 0;
                    foreach (var index in Enumerable.Range(0, strategy_items.Count))
                    {
                        var pre_date = TradingDates.PreDate(strategy_items[index].Date!);
                        double score = ZZ5005M.Instance.GetScore(strategy_items[index].StockCode!, pre_date!);

                        if (score > max_score)
                        {
                            max_score = score;
                            max_index = index;
                        }
                    }

                    if (max_score < 0.0) continue;

                    var values = ZZ5005M.Instance.GetM5Ratio(strategy_items[max_index].StockCode!, strategy_items[max_index].Date!);
                    ratio = (values[1] / values[0] - 1.0) * 100.0;

                    StrategyDetailVWAPTicketItem ticket_item = new StrategyDetailVWAPTicketItem();
                    ticket_item.Date = date;
                    ticket_item.StockCode = strategy_items[max_index].StockCode;
                    ticket_item.StockName = strategy_items[max_index].StockName;
                    ticket_item.CloseRatio = strategy_items[max_index].CloseRatio;
                    ticket_item.HighRatio = strategy_items[max_index].HighRatio;
                    ticket_item.LowRatio = strategy_items[max_index].LowRatio;
                    ticket_item.OpenRatio = strategy_items[max_index].OpenRatio;
                    ticket_item.Ratio = (values[1] / values[0] - 1.0).ToString("P2");
                    ticket_item.BuyPrice = values[0];
                    ticket_item.SellPrice = values[1];
                    ticket_item.Score = Math.Round(max_score, 2);
                    DataVWAPTickets.Add(ticket_item);

                    total += 1;
                    if (ratio > 0.0) win += 1;

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
            detail_total.Detail2024 = (total_ratio_2024 / 1).ToString("P2");
            detail_total.Detail2025 = (total_ratio_2025 / 1).ToString("P2");
            detail_total.Detail2026 = (total_ratio_2026 / 1).ToString("P2");
            DataVWAP.Clear();
            DataVWAP.Insert(0, detail_total);
        }

        private void UpdateStrategyDetailVWAPTickets()
        {

        }

        private double GetRatio(StrategyItem item)
        {
            double botton_ratio = -0.05;

            var record_1 = ZZ5001D.Instance.PreRecord(item.StockCode!, item.Date!, 0);
            var record_2 = ZZ5001D.Instance.PreRecord(item.StockCode!, item.Date!, 1);
            if ((record_1!.Open / record_2!.Close - 1.0) <= botton_ratio)
                return (record_1.Open / record_2.Close - 1.0) * 100.0;
            else if ((record_1.Low / record_2.Close - 1.0) <= botton_ratio)
                return botton_ratio * 100.0;
            if (record_1.IsToped)
                return (record_1.Top / record_2.Close - 1.0) * 100.0;
            else
                return (record_1.Close / record_2.Close - 1.0) * 100.0;
        }

        private double GetPrice(Record1DItem? item)
        {
            return item!.High;
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
