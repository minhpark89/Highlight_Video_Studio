from pathlib import Path

html_path = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = html_path.read_text(encoding="utf-8")

# Let's inspect loadPostsTable in index.html to render direct Facebook link for published reels!
pos = html.find('async function loadPostsTable')
pos_end = html.find('tbody.innerHTML = rows;', pos)

old_table_row = """            <td style="padding: 12px 16px;">
              <span class="badge" style="background: ${statusColor}; color: #fff; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 11px;">
                ${statusText}
              </span>
            </td>"""

new_table_row = """            <td style="padding: 12px 16px;">
              <span class="badge" style="background: ${statusColor}; color: #fff; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                ${statusText}
              </span>
              ${p.post_fb_id ? `
                <div style="margin-top: 5px;">
                  <a href="https://www.facebook.com/reel/${p.post_fb_id}" target="_blank" style="color: #38bdf8; font-size: 11px; text-decoration: none; font-weight: 700; display: inline-flex; align-items: center; gap: 4px; background: rgba(56, 189, 248, 0.1); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(56, 189, 248, 0.25);">
                    <i class="bi bi-box-arrow-up-right"></i> Xem Reel Facebook
                  </a>
                </div>
              ` : ''}
            </td>"""

if old_table_row in html:
    html = html.replace(old_table_row, new_table_row, 1)
    html_path.write_text(html, encoding="utf-8")
    print("Added direct Facebook Reel link to Quản lý Bài Đăng table!")
else:
    print("Could not find exact old_table_row in loadPostsTable, inspecting snippet:")
    pos_td = html.find('${statusText}', pos)
    print(html[pos_td-100:pos_td+150])
