from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's locate pane-pages in index.html
pos_pages = html.find('id="pane-pages"')
pos_cards = html.find('id="fb-page-cards-grid"', pos_pages)

# Let's see what is right before fb-page-cards-grid
snippet = html[pos_pages:pos_cards]

# Create the LoHa Page Group Pills Bar
pills_bar_html = """
          <!-- THANH NHÓM PAGE ĐƯỢC ĐƯA RA NGOÀI MẶT TIỀN (CHUẨN LOHAPAGE) -->
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
              <span style="display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-collection-play-fill" style="color: #38bdf8;"></i> Chọn Nhóm Page để lọc & xem dàn trang:
              </span>
              <span style="font-size: 11px; color: #64748b; text-transform: none; font-weight: normal;">Bấm vào nhóm để lọc nhanh các Page thuộc nhóm đó</span>
            </div>
            <div id="loha-page-group-pills" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
              <!-- Render động bằng JS: [ Tất cả (100) ] [ BM 1 (Dàn 100 Page) (100) ] [ nhóm 1 (4) ] -->
            </div>
          </div>
"""

# Insert pills_bar_html right before <div id="fb-page-cards-grid"
if 'id="loha-page-group-pills"' not in html:
    html = html[:pos_cards] + pills_bar_html + "\n          " + html[pos_cards:]
    print("Inserted loha-page-group-pills bar into pane-pages!")
else:
    print("loha-page-group-pills already exists!")

tmpl.write_text(html, encoding="utf-8")
