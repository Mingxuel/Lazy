using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public class StrategyItem
    {
        public string? StockName { get; set; }
        public string? StockCode { get; set; }
        public string? Date { get; set; }
        public double Open { get; set; } = 0.0;
        public double High { get; set; } = 0.0;
        public double Low { get; set; } = 0.0;
        public double Close { get; set; } = 0.0;
        public string CloseRatio { get; set; } = "00.00%";
        public string HighRatio { get; set; } = "00.00%";
        public string LowRatio { get; set; } = "00.00%";
        public string OpenRatio { get; set; } = "00.00%";
        public string VWAPHighRatio { get; set; } = "00.00%";
        public string VWAPAllRatio { get; set; } = "00.00%";
        public override string ToString()
        {
            return $"{StockName}|{StockCode}|{Date}|{Open}|{High}|{Low}|{Close}|{CloseRatio}|{HighRatio}|{LowRatio}|{OpenRatio}|{VWAPHighRatio}|{VWAPAllRatio}";
        }
    }
}
