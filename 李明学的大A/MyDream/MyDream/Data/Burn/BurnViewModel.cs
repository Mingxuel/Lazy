using CommunityToolkit.Mvvm.ComponentModel;
using MathNet.Numerics.Distributions;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Media;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        private const double CellSizeWidth = 2.85;
        private Burn burn = new Burn();

        [ObservableProperty]
        private DrawingImage? burn2024;

        [ObservableProperty]
        private DrawingImage? burn2025;

        [ObservableProperty]
        private DrawingImage? burn2026;

        [ObservableProperty]
        private DrawingImage? burn2027;

        [ObservableProperty]
        private DrawingImage? burn2028;

        [ObservableProperty]
        private DrawingImage? burn2029;

        [ObservableProperty]
        private DrawingImage? burn2030;

        public void UpdateBurn()
        {
            burn.Update();
            Burn2024 = Draw(burn.Burn2024);
            Burn2025 = Draw(burn.Burn2025);
            Burn2026 = Draw(burn.Burn2026);
            Burn2027 = Draw(burn.Burn2027);
            Burn2028 = Draw(burn.Burn2028);
            Burn2029 = Draw(burn.Burn2029);
            Burn2030 = Draw(burn.Burn2030);
        }

        private DrawingImage Draw(List<List<BurnItem>> item)
        {
            var drawingVisual = new DrawingVisual();
            using (var dc = drawingVisual.RenderOpen())
            {
                foreach (var row in item)
                {
                    double y = item.IndexOf(row);
                    foreach (var col in row)
                    {
                        double x = row.IndexOf(col) * CellSizeWidth;
                        dc.DrawRectangle(col.Brush, null, new Rect(x, y, CellSizeWidth, 1.0));
                    }
                }
            }

            var drawingGroup = new DrawingGroup();
            drawingGroup.Children.Add(drawingVisual.Drawing);
            return new DrawingImage(drawingGroup);
        }
    }
}
