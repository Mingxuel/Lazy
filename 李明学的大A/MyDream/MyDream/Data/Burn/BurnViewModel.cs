using CommunityToolkit.Mvvm.ComponentModel;
using MathNet.Numerics.Distributions;
using Newtonsoft.Json.Linq;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
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
        private DrawingImage? burnAll;

        [ObservableProperty]
        private ObservableCollection<BurnChartItem> burnChart = new ObservableCollection<BurnChartItem>();

        public void UpdateBurn()
        {
            burn.Update();
            BurnAll = Draw(burn.BurnAll);

            BurnChart.Clear();
            foreach (var item in burn.BurnChart)
            {
                BurnChart.Add(item);
            }
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
