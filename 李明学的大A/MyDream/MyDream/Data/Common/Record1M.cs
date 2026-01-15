using System;
using System.Collections.Generic;

namespace MyDream
{
    public class Record1M
    {
        public Record1M()
        {
            foreach(var date in TradingDates.Dates)
            {
                _data[date] = new List<Record1MItem>();
            }
        }

        private Dictionary<string, List<Record1MItem>> _data { get; set; } = new Dictionary<string, List<Record1MItem>>();

        public List<Record1MItem> this[string date]
        {
            get => _data[date];
            set
            {
                _data[date] = value;
            }
        }
    }
}
