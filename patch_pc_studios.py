import sys
import re

# 1. Patch Highlight_Video_Studio/src/pipeline.py
pipeline_path = r'D:\Highlight_Video_Studio\src\pipeline.py'
with open(pipeline_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Make sure subprocess.CREATE_NO_WINDOW is used
# Define no_window_flag
if 'CREATE_NO_WINDOW' not in code:
    # Add a helper at the top or define NO_WINDOW
    flag_def = "\n# Hide console window on Windows\nNO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0\n"
    idx = code.find("import subprocess")
    if idx != -1:
        end_line = code.find("\n", idx)
        code = code[:end_line+1] + flag_def + code[end_line+1:]

    # Replace subprocess.run calls to include creationflags=NO_WINDOW
    # 1. info_proc = subprocess.run(info_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    code = code.replace(
        'info_proc = subprocess.run(info_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")',
        'info_proc = subprocess.run(info_cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", creationflags=NO_WINDOW)'
    )
    # 2. res = subprocess.run(cmd, capture_output=True, text=True)
    code = code.replace(
        'res = subprocess.run(cmd, capture_output=True, text=True)',
        'res = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)'
    )
    # 3. subprocess.run(cmd_audio, capture_output=True)
    code = code.replace(
        'subprocess.run(cmd_audio, capture_output=True)',
        'subprocess.run(cmd_audio, capture_output=True, creationflags=NO_WINDOW)'
    )
    # 4. subprocess.run(cmd_cut, capture_output=True)
    code = code.replace(
        'subprocess.run(cmd_cut, capture_output=True)',
        'subprocess.run(cmd_cut, capture_output=True, creationflags=NO_WINDOW)'
    )
    # 5. p = subprocess.run(cmd, capture_output=True, text=True)
    code = code.replace(
        'p = subprocess.run(cmd, capture_output=True, text=True)',
        'p = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)'
    )
    # 6. p2 = subprocess.run(cmd_fallback, capture_output=True, text=True)
    code = code.replace(
        'p2 = subprocess.run(cmd_fallback, capture_output=True, text=True)',
        'p2 = subprocess.run(cmd_fallback, capture_output=True, text=True, creationflags=NO_WINDOW)'
    )

    with open(pipeline_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print("Patched pipeline.py successfully")

# 2. Patch Highlight_Video_Studio/src/content_builder.py
cb_path = r'D:\Highlight_Video_Studio\src\content_builder.py'
with open(cb_path, 'r', encoding='utf-8') as f:
    cb_code = f.read()

if 'CREATE_NO_WINDOW' not in cb_code:
    flag_def = "\nNO_WINDOW = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0\n"
    idx = cb_code.find("import subprocess")
    if idx != -1:
        end_line = cb_code.find("\n", idx)
        cb_code = cb_code[:end_line+1] + flag_def + cb_code[end_line+1:]
        cb_code = cb_code.replace(
            'subprocess.run(cmd, capture_output=True, timeout=30)',
            'subprocess.run(cmd, capture_output=True, timeout=30, creationflags=NO_WINDOW)'
        )
        with open(cb_path, 'w', encoding='utf-8') as f:
            f.write(cb_code)
        print("Patched content_builder.py successfully")

