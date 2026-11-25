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

ACTOR = os.environ.get("YTT_CLOUD_ACTOR", "refulgent_enchantment_ghr~youtube-transcript-translate")
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
        out[vid] = _segments(tr.get("segments") if translate_to and tr.get("segments") else item.get("segments"))
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
