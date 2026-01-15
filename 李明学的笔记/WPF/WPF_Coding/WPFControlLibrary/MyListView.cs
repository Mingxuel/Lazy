using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Controls;
using System.Windows;

namespace WPFControlLibrary
{
    public class MyListView : ListView
    {
        // 静态构造函数，用于注册元数据
        static MyListView()
        {
            DefaultStyleKeyProperty.OverrideMetadata(typeof(MyListView), new FrameworkPropertyMetadata(typeof(MyListView)));
        }
    }
}
