using System;
using System.Diagnostics;
using System.Security.Cryptography.X509Certificates;

namespace MyDream
{
    public class Record5MItem
    {
        public Record5MItem(string time, double open, double high, double low, double close, int volumn)
        {
            Time = time;
            Open = open;
            High = high;
            Low = low;
            Close = close;
            Volume = volumn;
        }

        public string Time { get; set; }
        public double Open { get; set; } = 0.0;
        public double High { get; set; } = 0.0;
        public double Low { get; set; } = 0.0;
        public double Close { get; set; } = 0.0;
        public int Volume { get; set; } = 0;
        public double PreClose { get; set; } = 0.0;
        public string Date { get => Time.Substring(0, 8); }
        public string Year { get => Time.Substring(0, 4); }
        public string Month { get => Time.Substring(4, 2); }
        public string Day { get => Time.Substring(6, 2); }

        public override string ToString()
        {
            return $"{Time}|{Open}|{High}|{Low}|{Close}|{Volume}";
        }
    }
}
