using NPOI.HPSF;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public static class APath
    {
        public static string GetRoot()
        {
            string current_path = Assembly.GetExecutingAssembly().Location;
            int index = current_path.IndexOf("李明学的大A", StringComparison.OrdinalIgnoreCase);
            return current_path.Substring(0, index + "李明学的大A".Length);
        }

        public static string GetZZ500Xlsx()
        {
            return GetRoot() + "\\Data\\ZZ500\\Tickets_ZZ500.xlsx";
        }

        public static string GetSZ200Xlsx()
        {
            return GetRoot() + "\\Data\\ZZ500\\Tickets_SZ200.xlsx";
        }

        public static string GetZZ500DataConfig()
        {
            return GetRoot() + "\\Data\\ZZ500\\Data.config";
        }

        public static string GetZZ500TicketsConfig()
        {
            return GetRoot() + "\\Data\\ZZ500\\Tickets_ZZ500.config";
        }

        public static string GetSZ200TicketsConfig()
        {
            return GetRoot() + "\\Data\\ZZ500\\Tickets_SZ200.config";
        }

        public static string GetTicketsConfig()
        {
            return GetRoot() + "\\Data\\ZZ500\\Tickets.config";
        }

        public static string GetIndustryConfig()
        {
            return GetRoot() + "\\Data\\ZZ500\\Industry.config";
        }

        public static string GetConceptsConfig()
        {
            return GetRoot() + "\\Data\\ZZ500\\Concepts.config";
        }

        public static string GetTradingDates()
        {
            return GetRoot() + "\\Data\\交易日.config";
        }

        public static string GetTradingTimes()
        {
            return GetRoot() + "\\Data\\交易时间.config";
        }

        public static string GetTrendConfig()
        {
            return GetRoot() + "\\Data\\趋势.config";
        }

        public static string Get1D()
        {
            return GetRoot() + "\\Data\\1D\\";
        }

        public static string Get1M()
        {
            return GetRoot() + "\\Data\\1M\\";
        }

        public static string Get3B()
        {
            return GetRoot() + "\\Data\\3B\\";
        }

        public static string Get4B()
        {
            return GetRoot() + "\\Data\\4B\\";
        }

        public static string Get5B()
        {
            return GetRoot() + "\\Data\\5B\\";
        }

        public static string Get6B()
        {
            return GetRoot() + "\\Data\\6B\\";
        }

        public static string GetStrategy()
        {
            return GetRoot() + "\\Data\\Strategy\\";
        }

        public static string GetTesting()
        {
            return GetRoot() + "\\Data\\Testing\\";
        }

        public static string GetSeven()
        {
            return GetRoot() + "\\Data\\Seven\\";
        }

        public static string GetTHS()
        {
            return GetRoot() + "\\Data\\THS\\";
        }

        public static string GetTHSStrategyFileOrigin()
        {
            return GetRoot() + "\\Data\\THS\\blockstockV3.xml";
        }

        public static string GetTHSStrategyFileTarget()
        {
            return "C:\\同花顺远航版\\bin\\users\\狗蛋儿家的金\\blockstockV3.xml";
        }

        public static string GetRuntime()
        {
            return GetRoot() + "\\Data\\Runtime";
        }
    }
}
