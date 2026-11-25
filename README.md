# ClearCaption: YouTube transcripts that work from the cloud

`youtube-transcript-api` works on your laptop, then fails on AWS, GCP, Colab, Vercel or Render with
`RequestBlocked`, `IpBlocked`, `TranscriptsDisabled` (when captions clearly exist) or `429 Too Many Requests`.
YouTube blocks cloud IP ranges, and translated captions (`transcript.translate('de')`) return 429 from almost any IP.

ClearCaption is a drop-in fallback: the same output (`[{"text", "start", "duration"}]`), but the request runs on
Apify's rotating proxies, so it works from any server. It can also translate: it fetches the original track and translates it.

```bash
pip install requests
export APIFY_TOKEN=your_token   # free account: https://console.apify.com/sign-up
```

```python
from clearcaption import fetch, fetch_many

fetch("dQw4w9WgXcQ")                        # [{'text': ..., 'start': 18.64, 'duration': 3.24}, ...]
fetch("dQw4w9WgXcQ", translate_to="de")     # translated
fetch_many(["https://youtu.be/dQw4w9WgXcQ", "https://www.youtube.com/@channel"])  # videos, channels, playlists
```

### Keep youtube-transcript-api and fall back only when blocked

```python
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import RequestBlocked, IpBlocked
from clearcaption import fetch

def transcript(video_id):
    try:
        return YouTubeTranscriptApi().fetch(video_id).to_raw_data()
    except (RequestBlocked, IpBlocked):
        return fetch(video_id)
```

### Other ways to call it
- **REST / any language:** `POST https://api.apify.com/v2/acts/refulgent_enchantment_ghr~youtube-transcript-translate/run-sync-get-dataset-items?token=...` with `{"videos": ["dQw4w9WgXcQ"]}`.
- **AI agents (Claude, Cursor, n8n) via MCP:** add `https://mcp.apify.com?tools=refulgent_enchantment_ghr/youtube-transcript-translate` as an MCP server (header `Authorization: Bearer <APIFY_TOKEN>`, or sign in to Apify on first connection).
- **No code:** [Apify Store page](https://apify.com/refulgent_enchantment_ghr/youtube-transcript-translate): paste URLs, download JSON / CSV / SRT / VTT.

### Price
$0.005 per video with captions. Videos without captions cost $0. Translation costs $0.005 per started 10 minutes of video, and is free when YouTube already has a track in that language.
Pay per use on Apify, no subscription. The free Apify plan includes monthly credit.

### Compared with
| | youtube-transcript-api + residential proxy | Hosted subscription APIs | ClearCaption |
|---|---|---|---|
| Works from cloud | yes, if you run proxy rotation | yes | yes |
| Translated captions | 429 on `tlang` | varies | yes |
| Channels / playlists / search | no | some | yes |
| Billing | proxy plan | monthly plan | per video, $0 without captions |

MIT license. Issues and PRs welcome.
