using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

internal static class AppLauncher
{
    private const string AppUrl = "http://127.0.0.1:5080";

    [STAThread]
    private static void Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        Directory.SetCurrentDirectory(baseDir);
        string python = Path.Combine(baseDir, "runtime", "python.exe");
        string server = Path.Combine(baseDir, "run_server.py");
        if (!File.Exists(python) || !File.Exists(server))
        {
            MessageBox.Show(
                "Bản cài thiếu Python portable hoặc run_server.py. Vui lòng cài lại Highlight Video Studio.",
                "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        if (!ServerReady())
        {
            try
            {
                var info = new ProcessStartInfo
                {
                    FileName = python,
                    Arguments = "\"" + server + "\"",
                    WorkingDirectory = baseDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden,
                    RedirectStandardError = true
                };
                var process = new Process { StartInfo = info, EnableRaisingEvents = true };
                process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs args)
                {
                    if (String.IsNullOrWhiteSpace(args.Data)) return;
                    try { File.AppendAllText(Path.Combine(baseDir, "server_error.log"), args.Data + Environment.NewLine); }
                    catch { }
                };
                process.Start();
                process.BeginErrorReadLine();
            }
            catch (Exception ex)
            {
                MessageBox.Show("Không thể khởi động ứng dụng: " + ex.Message,
                    "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            DateTime deadline = DateTime.UtcNow.AddSeconds(30);
            while (DateTime.UtcNow < deadline && !ServerReady()) Thread.Sleep(350);
        }

        if (!ServerReady())
        {
            MessageBox.Show("Máy chủ không khởi động trong 30 giây. Hãy xem server_error.log trong thư mục cài đặt.",
                "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        try { Process.Start(new ProcessStartInfo(AppUrl) { UseShellExecute = true }); }
        catch (Exception ex)
        {
            MessageBox.Show("Ứng dụng đã chạy tại " + AppUrl + "\n\n" + ex.Message,
                "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
    }

    private static bool ServerReady()
    {
        try
        {
            var request = (HttpWebRequest)WebRequest.Create(AppUrl + "/api/system/info");
            request.Timeout = 700;
            request.ReadWriteTimeout = 700;
            using (var response = (HttpWebResponse)request.GetResponse())
                return (int)response.StatusCode >= 200 && (int)response.StatusCode < 500;
        }
        catch { return false; }
    }
}
