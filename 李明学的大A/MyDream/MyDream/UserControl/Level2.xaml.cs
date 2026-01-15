using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Navigation;
using System.Windows.Shapes;
using static System.Runtime.InteropServices.JavaScript.JSType;

namespace MyDream
{
    /// <summary>
    /// Interaction logic for Level2.xaml
    /// </summary>
    public partial class Level2 : UserControl
    {
        private const string _url = "https://www.iwencai.com/unifiedwap/result?w=";
        private static string _keydays_config = @"../../../../../Data/Config/KeyDays.config";
        private static string _keywords_config = @"../../../../../Data/Config/KeyWords.config";
        private List<string> _dates = new List<string>();
        private List<string> _keywords = new List<string>();

        [DllImport("user32.dll")]
        static extern bool OpenClipboard(IntPtr hWndNewOwner);

        [DllImport("user32.dll")]
        static extern bool CloseClipboard();

        public Level2()
        {
            InitializeComponent();
        }

        private void bt_0_0_Click(object sender, RoutedEventArgs e)
        {
            //2F
            string keyword = _keywords[0];
            tb_0_0.Text = Format(keyword, lb_0_0.SelectedIndex);
            Clipboard.SetText(tb_0_0.Text);
        }

        private void bt_0_1_Click(object sender, RoutedEventArgs e)
        {
            //2F+1
            if (OpenClipboard(IntPtr.Zero))
            {
                string keyword = _keywords[1];
                tb_0_1.Text = Format(keyword, lb_0_1.SelectedIndex);
                Clipboard.SetText(tb_0_1.Text);
            }
        }

        private void bt_0_2_Click(object sender, RoutedEventArgs e)
        {
            //2F+2
            string keyword = _keywords[2];
            tb_0_2.Text = Format(keyword, lb_0_2.SelectedIndex);
            Clipboard.SetText(tb_0_2.Text);
        }

        private void bt_1_0_Click(object sender, RoutedEventArgs e)
        {
            //2S
            string keyword = _keywords[3];
            tb_1_0.Text = Format(keyword, lb_1_0.SelectedIndex);
            Clipboard.SetText(tb_1_0.Text);
        }

        private void bt_1_1_Click(object sender, RoutedEventArgs e)
        {
            //2S+1
            string keyword = _keywords[4];
            tb_1_1.Text = Format(keyword, lb_1_1.SelectedIndex);
            Clipboard.SetText(tb_1_1.Text);
        }

        private void bt_1_2_Click(object sender, RoutedEventArgs e)
        {
            //2S+2
            string keyword = _keywords[5];
            tb_1_2.Text = Format(keyword, lb_1_2.SelectedIndex);
            Clipboard.SetText(tb_1_2.Text);
        }

        private void OpenWebPage()
        {
            try
            {
                string url = _url + Clipboard.GetText();
                Process.Start(new ProcessStartInfo(url)
                {
                    UseShellExecute = true
                });
            }
            catch
            {

            }
        }

        private string Format(string keyword, int index)
        {
            keyword = keyword.Replace("D-0", _dates[index++]);
            keyword = keyword.Replace("D-1", _dates[index++]);
            keyword = keyword.Replace("D-2", _dates[index++]);
            keyword = keyword.Replace("D-3", _dates[index++]);
            keyword = keyword.Replace("D-4", _dates[index++]);
            keyword = keyword.Replace("D-5", _dates[index++]);
            keyword = keyword.Replace("D-6", _dates[index++]);
            keyword = keyword.Replace("D-7", _dates[index++]);
            keyword = keyword.Replace("D-8", _dates[index++]);
            keyword = keyword.Replace("D-9", _dates[index++]);

            return keyword;
        }

        private void LoadClick(object sender, RoutedEventArgs e)
        {
            File.WriteAllText(_keydays_config, tb_days.Text);
            UpdateData();
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            string[] keywords = File.ReadAllText(_keywords_config).Split("\r\n");

            _keywords.Add(keywords[0].Replace("，", "，\r\n"));
            _keywords.Add(keywords[1].Replace("，", "，\r\n"));
            _keywords.Add(keywords[2].Replace("，", "，\r\n"));
            _keywords.Add(keywords[3].Replace("，", "，\r\n"));
            _keywords.Add(keywords[4].Replace("，", "，\r\n"));
            _keywords.Add(keywords[5].Replace("，", "，\r\n"));

            tb_0_0.Text = _keywords[0];
            tb_0_1.Text = _keywords[1];
            tb_0_2.Text = _keywords[2];
            tb_1_0.Text = _keywords[3];
            tb_1_1.Text = _keywords[4];
            tb_1_2.Text = _keywords[5];
            UpdateData();
        }

        private void UpdateData()
        {
            tb_days.Text = File.ReadAllText(_keydays_config);
            lb_0_0.Items.Clear();
            lb_0_1.Items.Clear();
            lb_0_2.Items.Clear();
            lb_1_0.Items.Clear();
            lb_1_1.Items.Clear();
            lb_1_2.Items.Clear();
            _dates.Clear();
            string[] dates = File.ReadAllText(_keydays_config).Split("\r\n");
            foreach (string date in dates)
            {
                _dates.Add(date.Trim());
                lb_0_0.Items.Add(date.Trim());
                lb_0_1.Items.Add(date.Trim());
                lb_0_2.Items.Add(date.Trim());
                lb_1_0.Items.Add(date.Trim());
                lb_1_1.Items.Add(date.Trim());
                lb_1_2.Items.Add(date.Trim());
            }
        }
    }
}