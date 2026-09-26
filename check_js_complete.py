with open(r'D:\Highlight_Video_Studio\web\templates\index.html', 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

# Let's inspect loadTokensAndPages from start to finish
idx = html.find('async function loadTokensAndPages()')
print("loadTokensAndPages index:", idx)
if idx != -1:
    # find next function
    next_fn = html.find('\n  async function ', idx + 20)
    if next_fn == -1:
        next_fn = html.find('\n  function ', idx + 20)
    print(html[idx:next_fn])

# Let's inspect loadJobsTable
idx_jobs = html.find('async function loadJobsTable()')
print("loadJobsTable index:", idx_jobs)
if idx_jobs != -1:
    next_fn = html.find('\n  async function ', idx_jobs + 20)
    if next_fn == -1:
        next_fn = html.find('\n  function ', idx_jobs + 20)
    print(html[idx_jobs:next_fn])
