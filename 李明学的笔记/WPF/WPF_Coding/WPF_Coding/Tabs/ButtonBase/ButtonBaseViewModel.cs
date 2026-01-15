using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using WPF_Coding.Base;

namespace WPF_Coding.Tabs.ButtonBase
{
    class Member : ObservableObject
    {
        private string _name = "";
        public string Name
        {
            get { return _name; }
            set
            {
                _name = value;
                OnPropertyChanged();
            }
        }

        private string _id = "";
        public string ID
        {
            get { return _id; }
            set
            {
                _id = value;
                OnPropertyChanged();
            }
        }
    }

    class ButtonBaseViewModel : ObservableObject //INotifyPropertyChanged
    {
        #region Button
        private double _width = 100;
        public double ButtonWidth
        {
            get { return _width; }
            set
            {
                if (_width != value)
                {
                    _width = value;
                    OnPropertyChanged();
                }
            }
        }

        public double _height = 100;
        public double Height
        {
            get { return _height; }
            set {
                _height = value;
                OnPropertyChanged();
            }
        }

        public ObservableCollection<Member> Members { get; set; } = new()
        {
            new Member() { Name = "PS", ID="1" }
        };

/*      public event PropertyChangedEventHandler? PropertyChanged;
        protected virtual void OnPropertyChanged([CallerMemberName]string? propertyName=null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
*/
        #endregion
    }
}
