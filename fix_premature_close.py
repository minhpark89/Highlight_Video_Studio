from pathlib import Path
import re

INDEX_PATH = Path(r"D:\Highlight_Video_Studio\web\templates\index.html")
html = INDEX_PATH.read_text(encoding="utf-8")

# Let's inspect where </div> was closing content-area prematurely before pane-website!
# Look at:
# </section>
# </div>
# <!-- PANE: KẾT NỐI WEBSITE BÀI VIẾT & FIRST COMMENT -->

bad_str = """</section>
    </div>
  
      <!-- PANE: KẾT NỐI WEBSITE BÀI VIẾT & FIRST COMMENT -->"""

if bad_str in html:
    print("Found premature </div> closing content-area before pane-website!")
    # Replace it so pane-website stays INSIDE content-area
    html = html.replace(bad_str, "</section>\n\n      <!-- PANE: KẾT NỐI WEBSITE BÀI VIẾT & FIRST COMMENT -->")
    # And make sure content-area closes AFTER pane-website!
    pos_web = html.find('id="pane-website"')
    pos_web_end = html.find('</section>', pos_web)
    html = html[:pos_web_end+10] + "\n    </div><!-- end content-area -->" + html[pos_web_end+10:]
    INDEX_PATH.write_text(html, encoding="utf-8")
    print("Fixed content-area enclosure for pane-website and pane-settings!")
else:
    print("Checking exact text around pane-website...")
    pos_web = html.find('id="pane-website"')
    print(html[pos_web-150:pos_web+100])
