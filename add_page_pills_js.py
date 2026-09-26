from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect pane-pages JS logic:
# We need:
# 1. renderPageGroupPills()
# 2. filterPagesByGroup(groupId)
# 3. integrate with renderFbPageCards()

js_page_pills = """
  let currentSelectedPageGroupId = 'all';

  async function loadPageGroupsPills() {
    const pillsContainer = document.getElementById('loha-page-group-pills');
    if (!pillsContainer) return;

    try {
      const [resGrp, resPages] = await Promise.all([
        fetch('/api/groups'),
        fetch('/api/pages')
      ]);
      const dataGrp = await resGrp.json();
      const dataPages = await resPages.json();
      const groups = dataGrp.groups || [];
      const totalPages = (dataPages.pages || []).length;

      let pillsHtml = `
        <button class="btn btn-sm ${currentSelectedPageGroupId === 'all' ? 'btn-primary' : 'btn-outline'}" 
                onclick="filterPagesByGroup('all')" 
                style="border-radius: 20px; padding: 5px 16px; font-weight: 700; ${currentSelectedPageGroupId === 'all' ? 'background: #38bdf8; color: #0f172a; border: none;' : ''}">
          <i class="bi bi-grid-fill"></i> Tất cả (${totalPages})
        </button>
      `;

      groups.forEach(g => {
        const count = (g.page_ids || []).length;
        const isActive = currentSelectedPageGroupId === g.id;
        pillsHtml += `
          <button class="btn btn-sm ${isActive ? 'btn-primary' : 'btn-outline'}" 
                  onclick="filterPagesByGroup('${g.id}')" 
                  style="border-radius: 20px; padding: 5px 16px; font-weight: 700; ${isActive ? 'background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; color: #fff;' : ''}">
            <i class="bi bi-collection-play-fill"></i> ${g.name} (${count})
          </button>
        `;
      });

      pillsContainer.innerHTML = pillsHtml;
    } catch (e) {
      console.warn('Lỗi loadPageGroupsPills:', e);
    }
  }

  function filterPagesByGroup(groupId) {
    currentSelectedPageGroupId = groupId;
    loadPageGroupsPills();
    renderFbPageCards();
  }
"""

pos_render = html.find('function renderFbPageCards()')
if 'async function loadPageGroupsPills()' not in html and pos_render != -1:
    html = html[:pos_render] + js_page_pills + "\n  " + html[pos_render:]
    print("Added js_page_pills!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html!")
