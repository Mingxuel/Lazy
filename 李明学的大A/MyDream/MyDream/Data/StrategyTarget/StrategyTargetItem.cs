using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public class StrategyTargetItem
    {
        public string? StockName { get; set; }
        public string? StockCode { get; set; }
        public double? Score { get; set; }
        public string? Flag { get; set; }
        public int Count { get; set; }
        public int LastDateIndex { get; set; }
        public override string ToString()
        {
            return $"{StockName}|{StockCode}|{Flag}|{Count}|{LastDateIndex}";
        }
    }
}
