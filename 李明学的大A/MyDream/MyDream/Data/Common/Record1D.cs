using System;
using System.Collections.Generic;

namespace MyDream
{
    public class Record1D
    {
        public Record1D()
        {
            Data = new List<Record1DItem?>();
        }

        public List<Record1DItem?> Data
        {
            get => _data.Values.ToList();
            set => _data = value.Select((item, index) => new { item, index }).ToDictionary(x => TradingDates.Dates[x.index], x => x.item);
        }

        private Dictionary<string, Record1DItem?> _data { get; set; } = new Dictionary<string, Record1DItem?>();

        public Record1DItem? this[string time]
        {
            get => _data[time];
            set => _data[time] = value;
        }
    }
}
