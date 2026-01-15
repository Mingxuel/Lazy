using System;
using System.Globalization;
using System.Windows.Data;

namespace MyDream
{
    /// <summary>
    /// Double转保留符号位的00.00%格式字符串转换器
    /// </summary>
    public class StringToPercentStringConverter : IValueConverter
    {
        /// <summary>
        /// 正向转换（Double → String）
        /// </summary>
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            // 空值判断或类型不匹配判断
            if (value == null || !(value is string stringValue))
            {
                return "+00.00%"; // 默认返回零值格式
            }

            var doubleValue = double.Parse(stringValue) / 100.0;
            // 核心格式化逻辑，与纯C#代码一致
            return doubleValue.ToString("+00.00%;-00.00%;+00.00%", culture);
        }

        /// <summary>
        /// 反向转换（String → Double），此处无需实现（绑定为OneWay时）
        /// </summary>
        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException("反向转换（字符串转Double）暂不支持");
        }
    }
}