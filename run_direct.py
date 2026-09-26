import sys
import os
import traceback

sys.path.insert(0, r"D:\Highlight_Video_Studio")
os.chdir(r"D:\Highlight_Video_Studio")

try:
    from web.app import app
    print("App imported successfully! Starting test server...")
    # Just run a quick check
except Exception as e:
    with open(r"D:\Highlight_Video_Studio\direct_err.txt", "w", encoding="utf-8") as f:
        traceback.print_exc(file=f)
    print("Error written to direct_err.txt")
