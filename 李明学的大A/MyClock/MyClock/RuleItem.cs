using CommunityToolkit.Mvvm.ComponentModel;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics.Eventing.Reader;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Media;

namespace MyClock
{
    public partial class RuleItem : ObservableObject
    {
        [ObservableProperty]
        private int id;

        partial void OnIdChanged(int value)
        {
            OnPropertyChanged(nameof(Stroke));
            OnPropertyChanged(nameof(Fill));
        }

        public double Width { get; set; } = 2.9;
        public double Height { get; set; } = 9;
        public double StrokeThickness { get; set; } = 0;
        public Brush Stroke
        {
            get
            {
                if (Id == -1)
                {
                    return Brushes.Transparent;
                }
                else
                {
                    byte green = (byte)(128 - Id);
                    return new SolidColorBrush(Color.FromRgb(255, green, 0));
                }
            }
        }
        public Brush Fill
        {
            get
            {
                if (Id == -1)
                {
                    return Brushes.Transparent;
                }
                else
                {
                    byte green = (byte)(128 - Id);
                    return new SolidColorBrush(Color.FromRgb(255, green, 0));
                }
            }
        }
    }
}
