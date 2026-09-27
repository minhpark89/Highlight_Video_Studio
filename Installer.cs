using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

internal sealed class InstallerForm : Form
{
    private readonly TextBox destination = new TextBox();
    private readonly ProgressBar progress = new ProgressBar();
    private readonly Label status = new Label();
    private readonly Button install = new Button();

    internal InstallerForm()
    {
        Text = "Highlight Video Studio v1.0.16 — Cài đặt";
        ClientSize = new Size(620, 355);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        BackColor = Color.FromArgb(15, 23, 42);
        ForeColor = Color.White;
        Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);

        Controls.Add(new Label { Text = "Highlight Video Studio", Font = new Font("Segoe UI", 20, FontStyle.Bold), ForeColor = Color.FromArgb(56, 189, 248), AutoSize = true, Location = new Point(34, 27) });
        Controls.Add(new Label { Text = "AI Highlight • Research • Multi-channel Publisher", Font = new Font("Segoe UI", 10), ForeColor = Color.FromArgb(148, 163, 184), AutoSize = true, Location = new Point(37, 69) });
        Controls.Add(new Label { Text = "Thư mục cài đặt", Font = new Font("Segoe UI", 9, FontStyle.Bold), AutoSize = true, Location = new Point(38, 112) });

        destination.Text = DetectInstallLocation();
        destination.Location = new Point(38, 137);
        destination.Size = new Size(542, 27);
        destination.Font = new Font("Segoe UI", 10);
        Controls.Add(destination);

        progress.Location = new Point(38, 186);
        progress.Size = new Size(542, 20);
        progress.Style = ProgressBarStyle.Continuous;
        Controls.Add(progress);

        status.Text = "Sẵn sàng. Cấu hình và dữ liệu cũ sẽ được giữ nguyên khi nâng cấp.";
        status.ForeColor = Color.FromArgb(148, 163, 184);
        status.Location = new Point(38, 220);
        status.Size = new Size(542, 40);
        Controls.Add(status);

