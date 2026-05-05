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

        public List<double> GetM5Ratio(string stock_code, string date)
        {
            var record_2 = ZZ5001D.Instance.PreRecord(stock_code, date, 1);
            var record_1 = ZZ5001D.Instance.PreRecord(stock_code, date, 0);

            double botton_ratio = -0.05;

            double price_buy = 0.0;
            double price_sell = 0.0;

            string pre_date = TradingDates.PreDate(date)!;
            var pre_records = ZZ5005M.Instance.Read(stock_code, pre_date);
            if (pre_records != null && pre_records.Count == 48)
            {
                price_buy = pre_records[41].Close;
            }
            else
            {
                price_buy = record_2!.Close;
            }

            var records = ZZ5005M.Instance.Read(stock_code, date);
            if (records == null || records.Count < 48)
            {
                if ((record_1!.Open / record_2!.Close - 1.0) <= botton_ratio)
                    price_sell = record_1.Open;
                else if ((record_1.Low / record_2.Close - 1.0) <= -0.06)
                    price_sell = record_2.Close * (1 - 0.06);
                else if (record_1.IsToped)
                    price_sell = record_1.Top;
                else
                    price_sell = record_1.Close;
            }
            else
            {
                for (int i = 0; i < records.Count; i++)
                {
                    if (i == 0)
                    {
                        if ((records[i].Open / record_2!.Close - 1.0) <= botton_ratio)
                        {
                            price_sell = records[i].Open;
                            break;
                        }
                    }

                    if ((records[i].Low / record_2!.Close - 1.0) <= botton_ratio)
                    {
                        price_sell = record_2.Close * (1 + botton_ratio);
                        break;
                    }

                    if (Math.Abs(records[i].High - record_1!.Top) < 0.001)
                    {
                        price_sell = record_1.Top;
                        break;
                    }

                    if (i == 41)
                    {
                        price_sell = records[i].Close;
                        break;
                    }
                }
            }

            return new List<Double> { Math.Round(price_buy, 2), Math.Round(price_sell, 2) };
        }
/*
        public double GetScore(string stockCode, string date)
        {
            string date_3T = TradingDates.PreDate(date, 3)!;
            string date_2T = TradingDates.PreDate(date, 2)!;
            string date_1T = TradingDates.PreDate(date, 1)!;

            var records_3T = ZZ5005M.Instance.Read(stockCode, date_3T);
            var records_2T = ZZ5005M.Instance.Read(stockCode, date_2T);
            var records_1T = ZZ5005M.Instance.Read(stockCode, date_1T);

            if (records_3T == null || records_2T == null || records_1T == null) return 0.0;

            List<Record5MItem> records = new List<Record5MItem>();
            records.AddRange(records_3T!);
            records.AddRange(records_2T!);
            records.AddRange(records_1T!);

            double volume_buy_3T = 0.0;
            double volume_sell_3T = 0.0;
            foreach (var record in records_3T)
            {
                if (Math.Abs(record.High - record.Low) < 0.0001)
                {
                    volume_buy_3T += record.Volume / 2.0;
                    volume_sell_3T += record.Volume / 2.0;
                }
                else
                {
                    volume_buy_3T += (record.Close - record.Low) / (record.High - record.Low) * record.Volume;
                    volume_sell_3T += (record.High - record.Close) / (record.High - record.Low) * record.Volume;
                }
            }

            double volume_buy_2T = 0.0;
            double volume_sell_2T = 0.0;
            foreach (var record in records_2T)
            {
                if (Math.Abs(record.High - record.Low) < 0.0001)
                {
                    volume_buy_2T += record.Volume / 2.0;
                    volume_sell_2T += record.Volume / 2.0;
                }
                else
                {
                    volume_buy_2T += (record.Close - record.Low) / (record.High - record.Low) * record.Volume;
                    volume_sell_2T += (record.High - record.Close) / (record.High - record.Low) * record.Volume;
                }
            }
//
            double volume_buy_1T = 0.0;
            double volume_sell_1T = 0.0;
            foreach (var record in records_1T)
            {
                int index = records_1T.IndexOf(record);
                if (index > 40) break;

                if (Math.Abs(record.High - record.Low) < 0.0001)
                {
                    volume_buy_1T += record.Volume / 2.0;
                    volume_sell_1T += record.Volume / 2.0;
                }
                else
                {
                    volume_buy_1T += (record.Close - record.Low) / (record.High - record.Low) * record.Volume;
                    volume_sell_1T += (record.High - record.Close) / (record.High - record.Low) * record.Volume;
                }
            }
//
            //return (volume_sell_2T) / (volume_buy_3T + volume_buy_2T);
            return (volume_sell_2T) / (volume_buy_3T);
        }
*/
        public double GetScore(string stockCode, string date)
        {
            string date_3T = TradingDates.PreDate(date, 2)!;
            string date_2T = TradingDates.PreDate(date, 1)!;
            string date_1T = TradingDates.PreDate(date, 0)!;

            var records_3T = ZZ5005M.Instance.Read(stockCode, date_3T);
            var records_2T = ZZ5005M.Instance.Read(stockCode, date_2T);
            var records_1T = ZZ5005M.Instance.Read(stockCode, date_1T);

            if (records_3T == null || records_2T == null || records_1T == null) return 0.0;

            List<Record5MItem> records = new List<Record5MItem>();
            records.AddRange(records_3T!);
            records.AddRange(records_2T!);
            records.AddRange(records_1T!);

            double volume_buy_3T = 0.0;
            double volume_sell_3T = 0.0;
            foreach (var record in records_3T)
            {
                if (Math.Abs(record.High - record.Low) < 0.0001)
                {
                    volume_buy_3T += record.Volume / 2.0;
                    volume_sell_3T += record.Volume / 2.0;
                }
                else
                {
                    volume_buy_3T += (record.Close - record.Low) / (record.High - record.Low) * record.Volume;
                    volume_sell_3T += (record.High - record.Close) / (record.High - record.Low) * record.Volume;
                }
            }

            double volume_buy_2T = 0.0;
            double volume_sell_2T = 0.0;
            foreach (var record in records_2T)
            {
                if (Math.Abs(record.High - record.Low) < 0.0001)
                {
                    volume_buy_2T += record.Volume / 2.0;
                    volume_sell_2T += record.Volume / 2.0;
                }
                else
                {
                    volume_buy_2T += (record.Close - record.Low) / (record.High - record.Low) * record.Volume;
                    volume_sell_2T += (record.High - record.Close) / (record.High - record.Low) * record.Volume;
                }
            }

            double volume_buy_1T = 0.0;
            double volume_sell_1T = 0.0;
            foreach (var record in records_1T)
            {
                if (records_1T.IndexOf(record) > 40) break;

                if (Math.Abs(record.High - record.Low) < 0.0001)
                {
                    volume_buy_1T += record.Volume / 2.0;
                    volume_sell_1T += record.Volume / 2.0;
                }
                else
                {
                    volume_buy_1T += (record.Close - record.Low) / (record.High - record.Low) * record.Volume;
                    volume_sell_1T += (record.High - record.Close) / (record.High - record.Low) * record.Volume;
                }
            }

            return volume_buy_3T - volume_sell_2T - volume_sell_1T;
        }
    }
}
