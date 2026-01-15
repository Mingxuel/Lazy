using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Controls;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MarcoMVVM
{
    internal class BindingManualValidationRuleViewModel : ViewModelBaseIError
    {
        // 验证方法
        private void ValidateProperty(string propertyName, object value)
        {
            // 清除该属性的现有错误
            if (_errors.ContainsKey(propertyName))
                _errors.Remove(propertyName);

            // 执行验证逻辑
            if (propertyName == nameof(ID))
            {
                IDError = "";
                if (string.IsNullOrEmpty(value as string))
                    AddError(propertyName, "用户名不能为空");
                else if ((value as string).Length < 3)
                    AddError(propertyName, "用户名长度不能少于3个字符");
                var errors = GetErrors(propertyName);
                foreach (string error in errors)
                {
                    IDError += error;
                }
            }

            // 通知错误已更改
            OnErrorsChanged(propertyName);
        }

        private string _id = "1234567890123";
        public string ID
        {
            get
            {
                return _id;
            }
            set
            {
                _id = value;
                OnPropertyChanged();
                ValidateProperty(nameof(ID), value);
            }
        }

        private string _idError = "";
        public string IDError
        {
            get
            {
                return _idError;
            }
            set
            {
                _idError = value;
                OnPropertyChanged();
                ValidateProperty(nameof(IDError), value);
            }
        }

        private string _name = "1234567890123";
        public string Name
        {
            get
            {
                return _name;
            }
            set
            {
                _name = value;
                OnPropertyChanged();
               ValidateProperty(nameof(Name), value);
            }
        }
    }
}
