import os
import sys
import re
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any

try:
    import yt_dlp
    HAS_YTDLP_MODULE = True
except Exception:
    HAS_YTDLP_MODULE = False

logger = logging.getLogger('research')
BASE_DIR = Path(__file__).resolve().parent.parent

def search_videos(query: str, platform: str = 'youtube', max_results: int = 12, filter_type: str = 'all', sort_by: str = 'views') -> List[Dict[str, Any]]:
    query = query.strip()
    if not query:
        return []

    is_url = query.startswith('http://') or query.startswith('https://')

    # Ưu tiên dùng CLI yt-dlp.exe độc lập (standalone 17.8MB) để độc lập 100% với môi trường Python của máy trạm
    bin_path = BASE_DIR / "bin" / "yt-dlp.exe"
    if bin_path.exists() and bin_path.stat().st_size > 1_000_000:
        res = _search_videos_cli(query, platform, max_results, filter_type, sort_by, is_url, exe_cmd=str(bin_path))
        if res:
            return res

    # Nếu module yt_dlp có sẵn
    if HAS_YTDLP_MODULE:
        try:
            return _search_videos_module(query, platform, max_results, filter_type, sort_by, is_url)
        except Exception as e:
            logger.warning(f"yt_dlp module search error: {e}, falling back to CLI binary...")

    # Fallback cuối cùng: yt-dlp trong PATH hệ thống hoặc bin_path
    return _search_videos_cli(query, platform, max_results, filter_type, sort_by, is_url)

