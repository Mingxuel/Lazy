using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Controls;

namespace MarcoMVVM
{
    class NameValidationRule : ValidationRule
    {
        public override ValidationResult Validate(object value, CultureInfo cultureInfo)
        {
            var length = value.ToString().Length;
            if (length >=2 && length <=10)
            {
                return new ValidationResult(true, "");
            }

            return new ValidationResult(false, "用户名长度为2-10");
        }
    }
}
