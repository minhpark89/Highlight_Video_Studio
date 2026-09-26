from pathlib import Path

tmpl = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = tmpl.read_text(encoding="utf-8")

# Let's inspect pane-pages where filters/toolbar are located
pos_pages = html.find('id="pane-pages"')
pos_cards = html.find('id="fb-page-cards-grid"', pos_pages)
snippet = html[pos_pages:pos_cards]

# Pill bar for pane-pages:
page_pills_html = """
          <!-- THANH NHÓM PAGE ĐƯA RA NGOÀI MẶT TIỀN (CHUẨN LOHAPAGE) -->
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
              <span style="display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-collection-play-fill" style="color: #38bdf8;"></i> Lọc Fanpage theo Nhóm Trang:
              </span>
              <span style="font-size: 11px; color: #64748b; text-transform: none; font-weight: normal;">Bấm vào nhóm để xem danh sách page thuộc nhóm đó</span>
            </div>
            <div id="loha-page-group-pills" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
              <!-- Render động: [ Tất cả (100) ] [ BM 1 (Dàn 100 Page) (100) ] [ nhóm 1 (4) ] -->
            </div>
          </div>
"""

if 'id="loha-page-group-pills"' not in html:
    html = html[:pos_cards] + page_pills_html + "\n          " + html[pos_cards:]
    print("Inserted page pills html into pane-pages!")
else:
    print("Page pills already in pane-pages!")

# Let's inspect pane-groups to also add a quick group pill bar if needed
pos_groups = html.find('id="pane-groups"')
pos_table_groups = html.find('<table', pos_groups)

group_pills_html = """
          <!-- THANH NHÓM TRANG ĐƯA RA NGOÀI MẶT TIỀN (CHUẨN LOHAPAGE) -->
          <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 16px;">
            <div style="font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
              <span style="display: flex; align-items: center; gap: 6px;">
                <i class="bi bi-folder2-open" style="color: #ec4899;"></i> Danh mục Nhóm Trang đang quản lý:
              </span>
              <span style="font-size: 11px; color: #64748b; text-transform: none; font-weight: normal;">Chọn nhóm để thao tác nhanh hoặc lên lịch</span>
            </div>
            <div id="loha-main-group-pills" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
              <!-- Render động -->
            </div>
          </div>
"""

if 'id="loha-main-group-pills"' not in html:
    html = html[:pos_table_groups] + group_pills_html + "\n          " + html[pos_table_groups:]
    print("Inserted group pills html into pane-groups!")
else:
    print("Group pills already in pane-groups!")

tmpl.write_text(html, encoding="utf-8")
print("Saved template successfully!")
