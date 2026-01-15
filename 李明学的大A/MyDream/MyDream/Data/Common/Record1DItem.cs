using System;
using System.Diagnostics;

namespace MyDream
{
    public class Record1DItem
    {
        public Record1DItem(long date, double open, double high, double low, double close, int volumn, double amount, double settelementPrice, double openInterest, double preClose, double suspendFlag)
        {
            Date = date;
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

        public long Date { get; set; }
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
        public double Top { get => ConvertToLIMIT(1.1); }
        public double Top1 { get => ConvertToLIMIT(1.2); }
        public double Top2 { get => ConvertToLIMIT(1.3); }
        public double Bottom { get => ConvertToLIMIT(0.9); }
        public double Bottom1 { get => ConvertToLIMIT(0.8); }
        public double Bottom2 { get => ConvertToLIMIT(0.7); }
        public bool IsTop { get => Equals(Close, Top); }
        public bool IsTop1 { get => Equals(Close, Top1); }
        public bool IsTop2 { get => Equals(Close, Top2); }
        public bool IsBottom { get => Equals(Close, Bottom); }
        public bool IsBottom1 { get => Equals(Close, Bottom1); }
        public bool IsBottom2 { get => Equals(Close, Bottom2); }
        public bool IsToped { get => Equals(High, Top); }
        public bool IsToped1 { get => Equals(High, Top1); }
        public bool IsToped2 { get => Equals(High, Top2); }
        public double Ratio
        {
            get
            {
                if (PreClose.CompareTo(0.0) == 0) return 0.0;
                return Math.Round(Math.Round((Close - PreClose) / PreClose, 5), 4);
			}
        }
        public bool IsUp { get => Close.CompareTo(PreClose) > 0; }
        public bool IsDown { get => Close.CompareTo(PreClose) < 0; }
        public bool IsUped { get => High.CompareTo(PreClose) > 0; }
        public bool IsDowned { get => Low.CompareTo(PreClose) < 0; }
        public bool IsUpOpen { get => Open.CompareTo(PreClose) > 0; }
        public bool IsDownOpen { get => Open.CompareTo(PreClose) < 0; }
        public bool IsDecrease { get => Open.CompareTo(PreClose) > 0; }
        public bool IsRed { get => Close.CompareTo(Open) > 0; }
        public bool IsGreen { get => Open.CompareTo(Close) > 0; }
        public double MA5 { get; set; } = 0.0;
		public double MA10 { get; set; } = 0.0;

		private double ConvertToLIMIT(double rate)
        {
            decimal dec_rate = (decimal)rate;
            decimal dec_preclose = (decimal)PreClose;
            decimal dec_result = Math.Round(dec_preclose * dec_rate, 3, MidpointRounding.AwayFromZero);
            return (double)Math.Round(dec_result, 2, MidpointRounding.AwayFromZero);
        }

        private bool Equals(double a, double b)
        {
            return Math.Abs(a - b) < 0.0001;
        }
    }
}
