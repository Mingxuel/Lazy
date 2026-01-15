using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    internal class BindingManualDataViewModel : INotifyPropertyChanged
    {
        private string _marcoInput = "";
        public string MarcoInput
        {
            get
            {
                return _marcoInput;
            }
            set
            {
                _marcoInput = value;
                MarcoOutput = value;
                OnPropertyChanged();
            }
        }

        private string _marcoOutput = "";
        public string MarcoOutput
        {
            get
            {
                return _marcoOutput;
            }
            set
            {
                _marcoOutput = value;
                OnPropertyChanged();
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;
        protected virtual void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
