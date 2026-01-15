using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Input;
using System.Windows;
using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using System.Diagnostics.Metrics;
using CommunityToolkit.Mvvm.Input;
using System.Reflection;
using System.Windows.Media;
using System.Windows.Controls;

namespace MarcoMVVM
{
    public partial class MainWindowViewModel : ObservableObject
    {
        [ObservableProperty]
        private ObservableCollection<ButtonModel> manualButtons = new ObservableCollection<ButtonModel>();
        [ObservableProperty]
        private ObservableCollection<ButtonModel> toolkitButtons = new ObservableCollection<ButtonModel>();
        [ObservableProperty]
        private ObservableCollection<ButtonModel> wPFButtons = new ObservableCollection<ButtonModel>();

        [ObservableProperty]
        private UserControl? currentContent;

        [RelayCommand]
        public void Window_Loaded()
        {
            foreach(var content in Config.ManualButtons)
            {
                var button = new ButtonModel
                {
                    Content = content,
                    ButtonClick = new RelayCommand<object>(param => ButtonClickCommand(param))
                };
                ManualButtons.Add(button);
            }
            foreach (var content in Config.ToolkitButtons)
            {
                var button = new ButtonModel
                {
                    Content = content,
                    ButtonClick = new RelayCommand<object>(param => ButtonClickCommand(param))
                };
                ToolkitButtons.Add(button);
            }
            foreach (var content in Config.WPFButtons)
            {
                var button = new ButtonModel
                {
                    Content = content,
                    ButtonClick = new RelayCommand<object>(param => ButtonClickCommand(param))
                };
                WPFButtons.Add(button);
            }
        }

        public void ButtonClickCommand(object? buttonName)
        {
            if (buttonName == null) return;
            Type? type = Type.GetType("MarcoMVVM." + buttonName.ToString());
            if (type == null) return;
            object? control = Activator.CreateInstance(type);
            if (control is UserControl) CurrentContent = (UserControl)control;
        }
    }
}
