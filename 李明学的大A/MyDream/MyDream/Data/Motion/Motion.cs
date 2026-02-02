using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    internal class Motion
    {
        public List<MotionItem> Data = new List<MotionItem>();

        public void Init()
        {
            Data.Clear();
            foreach (var datas in Strategy.Instance.DataTop.Values)
            {
                if (datas.Count == 0) continue;
                foreach (var data in datas)
                {
                    MotionItem item = new MotionItem();
                    item.Date = data.Date;
                    item.StockCode = data.StockCode;
                    item.StockName = data.StockName;
                    var record_1 = ZZ5001D.Instance.NextRecord(data.StockCode!, data.Date!, 1);
                    var record_2 = ZZ5001D.Instance.NextRecord(data.StockCode!, data.Date!, 2);
                    var record_3 = ZZ5001D.Instance.NextRecord(data.StockCode!, data.Date!, 3);
                    var record_4 = ZZ5001D.Instance.NextRecord(data.StockCode!, data.Date!, 4);
                    var record_5 = ZZ5001D.Instance.NextRecord(data.StockCode!, data.Date!, 5);
                    item.DAY1 = record_1 != null ? ((record_1.Close - record_1.PreClose) / record_1.PreClose).ToString("P2") : "";
                    item.DAY2 = record_2 != null ? ((record_2.Close - record_2.PreClose) / record_2.PreClose).ToString("P2") : "";
                    item.DAY3 = record_3 != null ? ((record_3.Close - record_3.PreClose) / record_3.PreClose).ToString("P2") : "";
                    item.DAY4 = record_4 != null ? ((record_4.Close - record_4.PreClose) / record_4.PreClose).ToString("P2") : "";
                    item.DAY5 = record_5 != null ? ((record_5.Close - record_5.PreClose) / record_5.PreClose).ToString("P2") : "";
                    Data.Add(item);
                }
            }
        }
    }
}
