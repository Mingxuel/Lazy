using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.IO;

namespace MyDream
{
    public static class ZZ500StockCodes
    {
        public static List<string> StockCodes { get; } = new List<string>();

        public static void Init(EMarket market)
        {
            StockCodes.Clear();
            string file = market switch
            {
                EMarket.ZZ500 => APath.GetZZ500TicketsConfig(),
                EMarket.SZ200 => APath.GetSZ200TicketsConfig(),
                EMarket.SZ50_SZ250 => APath.GetSZ50_SZ250TicketsConfig(),
                _ => throw new Exception("Invalid market")
            };

            foreach (var line in File.ReadLines(file))
            {
                if (!string.IsNullOrEmpty(line.Trim())) StockCodes.Add(line.Trim());
            }
            StockCodes.Sort();
        }
    }
}
