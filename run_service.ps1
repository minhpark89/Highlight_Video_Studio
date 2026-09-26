$port = 5080
$tcp = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($tcp) {
    $pids = $tcp.OwningProcess | Select-Object -Unique
    foreach ($p in $pids) {
        Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 1
Start-Process -FilePath "python" -ArgumentList "D:\Highlight_Video_Studio\web\app.py" -WorkingDirectory "D:\Highlight_Video_Studio" -WindowStyle Hidden
Start-Sleep -Seconds 2
Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
