with open('D:/Highlight_Video_Studio/web/templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

def print_section(section_id):
    pos = text.find(f'id="{section_id}"')
    if pos != -1:
        end = text.find('</section>', pos)
        print(f"=== {section_id} (len: {end-pos}) ===")
        print(text[pos:pos+500])
        print("...\n")

print_section('pane-tokens')
print_section('pane-pages')
print_section('pane-website')
