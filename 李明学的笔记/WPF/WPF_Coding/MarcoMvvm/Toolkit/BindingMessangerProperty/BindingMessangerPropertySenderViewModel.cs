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
    public partial class BindingMessangerPropertySenderViewModel : ObservableObject
    {
        [ObservableProperty]
        private bool isTokenAEnabled;

        [ObservableProperty]
        private bool isTokenBEnabled;

        private string sendMessage = "";
        public string SendMessage
        {
            get { return sendMessage; }
            set
            {
                if (SetProperty(ref sendMessage, value))
                {
                    if (IsTokenAEnabled && !IsTokenBEnabled)
                    {
                        WeakReferenceMessenger.Default.Send(new PropertyChangedMessage<string>(this, nameof(SendMessage), default, "A "+value), "A");
                    }
                    else if (!IsTokenAEnabled && IsTokenBEnabled)
                    {
                        WeakReferenceMessenger.Default.Send(new PropertyChangedMessage<string>(this, nameof(SendMessage), default, "B " + value), "B");
                    }
                    else if (IsTokenAEnabled && IsTokenBEnabled)
                    {
                        WeakReferenceMessenger.Default.Send(new PropertyChangedMessage<string>(this, nameof(SendMessage), default, "A " + value), "A");
                        WeakReferenceMessenger.Default.Send(new PropertyChangedMessage<string>(this, nameof(SendMessage), default, "B " + value), "B");
                    }
                }
            }
        }
    }
}
