from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# 1. Look at switchTab in body script
pos1 = html.find('window.switchTab = function')
pos2 = html.find('window.switchTab = function', pos1 + 30)

print(f"Pos 1: {pos1}, Pos 2: {pos2}")

# In pos2, replace the whole switchTab so it includes all lazy loaders:
# pane-groups -> loadLoHaGroups()
# pane-tokens -> loadTokensOnly()
# pane-posts -> loadPostsTable()
# pane-pages -> loadTokensAndPages()

pos2_end = html.find('};\n', pos2)
if pos2_end == -1: pos2_end = html.find('};', pos2)

unified_switchtab = """window.switchTab = function(paneId, btnEl) {
    try {
      console.log('[Tab] Switching to:', paneId);
      // Remove active from all nav-btn
      var btns = document.querySelectorAll('.nav-btn');
      for (var i = 0; i < btns.length; i++) {
        btns[i].classList.remove('active');
      }
      // Remove active from all panes & force display
      var panes = document.querySelectorAll('.pane');
      for (var j = 0; j < panes.length; j++) {
        panes[j].classList.remove('active');
        panes[j].style.setProperty('display', 'none', 'important');
      }

      // Activate clicked button or matching button
      if (btnEl) {
        btnEl.classList.add('active');
      } else {
        var mBtn = document.querySelector('.nav-btn[data-pane="' + paneId + '"]');
        if (mBtn) mBtn.classList.add('active');
      }

      // Activate target pane & force display block
      var target = document.getElementById(paneId);
      if (target) {
        target.classList.add('active');
        target.style.setProperty('display', 'block', 'important');
      }

      // Safely call tab lazy loaders
      try {
        if (paneId === 'pane-jobs' && typeof loadJobsTable === 'function') loadJobsTable();
        if (paneId === 'pane-research' && typeof loadSavedResearchVideos === 'function') loadSavedResearchVideos();
        if (paneId === 'pane-gallery' && typeof loadClipsGallery === 'function') loadClipsGallery();
        if (paneId === 'pane-groups' && typeof loadLoHaGroups === 'function') loadLoHaGroups();
        if (paneId === 'pane-pages' && typeof loadTokensAndPages === 'function') loadTokensAndPages();
        if (paneId === 'pane-tokens' && typeof loadTokensOnly === 'function') loadTokensOnly();
        if (paneId === 'pane-posts' && typeof loadPostsTable === 'function') loadPostsTable();
        if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();
      } catch (e) { console.warn('Lazy loader err:', e); }
    } catch (err) {
      console.error('[switchTab error]', err);
    }
  };"""

html = html[:pos2] + unified_switchtab + html[pos2_end+2:]
print("Unified second switchTab with full LoHa lazy loaders!")

INDEX_PATH.write_text(html, encoding="utf-8")
print("Saved index.html!")
