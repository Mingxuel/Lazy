using CommunityToolkit.Mvvm.ComponentModel;
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public partial class BoardViewModel : ObservableObject
    {
        [ObservableProperty]
        private ObservableCollection<MotionItem?> motionData = new ObservableCollection<MotionItem?>();

        Motion motion = new Motion();

        private void UpdateMotion()
        {
            motion.Init();
            foreach (var item in motion.Data)
            {
                MotionData.Add(item);
            }
        }
    }
}
