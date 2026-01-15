using Microsoft.Web.WebView2.Core;
using Newtonsoft.Json;
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using Windows.UI.WebUI;

namespace MyDream
{
    /// <summary>
    /// Board.xaml 的交互逻辑
    /// </summary>
    public partial class Board : UserControl
    {
        public Board()
        {
            InitializeComponent();
            this.DataContext = new BoardViewModel();
        }
    }
}