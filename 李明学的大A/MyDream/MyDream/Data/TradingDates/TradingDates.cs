using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;

namespace MyDream
{
    public static class TradingDates
    {
        public static List<string> Dates { get; } = new List<string>();

        public static void Init()
        {
            Dates.Clear();
            foreach (var line in File.ReadLines(APath.GetTradingDates()))
            {
                var date = line.Trim();
                if (!string.IsNullOrEmpty(date)) Dates.Add(date);
            }
        }

        public static string? PreDate(string date, int count = 1)
        {
            int idx = Dates.IndexOf(date);
            if (idx > count - 1)
                return Dates[idx - count];

            return null;
        }

        public static string? NextDate(string date, int count = 1)
        {
            int idx = Dates.IndexOf(date);
            if (idx >= 0 && idx + count < Dates.Count)
                return Dates[idx + count];

            return null;
        }
    }
}
