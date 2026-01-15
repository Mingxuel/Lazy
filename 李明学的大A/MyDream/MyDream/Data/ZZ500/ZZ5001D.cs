using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;

namespace MyDream
{
    public class ZZ5001D
    {
        private static ZZ5001D? _instance = null;
        public static ZZ5001D Instance { get => _instance == null ? _instance = new ZZ5001D() : _instance; }
        public Dictionary<string, Record1D?> Records { get; } = new Dictionary<string, Record1D?>();

        public Record1D? this[string stock_code]
        {
            get => Records[stock_code];
        }

        public Record1DItem? PreRecord(string stock_code, string date, int count = 1, bool accept_empty = false)
        {
            if (!accept_empty)
            {
                var pre_date = TradingDates.PreDate(date, count);
                if (pre_date == null) return null;

                return Records[stock_code]?[pre_date];
            }
            else
            {
                var pre_date = TradingDates.PreDate(date);
                while (pre_date != null)
                {
                    var record = Records[stock_code]?[pre_date];
                    if (record != null)
                    {
                        count--;
                        if (count <= 0) return record;
                    }
                    pre_date = TradingDates.PreDate(pre_date);
                }

                return null;
            }
        }

        public Record1DItem? NextRecord(string stock_code, string date, int count = 1, bool accept_empty = false)
        {
            if (!accept_empty)
            {
                var next_date = TradingDates.NextDate(date, count);
                if (next_date == null) return null;

                return Records[stock_code]?[next_date];
            }
            else
            {
                var next_date = TradingDates.NextDate(date);
                while (next_date != null)
                {
                    var record = Records[stock_code]?[next_date];
                    if (record != null)
                    {
                        count--;
                        if (count == 0) return record;
                    }
                    next_date = TradingDates.NextDate(next_date);
                }
                return null;
            }
        }

        public void Init()
        {
            try
            {
                var stock_codes = ZZ500StockCodes.StockCodes;

                foreach (var stock_code in stock_codes)
                {
                    Records[stock_code] = new Record1D();
                    TradingDates.Dates.ForEach(date => Records[stock_code]![date] = null);
                }

                string[] files = Directory.GetFiles(APath.Get1D(), "*", SearchOption.TopDirectoryOnly);
                Parallel.ForEach(files, file =>
                {
                    string file_name = Path.GetFileName(file);
                    if (stock_codes.Contains(file_name))
                    {
                        var lines = File.ReadLines(file).Skip(1);
                        foreach (var line in lines)
                        {
                            var data = line.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                            var stock_code = Path.GetFileName(file);
                            Records[stock_code]![data[0]] = new Record1DItem(
                                ConvertDateTimeToSeconds(DateTime.ParseExact(data[0], "yyyyMMdd", System.Globalization.CultureInfo.InvariantCulture)),
                                double.Parse(data[1].Trim()),
                                double.Parse(data[2].Trim()),
                                double.Parse(data[3].Trim()),
                                double.Parse(data[4].Trim()),
                                (int)double.Parse(data[5].Trim()),
                                double.Parse(data[6].Trim()),
                                double.Parse(data[7].Trim()),
                                double.Parse(data[8].Trim()),
                                double.Parse(data[9].Trim()),
                                0.0);
                        }
                    }
                });
            }
            catch (Exception ex)
            {
                MessageBox.Show($"读取文件失败: {ex.Message}");
            }
        }

        private static long ConvertDateTimeToSeconds(DateTime dateTime)
        {
            DateTime epoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            TimeSpan timeSpan = dateTime.ToUniversalTime() - epoch;
            return (long)timeSpan.TotalMilliseconds;
        }
    }
}
