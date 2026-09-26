with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

# Check loadTokensAndPages
idx1 = html.find('async function loadTokensAndPages()')
print("=== loadTokensAndPages ===")
print(html[idx1:idx1+2000])

# Check loadJobsTable
idx2 = html.find('async function loadJobsTable()')
print("\n=== loadJobsTable ===")
print(html[idx2:idx2+2000])

