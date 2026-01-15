using System.IO;

namespace MyDream
{
    public static class Concepts
    {
        public static List<string> Data { get; set; } = new List<string>();

        public static void InitData()
        {
            Data.Clear();
            ZZ500.ReadFromXlsx();
            foreach (var data in ZZ500.Data)
            {
                foreach(var concept in data.Concepts!)
                {
                    if (concept != null && concept.Length != 0 && Data.IndexOf(concept) < 0)
                    {
                        Data.Add(concept);
                    }
                }
            }
        }

        public static void WriteDataToConfig()
        {
            using (StreamWriter writer = new StreamWriter(APath.GetConceptsConfig()))
            {
                foreach (var data in Data)
                {
                    writer.WriteLine(data.ToString());
                }
            }
        }

        public static List<string> GetStockCodes(string concept)
        {
            List<string> stock_codes = new List<string>();
            foreach (var data in ZZ500.Data)
            {
                foreach (var item in data.Concepts!)
                {
                    if (item != null && item == concept)
                    {
                        stock_codes.Add(data.StockCode!);
                        break;
                    }
                }
            }

            return stock_codes;
        }
    }
}
