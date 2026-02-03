using System;
using System.Collections.Generic;

namespace MyDream
{
    public class Record5M
    {
        public Record5M()
        {
            foreach (var date in TradingDates.Dates)
            {
                _data[date] = new List<Record5MItem>();
            }
        }

        private Dictionary<string, List<Record5MItem>> _data { get; set; } = new Dictionary<string, List<Record5MItem>>();

        public List<Record5MItem> this[string date]
        {
            get => _data[date];
            set
            {
                _data[date] = value;
            }
        }
    }
}
