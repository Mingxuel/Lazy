using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Messaging;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    public partial class BindingMessangerReceiverViewModel : ObservableObject
    {
        [ObservableProperty]
        private string receiveMessage = "";

        public BindingMessangerReceiverViewModel()
        {
            WeakReferenceMessenger.Default.Register<MessageString>(this, Receive);
        }

        private void Receive(object recipient, MessageString message)
        {
            ReceiveMessage = message.message;
        }
    }
}
