using NPOI.HSSF.UserModel;
using NPOI.SS.UserModel;
using NPOI.XSSF.UserModel;
using System.IO;

namespace MyDream
{
    public static class ZZ500
    {
        public static List<ZZ500Item> Data { get; } = new List<ZZ500Item>();

        public static void ReadFromXlsx(EMarket market)
        {
            Data.Clear();

            string filePath = market switch
            {
                EMarket.ZZ500 => APath.GetZZ500Xlsx(),
                EMarket.SZ200 => APath.GetSZ200Xlsx(),
                EMarket.SZ100 => APath.GetSZ100Xlsx(),
                _ => throw new ArgumentException("Invalid market type")
            };

            using (var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read))
            {
                IWorkbook workbook = Path.GetExtension(filePath).Equals(".xlsx", StringComparison.OrdinalIgnoreCase) ? new XSSFWorkbook(stream) : new HSSFWorkbook(stream);
                ISheet worksheet = workbook.GetSheetAt(0);
                for (int i = 1; i <= worksheet.LastRowNum; i++)
                {
                    IRow row = worksheet.GetRow(i);
                    if (row == null) continue;
                    ZZ500Item item = new ZZ500Item();
                    item.StockCode = row.GetCell(1).StringCellValue.Trim().StartsWith("60") ? row.GetCell(1).StringCellValue.Trim() + ".SH" : row.GetCell(1).StringCellValue.Trim() + ".SZ";
                    item.StockName = row.GetCell(2).StringCellValue.Trim();
                    item.Industry = row.GetCell(5).StringCellValue.Trim();
                    item.Concepts = row.GetCell(7).StringCellValue.Trim().Split(";").ToList();
                    item.Volume = double.TryParse(row.GetCell(9).ToString()!.Trim(), out double volume) ? volume : 0;
                    Data.Add(item);
                }
            }
        }

        public static void WriteToConfig(EMarket market)
        {
            string ticketConfigPath = market switch
            {
                EMarket.ZZ500 => APath.GetZZ500TicketsConfig(),
                EMarket.SZ200 => APath.GetSZ200TicketsConfig(),
                EMarket.SZ100 => APath.GetSZ100TicketsConfig(),
                _ => throw new ArgumentException("Invalid market type")
            };

            using (StreamWriter writer = new StreamWriter(APath.GetZZ500DataConfig()))
            {
                foreach (var data in Data)
                {
                    writer.WriteLine(data.ToString());
                }
            }

            using (StreamWriter writer = new StreamWriter(ticketConfigPath))
            {
                foreach (var data in Data)
                {
                    writer.WriteLine(data.StockCode!);
                }
            }
        }
    }
}
