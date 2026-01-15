using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;

namespace MyDream
{
    public class ZZ5001M
    {
        private static ZZ5001M? _instance = null;
        public static ZZ5001M Instance { get => _instance == null ? _instance = new ZZ5001M() : _instance; }
        public Dictionary<string, Record1M?> Records { get; } = new Dictionary<string, Record1M?>();

        public Record1M? this[string stock_code]
        {
            get
            {
                if (!Records.Keys.Contains(stock_code))
                {
                    Records[stock_code] = new Record1M();
                    TradingDates.Dates.ForEach(date => Records[stock_code]![date] = new List<Record1MItem>());
                    var lines = File.ReadLines(APath.Get1M() + stock_code).Skip(1);
                    foreach (var line in lines)
                    {
                        var data = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                        Records[stock_code]![data[0].Trim().Substring(0, 8)].Add(
                            new Record1MItem(
                                data[0].Trim(),
                                double.Parse(data[1].Trim()),
                                double.Parse(data[2].Trim()),
                                double.Parse(data[3].Trim()),
                                double.Parse(data[4].Trim()),
                                (int)double.Parse(data[5].Trim()),
                                double.Parse(data[6].Trim()),
                                double.Parse(data[7].Trim()),
                                double.Parse(data[8].Trim()),
                                double.Parse(data[9].Trim()),
                                0.0)
                        );
                    }
                }

                return Records[stock_code];
            }
        }

        public void Init()
        {
            try
            {

            }
            catch (Exception ex)
            {
                MessageBox.Show($"读取文件失败: {ex.Message}");
            }
        }
    }
}
