using System.IO;

namespace MyDream
{
    public static class Industry
    {
        public static List<string> Data { get; set; } = new List<string>();

        public static void InitData(EMarket market)
        {
            Data.Clear();
            ZZ500.ReadFromXlsx(market);
            foreach(var data in ZZ500.Data)
            {
                if (data.Industry != null && data.Industry.Length != 0 && Data.IndexOf(data.Industry) < 0)
                {
                    Data.Add(data.Industry);
                }
            }
        }

        public static void WriteDataToConfig()
        {
            using (StreamWriter writer = new StreamWriter(APath.GetIndustryConfig()))
            {
                foreach (var data in Data)
                {
                    writer.WriteLine(data.ToString());
                }
            }
        }

        public static List<string> GetStockCodes(string industry)
        {
            List<string> stock_codes = new List<string>();
            foreach (var data in ZZ500.Data)
            {
                if (data.Industry == industry)
                {
                    stock_codes.Add(data.StockCode!);
                }
            }

            return stock_codes;
        }
    }
}
