using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;

namespace MarcoMVVM
{
    public class BindingEventCommandViewModel : ViewModelBase
    {
        public ICommand TextClickCommand { get; }
        public BindingEventCommandViewModel()
        {
            TextClickCommand = new RelayTemplateCommand<string>
            (
                param => TextClick(param)
            );
        }

        private void TextClick(string text)
        {
            MessageBox.Show(text);
        }
    }
}
