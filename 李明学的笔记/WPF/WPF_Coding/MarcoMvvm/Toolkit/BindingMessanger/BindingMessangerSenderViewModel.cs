using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using CommunityToolkit.Mvvm.Messaging;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    public partial class BindingMessangerSenderViewModel : ObservableObject
    {
        [ObservableProperty]
        private string sendMessage = "";

        [ObservableProperty]
        private string receiveMessage = "";

        public BindingMessangerSenderViewModel() {
            
        }

        [RelayCommand]
        private void Send()
        {
            WeakReferenceMessenger.Default.Send(new MessageString(SendMessage));
        }
    }
}
