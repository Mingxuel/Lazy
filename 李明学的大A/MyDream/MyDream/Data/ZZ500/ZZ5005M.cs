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

        public void WriteConfig()
        {
            foreach(var stock_code in ZZ500StockCodes.StockCodes)
            {
                foreach (var date in TradingDates.Dates)
                {
                    string directory = APath.Get5M() + stock_code;
                    if (!Directory.Exists(directory)) Directory.CreateDirectory(directory);
                    string file = directory + "\\" + date;
                    if (File.Exists(file)) continue;

                    var records = ZZ5001M.Instance[stock_code][date];
                    if (records.Count == 0) continue;
                    string time = "";
                    double open = 0.0;
                    double high = 0.0;
                    double low = 10000.0;
                    double close = 0.0;
                    int volumn = 0;
                    foreach (var record in records)
                    {
                        int index = records.IndexOf(record);
                        if (index % 5 == 0)
                        {
                            open = record.Open;
                            time = record.Time;
                        }
                        high = Math.Max(high, record.High);
                        low = Math.Min(low, record.Low);
                        if (index % 5 == 4) close = record.Close;
                        volumn += record.Volume;

                        if (index % 5 == 4)
                        {
                            if (!File.Exists(file)) File.Create(file).Close();
                            Record5MItem record_5m = new Record5MItem(time, open, high, low, close, volumn);
                            File.AppendAllLines(file, new []{ record_5m.ToString() });
                            time = "";
                            open = 0.0;
                            high = 0.0;
                            low = 10000.0;
                            close = 0.0;
                            volumn = 0;
                        }
                    }
                }
            }
        }
    }
}
