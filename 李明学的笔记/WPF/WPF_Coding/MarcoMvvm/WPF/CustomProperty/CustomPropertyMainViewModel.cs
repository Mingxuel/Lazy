using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    public partial class CustomPropertyMainViewModel : ObservableObject
    {
        [ObservableProperty]
        private string value11;
		[ObservableProperty]
		private string value12;
		[ObservableProperty]
		private string value21;
		[ObservableProperty]
		private string value22;

		[RelayCommand]
        private void Click1()
        {
            Value11 = "Fuck You 11";
			Value12 = "Fuck You 12";
		}
		[RelayCommand]
		private void Click2()
		{
			Value21 = "Fuck You 21";
			Value22 = "Fuck You 22";
		}
	}
}
