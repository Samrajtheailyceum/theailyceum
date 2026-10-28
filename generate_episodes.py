#!/usr/bin/env python3
"""Generate individual episode HTML pages from episodes.json + template.html."""

import json
import os
from datetime import datetime
from html import escape
from urllib.parse import quote

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EPISODES_DIR = os.path.join(SCRIPT_DIR, "episodes")
EPISODES_JSON = os.path.join(EPISODES_DIR, "episodes.json")
TEMPLATE_FILE = os.path.join(EPISODES_DIR, "template.html")


def format_date_display(date_str):
    """Convert 2026-09-24 to '24 September 2026'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%-d %B %Y")


def build_episode_lookup(episodes):
    """Create a dict keyed by episode number for cross-referencing."""
    return {ep["num"]: ep for ep in episodes}


def generate_audio_player(ep):
    if ep["mp3Url"]:
        return (
            f'<audio controls preload="metadata">\n'
            f'            <source src="{escape(ep["mp3Url"])}" type="audio/mpeg">\n'
            f'            Your browser does not support the audio element.\n'
            f'          </audio>'
        )
    return (
        f'<div class="no-audio">Listen on '
        f'<a href="{escape(ep["rssUrl"])}" target="_blank" rel="noopener noreferrer">RSS.com</a>, '
        f'<a href="https://podcasts.apple.com/gb/podcast/the-ai-lyceum/id1837737167" target="_blank" rel="noopener noreferrer">Apple Podcasts</a>, '
        f'<a href="https://open.spotify.com/show/034vux8EWzb9M5Gn6QDMza" target="_blank" rel="noopener noreferrer">Spotify</a> or '
        f'<a href="https://www.youtube.com/@The.AI.Lyceum" target="_blank" rel="noopener noreferrer">YouTube</a>.'
        f'</div>'
    )


def generate_youtube_embed(ep):
    """Generate YouTube video embed or thumbnail link."""
    yt_id = ep.get("youtubeId", "")
    if yt_id:
        return (
            f'<div class="youtube-embed">\n'
            f'          <a href="https://www.youtube.com/watch?v={yt_id}" target="_blank" rel="noopener noreferrer" class="yt-thumb-link" aria-label="Watch on YouTube">\n'
            f'            <img src="https://img.youtube.com/vi/{yt_id}/hqdefault.jpg" alt="Watch Episode {ep["num"]}: {escape(ep["title"])} on YouTube" class="yt-thumb" loading="lazy" width="480" height="360" />\n'
            f'            <span class="yt-play" aria-hidden="true">\n'
            f'              <svg viewBox="0 0 68 48" width="68" height="48"><path d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55c-2.93.78-4.63 3.26-5.42 6.19C.06 13.05 0 24 0 24s.06 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.64-3.26 5.42-6.19C67.94 34.95 68 24 68 24s-.06-10.95-1.48-16.26z" fill="red"/><path d="M45 24 27 14v20" fill="#fff"/></svg>\n'
            f'            </span>\n'
            f'          </a>\n'
            f'        </div>'
        )
    return ""


def generate_guest_links(ep):
    """Generate guest affiliation and profile links."""
    links = []
    guest_url = ep.get("guestUrl", "")
    guest_linkedin = ep.get("guestLinkedin", "")
    guest_website = ep.get("guestWebsite", "")

    if guest_url:
        label = ep["affiliation"] if ep["affiliation"] else "Website"
        links.append(f'<a href="{escape(guest_url)}" target="_blank" rel="noopener noreferrer">{escape(label)}</a>')
    if guest_linkedin:
        links.append(f'<a href="{escape(guest_linkedin)}" target="_blank" rel="noopener noreferrer">LinkedIn</a>')
    if guest_website and guest_website != guest_url:
        links.append(f'<a href="{escape(guest_website)}" target="_blank" rel="noopener noreferrer">Personal site</a>')

    if links:
        return '<div class="guest-links">' + " ".join(links) + '</div>'
    return ""


def generate_guest_schema(ep):
    """Generate enhanced guest Person schema with sameAs links."""
    same_as = []
    guest_url = ep.get("guestUrl", "")
    guest_linkedin = ep.get("guestLinkedin", "")
    guest_website = ep.get("guestWebsite", "")
    if guest_url:
        same_as.append(f'"{guest_url}"')
    if guest_linkedin:
        same_as.append(f'"{guest_linkedin}"')
    if guest_website and guest_website != guest_url:
        same_as.append(f'"{guest_website}"')

    same_as_json = ""
    if same_as:
        same_as_json = ',\n            "sameAs": [' + ", ".join(same_as) + ']'

    return same_as_json


def generate_video_schema(ep):
    """Generate VideoObject JSON-LD for episodes with YouTube videos."""
    yt_id = ep.get("youtubeId", "")
    if not yt_id:
        return ""
    return (
        f',\n        {{\n'
        f'          "@type": "VideoObject",\n'
        f'          "name": "{ep["title"]}",\n'
        f'          "description": "{ep["description"]}",\n'
        f'          "thumbnailUrl": "https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg",\n'
        f'          "uploadDate": "{ep["date"]}",\n'
        f'          "embedUrl": "https://www.youtube.com/embed/{yt_id}",\n'
        f'          "contentUrl": "https://www.youtube.com/watch?v={yt_id}",\n'
        f'          "publisher": {{ "@id": "https://theailyceum.com/#organization" }}\n'
        f'        }}'
    )


def generate_related_episodes(ep, lookup):
    """Generate HTML for related episode links with YouTube thumbnails."""
    items = []
    for rel_num in ep.get("relatedEpisodes", [])[:3]:
        rel = lookup.get(rel_num)
        if not rel:
            continue
        guest_display = escape(rel["guest"])
        if rel["affiliation"]:
            guest_display += f' &middot; {escape(rel["affiliation"])}'

        yt_id = rel.get("youtubeId", "")
        thumb_html = ""
        if yt_id:
            thumb_html = (
                f'<img src="https://img.youtube.com/vi/{yt_id}/mqdefault.jpg" '
                f'alt="" class="related-thumb" loading="lazy" width="120" height="68" />\n'
                f'              '
            )

        items.append(
            f'<a class="related-item" href="/episodes/{rel["slug"]}.html">\n'
            f'              {thumb_html}'
            f'<span class="related-num">{rel["num"]}</span>\n'
            f'              <div class="related-body">\n'
            f'                <p class="related-title">{escape(rel["title"])}</p>\n'
            f'                <p class="related-guest">{guest_display}</p>\n'
            f'              </div>\n'
            f'            </a>'
        )
    return "\n            ".join(items)


def generate_topics_list(topics):
    return "\n            ".join(f"<li>{escape(t)}</li>" for t in topics)


def render_episode(template, ep, lookup):
    """Replace all placeholders in the template with episode data."""
    html = template

    # Basic replacements
    html = html.replace("{{NUM}}", str(ep["num"]))
    html = html.replace("{{SLUG}}", ep["slug"])
    html = html.replace("{{TITLE}}", escape(ep["title"]))
    html = html.replace("{{GUEST}}", escape(ep["guest"]))
    html = html.replace("{{DATE}}", ep["date"])
    html = html.replace("{{RSS_URL}}", escape(ep["rssUrl"]))
    html = html.replace("{{DESCRIPTION}}", escape(ep["description"]))
    html = html.replace("{{GUEST_DESCRIPTION}}", escape(ep["guestDescription"]))

    # Date display
    html = html.replace("{{DATE_DISPLAY}}", format_date_display(ep["date"]))

    # Affiliation
    if ep["affiliation"]:
        html = html.replace("{{AFFILIATION_META}}", f', {escape(ep["affiliation"])}')
        html = html.replace(
            "{{AFFILIATION_DISPLAY}}",
            f'<p class="ep-guest-affiliation">{escape(ep["affiliation"])}</p>',
        )
        html = html.replace(
            "{{AFFILIATION_JSON}}",
            f',\n            "affiliation": {{ "@type": "Organization", "name": "{ep["affiliation"]}" }}',
        )
    else:
        html = html.replace("{{AFFILIATION_META}}", "")
        html = html.replace("{{AFFILIATION_DISPLAY}}", "")
        html = html.replace("{{AFFILIATION_JSON}}", "")

    # Actor type (most are Person, GreenPT is Organization)
    if ep["guest"] == "GreenPT":
        html = html.replace("{{ACTOR_TYPE}}", "Organization")
    else:
        html = html.replace("{{ACTOR_TYPE}}", "Person")

    # Duration
    if ep["duration"]:
        html = html.replace("{{DURATION_META}}", f'{ep["durationLabel"]}.')
        html = html.replace(
            "{{DURATION_DISPLAY}}",
            f'<span>{escape(ep["durationLabel"])}</span>',
        )
        html = html.replace(
            "{{DURATION_JSON}}",
            f'"duration": "{ep["duration"]}",',
        )
    else:
        html = html.replace("{{DURATION_META}}", "")
        html = html.replace("{{DURATION_DISPLAY}}", "")
        html = html.replace("{{DURATION_JSON}}", "")

    # YouTube embed
    html = html.replace("{{YOUTUBE_EMBED}}", generate_youtube_embed(ep))

    # Audio player
    html = html.replace("{{AUDIO_PLAYER}}", generate_audio_player(ep))

    # Guest links
    html = html.replace("{{GUEST_LINKS}}", generate_guest_links(ep))

    # Guest schema sameAs
    html = html.replace("{{GUEST_SAMEAS}}", generate_guest_schema(ep))

    # Video schema
    html = html.replace("{{VIDEO_SCHEMA}}", generate_video_schema(ep))

    # Media JSON-LD
    if ep["mp3Url"]:
        html = html.replace(
            "{{MEDIA_JSON}}",
            f'"associatedMedia": {{ "@type": "AudioObject", "contentUrl": "{ep["mp3Url"]}", "encodingFormat": "audio/mpeg" }},',
        )
    else:
        html = html.replace("{{MEDIA_JSON}}", "")

    # OG image: use YouTube thumbnail if available, else default podcast cover
    yt_id = ep.get("youtubeId", "")
    if yt_id:
        html = html.replace("{{OG_IMAGE}}", f"https://img.youtube.com/vi/{yt_id}/maxresdefault.jpg")
        html = html.replace("{{OG_IMAGE_WIDTH}}", "1280")
        html = html.replace("{{OG_IMAGE_HEIGHT}}", "720")
    else:
        html = html.replace("{{OG_IMAGE}}", "https://media.rss.com/the-ai-lyceum/20250904_110936_a722fada418428b02d5417c12a526b4e.png")
        html = html.replace("{{OG_IMAGE_WIDTH}}", "1400")
        html = html.replace("{{OG_IMAGE_HEIGHT}}", "1400")

    # Topics
    html = html.replace("{{TOPICS_LIST}}", generate_topics_list(ep["topics"]))
    html = html.replace("{{TOPICS_META}}", ", ".join(ep["topics"]))

    # Related episodes
    html = html.replace("{{RELATED_EPISODES}}", generate_related_episodes(ep, lookup))

    # Cluster
    html = html.replace("{{CLUSTER}}", escape(ep.get("cluster", "")))

    return html


def generate_episodes_index(episodes):
    """Generate the episodes/index.html listing page with YouTube thumbnails."""
    episode_items = []
    for ep in episodes:
        guest_display = escape(ep["guest"])
        if ep["affiliation"]:
            guest_display += f' <span style="color:var(--muted);font-weight:400">&middot; {escape(ep["affiliation"])}</span>'

        yt_id = ep.get("youtubeId", "")
        thumb_html = ""
        if yt_id:
            thumb_html = (
                f'<a href="https://www.youtube.com/watch?v={yt_id}" target="_blank" rel="noopener noreferrer" class="ep-thumb-link" aria-label="Watch on YouTube">\n'
                f'                <img src="https://img.youtube.com/vi/{yt_id}/mqdefault.jpg" alt="" class="ep-thumb" loading="lazy" width="168" height="94" />\n'
                f'                <span class="ep-thumb-play" aria-hidden="true"><svg viewBox="0 0 68 48" width="34" height="24"><path d="M66.52 7.74c-.78-2.93-2.49-5.41-5.42-6.19C55.79.13 34 0 34 0S12.21.13 6.9 1.55c-2.93.78-4.63 3.26-5.42 6.19C.06 13.05 0 24 0 24s.06 10.95 1.48 16.26c.78 2.93 2.49 5.41 5.42 6.19C12.21 47.87 34 48 34 48s21.79-.13 27.1-1.55c2.93-.78 4.64-3.26 5.42-6.19C67.94 34.95 68 24 68 24s-.06-10.95-1.48-16.26z" fill="red"/><path d="M45 24 27 14v20" fill="#fff"/></svg></span>\n'
                f'              </a>\n'
                f'              '
            )

        # Guest link
        guest_url = ep.get("guestUrl", "")
        affiliation_link = ""
        if guest_url and ep["affiliation"]:
            affiliation_link = f' <a href="{escape(guest_url)}" target="_blank" rel="noopener noreferrer" style="color:var(--gold-hover);text-decoration:none;font-weight:400;font-size:12px">{escape(ep["affiliation"])} &nearr;</a>'

        episode_items.append(
            f'<li class="episode-item">\n'
            f'              {thumb_html}'
            f'<span class="ep-num">{ep["num"]}</span>\n'
            f'              <div class="ep-body">\n'
            f'                <h3 class="ep-title"><a href="/episodes/{ep["slug"]}.html" style="color:inherit;text-decoration:none">{escape(ep["title"])}</a></h3>\n'
            f'                <p class="ep-guest"><strong>{guest_display}</strong>{affiliation_link}</p>\n'
            f'                <p class="ep-date">{format_date_display(ep["date"])}</p>\n'
            f'                <div class="ep-links-row" style="display:flex;gap:12px;margin-top:6px">\n'
            f'                  <a class="ep-listen" href="/episodes/{ep["slug"]}.html">Show notes &rarr;</a>\n'
            f'                  <a class="ep-listen" href="{escape(ep["rssUrl"])}" target="_blank" rel="noopener noreferrer" style="color:var(--pewter)">Listen &rarr;</a>\n'
            f'                </div>\n'
            f'              </div>\n'
            f'            </li>'
        )
    items_html = "\n\n            ".join(episode_items)

    # JSON-LD ItemList
    json_items = []
    for i, ep in enumerate(episodes):
        json_items.append(
            f'{{"@type":"ListItem","position":{i + 1},"url":"https://theailyceum.com/episodes/{ep["slug"]}.html","name":"{ep["title"]}"}}'
        )
    json_list = ",\n            ".join(json_items)

    # Collect all guest names for meta keywords
    guest_names = ", ".join(ep["guest"] for ep in episodes)

    return f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>All Episodes — The AI Lyceum Podcast | AI Ethics, Agentic AI & Philosophy</title>
    <meta name="description" content="All {len(episodes)} episodes of The AI Lyceum podcast. Long-form conversations on AI ethics, agentic AI, philosophy and governance with researchers from Google DeepMind, Cerebras, IBM Research, UC Berkeley, Tel Aviv University, UCL, Oxford and more. Founded by Samraj Matharu in London, UK." />
    <meta name="keywords" content="The AI Lyceum podcast, AI podcast episodes, AI ethics podcast, agentic AI podcast, {guest_names}, Samraj Matharu, AI philosophy, AI governance, London AI podcast" />
    <meta property="og:title" content="All Episodes — The AI Lyceum Podcast" />
    <meta property="og:description" content="All {len(episodes)} episodes. Long-form conversations on AI ethics, agentic AI, philosophy and governance." />
    <meta property="og:type" content="website" />
    <meta property="og:url" content="https://theailyceum.com/episodes/" />
    <meta property="og:site_name" content="The AI Lyceum" />
    <meta property="og:image" content="https://media.rss.com/the-ai-lyceum/20250904_110936_a722fada418428b02d5417c12a526b4e.png" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="All Episodes — The AI Lyceum Podcast" />
    <meta name="twitter:description" content="All {len(episodes)} episodes. Long-form conversations on AI ethics, agentic AI, philosophy and governance." />
    <meta name="twitter:image" content="https://media.rss.com/the-ai-lyceum/20250904_110936_a722fada418428b02d5417c12a526b4e.png" />
    <meta name="theme-color" content="#0C0C0E" />
    <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />
    <meta name="geo.region" content="GB-LND" />
    <meta name="geo.placename" content="London" />
    <meta name="geo.position" content="51.5074;-0.1278" />
    <meta name="ICBM" content="51.5074, -0.1278" />
    <link rel="canonical" href="https://theailyceum.com/episodes/" />
    <link rel="me" href="/llms.txt" />
    <meta name="google-site-verification" content="REPLACE_WITH_GSC_CODE" />
    <meta name="msvalidate.01" content="REPLACE_WITH_BING_CODE" />

    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@graph": [
        {{
          "@type": "ItemList",
          "name": "The AI Lyceum — All Episodes",
          "numberOfItems": {len(episodes)},
          "itemListOrder": "https://schema.org/ItemListOrderDescending",
          "itemListElement": [
            {json_list}
          ]
        }},
        {{
          "@type": "BreadcrumbList",
          "itemListElement": [
            {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://theailyceum.com/" }},
            {{ "@type": "ListItem", "position": 2, "name": "Episodes", "item": "https://theailyceum.com/episodes/" }}
          ]
        }}
      ]
    }}
    </script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">

    <style>
      :root {{
        --obsidian: #0C0C0E; --charcoal: #1C1B1F; --pewter: #6B6B76;
        --silver: #9E9EA8; --ivory: #F5F2ED; --gold: #C9A84C;
        --gold-hover: #A8872A; --surface: #FAFAF8; --surface-alt: #F2F0EC;
        --ink: #1C1917; --muted: #78716c; --border-light: #e7e5e4;
        --border-dark: rgba(255,255,255,0.08);
        --font-display: 'Instrument Serif', Georgia, serif;
        --font-body: 'Inter', system-ui, -apple-system, sans-serif;
      }}
      * {{ box-sizing: border-box; margin: 0; }}
      html {{ scroll-behavior: smooth; }}
      body {{
        font-family: var(--font-body); background: var(--surface);
        color: var(--ink); line-height: 1.6; min-height: 100vh;
        display: flex; flex-direction: column;
      }}
      .wrap {{ max-width: 820px; margin: 0 auto; padding: 0 24px; width: 100%; }}
      .site-nav {{
        position: sticky; top: 0; z-index: 100; height: 56px;
        display: flex; align-items: center; justify-content: center; gap: 32px;
        background: rgba(12, 12, 14, 0.88);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        border-bottom: 1px solid rgba(255,255,255,0.06); padding: 0 24px;
      }}
      .site-nav .nav-brand {{
        font-family: var(--font-display); font-size: 18px; color: var(--ivory);
        text-decoration: none; letter-spacing: -0.01em;
      }}
      .site-nav a:not(.nav-brand) {{
        font-size: 13px; font-weight: 500; color: var(--silver);
        text-decoration: none; transition: color 0.3s;
      }}
      .site-nav a:not(.nav-brand):hover {{ color: var(--gold); }}
      .breadcrumb {{
        padding: 16px 0 0; font-size: 13px; color: var(--muted);
      }}
      .breadcrumb a {{ color: var(--gold-hover); text-decoration: none; font-weight: 500; }}
      .breadcrumb a:hover {{ text-decoration: underline; text-underline-offset: 3px; }}
      .breadcrumb .sep {{ margin: 0 8px; color: var(--pewter); }}
      .page-header {{
        padding: clamp(40px, 6vw, 80px) 0 clamp(24px, 3vw, 40px);
      }}
      .page-header h1 {{
        font-family: var(--font-display);
        font-size: clamp(28px, 5vw, 44px);
        line-height: 1.12; font-weight: 400; margin-bottom: 12px;
      }}
      .page-header p {{
        font-size: 16px; color: var(--muted); line-height: 1.7; max-width: 620px;
      }}
      .page-header p a {{ color: var(--gold-hover); text-decoration: none; font-weight: 500; }}
      .page-header p a:hover {{ text-decoration: underline; }}
      .episode-list {{ list-style: none; padding: 0; }}
      .episode-item {{
        display: flex; gap: 16px; padding: 22px 0;
        border-bottom: 1px solid var(--border-light);
        align-items: flex-start; transition: padding-left 0.3s;
      }}
      .episode-item:first-child {{ border-top: 1px solid var(--border-light); }}
      .episode-item:hover {{ padding-left: 8px; }}
      .ep-num {{
        flex-shrink: 0; width: 38px; height: 38px;
        display: flex; align-items: center; justify-content: center;
        background: var(--obsidian); color: var(--gold);
        font-size: 13px; font-weight: 700; border-radius: 8px; margin-top: 2px;
      }}
      .ep-thumb-link {{
        flex-shrink: 0; position: relative; display: block;
        border-radius: 8px; overflow: hidden; margin-top: 2px;
      }}
      .ep-thumb {{
        display: block; width: 168px; height: 94px; object-fit: cover;
        border-radius: 8px; transition: opacity 0.3s;
      }}
      .ep-thumb-link:hover .ep-thumb {{ opacity: 0.85; }}
      .ep-thumb-play {{
        position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
        opacity: 0.85; transition: opacity 0.3s;
      }}
      .ep-thumb-link:hover .ep-thumb-play {{ opacity: 1; }}
      .ep-body {{ flex: 1; min-width: 0; }}
      .ep-title {{
        font-family: var(--font-display); font-size: 18px;
        font-weight: 400; line-height: 1.3; margin: 0 0 4px; color: var(--ink);
      }}
      .ep-guest {{ font-size: 14px; color: var(--ink); margin: 0 0 4px; }}
      .ep-guest strong {{ font-weight: 600; }}
      .ep-date {{
        font-size: 11px; color: var(--pewter); text-transform: uppercase;
        letter-spacing: 0.1em; font-weight: 500;
      }}
      .ep-listen {{
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 13px; font-weight: 600; color: var(--gold-hover);
        text-decoration: none; transition: color 0.2s;
      }}
      .ep-listen:hover {{ color: var(--gold); }}
      .cross-links {{
        text-align: center; padding: 40px 0 0;
        border-top: 1px solid var(--border-light); margin-top: 48px;
      }}
      .cross-links a {{
        color: var(--gold-hover); text-decoration: none;
        font-size: 13px; font-weight: 600; margin: 0 14px; transition: color 0.2s;
      }}
      .cross-links a:hover {{ color: var(--gold); }}
      footer {{
        margin-top: auto; padding: 40px 0; text-align: center;
        font-size: 13px; color: var(--pewter);
        background: var(--obsidian); border-top: 1px solid var(--border-dark);
      }}
      footer a {{ color: var(--silver); text-decoration: none; transition: color 0.2s; }}
      footer a:hover {{ color: var(--gold); }}
      .footer-links {{ margin-top: 10px; }}
      .footer-links a {{ margin: 0 10px; }}
      @media (max-width: 640px) {{
        .site-nav {{ gap: 16px; }}
        .site-nav a:not(.nav-brand):not(.nav-episodes) {{ display: none; }}
        .ep-num {{ width: 32px; height: 32px; font-size: 11px; }}
        .ep-thumb {{ width: 120px; height: 68px; }}
      }}
    </style>
  </head>
  <body>
    <nav class="site-nav">
      <a href="/" class="nav-brand">The AI Lyceum</a>
      <a href="/#about">About</a>
      <a href="/episodes/" class="nav-episodes">Episodes</a>
      <a href="/#newsletter">Newsletter</a>
      <a href="/#faq">FAQ</a>
    </nav>

    <main>
      <div class="wrap">
        <nav class="breadcrumb" aria-label="Breadcrumb">
          <a href="/">Home</a><span class="sep">/</span>Episodes
        </nav>

        <div class="page-header">
          <h1>All episodes</h1>
          <p>{len(episodes)} long-form conversations on AI ethics, agentic AI, philosophy and governance. Guests include researchers from Google DeepMind, Cerebras, IBM Research, Tel Aviv University, UC Berkeley, UCL, Oxford, Kellogg and more. Founded by <a href="https://samrajmatharu.com">Samraj Matharu</a>.</p>
        </div>

        <ol class="episode-list" reversed>
            {items_html}
        </ol>

        <div class="cross-links">
          <a href="/">theailyceum.com</a>
          <a href="https://samrajmatharu.com">samrajmatharu.com</a>
          <a href="https://advertisingprotocols.com">advertisingprotocols.com</a>
        </div>
      </div>
    </main>

    <footer>
      <div class="wrap">
        <p style="font-family:var(--font-display);font-size:16px;color:var(--ivory);margin-bottom:8px;">The AI Lyceum</p>
        <p>&copy; 2026 <a href="https://samrajmatharu.com">Samraj Matharu</a>. London, UK.</p>
        <div class="footer-links">
          <a href="https://www.linkedin.com/in/samrajmatharu/">LinkedIn</a>
          <a href="https://uk.linkedin.com/company/the-ai-lyceum">Company page</a>
          <a href="https://www.youtube.com/@The.AI.Lyceum">YouTube</a>
          <a href="mailto:hello@theailyceum.com">hello@theailyceum.com</a>
        </div>
      </div>
    </footer>
  </body>
</html>'''


def main():
    with open(EPISODES_JSON, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    lookup = build_episode_lookup(episodes)

    # Generate individual episode pages
    count = 0
    for ep in episodes:
        html = render_episode(template, ep, lookup)
        output_path = os.path.join(EPISODES_DIR, f'{ep["slug"]}.html')
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        count += 1
        print(f"  Generated: episodes/{ep['slug']}.html")

    # Generate episodes index
    index_html = generate_episodes_index(episodes)
    index_path = os.path.join(EPISODES_DIR, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"  Generated: episodes/index.html")

    print(f"\nDone. {count} episode pages + 1 index page generated.")


if __name__ == "__main__":
    main()
