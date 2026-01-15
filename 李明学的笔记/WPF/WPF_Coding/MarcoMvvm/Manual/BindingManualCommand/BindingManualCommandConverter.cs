using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Data;
using System.Windows.Media;

namespace MarcoMVVM
{
    internal class BindingManualCommandConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            BindingManualCommandModel.UserInfo userInfo = new BindingManualCommandModel.UserInfo();
            userInfo.ID = values[0].ToString();
            userInfo.NAME = values[1].ToString();
            
            return userInfo;
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            return null;
        }
    }
}
