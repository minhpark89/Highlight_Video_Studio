
  // Robust Head Switcher: Chạy độc lập, không phụ thuộc script khác
  window.switchTab = function(paneId, btnEl) {
    try {
      console.log('[Tab Direct] Switching to:', paneId);
      document.querySelectorAll('.nav-btn').forEach(function(b) { b.classList.remove('active'); });
      document.querySelectorAll('.pane').forEach(function(p) {
        p.classList.remove('active');
        p.style.display = 'none';
      });

      if (btnEl) {
        btnEl.classList.add('active');
      } else {
        var mBtn = document.querySelector('.nav-btn[data-pane="' + paneId + '"]');
        if (mBtn) mBtn.classList.add('active');
      }

      var target = document.getElementById(paneId);
      if (target) {
        target.classList.add('active');
        target.style.display = 'block';
      }

      // Lazy loaders
      try {
        if (paneId === 'pane-jobs' && typeof loadJobsTable === 'function') loadJobsTable();
        if (paneId === 'pane-research' && typeof loadSavedResearchVideos === 'function') loadSavedResearchVideos();
        if (paneId === 'pane-gallery' && typeof loadClipsGallery === 'function') loadClipsGallery();
        if (paneId === 'pane-tokens' && typeof loadTokensOnly === 'function') loadTokensOnly();
        if (paneId === 'pane-pages' && typeof loadTokensAndPages === 'function') loadTokensAndPages();
        if (paneId === 'pane-website' && typeof loadWebsiteConfig === 'function') loadWebsiteConfig();
      } catch (err) {
        console.warn('Lazy loader warning:', err);
      }
    } catch (e) {
      console.error('[switchTab error]', e);
    }
  };

  document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.nav-btn[data-pane]').forEach(function(btn) {
      btn.onclick = function(e) {
        e.preventDefault();
        var pId = this.getAttribute('data-pane');
        window.switchTab(pId, this);
      };
    });
  });
