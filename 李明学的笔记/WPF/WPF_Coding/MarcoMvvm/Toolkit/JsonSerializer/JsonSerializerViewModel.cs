using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace MarcoMVVM
{
    public partial class JsonSerializerViewModel : ObservableObject
    {
        [ObservableProperty]
        public string name;

        [ObservableProperty]
        public string age;

        [ObservableProperty]
        public string password;

        [ObservableProperty]
        private string message;


        [RelayCommand]
        private void JsonSerializerClick()
        {
            var vm = new User() { Name = Name, Age = Age, Password = Password };
            Message = JsonSerializer.Serialize(vm);
        }
    }
}
