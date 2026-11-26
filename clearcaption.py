"""ClearCaption: hosted fallback for youtube-transcript-api when YouTube blocks your cloud IP.

Same output shape as youtube-transcript-api (list of {"text", "start", "duration"}),
but the request runs on Apify with rotating proxies, so AWS / GCP / Colab / Vercel work.
Translation works too (original track + LLM translation), which tlang= in the library cannot do (issue #572).

    pip install requests
    export APIFY_TOKEN=...            # free account: https://console.apify.com/sign-up
    from clearcaption import fetch
    fetch("dQw4w9WgXcQ")                          # original language
    fetch("dQw4w9WgXcQ", translate_to="de")       # translated, with timestamps

Pricing: $0.005 per video with captions, $0 for videos without captions; translation $0.005 per started 10 min
(free when YouTube already has a track in that language). Billed by Apify per event, no subscription.
"""
import os

import requests

ACTOR = os.environ.get("YTT_CLOUD_ACTOR", "clearcaption~youtube-transcript-translate")
API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


class TranscriptError(Exception):
    """The video has no captions, is private, or the input was not a YouTube video."""


def _segments(segs):
    return [{"text": s["text"], "start": s["start"], "duration": s["dur"]} for s in segs or []]


def fetch_many(videos, translate_to=None, token=None, timeout=300):
    """videos: ids or URLs (also channel / playlist URLs) -> {video_id: [segments]} or TranscriptError per video"""
    token = token or os.environ["APIFY_TOKEN"]
    body = {"videos": list(videos), "outputFormats": ["segments"], "includeTimestamps": True}
    if translate_to:
        body["targetLanguage"] = translate_to
    r = requests.post(API.format(actor=ACTOR), params={"token": token}, json=body, timeout=timeout)
    r.raise_for_status()
    out = {}
    for item in r.json():
        vid = item.get("videoId") or item.get("input")
        if item.get("status") != "OK":
            out[vid] = TranscriptError(item.get("status"))
            continue
        tr = item.get("translation") or {}
        if translate_to and not tr.get("segments"):
            out[vid] = TranscriptError(f"translation to {translate_to!r} is unavailable")
            continue
        out[vid] = _segments(tr.get("segments") if translate_to else item.get("segments"))
    return out


def fetch(video, translate_to=None, token=None):
    """one video -> [{"text", "start", "duration"}], like YouTubeTranscriptApi().fetch(video).to_raw_data()"""
    res = fetch_many([video], translate_to, token)
    if not res:
        raise TranscriptError("no result")
    seg = next(iter(res.values()))
    if isinstance(seg, Exception):
        raise seg
    return seg


def main(argv=None):
    """CLI: clearcaption VIDEO [VIDEO ...] [--to de] [--srt]  (needs APIFY_TOKEN)"""
    import argparse, json, sys
    ap = argparse.ArgumentParser(prog="clearcaption", description="YouTube transcripts from any server (videos, channels, playlists).")
    ap.add_argument("videos", nargs="+", help="video / channel / playlist URLs or video IDs")
    ap.add_argument("--to", dest="translate_to", help="translate to language code (de, es, uk...), timestamps kept")
    ap.add_argument("--srt", action="store_true", help="print SRT instead of plain text")
    ap.add_argument("--json", action="store_true", help="print raw segments as JSON")
    a = ap.parse_args(argv)
    res = fetch_many(a.videos, a.translate_to)
    for vid, seg in res.items():
        if isinstance(seg, Exception):
            print(f"# {vid}: {seg}", file=sys.stderr)
            continue
        if a.json:
            print(json.dumps({vid: seg}, ensure_ascii=False))
        elif a.srt:
            ts = lambda s: "%02d:%02d:%02d,%03d" % (s // 3600, s % 3600 // 60, s % 60, round(s % 1 * 1000) % 1000)
            for i, s in enumerate(seg, 1):
                print(f"{i}\n{ts(s['start'])} --> {ts(s['start'] + s['duration'])}\n{s['text']}\n")
        else:
            print(f"# {vid}\n" + " ".join(s["text"] for s in seg) + "\n")


if __name__ == "__main__":
    main()
