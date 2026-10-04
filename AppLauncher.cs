using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;

internal static class AppLauncher
{
    private static string appUrl;
    private static int appPort;
    private static Process ownedServer;
    private static Mutex instanceMutex;

    [STAThread]
    private static void Main()
    {
        bool created;
        instanceMutex = new Mutex(true, @"Local\HighlightDesktopTest", out created);
        if (!created)
        {
            OpenBrowser();
            return;
        }

        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        Directory.SetCurrentDirectory(baseDir);
        appPort = PickFreeLoopbackPort();
        appUrl = "http://127.0.0.1:" + appPort;
        string python = Path.Combine(baseDir, "runtime", "python.exe");
        string server = Path.Combine(baseDir, "run_server.py");
        if (!File.Exists(python) || !File.Exists(server))
        {
            MessageBox.Show("The desktop-test package is incomplete. Reinstall Highlight Desktop Test.",
                "Highlight Desktop Test", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        Application.ApplicationExit += delegate { StopOwnedServer(); };
        AppDomain.CurrentDomain.ProcessExit += delegate { StopOwnedServer(); };

        if (!ServerReady() && !StartServer(python, server, baseDir)) return;

        DateTime deadline = DateTime.UtcNow.AddSeconds(120);
        while (DateTime.UtcNow < deadline && !ServerReady())
        {
            if (ownedServer != null && ownedServer.HasExited) break;
            Thread.Sleep(400);
        }

        if (!ServerReady())
        {
            StopOwnedServer();
            MessageBox.Show("The local server did not become ready. See server_error.log in the install directory.",
                "Highlight Desktop Test", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        OpenBrowser();
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new LauncherForm());
    }

    private static bool StartServer(string python, string server, string baseDir)
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
                RedirectStandardError = true,
                RedirectStandardOutput = true
            };
            info.EnvironmentVariables["HIGHLIGHT_BIND_HOST"] = "127.0.0.1";
            info.EnvironmentVariables["HIGHLIGHT_PORT"] = appPort.ToString();
            info.EnvironmentVariables["BUILD_CHANNEL"] = "desktop-test";
            ownedServer = new Process { StartInfo = info, EnableRaisingEvents = true };
            DataReceivedEventHandler log = delegate(object sender, DataReceivedEventArgs args)
            {
                if (String.IsNullOrWhiteSpace(args.Data)) return;
                try { File.AppendAllText(Path.Combine(baseDir, "server_error.log"), args.Data + Environment.NewLine); } catch { }
            };
            ownedServer.ErrorDataReceived += log;
            ownedServer.OutputDataReceived += log;
            ownedServer.Start();
            ownedServer.BeginErrorReadLine();
            ownedServer.BeginOutputReadLine();
            return true;
        }
        catch (Exception ex)
        {
            MessageBox.Show("Cannot start the local application: " + ex.Message,
                "Highlight Desktop Test", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return false;
        }
    }

    private static void StopOwnedServer()
    {
        try
        {
            if (ownedServer != null && !ownedServer.HasExited)
            {
                ownedServer.CloseMainWindow();
                if (!ownedServer.WaitForExit(1500)) ownedServer.Kill();
            }
        }
        catch { }
    }

    private static void OpenBrowser()
    {
        if (String.IsNullOrWhiteSpace(appUrl)) return;
        try { Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true }); }
        catch (Exception ex)
        {
            MessageBox.Show("Application is available at " + appUrl + "\n\n" + ex.Message,
                "Highlight Desktop Test", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
    }

    private static bool ServerReady()
    {
        try
        {
            if (String.IsNullOrWhiteSpace(appUrl)) return false;
            var request = (HttpWebRequest)WebRequest.Create(appUrl + "/api/system/info");
            request.Timeout = 800;
            request.ReadWriteTimeout = 800;
            using (var response = (HttpWebResponse)request.GetResponse())
                return response.StatusCode == HttpStatusCode.OK;
        }
        catch { return false; }
    }

    private static int PickFreeLoopbackPort()
    {
        for (int attempt = 0; attempt < 12; attempt++)
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            try
            {
                listener.Start();
                int port = ((IPEndPoint)listener.LocalEndpoint).Port;
                if (port != 5080) return port;
            }
            finally { listener.Stop(); }
        }
        throw new InvalidOperationException("Unable to reserve a safe loopback port.");
    }

    private sealed class LauncherForm : Form
    {
        internal LauncherForm()
        {
            Text = "Highlight Desktop Test v1.1.9";
            Width = 410;
            Height = 175;
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            MinimizeBox = true;
            var label = new Label { Left = 24, Top = 20, Width = 350, Height = 42, Text = "Highlight Desktop Test is running locally.\nClose this window to stop its backend." };
            var open = new Button { Left = 24, Top = 78, Width = 170, Height = 36, Text = "Open application" };
            var stop = new Button { Left = 204, Top = 78, Width = 170, Height = 36, Text = "Stop and exit" };
            open.Click += delegate { OpenBrowser(); };
            stop.Click += delegate { Close(); };
            Controls.Add(label);
            Controls.Add(open);
            Controls.Add(stop);
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            StopOwnedServer();
            base.OnFormClosing(e);
        }
    }
}

