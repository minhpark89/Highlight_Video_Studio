$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$work = Join-Path $root 'build\v132-native-icon'
New-Item -ItemType Directory -Force -Path $work | Out-Null
$launcher = Join-Path $work 'Launcher.exe'
$csc = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
& $csc /nologo /target:winexe /optimize+ ("/out:" + $launcher) ("/win32icon:" + (Join-Path $root 'assets\highlight.ico')) /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll (Join-Path $root 'AppLauncher.cs')
if ($LASTEXITCODE -ne 0) { throw 'Launcher compile failed' }
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class IconMessages {
    [DllImport("user32.dll")]
    public static extern IntPtr SendMessage(IntPtr window, uint message, IntPtr wParam, IntPtr lParam);
}
'@
$assembly = [Reflection.Assembly]::LoadFile($launcher)
$type = $assembly.GetType('AppLauncher')
$flags = [Reflection.BindingFlags]'Static,NonPublic'
$big = [Drawing.Icon]::new((Join-Path $root 'assets\highlight.ico'), [Drawing.Size]::new(48,48))
$small = [Drawing.Icon]::new((Join-Path $root 'assets\highlight.ico'), [Windows.Forms.SystemInformation]::SmallIconSize)
$form = [Windows.Forms.Form]::new()
try {
    $form.Text = 'Isolated native icon test'
    $handle = $form.Handle
    $type.GetField('appIcon',$flags).SetValue($null,$big)
    $type.GetField('smallAppIcon',$flags).SetValue($null,$small)
    $type.GetMethod('ApplyWindowIcon',$flags).Invoke($null,@($handle)) | Out-Null
    $readBig = [IconMessages]::SendMessage($handle,0x007F,[IntPtr]::new(1),[IntPtr]::Zero)
    $readSmall = [IconMessages]::SendMessage($handle,0x007F,[IntPtr]::Zero,[IntPtr]::Zero)
    if ($readBig -ne $big.Handle -or $readSmall -ne $small.Handle) { throw 'Native window icon mismatch' }
    $report = @{success=$true; big_icon_matches=$true; small_icon_matches=$true;
        launcher_compiles=$true; scope='Hidden isolated Win32 window using actual launcher code and app ICO'}
    $report | ConvertTo-Json | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $root 'checkpoints\evidence\v1.3.2\native_icon.json')
    $report | ConvertTo-Json
}
finally { $form.Dispose(); $big.Dispose(); $small.Dispose() }
