using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;

namespace MyDream
{
    public class ZZ5005M
    {
        private static ZZ5005M? _instance = null;
        public static ZZ5005M Instance { get => _instance == null ? _instance = new ZZ5005M() : _instance; }
        public Dictionary<string, Record5M?> Records { get; } = new Dictionary<string, Record5M?>();

        public List<Record5MItem>? Read(string? stock_code, string? date)
        {
            string file = string.Format("{0}{1}\\{2}", APath.Get5M(), stock_code, date);
            if (!File.Exists(file)) return null;

            List<Record5MItem>? list = new List<Record5MItem>();

            var lines = File.ReadAllLines(file);
            foreach(var line in lines)
            {
                if (line.Trim().Length == 0) continue;
                var items = line.Split("|");
                Record5MItem record = new Record5MItem(items[0], double.Parse(items[1]), double.Parse(items[2]), double.Parse(items[3]), double.Parse(items[4]), (int)double.Parse(items[5]), (int)double.Parse(items[6]), double.Parse(items[7]));
                list.Add(record);
            }

            return list;
        }

        public double? GetVWAP(string stock_code, string date)
        {
            double total_high_value = 0.0;
            double total_close_value = 0.0;
            double total_volume = 0.0;
            for (int i = 1; i < 5; i++)
            {
                var records = Read(stock_code, TradingDates.PreDate(date, i));
                if (records == null) return null;
                foreach (var record in records)
                {
                    total_high_value += record!.High * record!.Volume;
                    total_close_value += record!.Close * record!.Volume;
                    total_volume += record!.Volume;
                }
            }

            var record_1 = ZZ5001D.Instance.PreRecord(stock_code, date, 1);
            if (record_1 == null) return null;

            double vwap_high = total_high_value / total_volume;
            double vwap_close = total_close_value / total_volume;
            var vwap = (vwap_high - record_1.Close) / record_1.Close * 100.0;

            return vwap;
        }
    }
}
