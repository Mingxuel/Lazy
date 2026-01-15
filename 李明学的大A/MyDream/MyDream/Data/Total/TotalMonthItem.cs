using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public class TotalMonthItem
    {
        public string? Month { get; set; } = "-";
        public int SellCount { get; set; } = 0;
        public int PerSellCount { get; set; } = 0;
        public string? CloseWin { get; set; }
        public string? PerCloseWin { get; set; }
        public string? CloseRatio { get; set; }
        public string? OpenWin { get; set; }
        public string? PerOpenWin { get; set; }
        public string? OpenRatio { get; set; }
        public string? HighWin { get; set; }
        public string? PerHighWin { get; set; }
        public string? HighRatio { get; set; }
    }
}
 