using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;

namespace MarcoMVVM
{
    /// <summary>
    /// CustomProperty.xaml 的交互逻辑
    /// </summary>
    public partial class CustomUC : UserControl
    {
        public CustomUC()
        {
            InitializeComponent();
        }

        public static readonly DependencyProperty TextValue1Property =
            DependencyProperty.Register(
                "TextValue1",                   // 属性名称
                typeof(string),                 // 属性类型
                typeof(CustomUC),          // 所有者类型
                new FrameworkPropertyMetadata(string.Empty, FrameworkPropertyMetadataOptions.BindsTwoWayByDefault)
            );

        public string TextValue1
        {
            get => (string)GetValue(TextValue1Property);
            set => SetValue(TextValue1Property, value);
        }

		public static readonly DependencyProperty TextValue2Property =
			DependencyProperty.Register(
				"TextValue2",                   // 属性名称
				typeof(string),                 // 属性类型
				typeof(CustomUC),          // 所有者类型
				new FrameworkPropertyMetadata(string.Empty, FrameworkPropertyMetadataOptions.BindsTwoWayByDefault)
			);

		public string TextValue2
		{
			get => (string)GetValue(TextValue2Property);
			set => SetValue(TextValue2Property, value);
		}

		public static readonly DependencyProperty ButtonCommandProperty =
			DependencyProperty.Register(
				nameof(ButtonCommand),
				typeof(ICommand),
				typeof(CustomUC),
				new PropertyMetadata(null));

		public ICommand ButtonCommand
		{
			get => (ICommand)GetValue(ButtonCommandProperty);
			set => SetValue(ButtonCommandProperty, value);
		}
	}
}
