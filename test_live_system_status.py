import requests

# Test 1: Get jobs
r_jobs = requests.get("http://127.0.0.1:5080/api/jobs")
print("Live Jobs count:", len(r_jobs.json()))

# Test 2: Get clips
r_clips = requests.get("http://127.0.0.1:5080/api/clips")
clips = r_clips.json()
print("Live Clips count:", len(clips))
posted_clips = [c for c in clips if c.get("is_posted")]
print(f"Clips marked as posted: {len(posted_clips)} / {len(clips)}")

# Test 3: Get posts
r_posts = requests.get("http://127.0.0.1:5080/api/posts")
print("Live Posts count:", len(r_posts.json()))
for p in r_posts.json():
    print(f"  Post {p['id']}: Status={p.get('status')}, Scheduled={p.get('scheduled_time')}, Err={p.get('error')}")
