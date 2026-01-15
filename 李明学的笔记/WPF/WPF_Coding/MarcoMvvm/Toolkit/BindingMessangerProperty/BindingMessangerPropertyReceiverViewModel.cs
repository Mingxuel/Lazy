using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Messaging;
using CommunityToolkit.Mvvm.Messaging.Messages;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MarcoMVVM
{
    public partial class BindingMessangerPropertyReceiverViewModel : ObservableObject
    {
        [ObservableProperty]
        private string receiveMessageA = "";
        [ObservableProperty]
        private string receiveMessageB = "";

        private string tokenA = "A";
        private string tokenB = "B";

        public BindingMessangerPropertyReceiverViewModel()
        {
            WeakReferenceMessenger.Default.Register<PropertyChangedMessage<string>, string>(this, tokenA, ReceiveA);
            WeakReferenceMessenger.Default.Register<PropertyChangedMessage<string>, string>(this, tokenB, ReceiveB);
        }

        private void ReceiveA(object recipient, PropertyChangedMessage<string> message)
        {
            ReceiveMessageA = message.NewValue;
        }
        private void ReceiveB(object recipient, PropertyChangedMessage<string> message)
        {
            ReceiveMessageB = message.NewValue;
        }
    }
}
