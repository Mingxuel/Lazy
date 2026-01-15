using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;

namespace MarcoMVVM
{
    public class BindingManualCommandViewModel
    {
        public ICommand NoParamCommand { get; }
        public ICommand ParamCommand { get; }
        public ICommand TemplateParamCommand {  get; }
        public ICommand TemplateMultiParamCommand { get; }

        public string ID { get; set; }
        public string NAME { get; set; }

        public BindingManualCommandViewModel()
        {
            // 命令1：无参数，始终可执行
            NoParamCommand = new RelayCommand(
                param => NoParamFunc()  // 执行逻辑
            );

            // 命令2：带参数，根据条件决定是否可执行
            ParamCommand = new RelayCommand(
                param => ParamFunc(param),  // 执行逻辑
                param => CanParamFunc(param));

            TemplateParamCommand = new RelayTemplateCommand<string>(
                param => TemplateParamFunc(param)
            );
            TemplateMultiParamCommand = new RelayTemplateCommand<BindingManualCommandModel.UserInfo>(
                param => TemplateMultiParamFunc(param)
            );
        }

        private void NoParamFunc()
        {
            ID = "Hello World"; //MarcoInput因为没有双向绑定，因此不会在UI上体现
            MessageBox.Show($"{ID}");
        }

        private void ParamFunc(object param)
        {
            MessageBox.Show($"{param}");
        }

        private bool CanParamFunc(object param)
        {
            // 判断是否可以删除
            return param != null && !string.IsNullOrEmpty(param.ToString());
        }

        private void TemplateParamFunc(string param)
        {
            MessageBox.Show($"{param}");
        }

        private void TemplateMultiParamFunc(BindingManualCommandModel.UserInfo param)
        {
            MessageBox.Show($"ID={param.ID} NAME={param.NAME}");
        }
    }
}
