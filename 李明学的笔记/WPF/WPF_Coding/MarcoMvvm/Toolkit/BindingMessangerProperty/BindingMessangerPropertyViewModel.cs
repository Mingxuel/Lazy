using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace MarcoMVVM
{
    public partial class BindingMessangerPropertyViewModel : ObservableObject
    {
        [ObservableProperty]
        private string id = "";

        [ObservableProperty]
        private string name = "";

        [RelayCommand]
        private void ButtonClick()
        {
            Id = Name;
        }
    }
}
