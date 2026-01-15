using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Controls;

namespace MyDream
{
    public class TrendItem
    {
        public int Index { get; set; }
        public string? StockName { get; set; }
        public string? StockCode { get; set; }
        public string? BeginDate { get; set; }
        public string? EndDate { get; set; }
        public override string ToString()
        {
            return $"{Index}|{StockName}|{StockCode}|{BeginDate}|{EndDate}";
        }
    }
}
