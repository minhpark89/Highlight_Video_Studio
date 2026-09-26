with open('D:/Highlight_Video_Studio/web/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

def get_route_code(route_name):
    pos = text.find(f'@app.route("{route_name}"')
    if pos == -1:
        pos = text.find(f"@app.route('{route_name}'")
    if pos != -1:
        print(f"=== ROUTE: {route_name} ===")
        print(text[pos:pos+1500])
        print("...\n")

get_route_code('/api/distribute/batch')
get_route_code('/api/posts')
get_route_code('/api/clips/purge_posted')
get_route_code('/api/website/publish_draft')
