using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace MyDream
{
    public static class CallPythonAPI
    {
        private const string _file_runtime = @"../../../../../Miniqmt/src/RuntimeForCSharp.py";
        private const string _file_update = @"../../../../../Miniqmt/src/UpdateForCSharp.py";
        private const string _update_trading_dates = "--update_trading_dates";
        private const string _download_history_1d = "--download_history_1d";
        private const string _update_history_1d = "--update_history_1d";
        private const string _download_history_1m = "--download_history_1m";
        private const string _update_history_1m = "--update_history_1m";

        public static async Task<string?> UpdateTradingDatesAsync()
        {
            return await Task.Run(() => Call(_update_trading_dates));
        }

        public static async Task<string?> DownloadHistory1DAsync()
        {
            return await Task.Run(() => Call(_download_history_1d));
        }

        public static async Task<string?> UpdateHistory1DAsync()
        {
            return await Task.Run(() => Call(_update_history_1d));
        }

        public static async Task<string?> DownloadHistory1MAsync()
        {
            return await Task.Run(() => Call(_download_history_1m));
        }

        public static async Task<string?> UpdateHistory1MAsync()
        {
            return await Task.Run(() => Call(_update_history_1m));
        }

        public static void RunAsync(List<string> stock_list)
        {
            Task.Run(() =>
            {
                try
                {
                    Thread.CurrentThread.IsBackground = true;

                    var start_info = new ProcessStartInfo
                    {
                        FileName = "python",
                        Arguments = string.Format("{0} {1}", _file_runtime, string.Join("|", stock_list)),
                        RedirectStandardOutput = true,
                        UseShellExecute = false,
                        CreateNoWindow = true
                    };
                    var process = Process.Start(start_info);
                }
                catch (Exception e)
                {
                    Trace.WriteLine(e.Message);
                }
            });
        }

        private static string? Call(string param)
        {
            var start_info = new ProcessStartInfo
            {
                FileName = "python",
                Arguments = string.Format("{0} {1}", _file_update, param),
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };
            var process = Process.Start(start_info);
            var output = process?.StandardOutput.ReadToEnd();
            process?.WaitForExit();
            return output ?? null;
        }
    }
}
