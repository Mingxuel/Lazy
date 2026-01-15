using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Globalization;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Data;
using System.Windows.Media;

namespace MarcoMVVM
{
    public class BindingManualMultiConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            Brush brush = Brushes.White;
            int.TryParse(values[0].ToString(), out int value1);
            int.TryParse(values[1].ToString(), out int value2);
            int value = value1 + value2;
            
            brush = value switch
            {
                <= 10 => Brushes.Green,
                <= 20 => Brushes.Blue,
                <= 30 => Brushes.Red,
                _ => Brushes.Black,
            };

            return brush;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            return null;
        }
    }
}