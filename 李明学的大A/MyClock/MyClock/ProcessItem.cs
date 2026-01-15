using System.ComponentModel;
using System.Windows.Media;

namespace MyClock
{
    /// <summary>
    /// 矩形数据模型（新增IsSolid标识）
    /// </summary>
    public class ProcessItem
    {
        public int Id { get; set; }
        public int IsSolid { get; set; } = 1;
        public double Width { get; set; } = 4;
        public double Height { get; set; } = 4;
        public double StrokeThickness { get; set; } = 0;
        public Brush HollowStroke => new SolidColorBrush(Color.FromRgb(20, 20, 20));
        public Brush HollowFill => new SolidColorBrush(Color.FromRgb(20, 20, 20));
        public Brush SolidStroke => new SolidColorBrush(Color.FromRgb(255, 128, 0));
        public Brush SolidFill => new SolidColorBrush(Color.FromRgb(255, 128, 0));
        public Brush SolidBiddingStroke => Brushes.Red;
        public Brush SolidBiddingFill => Brushes.Red;
    }
}