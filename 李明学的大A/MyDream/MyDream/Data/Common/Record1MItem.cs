using System;
using System.Diagnostics;

namespace MyDream
{
    public class Record1MItem
    {
        public Record1MItem(string time, double open, double high, double low, double close, int volumn, double amount, double settelementPrice, double openInterest, double preClose, double suspendFlag)
        {
            Time = time;
            Open = open;
            High = high;
            Low = low;
            Close = close;
            Volume = volumn;
            Amount = amount;
            SettelementPrice = settelementPrice;
            OpenInterest = openInterest;
            PreClose = preClose;
            SuspendFlag = suspendFlag;
        }

        public string Time { get; set; }
        public double Open { get; set; } = 0.0;
        public double High { get; set; } = 0.0;
        public double Low { get; set; } = 0.0;
        public double Close { get; set; } = 0.0;
        public int Volume { get; set; } = 0;
        public double Amount { get; set; } = 0.0;
        public double SettelementPrice { get; set; } = 0.0;
        public double OpenInterest { get; set; } = 0.0;
        public double PreClose { get; set; } = 0.0;
        public double SuspendFlag { get; set; } = 0.0;
        public string Date { get => Time.Substring(0, 8); }
        public string Year { get => Time.Substring(0, 4); }
        public string Month { get => Time.Substring(4, 2); }
        public string Day { get => Time.Substring(6, 2); }
    }
}
