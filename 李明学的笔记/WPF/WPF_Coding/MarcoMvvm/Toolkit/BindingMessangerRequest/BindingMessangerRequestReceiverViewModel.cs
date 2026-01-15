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
    public partial class BindingMessangerRequestReceiverViewModel : ObservableRecipient, IRecipient<RequestMessage<string>>
    {
        [ObservableProperty]
        private string receiveMessage = "";

        public BindingMessangerRequestReceiverViewModel()
        {
            IsActive = true;
        }

        public void Receive(RequestMessage<string> message)
        {
            ReceiveMessage = "Hello World";
            message.Reply(ReceiveMessage);
        }
    }
}
