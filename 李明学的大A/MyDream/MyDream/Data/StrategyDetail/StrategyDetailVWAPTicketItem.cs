using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Controls;

namespace MyDream
{
    public class StrategyDetailVWAPTicketItem
    {
        public string? Date { get; set; }
        public string? StockCode { get; set; }
        public string? StockName { get; set; }
        public string CloseRatio { get; set; } = "00.00%";
        public string HighRatio { get; set; } = "00.00%";
        public string LowRatio { get; set; } = "00.00%";
        public string OpenRatio { get; set; } = "00.00%";
        public string? VWAPHigh { get; set; }
        public string? VWAPClose { get; set; }
    }
}
