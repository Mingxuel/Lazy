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
        public double Value { get; set; } = 0.0;
        public Brush Brush
        {
            get
            {
                double new_value = Value - 1.0;
                int ratio = 450 * 3;
                if (new_value > 0.0)
                {
                    double value = new_value * ratio;
                    if (value > 255) value = 255;
                    return new SolidColorBrush(Color.FromRgb((byte)value, 0, 0));
                }
                else if (new_value < 0.0)
                {
                    double value = Math.Abs(new_value * ratio);
                    if (value > 255) value = 255;
                    return new SolidColorBrush(Color.FromRgb(0, (byte)value, 0));
                }
                else
                {
                    return new SolidColorBrush(Color.FromRgb(0, 0, 0));
                }
            }
        }
    }
}
