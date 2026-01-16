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

        public static void Init(bool isZZ500)
        {
            StockCodes.Clear();
            string file = isZZ500 ? APath.GetZZ500TicketsConfig() : APath.GetSZ200TicketsConfig();
            foreach (var line in File.ReadLines(file))
            {
                if (!string.IsNullOrEmpty(line.Trim())) StockCodes.Add(line.Trim());
            }
            StockCodes.Sort();
        }
    }
}
