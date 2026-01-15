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
                if (int.Parse(date) < 20240604) continue;

                var date_index = TradingDates.Dates.IndexOf(date);
                var data = Strategy.Instance.Data[date];
                foreach (var time in TradingTimes.Times)
                {
                    var time_index = TradingTimes.Times.IndexOf(time);
                    string datetime = date + time;
                    var total_ratio = 0.0;
                    foreach (var item in data)
                    {
                        var record_1d = ZZ5001D.Instance.Records[item.StockCode!];
                        var record_1m = ZZ5001M.Instance[item.StockCode!];
                        var high = record_1d![date!]!.High;
                        var low = record_1d![date!]!.Low;
                        var pre_close = record_1d![date!]!.PreClose;
                        var close = record_1m![date][time_index].Close;
                        total_ratio += (close - pre_close) / (pre_close) * 100.0;
                    }
                    if (date.StartsWith("2024"))
                    {
                        Burn2024[date_index][time_index].Index = time_index;
                        Burn2024[date_index][time_index].Value = (total_ratio / (double)data.Count);
                    }
                    else if (date.StartsWith("2025"))
                    {
                        var index = TradingDates.Dates.IndexOf("20250102");
                        Burn2025[date_index - index][time_index].Index = time_index;
                        Burn2025[date_index - index][time_index].Value = (total_ratio / (double)data.Count);
                    }
                }
            }
        }
    }
}
