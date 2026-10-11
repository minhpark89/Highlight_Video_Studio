"""Isolated, repeatable measurements; never uses installed app ledgers."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
TOOLS = Path(r'E:\OPENCLAW\BOB\Highlight destop test\bin')
os.environ['PATH'] = str(TOOLS) + os.pathsep + os.environ['PATH']
EVIDENCE = ROOT / 'checkpoints' / 'evidence' / 'v1.3.2'
EVIDENCE.mkdir(parents=True, exist_ok=True)
WORK = ROOT / 'build' / 'v132-benchmark'
WORK.mkdir(parents=True, exist_ok=True)


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                            errors='replace', timeout=180,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    return result


def api_measurement():
    from web import app as api
    from src import job_store
    api.IS_QUEUE_PAUSED = True
    with tempfile.TemporaryDirectory(prefix='highlight-v132-benchmark-') as directory:
        api.JOBS_FILE = Path(directory) / 'jobs.json'
        rows = [{'id': 'job_' + str(i), 'status': ['error','queued','running','completed'][i % 4],
                 'video_title': 'Fixture video ' + str(i), 'created_at': '2026-10-11',
                 'all_segments': [{'start':j, 'end':j+1, 'text':'Fixture transcription words for measurement only.'} for j in range(100)],
                 'clips': [{'filename':'fixture.mp4'}] * 3} for i in range(1264)]
        job_store.save(api.JOBS_FILE, rows)
        client = api.app.test_client()
        paths = {'legacy_full': '/api/jobs', 'paged_25': '/api/jobs?status=all&page_size=25&page=1',
                 'queue_status': '/api/queue/status'}
        measurements = {}
        for name, url in paths.items():
            client.get(url)
            samples = []
            for _ in range(5):
                start = time.perf_counter()
                response = client.get(url)
                samples.append((time.perf_counter()-start)*1000)
                assert response.status_code == 200
            measurements[name] = {'median_ms': round(statistics.median(samples), 3),
                                  'payload_bytes':len(response.data), 'samples_ms':samples}
        measurements['jobs'] = len(rows)
        return measurements


def render_measurement():
    source = WORK / 'source.mp4'
    run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',
         'testsrc2=size=1920x1080:rate=30','-f','lavfi','-i','sine=frequency=440:sample_rate=48000',
         '-t','6','-c:v','libx264','-preset','ultrafast','-crf','20','-c:a','aac',str(source)])
    filters = {
        'scale_then_crop': 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
        'crop_then_scale': "crop=w='trunc(min(iw,ih*9/16)/2)*2':h='trunc(min(ih,iw*16/9)/2)*2',scale=1080:1920"}
    measurements = {}
    encoder = ['-c:v','h264_nvenc','-preset','p2','-cq','21']
    try:
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-t','0.2',
             *encoder, '-an',str(WORK / 'nvenc-canary.mp4')])
        encoder_name = 'h264_nvenc'
    except RuntimeError:
        encoder = ['-c:v','libx264','-preset','veryfast','-crf','21']
        encoder_name = 'libx264'
    from src.render_quality import validate_render
    samples = {name:[] for name in filters}
    for repetition in range(3):
        order = list(filters) if repetition % 2 == 0 else list(reversed(filters))
        for name in order:
            output = WORK / (name + '.mp4')
            start = time.perf_counter()
            run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-t','6',
                 '-vf',filters[name] + ',setsar=1,setpts=PTS-STARTPTS', '-r','30','-fps_mode','cfr',
                 *encoder,'-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)])
            samples[name].append(time.perf_counter()-start)
            validate_render(output, 6)
    for name, values in samples.items():
        measurements[name] = {'median_seconds':round(statistics.median(values),3),
                              'samples_seconds':values, 'full_decode_validated':True}
    measurements['encoder'] = encoder_name
    measurements['input'] = 'synthetic 1920x1080 30fps with audio 6 seconds'
    measurements['output'] = '1080x1920 30fps same encoder preset and quality'
    measurements['speedup'] = round(statistics.median(samples['scale_then_crop']) /
                                     statistics.median(samples['crop_then_scale']), 3)
    return measurements


report = {'api':api_measurement(), 'render':render_measurement(),
          'scope':'isolated synthetic fixture on this machine; not a universal speed guarantee'}
(EVIDENCE / 'performance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
