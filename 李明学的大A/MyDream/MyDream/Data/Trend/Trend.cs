using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Windows.UI.StartScreen;

namespace MyDream
{
    public class Trend
    {
        private static Trend? _instance = null;
        public static Trend Instance { get => _instance == null ? _instance = new Trend() : _instance; }
        public Dictionary<int, TrendItem> Data { get; set; } = new Dictionary<int, TrendItem>();

        public void Init()
        {
            Data.Clear();
            foreach (var line in File.ReadLines(APath.GetTrendConfig()))
            {
                if (!string.IsNullOrEmpty(line.Trim()))
                {
                    string[] items = line.Split("|");
                    Data[int.Parse(items[0])] = new TrendItem {
                        Index = int.Parse(items[0]),
                        StockName = items[1],
                        StockCode = items[2],
                        BeginDate = items[3],
                        EndDate = items[4]
                    };
                }
            }
        }

        public void WriteToConfig()
        {
            using (StreamWriter writer = new StreamWriter(APath.GetTrendConfig()))
            {
                foreach (var data in Data.Values)
                {
                    writer.WriteLine(data.ToString());
                }
            }
        }
    }
}
