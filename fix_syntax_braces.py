import os, re
from pathlib import Path

BASE_DIR = Path(r"D:\Highlight_Video_Studio")
TEMPLATE_PATH = BASE_DIR / "web" / "templates" / "index.html"
INDEX_ALT_PATH = BASE_DIR / "web" / "index.html"

with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    text = f.read()

# Locate the extra braces around line 1285-1295
target_snippet = """        }).join('');
      }
    }
      }
    }
  }
  function closeAddGroupModal() {"""

replacement_snippet = """        }).join('');
      }
    }
  }
  function closeAddGroupModal() {"""

if target_snippet in text:
    text = text.replace(target_snippet, replacement_snippet)
    print("Fixed extra closing braces in openAddGroupModal!")
else:
    print("Target snippet not found verbatim, checking regex...")
    # Find openAddGroupModal definition
    p_start = text.find("function openAddGroupModal()")
    p_end = text.find("function closeAddGroupModal()", p_start)
    if p_start != -1 and p_end != -1:
        fn_body = text[p_start:p_end]
        # Clean up any malformed braces before function closeAddGroupModal
        print("Current openAddGroupModal ends with:")
        print(repr(fn_body[-100:]))

with open(TEMPLATE_PATH, "w", encoding="utf-8") as f:
    f.write(text)
if INDEX_ALT_PATH.exists():
    with open(INDEX_ALT_PATH, "w", encoding="utf-8") as f:
        f.write(text)

print("Saved index.html.")
