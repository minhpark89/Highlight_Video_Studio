import requests
import json

# 1. Clear scheduled posts first to test fresh
requests.post('http://127.0.0.1:5080/api/posts/clear', json={'status': 'all'})

# 2. Call batch distribution with posts_per_page = 2
r = requests.post('http://127.0.0.1:5080/api/distribute/batch', json={
    'group_id': 'grp_1790349600_3',
    'posts_per_page': 2,
    'stagger_minutes': 15,
    'auto_first_comment': True
})
print('Batch schedule status:', r.status_code)
print('Batch schedule response:', r.json())

# 3. Check created posts
r_posts = requests.get('http://127.0.0.1:5080/api/posts')
posts = r_posts.json()
print(f'Total posts in posts.json: {len(posts)}')
for p in posts:
    print(f"ID: {p['id']} | Page: {p['page_name']} | Sched: {p['scheduled_time']} | Status: {p['status']}")
