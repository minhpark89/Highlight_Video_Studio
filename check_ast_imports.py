from pathlib import Path

app_path = Path(r"D:\Highlight_Video_Studio\web\app.py")
text = app_path.read_text(encoding="utf-8")

# Let's see all imports in the file
import ast
tree = ast.parse(text)
imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for n in node.names:
            imports.append((n.name, node.lineno))
    elif isinstance(node, ast.ImportFrom):
        imports.append((f"from {node.module} import ...", node.lineno))

print("Imports found in app.py:")
for imp in imports:
    print(imp)
