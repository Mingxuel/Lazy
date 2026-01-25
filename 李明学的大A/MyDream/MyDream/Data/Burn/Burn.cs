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
        public List<List<BurnItem>> Burn2024 = new List<List<BurnItem>>();
        public List<List<BurnItem>> Burn2025 = new List<List<BurnItem>>();
        public List<List<BurnItem>> Burn2026 = new List<List<BurnItem>>();
        public List<List<BurnItem>> Burn2027 = new List<List<BurnItem>>();
        public List<List<BurnItem>> Burn2028 = new List<List<BurnItem>>();
        public List<List<BurnItem>> Burn2029 = new List<List<BurnItem>>();
        public List<List<BurnItem>> Burn2030 = new List<List<BurnItem>>();

        public Burn()
        {
            for (int row = 0; row < 270; row++)
            {
                Burn2024.Add(new List<BurnItem>());
                Burn2025.Add(new List<BurnItem>());
                Burn2026.Add(new List<BurnItem>());
                Burn2027.Add(new List<BurnItem>());
                Burn2028.Add(new List<BurnItem>());
                Burn2029.Add(new List<BurnItem>());
                Burn2030.Add(new List<BurnItem>());
                for (int col = 0; col < 238; col++)
                {
                    Burn2024[row].Add(new BurnItem(col, 0.0));
                    Burn2025[row].Add(new BurnItem(col, 0.0));
                    Burn2026[row].Add(new BurnItem(col, 0.0));
                    Burn2027[row].Add(new BurnItem(col, 0.0));
                    Burn2028[row].Add(new BurnItem(col, 0.0));
                    Burn2029[row].Add(new BurnItem(col, 0.0));
                    Burn2030[row].Add(new BurnItem(col, 0.0));
                }
            }
        }

        public void Update()
        {
            foreach (var date in TradingDates.Dates)
            {
                if (int.Parse(date) < 20240604 || int.Parse(date) > 20260101) continue;

                var date_index = TradingDates.Dates.IndexOf(date);
                var data = Strategy.Instance.Data[date];
                List<double> total_ratios = new List<double>();
                for (int i = 0; i < 238; i++)
                {
                    total_ratios.Add(0.0);
                }
                foreach (var time in TradingTimes.Times)
                {
                    var time_index = TradingTimes.Times.IndexOf(time);
                    string datetime = date + time;

                    foreach (var item in data)
                    {
                        int item_index = data.IndexOf(item);
                        var record_1m = ZZ5001M.Instance[item.StockCode!];
                        var record_1d = ZZ5001D.Instance[item.StockCode!];
                        var pre_close = record_1d![date]!.PreClose;
                        var close = record_1m![date][time_index].High;
                        var ratio = (close - pre_close) / pre_close * 100;
                        total_ratios[time_index] += ratio;
                    }
                    if (data.Count > 0) total_ratios[time_index] = total_ratios[time_index] / data.Count;
                    else total_ratios[time_index] = 0.0;
                }

                if (date.StartsWith("2024"))
                {
                    foreach (var time in TradingTimes.Times)
                    {
                        var time_index = TradingTimes.Times.IndexOf(time);
                        Burn2024[date_index][time_index].Index = time_index;
                        Burn2024[date_index][time_index].Value = total_ratios[time_index];
                    }
                }
                else if (date.StartsWith("2025"))
                {
                    foreach (var time in TradingTimes.Times)
                    {
                        var time_index = TradingTimes.Times.IndexOf(time);
                        Burn2025[date_index - 242][time_index].Index = time_index;
                        Burn2025[date_index - 242][time_index].Value = total_ratios[time_index];
                    }
                }
            }

            foreach (var time in TradingTimes.Times)
            {
                var time_index = TradingTimes.Times.IndexOf(time);
                List<double> ratios = new List<double>();
                for (int i = 0; i < 60; i++)
                {
                    ratios.Add(1.0);
                }
                int count = 0;
                int index = 0;
                foreach (var date in TradingDates.Dates)
                {
                    if (int.Parse(date) <= 20241231 || int.Parse(date) >= 20260101) continue;

                    if (count >= 5) 
                    {
                        index += 1;
                        count = 0;
                    }
                    count++;

                    var date_index = TradingDates.Dates.IndexOf(date);
                    ratios[index] = ratios[index] * (1 + Burn2025[date_index - 242][time_index].Value / 100.0);
                }
                count = 0;
                index = 0;
                foreach (var date in TradingDates.Dates)
                {
                    if (int.Parse(date) <= 20241231 || int.Parse(date) >= 20260101) continue;

                    if (count >= 5)
                    {
                        index += 1;
                        count = 0;
                    }
                    count++;

                    var date_index = TradingDates.Dates.IndexOf(date);
                    Burn2025[date_index - 242][time_index].Value = ratios[index];
                }
            }
        }
    }
}
