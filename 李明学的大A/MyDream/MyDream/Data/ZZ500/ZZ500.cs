using NPOI.HSSF.UserModel;
using NPOI.SS.UserModel;
using NPOI.XSSF.UserModel;
using System.IO;

namespace MyDream
{
    public static class ZZ500
    {
        public static List<ZZ500Item> Data { get; } = new List<ZZ500Item>();

        public static void ReadFromXlsx()
        {
            Data.Clear();

            using (var stream = new FileStream(APath.GetZZ500Xlsx(), FileMode.Open, FileAccess.Read))
            {
                IWorkbook workbook = Path.GetExtension(APath.GetZZ500Xlsx()).Equals(".xlsx", StringComparison.OrdinalIgnoreCase) ? new XSSFWorkbook(stream) : new HSSFWorkbook(stream);
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
                    Data.Add(item);
                }
            }
        }

        public static void WriteToConfig()
        {
            using (StreamWriter writer = new StreamWriter(APath.GetZZ500DataConfig()))
            {
                foreach (var data in Data)
                {
                    writer.WriteLine(data.ToString());
                }
            }

            using (StreamWriter writer = new StreamWriter(APath.GetZZ500TicketConfig()))
            {
                foreach (var data in Data)
                {
                    writer.WriteLine(data.StockCode!);
                }
            }
        }
    }
}
