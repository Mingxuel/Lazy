// 可验证的按钮模型
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using System.Windows.Input;

namespace MarcoMVVM
{
    public partial class ButtonModel : ObservableObject
    {
        [ObservableProperty]
        private string? content;
        public ICommand? ButtonClick { get; set; }
    }

    public class Config 
    {
        public static List<string> ManualButtons = new List<string>() {
            "UC_BindingManualCommand",
            "UC_BindingManualData",
            "UC_BindingStatic" ,
            "UC_BindingAnotherControl",
            "UC_BindingRelativeSource",
            "UC_BindingManualCollection",
            "UC_BindingManualConverter",
            "UC_BindingManualMultiConverter",
            "UC_BindingManualValidationRule",
            "UC_BindingEventCommand",
        };

        public static List<string> ToolkitButtons = new List<string>() {
            "UC_BindingData",
            "UC_BindingCommand",
            "UC_BindingMessanger",
            "UC_BindingMessangerProperty",
            "UC_BindingMessangerRequest",
            "UC_Validation",
            "UC_JsonSerializer",
        };

        public static List<string> WPFButtons = new List<string>() {
            "CustomPropertyMain",
			"NavigationMain",
		};
    }
}
