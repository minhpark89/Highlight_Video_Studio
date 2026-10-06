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
    private const string TestProductName = "Highlight Desktop Test";
    private const string ProductKey = @"Software\HighlightDesktopTest";

    internal InstallerForm()
    {
        Text = TestProductName + " v1.2.6 - Installer";
        ClientSize = new Size(620, 355);
        StartPosition = FormStartPosition.CenterScreen;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        BackColor = Color.FromArgb(15, 23, 42);
        ForeColor = Color.White;
        Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);

        Controls.Add(new Label { Text = TestProductName, Font = new Font("Segoe UI", 20, FontStyle.Bold), ForeColor = Color.FromArgb(56, 189, 248), AutoSize = true, Location = new Point(34, 27) });
        Controls.Add(new Label { Text = "Isolated local-first test build • loopback only", Font = new Font("Segoe UI", 10), ForeColor = Color.FromArgb(148, 163, 184), AutoSize = true, Location = new Point(37, 69) });
        Controls.Add(new Label { Text = "Install directory", Font = new Font("Segoe UI", 9, FontStyle.Bold), AutoSize = true, Location = new Point(38, 112) });

        destination.Text = DetectInstallLocation();
        destination.Location = new Point(38, 137);
        destination.Size = new Size(542, 27);
        destination.Font = new Font("Segoe UI", 10);
        Controls.Add(destination);

        progress.Location = new Point(38, 186);
        progress.Size = new Size(542, 20);
        progress.Style = ProgressBarStyle.Continuous;
        Controls.Add(progress);

        status.Text = "Ready. This test product does not modify the production Highlight install.";
        status.ForeColor = Color.FromArgb(148, 163, 184);
        status.Location = new Point(38, 220);
        status.Size = new Size(542, 40);
        Controls.Add(status);

        install.Text = "INSTALL & LAUNCH TEST BUILD";
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
        new Thread(delegate() { InstallPayload(target); }) { IsBackground = true }.Start();
    }

    private void InstallPayload(string target)
    {
        try
        {
            // An explicitly selected production directory must not be stopped or overwritten.
            string fullTarget = Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar);
            string production = Path.GetFullPath(@"D:\Highlight_Video_Studio").TrimEnd(Path.DirectorySeparatorChar);
            if (fullTarget.Equals(production, StringComparison.OrdinalIgnoreCase) ||
                fullTarget.StartsWith(production + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("Choose an isolated test install directory outside the production Highlight install.");
            Directory.CreateDirectory(target);
            UpdateUi("Stopping an earlier test instance…", 0);
            StopRunningApplication(target);
            BackupMutableState(target);
            using (Stream payload = Assembly.GetExecutingAssembly().GetManifestResourceStream("HighlightDesktopTest.Payload"))
            {
                if (payload == null) throw new InvalidOperationException("Installer payload is missing.");
                using (var archive = new ZipArchive(payload, ZipArchiveMode.Read))
                {
                    ExtractArchive(archive, target, UpdateUi);
                }
            }

            string launcher = Path.Combine(target, "Highlight_Desktop_Test.exe");
            CreateShortcut(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), TestProductName + ".lnk"), launcher, target);
            string programs = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs), TestProductName);
            Directory.CreateDirectory(programs);
            CreateShortcut(Path.Combine(programs, TestProductName + ".lnk"), launcher, target);
            SaveInstallLocation(target);
            UpdateUi("Installation complete. Starting the isolated test build…", 100);
            Process.Start(new ProcessStartInfo(launcher) { WorkingDirectory = target, UseShellExecute = true });
            Thread.Sleep(800);
            BeginInvoke(new Action(Close));
        }
        catch (Exception ex)
        {
            BeginInvoke(new Action(delegate
            {
                MessageBox.Show("Installation failed:\n" + ex.Message, TestProductName, MessageBoxButtons.OK, MessageBoxIcon.Error);
                install.Enabled = true;
                destination.Enabled = true;
            }));
        }
    }

    private static bool ShouldPreserve(string relative)
    {
        string path = NormalizePackagePath(relative).ToLowerInvariant();
        return path == "config.json" || path == "config/website_config.json" ||
               path == "posts.json" || path == "jobs.json" || path == "pages.json" ||
               path == "page_groups.json" || path == "tokens_vault.json" ||
               path == "token_groups.json" || path == "posted_clips.json" ||
               path == "crawled_videos.json" || path == "posts.json.bak" ||
               path.StartsWith("posts.history.") ||
               path.StartsWith("downloads/") || path.StartsWith("output/") ||
               path.StartsWith("chrome_profile/") || path.StartsWith("data/");
    }

    private static string NormalizePackagePath(string relative)
    {
        // bsdtar packages the stage as ./posts.json. Compare the canonical
        // member name, or upgrades replace populated user ledgers with seeds.
        var parts = new System.Collections.Generic.List<string>();
        foreach (string part in relative.Replace('\\', '/').Split('/'))
        {
            if (part == "" || part == ".") continue;
            if (part == "..") throw new InvalidDataException("Unsafe package path: " + relative);
            parts.Add(part);
        }
        return String.Join("/", parts.ToArray());
    }

    private static void ExtractArchive(ZipArchive archive, string target, Action<string, int> update)
    {
        string root = Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        // Validate the whole archive before replacing any application files.
        foreach (var entry in archive.Entries)
        {
            string relative = NormalizePackagePath(entry.FullName);
            if (relative == "" && String.IsNullOrEmpty(entry.Name)) continue;
            string output = Path.GetFullPath(Path.Combine(target, relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!output.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Unsafe package path: " + entry.FullName);
        }
        int index = 0;
        foreach (var entry in archive.Entries)
        {
            index++;
            string relative = NormalizePackagePath(entry.FullName);
            if (relative == "" && String.IsNullOrEmpty(entry.Name)) continue;
            string output = Path.GetFullPath(Path.Combine(target, relative.Replace('/', Path.DirectorySeparatorChar)));
            update("Installing: " + relative, index * 100 / archive.Entries.Count);
            if (String.IsNullOrEmpty(entry.Name)) { Directory.CreateDirectory(output); continue; }
            Directory.CreateDirectory(Path.GetDirectoryName(output));
            if (ShouldPreserve(relative) && File.Exists(output)) continue;
            ExtractWithRetry(entry, output);
        }
    }

    private static void BackupMutableState(string target)
    {
        if (!File.Exists(Path.Combine(target, "posts.json")) && !File.Exists(Path.Combine(target, "config.json"))) return;
        string backup = Path.Combine(target, "update_backups", DateTime.Now.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(backup);
        foreach (string file in Directory.GetFiles(target))
        {
            string name = Path.GetFileName(file);
            if (ShouldPreserve(name) && (name.EndsWith(".json", StringComparison.OrdinalIgnoreCase) || name.EndsWith(".bak", StringComparison.OrdinalIgnoreCase)))
                File.Copy(file, Path.Combine(backup, name), false);
        }
        foreach (string directory in new[] { "config", "data" })
        {
            string source = Path.Combine(target, directory);
            if (!Directory.Exists(source)) continue;
            foreach (string file in Directory.GetFiles(source, "*.json", SearchOption.AllDirectories))
            {
                string relative = file.Substring(Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar).Length + 1);
                string destination = Path.Combine(backup, relative);
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                File.Copy(file, destination, false);
            }
        }
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
                if (!String.IsNullOrWhiteSpace(executable) && Path.GetFullPath(executable).StartsWith(installRoot, StringComparison.OrdinalIgnoreCase))
                {
                    process.CloseMainWindow();
                    if (!process.WaitForExit(1800)) { process.Kill(); process.WaitForExit(5000); }
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
                try { File.Copy(temporary, output, true); return; }
                catch (Exception ex) { lastError = ex; Thread.Sleep(150 + attempt * 120); }
            }
            throw new IOException("Cannot update file: " + output, lastError);
        }
        finally { try { if (File.Exists(temporary)) File.Delete(temporary); } catch { } }
    }

    private static string DetectInstallLocation()
    {
        try
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(ProductKey))
            {
                string saved = key == null ? null : key.GetValue("InstallLocation") as string;
                if (!String.IsNullOrWhiteSpace(saved) && Directory.Exists(saved)) return saved;
            }
        }
        catch { }
        return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), TestProductName);
    }

    private static void SaveInstallLocation(string target)
    {
        try { using (RegistryKey key = Registry.CurrentUser.CreateSubKey(ProductKey)) key.SetValue("InstallLocation", target, RegistryValueKind.String); }
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
        shortcut.Description = TestProductName;
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

