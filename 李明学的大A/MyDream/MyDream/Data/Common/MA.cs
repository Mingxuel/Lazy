using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public class MA
    {
        public static string? MA5(string stockCode, string date)
        {
            return _MA(stockCode, date, 5);
        }

        public static string? MA10(string stockCode, string date)
        {
            return _MA(stockCode, date, 10);
        }

        public static string? MA20(string stockCode, string date)
        {
            return _MA(stockCode, date, 20);
        }

        private static string? _MA(string stockCode, string date, int cycle = 5)
        {
            if (!TradingDates.Dates.Contains(date)) return null;
            if (!ZZ500StockCodes.StockCodes.Contains(stockCode)) return null;

            Record1DItem? record = ZZ5001D.Instance.Records[stockCode]?[date];
            if (record == null) return null;

            int count = 0;
            string? pre_date = null;
            double total_price = record.Close;
            while (count < cycle - 1)
            {
                pre_date = TradingDates.PreDate(date);
                if (pre_date == null) return null;
                record = ZZ5001D.Instance.Records[stockCode]?[pre_date];
                if (record == null) continue;
                count++;
                total_price += record.Close;
            }
            return ConvertToString(total_price / cycle);
        }

        private static string ConvertToString(double price)
        {
            return Math.Round(Math.Round(price, 3), 2).ToString();
        }
    }
}
