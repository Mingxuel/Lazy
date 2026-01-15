using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Text;
using System.Threading.Tasks;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using static System.Net.Mime.MediaTypeNames;

namespace MarcoMVVM
{
    public partial class BindingCommandViewModel : ObservableObject
    {
        [ObservableProperty]
        [NotifyPropertyChangedFor(nameof(Group1_Out))]
        private string group1_In = "Hello World!";

        public string Group1_Out => $"{Group1_In}";

        [ObservableProperty]
        private string group2_In = "Hello World!";

        public string Group2_Out => $"{Group2_In}";


        partial void OnGroup2_InChanged(string value)
        {
            OnPropertyChanged(nameof(Group2_Out));
        }

        [ObservableProperty]
        [NotifyCanExecuteChangedFor(nameof(SyncClickCommand))]
        [NotifyCanExecuteChangedFor(nameof(AsyncClickCommand))]
        [NotifyCanExecuteChangedFor(nameof(AsyncContinueClickCommand))]
        private bool isEnabled = false;

        [RelayCommand(CanExecute =nameof(CanSyncClick))]
        private void SyncClick(bool IsEnabled)
        {
            if (Group1_In == "Goobye World!")
            {
                Group1_In = "Hello World!";
            }
            else
            {
                Group1_In = "Goobye World!";
            }
        }

        //[RelayCommand(CanExecute = nameof(CanAsyncClick))]
        //private async Task AsyncClick()
        //{
        //    await Task.Delay(2000);
        //    if (Group2_In == "Goobye World!")
        //    {
        //        Group2_In = "Hello World!";
        //    }
        //    else
        //    {
        //        Group2_In = "Goobye World!";
        //    }
        //}

        //绑定Can函数或者直接绑定属性也是可以的
        [RelayCommand(CanExecute = nameof(IsEnabled), IncludeCancelCommand =true)]
        private async Task AsyncClick(CancellationToken token)
        {
            try
            {
                await Task.Delay(2000, token);
                if (Group2_In == "Goobye World!")
                {
                    Group2_In = "Hello World!";
                }
                else
                {
                    Group2_In = "Goobye World!";
                }
            }
            catch(OperationCanceledException)
            {

            }
        }

 

        [RelayCommand(CanExecute = nameof(IsEnabled), AllowConcurrentExecutions =true)]
        private async Task AsyncContinueClick()
        {
            await Task.Delay(2000);
            if (Group2_In == "Goobye World!")
            {
                Group2_In = "Hello World!";
            }
            else
            {
                Group2_In = "Goobye World!";
            }
        }

        private bool CanSyncClick() => IsEnabled;
        private bool CanAsyncClick() => IsEnabled;
    }
}
