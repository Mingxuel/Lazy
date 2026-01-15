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
    public partial class TaskObjectViewModel : ObservableObject
    {
        [ObservableProperty]
        private string id = "10086";

        [ObservableProperty]
        private string title = "Marco";

        private TaskNotifier? changeTitleRequest;

        public Task? ChangeTitleRequest
        {
            get => changeTitleRequest;
            set => SetPropertyAndNotifyOnCompletion(ref changeTitleRequest, value);
        }

        [RelayCommand]
        private void ChangeTitle()
        {
            ChangeTitleRequest = Task.Delay(2000).ContinueWith(_ => Title = "Hello Marco");
        }
    }
}
