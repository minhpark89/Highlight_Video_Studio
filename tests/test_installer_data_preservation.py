"""Exercise real installer extraction against bsdtar's ./ member names."""
from pathlib import Path
import os
import subprocess

import pytest


@pytest.mark.skipif(os.name != "nt", reason="Desktop installer uses the Windows .NET Framework")
def test_upgrade_preserves_existing_state_and_replaces_code(tmp_path):
    csc = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    if not csc.exists():
        pytest.skip("Windows C# compiler unavailable")
    root = Path(__file__).resolve().parents[1]
    harness = tmp_path / "Harness.cs"
    harness.write_text(r'''
using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
class InstallerPreservationHarness {
    static MethodInfo Method(string name) {
        return typeof(InstallerForm).GetMethod(name, BindingFlags.Static | BindingFlags.NonPublic);
    }
    static void Main(string[] args) {
        string root = args[0];
        Directory.CreateDirectory(root);
        string[] preserved = {"posts.json", "posts.json.bak", "config.json", "jobs.json",
            "pages.json", "page_groups.json", "tokens_vault.json", "token_groups.json",
            "posted_clips.json", "crawled_videos.json", "data/first_comment_profiles.json",
            "data/pending_first_comments.json", "data/content_packages.json", "config/website_config.json"};
        foreach (string name in preserved) {
            string path = Path.Combine(root, name);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, "original:" + name);
            foreach (string prefix in new[] {"", "./", ".\\", "././"}) {
                if (!(bool)Method("ShouldPreserve").Invoke(null, new object[] {prefix + name}))
                    throw new Exception("Preservation missed " + prefix + name);
            }
        }
        Method("BackupMutableState").Invoke(null, new object[] {root});
        string backup = Directory.GetDirectories(Path.Combine(root, "update_backups"))[0];
        foreach (string name in preserved)
            if (File.ReadAllText(Path.Combine(backup, name)) != "original:" + name)
                throw new Exception("Backup missed " + name);
        string code = Path.Combine(root, "web/app.py");
        Directory.CreateDirectory(Path.GetDirectoryName(code));
        File.WriteAllText(code, "old code");
        using (var buffer = new MemoryStream()) {
            using (var archive = new ZipArchive(buffer, ZipArchiveMode.Create, true)) {
                foreach (string name in preserved) {
                    using (var writer = new StreamWriter(archive.CreateEntry("./" + name).Open()))
                        writer.Write("package seed");
                }
                using (var writer = new StreamWriter(archive.CreateEntry("./web/app.py").Open()))
                    writer.Write("new code");
            }
            buffer.Position = 0;
            using (var archive = new ZipArchive(buffer, ZipArchiveMode.Read))
                Method("ExtractArchive").Invoke(null, new object[] {archive, root, new Action<string,int>((s, n) => {})});
        }
        foreach (string name in preserved)
            if (File.ReadAllText(Path.Combine(root, name)) != "original:" + name)
                throw new Exception("Upgrade overwrote " + name);
        if (File.ReadAllText(code) != "new code") throw new Exception("Code was not upgraded");
        using (var buffer = new MemoryStream()) {
            using (var archive = new ZipArchive(buffer, ZipArchiveMode.Create, true)) {
                using (var writer = new StreamWriter(archive.CreateEntry("./web/app.py").Open())) writer.Write("bad code");
                archive.CreateEntry("../escape.json");
            }
            buffer.Position = 0;
            using (var archive = new ZipArchive(buffer, ZipArchiveMode.Read)) {
                try {
                    Method("ExtractArchive").Invoke(null, new object[] {archive, root, new Action<string,int>((s, n) => {})});
                    throw new Exception("Traversal accepted");
                } catch (TargetInvocationException e) {
                    if (!(e.InnerException is InvalidDataException)) throw;
                }
            }
        }
        if (File.ReadAllText(code) != "new code") throw new Exception("Unsafe archive partially installed");
        Console.WriteLine("preserved state, durable backup, code upgrade, traversal rejection");
    }
}
''', encoding="utf-8")
    exe = tmp_path / "Harness.exe"
    compile_result = subprocess.run([str(csc), "/nologo", "/target:exe", "/main:InstallerPreservationHarness",
        f"/out:{exe}", "/reference:System.dll", "/reference:System.Drawing.dll",
        "/reference:System.Windows.Forms.dll", "/reference:System.IO.Compression.dll",
        "/reference:System.IO.Compression.FileSystem.dll", "/reference:Microsoft.CSharp.dll",
        str(root / "Installer.cs"), str(harness)], capture_output=True, text=True)
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr
    run = subprocess.run([str(exe), str(tmp_path / "install")], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
