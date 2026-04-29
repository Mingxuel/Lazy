using NPOI.HPSF;
using NPOI.SS.Formula.Functions;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Windows.Networking.Sockets;

namespace MyDream
{
    public class Burn
    {
        public List<List<BurnItem>> BurnAll = new List<List<BurnItem>>();
        public List<BurnChartItem> BurnChart = new List<BurnChartItem>();

        public void Update()
        {
            /*
                        BurnAll.Clear();
                        for (int row = 0; row < TradingDates.Dates.Count; row++)
                        {
                            BurnAll.Add(new List<BurnItem>());
                            for (int col = 0; col < TradingTimes.Times.Count; col++)
                            {
                                BurnAll[row].Add(new BurnItem(col, 0.0));
                            }
                        }

                        foreach (var time in TradingTimes.Times)
                        {
                            var time_index = TradingTimes.Times.IndexOf(time);
                            foreach(var ticket in StrategyDetail.Instance.DataVWAPTickets)
                            {
                                if (double.Parse(ticket.Date!) < 20240604) continue;

                                int ticket_index = StrategyDetail.Instance.DataVWAPTickets.IndexOf(ticket);
                                var date_index = TradingDates.Dates.IndexOf(ticket.Date!);
                                BurnAll[date_index][time_index].Index = time_index;
                                var close = ZZ5001M.Instance[ticket.StockCode!]![ticket.Date!][time_index].Close;
                                var pre_close = ZZ5001D.Instance[ticket.StockCode!]!.Data![date_index]!.PreClose;
                                BurnAll[date_index][time_index].Value = (close - pre_close) / pre_close * 100;
                            }
                        }

                        BurnChart.Clear();
                        foreach (var time in TradingTimes.Times)
                        {
                            var time_index = TradingTimes.Times.IndexOf(time);
                            double total = 100.0;
                            foreach (var date in TradingDates.Dates)
                            {
                                if (double.Parse(date) < 20240604) continue;
                                var date_index = TradingDates.Dates.IndexOf(date);
                                total *= (1.0 + BurnAll[date_index][time_index].Value / 100);
                            }
                            BurnChartItem item = new BurnChartItem();
                            item.Time = time;
                            item.Count = (int)total;
                            BurnChart.Add(item);
                        }
            */
            BurnChart.Clear();
            for (int year = 2024; year <=2026; year++)
            {
                foreach (var month in Enumerable.Range(1, 12))
                {
                    BurnChartItem item = new BurnChartItem();
                    item.Time = string.Format("{0}{1:00}", year, month);
                    BurnChart.Add(item);
                }
            }

            double total = 100.0;
            double month_total = 100.0;
            int pre_index = -1;
            double day_ratio = 0.0;
            int day_count = 1;
            string pre_date = "";
            double pre_ratio = 0.0;

            foreach (var ticket in StrategyDetail.Instance.DataVWAPTickets)
            {
                int index = 0;
                var year = ticket!.Date!.Substring(0, 4);
                string month = ticket!.Date!.Substring(4, 2)!;
                if (year == "2024") {
                    index = int.Parse(month) - 1;
                } else if (year == "2025") {
                    index = 12 + int.Parse(month) - 1;
                } else if (year == "2026") {
                    index = 24 + int.Parse(month) - 1;
                }

                if (pre_index == -1)
                {
                    pre_index = index;
                }
                else if (pre_index != index)
                {
                    pre_index = index;
                    total *= month_total / 100.0;
                    BurnChart[index-1].Count = (int)total;
                    month_total = 100.0;
                }

                var data = ZZ5001D.Instance[ticket.StockCode!]![ticket.Date!];
                var values = ZZ5005M.Instance.GetM5Ratio(ticket.StockCode!, ticket.Date!);
                var ratio  = (values[1] / values[0] - 1.0) * 100.0;

                if (pre_date == ticket!.Date!)
                {
                    day_ratio += ratio;
                    day_count += 1;
                    ratio = day_ratio / day_count;
                    month_total /= (1 + (double)pre_ratio / 100.0);
                }
                else
                {
                    day_ratio = ratio;
                    day_count = 1;
                    pre_date = ticket!.Date!;
                }
                pre_ratio = ratio;

                month_total *= (1 + (double)ratio / 100.0);

                if (StrategyDetail.Instance.DataVWAPTickets.IndexOf(ticket) == StrategyDetail.Instance.DataVWAPTickets.Count - 1)
                {
                    total *= month_total / 100.0;
                    BurnChart[index].Count = (int)total;
                }
            }
        }
    }
}
