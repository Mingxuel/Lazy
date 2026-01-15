using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;

namespace MyDream
{
    public static class TradingTimes
    {
        public static List<string> Times { get; } = new List<string>();

        public static void Init()
        {
            Times.Clear();
            foreach (var line in File.ReadLines(APath.GetTradingTimes()))
            {
                var time = line.Trim();
                if (!string.IsNullOrEmpty(time)) Times.Add(time);
            }
        }
    }
}
