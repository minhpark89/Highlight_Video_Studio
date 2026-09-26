Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\Highlight_Video_Studio"
WshShell.Run "C:\Users\Admin\AppData\Local\Programs\Python\Python313\python.exe web\app.py", 0, False
