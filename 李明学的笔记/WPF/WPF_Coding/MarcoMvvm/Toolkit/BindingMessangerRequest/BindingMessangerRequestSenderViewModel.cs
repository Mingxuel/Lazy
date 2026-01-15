using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using CommunityToolkit.Mvvm.Messaging;
using CommunityToolkit.Mvvm.Messaging.Messages;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    public partial class BindingMessangerRequestSenderViewModel : ObservableObject
    {
        [ObservableProperty]
        private string sendMessage = "";

        [ObservableProperty]
        private string receiveMessage = "";

        public BindingMessangerRequestSenderViewModel() {
            
        }

        [RelayCommand]
        private void Send()
        {
            var res = WeakReferenceMessenger.Default.Send(new RequestMessage<string>());
            ReceiveMessage = res.Response;
        }
    }
}
