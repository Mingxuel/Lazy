using NPOI.SS.Formula.Functions;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Media;

namespace MyDream
{
    public class BurnItem
    {
        public BurnItem(int index, double value)
        {
            Index = index;
            Value = value;
        }

        public int Index { get; set; }
        public double Value { get; set; } = -100.0;
        public Brush Brush
        {
            get
            {
                if (Value > 0.0)
                {
                    return new SolidColorBrush(Color.FromRgb(255, 0, 0));
                }
                else if (Value < 0.0)
                {
                    return new SolidColorBrush(Color.FromRgb(0, 255, 0));
                }

                return new SolidColorBrush(Color.FromRgb(0, 0, 0));
            }
        }
    }
}
 