def _search_videos_cli(query: str, platform: str, max_results: int, filter_type: str, sort_by: str, is_url: bool, exe_cmd: str = None) -> List[Dict[str, Any]]:
    if not exe_cmd:
        bin_path = BASE_DIR / "bin" / "yt-dlp.exe"
        exe_cmd = str(bin_path) if bin_path.exists() else "yt-dlp"

    target_query = query
    if not is_url:
        fetch_count = max(30, int(max_results * 1.5))
        if platform == 'youtube_shorts':
            target_query = f"ytsearch{fetch_count}:{query} #shorts"
        elif platform == 'podcast':
            target_query = f"ytsearch{fetch_count}:{query} podcast"
        elif platform == 'viral':
            target_query = f"ytsearch{fetch_count}:{query} viral"
        else:
            target_query = f"ytsearch{fetch_count}:{query}"

    cmd = [
        exe_cmd,
        "--dump-json",
        "--flat-playlist",
        "--no-warnings",
        "--ignore-errors",
        target_query
    ]
    if is_url:
        cmd.extend(["--playlist-end", str(max_results)])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=60)
        if proc.returncode != 0 and not proc.stdout:
            err_msg = (proc.stderr or "").strip()
            logger.error(f"yt-dlp cli returned code {proc.returncode}: {err_msg}")
            if "not recognized" in err_msg or "cannot find" in err_msg:
                raise RuntimeError(f"Không tìm thấy công cụ yt-dlp: {err_msg}")
            elif err_msg:
                raise RuntimeError(f"Lỗi YouTube: {err_msg[:200]}")

        raw_lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        results = []
        for line in raw_lines:
            try:
                e = json.loads(line)
                vid = e.get("id") or ""
                vurl = e.get("url") or f"https://www.youtube.com/watch?v={vid}"
                dur = e.get("duration") or 0
                
                # Filter duration
                if filter_type == 'short' and dur > 300:
                    continue
                elif filter_type == 'medium' and (dur < 300 or dur > 1800):
                    continue
                elif filter_type == 'long' and dur < 1800 and dur > 0:
                    continue

                dur_str = ''
                if dur:
                    m, s = divmod(int(dur), 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

                view_cnt = e.get("view_count") or 0
                if view_cnt >= 1_000_000_000:
                    view_str = f"{view_cnt/1_000_000_000:.1f}B views"
                elif view_cnt >= 1_000_000:
                    view_str = f"{view_cnt/1_000_000:.1f}M views"
                elif view_cnt >= 1_000:
                    view_str = f"{view_cnt/1_000:.1f}K views"
                elif view_cnt > 0:
                    view_str = f"{view_cnt:,} views"
                else:
                    view_str = "N/A views"

                thumb = e.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"

                results.append({
                    "id": vid,
                    "title": e.get("title", "Untitled"),
                    "url": vurl,
                    "platform": "youtube",
                    "uploader": e.get("uploader") or e.get("channel") or "Creator",
                    "duration": dur,
                    "duration_str": dur_str,
                    "view_count": view_cnt,
                    "view_count_str": view_str,
                    "thumbnail": thumb
                })
            except Exception:
                continue

        if sort_by == 'views':
            results.sort(key=lambda x: (x.get("view_count") or 0), reverse=True)

        return results[:max_results]
    except Exception as ex:
        logger.error(f"yt-dlp cli search error: {ex}")
        raise ex

def _search_videos_module(query: str, platform: str, max_results: int, filter_type: str, sort_by: str, is_url: bool) -> List[Dict[str, Any]]:
    query = query.strip()
    if not query:
        return []

    is_url = query.startswith('http://') or query.startswith('https://')
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'playlistend': max_results if is_url else None
    }

    results = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            target_query = query
            if not is_url:
                fetch_count = max(30, int(max_results * 1.5))
                if fetch_count > 1000:
                    fetch_count = 1000
                if platform == 'youtube_shorts':
                    target_query = f"ytsearch{fetch_count}:{query} #shorts"
                elif platform == 'podcast':
                    target_query = f"ytsearch{fetch_count}:{query} podcast"
                elif platform == 'viral':
                    target_query = f"ytsearch{fetch_count}:{query} viral"
                else:
                    target_query = f"ytsearch{fetch_count}:{query}"

            info = ydl.extract_info(target_query, download=False)
            if not info:
                return []

            entries = info.get('entries', [])
            if not entries and 'title' in info:
                entries = [info]

            raw_entries = [e for e in entries if e and (e.get('id') or e.get('url'))]

            if sort_by == 'views':
                raw_entries.sort(key=lambda x: (x.get('view_count') or 0), reverse=True)

            for idx, item in enumerate(raw_entries):
                video_id = item.get('id')
                url = item.get('url') or item.get('webpage_url')
                if not url or not str(url).startswith('http'):
                    if video_id:
                        url = f"https://www.youtube.com/watch?v={video_id}"
                    else:
                        continue

                duration = item.get('duration') or 0
                if filter_type == 'short' and duration > 300:
                    continue
                elif filter_type == 'medium' and (duration < 300 or duration > 1800):
                    continue
                elif filter_type == 'long' and duration < 1800 and duration > 0:
                    continue

                dur_str = ''
                if duration:
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

                thumb = item.get('thumbnail')
                if not thumb and item.get('thumbnails'):
                    thumb = item.get('thumbnails')[-1].get('url')
                if not thumb and video_id:
                    thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

                view_cnt = item.get('view_count') or 0
                if view_cnt >= 1_000_000_000:
                    view_str = f"{view_cnt/1_000_000_000:.1f}B views"
                elif view_cnt >= 1_000_000:
                    view_str = f"{view_cnt/1_000_000:.1f}M views"
                elif view_cnt >= 1_000:
                    view_str = f"{view_cnt/1_000:.1f}K views"
                elif view_cnt > 0:
                    view_str = f"{view_cnt:,} views"
                else:
                    view_str = "N/A views"

                uploader = item.get('uploader') or item.get('channel') or 'Creator'

                results.append({
                    'id': video_id or f"vid_{idx}",
                    'title': item.get('title') or "Untitled Video",
                    'url': url,
                    'platform': 'youtube',
                    'uploader': uploader,
                    'duration': duration,
                    'duration_str': dur_str,
                    'view_count': view_cnt,
                    'view_count_str': view_str,
                    'thumbnail': thumb,
                    'description': (item.get('description') or '')[:180]
                })

                if len(results) >= max_results:
                    break
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise e

    return results
