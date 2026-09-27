using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Windows.Forms;

public class AppLauncher
{
    [STAThread]
    public static void Main()
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        Directory.SetCurrentDirectory(baseDir);

        string pythonExe = "";
        string[] candidates = new string[]
        {
            Path.Combine(baseDir, "runtime\\python.exe"),
            Path.Combine(baseDir, "venv\\Scripts\\python.exe"),
            "python.exe",
            "py.exe",
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs\\Python\\Python313\\python.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs\\Python\\Python312\\python.exe"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs\\Python\\Python311\\python.exe"),
            "C:\\Python313\\python.exe",
            "C:\\Python312\\python.exe",
            "C:\\Python311\\python.exe"
        };

        foreach (var c in candidates)
        {
            if (File.Exists(c))
            {
                pythonExe = c;
                break;
            }
        }

        if (string.IsNullOrEmpty(pythonExe))
        {
            try
            {
                Process p = new Process();
                p.StartInfo.FileName = "where";
                p.StartInfo.Arguments = "python";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                string output = p.StandardOutput.ReadLine();
                p.WaitForExit();
                if (!string.IsNullOrEmpty(output) && File.Exists(output.Trim()))
                {
                    pythonExe = output.Trim();
                }
            }
            catch {}
        }

        if (string.IsNullOrEmpty(pythonExe))
        {
            MessageBox.Show("Khong tim thay Python tren may tinh!\n\nVui long cai dat Python (nho tich Add python.exe to PATH) de khoi chay Highlight Video Studio.", "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        // Kiem tra va tu dong cai thu vien Flask, Waitress, Requests neu may chua co
        try
        {
            Process checkP = new Process();
            checkP.StartInfo.FileName = pythonExe;
            checkP.StartInfo.Arguments = "-c \"import flask, waitress, requests, yt_dlp\"";
            checkP.StartInfo.UseShellExecute = false;
            checkP.StartInfo.CreateNoWindow = true;
            checkP.Start();
            checkP.WaitForExit();

            if (checkP.ExitCode != 0)
            {
                // Cai dat thu vien can thiet
                Process pipP = new Process();
                pipP.StartInfo.FileName = pythonExe;
                pipP.StartInfo.Arguments = "-m pip install flask waitress requests yt-dlp";
                pipP.StartInfo.UseShellExecute = false;
                pipP.StartInfo.CreateNoWindow = false; // hien de user thay tien trinh
                pipP.Start();
                pipP.WaitForExit();
            }
        }
        catch {}

        try
        {
            // Chay run_server.py
            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = pythonExe;
            psi.Arguments = "run_server.py";
            psi.WorkingDirectory = baseDir;
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            psi.CreateNoWindow = true;
            psi.UseShellExecute = false;
            
            // Redirect stderr de bat loi neu crash
            string logFile = Path.Combine(baseDir, "server_error.log");
            psi.RedirectStandardError = true;
            
            Process proc = new Process();
            proc.StartInfo = psi;
            proc.ErrorDataReceived += (s, e) => {
                if (!string.IsNullOrEmpty(e.Data))
                {
                    try { File.AppendAllText(logFile, e.Data + "\n"); } catch {}
                }
            };
            proc.Start();
            proc.BeginErrorReadLine();

            // Cho 2s kiem tra xem port 5080 da len chua
            Thread.Sleep(2000);
            Process.Start("http://localhost:5080");
        }
        catch (Exception ex)
        {
            MessageBox.Show("Loi khoi dong: " + ex.Message, "Highlight Video Studio", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
