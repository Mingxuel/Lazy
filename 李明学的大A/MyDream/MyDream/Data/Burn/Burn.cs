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
            double total = 100.0;
            foreach (var ticket in StrategyDetail.Instance.DataVWAPTickets)
            {
                BurnChartItem item = new BurnChartItem();
                var data = ZZ5001D.Instance[ticket.StockCode!]![ticket.Date!];
                if (data!.IsToped)
                {
                    total *= (1 + (data.High - data.PreClose) / data.PreClose);
                }
                else
                {
                    total *= (1 + double.Parse(ticket.CloseRatio) / 100.0);
                }

                item.Time = ticket.Date!;
                item.Count = (int)total;
                BurnChart.Add(item);
            }
        }
    }
}
