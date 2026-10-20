using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Text;

internal static class AppLauncher
{
    private static string appUrl;
    private static string appUrlFile;
    private static int appPort;
    private static Process ownedServer;
    private static Process embeddedWindow;
    private static Mutex instanceMutex;
    private static Icon appIcon;
    private static Icon smallAppIcon;

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(WindowVisitor visitor, IntPtr parameter);
    private delegate bool WindowVisitor(IntPtr window, IntPtr parameter);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int GetWindowText(IntPtr window, StringBuilder text, int count);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern IntPtr SendMessageTimeout(IntPtr window, uint message,
        IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);

    private static void ApplyApplicationIcon()
    {
        if (appIcon == null) return;
        EnumWindows(delegate(IntPtr window, IntPtr parameter)
        {
            var title = new StringBuilder(256);
            GetWindowText(window, title, title.Capacity);
            if (title.ToString() == "Highlight Video Studio - AI Shorts & Viral Clips Cutter")
            {
                ApplyWindowIcon(window);
            }
            return true;
        }, IntPtr.Zero);
    }

    private static void ApplyWindowIcon(IntPtr window)
    {
        if (appIcon == null || smallAppIcon == null) return;
        IntPtr result;
        SendMessageTimeout(window, 0x0080, new IntPtr(1), appIcon.Handle, 2, 200, out result);
        SendMessageTimeout(window, 0x0080, IntPtr.Zero, smallAppIcon.Handle, 2, 200, out result);
    }

    [STAThread]
    private static void Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        Directory.SetCurrentDirectory(baseDir);
        string iconFile = Path.Combine(baseDir, "app.ico");
        if (File.Exists(iconFile))
        {
            appIcon = new Icon(iconFile, new Size(48, 48));
            smallAppIcon = new Icon(iconFile, SystemInformation.SmallIconSize);
        }
        bool created;
        instanceMutex = new Mutex(true, @"Local\HighlightDesktopTest", out created);
        if (!created)
        {
            appUrlFile = Path.Combine(baseDir, "run", "desktop_url.txt");
            try { appUrl = File.ReadAllText(appUrlFile).Trim(); } catch { appUrl = null; }
            // A previous shell can outlive its server child after an abrupt
            // backend failure. Do not reopen its dead URL forever: reclaim
            // the stale shell and let a fresh instance acquire the mutex.
            if (!ServerReady())
            {
                int currentPid = Process.GetCurrentProcess().Id;
                foreach (Process other in Process.GetProcessesByName("Highlight_Desktop_Test"))
                {
                    if (other.Id == currentPid) continue;
                    try { other.Kill(); other.WaitForExit(1500); } catch { }
                    finally { other.Dispose(); }
                }
                try { instanceMutex.Close(); } catch { }
                Thread.Sleep(250);
                try
                {
                    Process.Start(new ProcessStartInfo
                    {
                        FileName = Application.ExecutablePath,
                        WorkingDirectory = baseDir,
                        UseShellExecute = true
                    });
                }
                catch { }
                return;
            }
            OpenBrowser();
            return;
        }

        appPort = PickFreeLoopbackPort();
        appUrl = "http://127.0.0.1:" + appPort;
        appUrlFile = Path.Combine(baseDir, "run", "desktop_url.txt");
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

        Directory.CreateDirectory(Path.GetDirectoryName(appUrlFile));
        File.WriteAllText(appUrlFile, appUrl);
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
            if (!String.IsNullOrWhiteSpace(appUrlFile) && File.Exists(appUrlFile)) File.Delete(appUrlFile);
        }
        catch { }
    }

    private static void OpenBrowser()
    {
        if (String.IsNullOrWhiteSpace(appUrl)) return;
        try
        {
            string chrome = FindChromeExecutable();
            if (!String.IsNullOrWhiteSpace(chrome))
            {
                embeddedWindow = Process.Start(new ProcessStartInfo
                {
                    FileName = chrome,
                    // Use the user's normal Chrome profile so its existing YouTube
                    // session is visible to the app. Do not silently switch to Edge
                    // or create a second, empty browser profile.
                    Arguments = "--app=\"" + appUrl + "\" --profile-directory=Default --no-first-run --no-default-browser-check",
                    WorkingDirectory = AppDomain.CurrentDomain.BaseDirectory,
                    UseShellExecute = true
                });
                return;
            }
            MessageBox.Show("Google Chrome was not found. Please install Chrome to open the desktop app.",
                "Highlight Desktop Test", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
        catch (Exception ex)
        {
            MessageBox.Show("Application is available at " + appUrl + "\n\n" + ex.Message,
                "Highlight Desktop Test", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
    }

    private static string FindChromeExecutable()
    {
        string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        string programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        string programFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        string[] candidates = {
            Path.Combine(programFilesX86, "Google", "Chrome", "Application", "chrome.exe"),
            Path.Combine(programFiles, "Google", "Chrome", "Application", "chrome.exe"),
            Path.Combine(local, "Google", "Chrome", "Application", "chrome.exe")
        };
        foreach (string candidate in candidates) if (File.Exists(candidate)) return candidate;
        return null;
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
            if (appIcon != null) Icon = appIcon;
            var iconTimer = new System.Windows.Forms.Timer { Interval = 2000 };
            iconTimer.Tick += delegate { ApplyApplicationIcon(); };
            iconTimer.Start();
            FormClosed += delegate { iconTimer.Dispose(); };
            var healthTimer = new System.Windows.Forms.Timer { Interval = 2500 };
            healthTimer.Tick += delegate
            {
                if (ownedServer != null && ownedServer.HasExited)
                {
                    healthTimer.Stop();
                    Close();
                }
            };
            healthTimer.Start();
            FormClosed += delegate { healthTimer.Dispose(); };
            Text = "Highlight Desktop Test v1.3.4";
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
            Shown += delegate { Hide(); };
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            StopOwnedServer();
            base.OnFormClosing(e);
        }
    }
}