        install.Text = "CÀI ĐẶT & KHỞI CHẠY";
        install.Font = new Font("Segoe UI", 11, FontStyle.Bold);
        install.FlatStyle = FlatStyle.Flat;
        install.BackColor = Color.FromArgb(14, 165, 233);
        install.ForeColor = Color.White;
        install.Location = new Point(38, 270);
        install.Size = new Size(542, 48);
        install.Click += delegate { StartInstall(); };
        Controls.Add(install);
    }

    private void StartInstall()
    {
        string target = destination.Text.Trim();
        if (String.IsNullOrWhiteSpace(target)) return;
        install.Enabled = false;
        destination.Enabled = false;
        var worker = new Thread(delegate() { InstallPayload(target); }) { IsBackground = true };
        worker.Start();
    }

    private void InstallPayload(string target)
    {
        try
        {
            Directory.CreateDirectory(target);
            UpdateUi("Đang đóng phiên bản Highlight Studio cũ…", 0);
            StopRunningApplication(target);
            using (Stream payload = Assembly.GetExecutingAssembly().GetManifestResourceStream("HighlightStudio.Payload"))
            {
                if (payload == null) throw new InvalidOperationException("Installer không chứa gói ứng dụng.");
                using (var archive = new ZipArchive(payload, ZipArchiveMode.Read))
                {
                    int index = 0;
                    foreach (var entry in archive.Entries)
                    {
                        index++;
                        string relative = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                        string output = Path.GetFullPath(Path.Combine(target, relative));
                        string root = Path.GetFullPath(target) + Path.DirectorySeparatorChar;
                        if (!output.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                            throw new InvalidDataException("Đường dẫn không an toàn trong package: " + entry.FullName);
                        UpdateUi("Đang cài đặt: " + entry.FullName, archive.Entries.Count == 0 ? 0 : index * 100 / archive.Entries.Count);
                        if (String.IsNullOrEmpty(entry.Name)) { Directory.CreateDirectory(output); continue; }
                        Directory.CreateDirectory(Path.GetDirectoryName(output));
                        if (ShouldPreserve(relative) && File.Exists(output)) continue;
                        ExtractWithRetry(entry, output);
                    }
                }
            }

            string launcher = Path.Combine(target, "Highlight_Studio.exe");
            CreateShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), "Highlight Video Studio.lnk"), launcher, target);
            string programs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), "Highlight Video Studio");
            Directory.CreateDirectory(programs);
            CreateShortcut(Path.Combine(programs, "Highlight Video Studio.lnk"), launcher, target);
            SaveInstallLocation(target);
            UpdateUi("Cài đặt hoàn tất. Đang mở Highlight Video Studio…", 100);
            Process.Start(new ProcessStartInfo(launcher) { WorkingDirectory = target, UseShellExecute = true });
            Thread.Sleep(800);
            BeginInvoke(new Action(Close));
        }
        catch (Exception ex)
        {
            BeginInvoke(new Action(delegate
            {
                MessageBox.Show("Cài đặt thất bại:\n" + ex.Message, "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
                install.Enabled = true;
                destination.Enabled = true;
            }));
        }
    }

    private static bool ShouldPreserve(string relative)
    {
        string path = relative.Replace('\\', '/').ToLowerInvariant();
        return path == "config.json" || path == "config/website_config.json" ||
               path == "posts.json" || path == "jobs.json" || path == "pages.json" ||
               path == "page_groups.json" || path == "tokens_vault.json" ||
               path.StartsWith("downloads/") || path.StartsWith("output/") ||
               path.StartsWith("chrome_profile/") || path.StartsWith("data/");
    }

    private static void StopRunningApplication(string target)
    {
        string installRoot = Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        foreach (Process process in Process.GetProcesses())
        {
            try
            {
                if (process.Id == Process.GetCurrentProcess().Id) continue;
                string executable = process.MainModule == null ? "" : process.MainModule.FileName;
                if (!String.IsNullOrWhiteSpace(executable) &&
                    Path.GetFullPath(executable).StartsWith(installRoot, StringComparison.OrdinalIgnoreCase))
                {
                    process.CloseMainWindow();
                    if (!process.WaitForExit(1800))
                    {
                        process.Kill();
                        process.WaitForExit(5000);
                    }
                }
            }
            catch { }
            finally { process.Dispose(); }
        }
        Thread.Sleep(500);
    }

    private static void ExtractWithRetry(ZipArchiveEntry entry, string output)
    {
        string temporary = output + ".update." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            entry.ExtractToFile(temporary, true);
            Exception lastError = null;
            for (int attempt = 0; attempt < 12; attempt++)
            {
                try
                {
                    File.Copy(temporary, output, true);
                    return;
                }
                catch (Exception ex)
                {
                    lastError = ex;
                    Thread.Sleep(150 + attempt * 120);
                }
            }
            throw new IOException("Không thể cập nhật file đang được sử dụng: " + output, lastError);
        }
        finally
        {
            try { if (File.Exists(temporary)) File.Delete(temporary); } catch { }
        }
    }

    private static string DetectInstallLocation()
    {
        try
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(@"Software\HighlightVideoStudio"))
            {
                string saved = key == null ? null : key.GetValue("InstallLocation") as string;
                if (!String.IsNullOrWhiteSpace(saved) && Directory.Exists(saved)) return saved;
            }
        }
        catch { }
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Highlight Video Studio");
    }

    private static void SaveInstallLocation(string target)
    {
        try
        {
            using (RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\HighlightVideoStudio"))
                key.SetValue("InstallLocation", target, RegistryValueKind.String);
        }
        catch { }
    }

    private static void CreateShortcut(string shortcutPath, string target, string workingDirectory)
    {
        Type type = Type.GetTypeFromProgID("WScript.Shell");
        dynamic shell = Activator.CreateInstance(type);
        dynamic shortcut = shell.CreateShortcut(shortcutPath);
        shortcut.TargetPath = target;
        shortcut.WorkingDirectory = workingDirectory;
        shortcut.IconLocation = target + ",0";
        shortcut.Description = "Highlight Video Studio";
        shortcut.Save();
    }

    private void UpdateUi(string message, int value)
    {
        if (InvokeRequired) { BeginInvoke(new Action<string, int>(UpdateUi), message, value); return; }
        status.Text = message;
        progress.Value = Math.Max(0, Math.Min(100, value));
    }

    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Application.Run(new InstallerForm());
    }
}
