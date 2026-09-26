from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect loadTokensOnly function in index.html and update it to render loha-token-group-pills
old_loadtokens_call = """  async function loadTokensOnly() {
    try {
      const res = await fetch('/api/tokens');"""

new_loadtokens_impl = """  let currentSelectedTokenGroupId = 'all';

  async function loadTokenGroupsPills() {
    const pillsContainer = document.getElementById('loha-token-group-pills');
    if (!pillsContainer) return;

    try {
      const res = await fetch('/api/token-groups');
      const data = await res.json();
      const groups = data.groups || [];

      // Calculate total tokens
      const resTok = await fetch('/api/tokens');
      const dataTok = await resTok.json();
      const totalTokensCount = (dataTok.tokens || []).length;

      let pillsHtml = `
        <button class="btn btn-sm ${currentSelectedTokenGroupId === 'all' ? 'btn-primary' : 'btn-outline'}" 
                onclick="filterTokensByGroup('all')" 
                style="border-radius: 20px; padding: 4px 14px; font-weight: 700;">
          <i class="bi bi-grid-fill"></i> Tất cả (${totalTokensCount})
        </button>
      `;

      groups.forEach(g => {
        const count = (g.token_ids || []).length;
        const isActive = currentSelectedTokenGroupId === g.id;
        pillsHtml += `
          <button class="btn btn-sm ${isActive ? 'btn-primary' : 'btn-outline'}" 
                  onclick="filterTokensByGroup('${g.id}')" 
                  style="border-radius: 20px; padding: 4px 14px; font-weight: 700; ${isActive ? 'background: linear-gradient(135deg, #ec4899, #8b5cf6); border: none;' : ''}">
            <i class="bi bi-collection"></i> ${g.name} (${count})
          </button>
        `;
      });

      pillsContainer.innerHTML = pillsHtml;
    } catch (e) {
      console.warn('Lỗi loadTokenGroupsPills:', e);
    }
  }

  function filterTokensByGroup(groupId) {
    currentSelectedTokenGroupId = groupId;
    loadTokensOnly();
  }

  async function loadTokensOnly() {
    await loadTokenGroupsPills();
    try {
      const [resTok, resGrp] = await Promise.all([
        fetch('/api/tokens'),
        fetch('/api/token-groups')
      ]);
      const data = await resTok.json();
      const dataGrp = await resGrp.json();
      let tokens = data.tokens || [];
      const groups = dataGrp.groups || [];

      // Create token-id to group names map
      const tokenGroupMap = {};
      groups.forEach(g => {
        (g.token_ids || []).forEach(tid => {
          if (!tokenGroupMap[tid]) tokenGroupMap[tid] = [];
          tokenGroupMap[tid].push(g.name);
        });
      });

      // Filter by currentSelectedTokenGroupId if not 'all'
      if (currentSelectedTokenGroupId !== 'all') {
        const selGroup = groups.find(g => g.id === currentSelectedTokenGroupId);
        if (selGroup && selGroup.token_ids) {
          const idSet = new Set(selGroup.token_ids);
          tokens = tokens.filter(t => idSet.has(t.id));
        }
      }"""

pos = html.find('async function loadTokensOnly() {')
if pos != -1:
    pos_end = html.find('const tbody = document.getElementById(\'tokens-table-body\');', pos)
    html = html[:pos] + new_loadtokens_impl + "\n\n      " + html[pos_end:]
    print("Updated loadTokensOnly with pill filtering!")

# Also update the token row rendering to show Nhóm Token name
old_row_render = """            <td style="padding: 12px 16px;">
              <span style="color: #e2e8f0; font-weight: 700; font-size: 12px;"><i class="bi bi-cpu" style="color: #38bdf8;"></i> ${threads} luồng</span>
            </td>"""

new_row_render = """            <td style="padding: 12px 16px;">
              ${(tokenGroupMap[t.id] || []).length > 0 
                ? tokenGroupMap[t.id].map(gn => `<span style="background: rgba(236,72,153,0.15); color: #f472b6; border: 1px solid rgba(236,72,153,0.3); padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; margin-right: 4px;"><i class="bi bi-diagram-3-fill"></i> ${gn}</span>`).join('')
                : '<span style="color: #64748b; font-size: 11px;">(Mặc định)</span>'
              }
            </td>"""

if old_row_render in html:
    html = html.replace(old_row_render, new_row_render, 1)
    print("Updated token row to display Group name!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html successfully!")
