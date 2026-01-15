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
    public class BindingManualConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            Brush brush = Brushes.White;
            if (value != null && int.TryParse(value.ToString(), out int size))
            {
                brush = size switch
                {
                    <= 10 => Brushes.Green,
                    <= 20 => Brushes.Blue,
                    <= 30 => Brushes.Red,
                    _ => Brushes.Black,
                };
            }

            return brush;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            return null;
        }
    }
}