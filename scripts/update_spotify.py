"""
Fetches the top 5 tracks (short_term ~ last 4 weeks) and recently played tracks
from the Spotify API and rewrites the README.md blocks.
"""

import base64
from datetime import datetime, timezone
import os
import re
import requests

README_PATH = "README.md"

# Markers for top tracks
TOP_START_MARKER = "<!-- SPOTIFY_TOP_TRACKS:START -->"
TOP_END_MARKER = "<!-- SPOTIFY_TOP_TRACKS:END -->"

# Markers for recently played
RECENT_START_MARKER = "<!-- SPOTIFY_RECENTLY_PLAYED:START -->"
RECENT_END_MARKER = "<!-- SPOTIFY_RECENTLY_PLAYED:END -->"

# Markers for top artists
ARTISTS_START_MARKER = "<!-- SPOTIFY_TOP_ARTISTS:START -->"
ARTISTS_END_MARKER = "<!-- SPOTIFY_TOP_ARTISTS:END -->"

# Markers for last update timestamp
UPDATE_START_MARKER = "<!-- SPOTIFY_LAST_UPDATE:START -->"
UPDATE_END_MARKER = "<!-- SPOTIFY_LAST_UPDATE:END -->"

TOP_TRACKS_API = "https://api.spotify.com/v1/me/top/tracks"
TOP_ARTISTS_API = "https://api.spotify.com/v1/me/top/artists"
RECENTLY_PLAYED_API = "https://api.spotify.com/v1/me/player/recently-played"


def get_access_token() -> str:
    """Exchange the refresh token for a fresh access token."""
    client_id = os.environ["SPOTIFY_CLIENT_ID"].strip()
    client_secret = os.environ["SPOTIFY_CLIENT_SECRET"].strip()
    refresh_token = os.environ["SPOTIFY_REFRESH_TOKEN"].strip()

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
    )
    if not resp.ok:
        print(f"[Spotify token error] status={resp.status_code} body={resp.text}")
        resp.raise_for_status()
    return resp.json()["access_token"]


ACCESS_TOKEN = get_access_token()


def fetch_top_tracks(limit: int = 5) -> list[dict]:
    resp = requests.get(
        TOP_TRACKS_API,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        params={"time_range": "short_term", "limit": limit},
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def fetch_recently_played(limit: int = 5) -> list[dict]:
    resp = requests.get(
        RECENTLY_PLAYED_API,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        params={"limit": limit},
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    # Extract track from each item (recently played wraps track in {track: ...})
    return [item["track"] for item in items]


def fetch_top_artists(limit: int = 5) -> list[dict]:
    resp = requests.get(
        TOP_ARTISTS_API,
        headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
        params={"time_range": "short_term", "limit": limit},
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def build_markdown_block(tracks: list[dict]) -> str:
    rows = ""
    for track in tracks:
        name = track["name"]
        artists_list = [a["name"] for a in track["artists"]][:5]  # limit to 5 artists
        artists = ", ".join(artists_list)
        url = track["external_urls"]["spotify"]
        images = track["album"]["images"]
        # prefer medium size (index 1), fallback to first available
        album_img = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else "")

        rows += (
            f"<tr>"
            f'<td><img src="{album_img}" width="36" height="36" alt="album art"/></td>'
            f'<td><b>{name}</b><br/><sub>{artists}</sub></td>'
            f'<td><a href="{url}"><img src="https://img.shields.io/badge/-Play-1DB954?style=flat-square&logo=spotify&logoColor=white" alt="Play"/></a></td>'
            f"</tr>\n"
        )

    block = (
        '\n<table>\n'
        '<tbody>\n'
        + rows +
        '</tbody>\n</table>\n'
    )
    return block


def build_artists_block(artists: list[dict]) -> str:
    rows = ""
    for artist in artists:
        name = artist["name"]
        url = artist["external_urls"]["spotify"]
        images = artist.get("images", [])
        artist_img = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else "")
        genres = ", ".join(artist.get("genres", [])[:2]) or "Artist"

        rows += (
            f"<tr>"
            f'<td><img src="{artist_img}" width="36" height="36" alt="artist"/></td>'
            f'<td><b>{name}</b><br/><sub>{genres}</sub></td>'
            f'<td><a href="{url}"><img src="https://img.shields.io/badge/-Open-1DB954?style=flat-square&logo=spotify&logoColor=white" alt="Open"/></a></td>'
            f"</tr>\n"
        )

    block = (
        '\n<table>\n'
        '<tbody>\n'
        + rows +
        '</tbody>\n</table>\n'
    )
    return block


def update_readme(top_block: str, artists_block: str, recent_block: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Update top tracks
    top_pattern = re.compile(
        rf"{re.escape(TOP_START_MARKER)}.*?{re.escape(TOP_END_MARKER)}",
        re.DOTALL,
    )
    top_replacement = f"{TOP_START_MARKER}\n{top_block}\n{TOP_END_MARKER}"

    if not top_pattern.search(content):
        raise ValueError("Top tracks markers not found in README.md")

    content = top_pattern.sub(top_replacement, content)

    # Update top artists
    artists_pattern = re.compile(
        rf"{re.escape(ARTISTS_START_MARKER)}.*?{re.escape(ARTISTS_END_MARKER)}",
        re.DOTALL,
    )
    artists_replacement = f"{ARTISTS_START_MARKER}\n{artists_block}\n{ARTISTS_END_MARKER}"

    if not artists_pattern.search(content):
        raise ValueError("Top artists markers not found in README.md")

    content = artists_pattern.sub(artists_replacement, content)

    # Update recently played
    recent_pattern = re.compile(
        rf"{re.escape(RECENT_START_MARKER)}.*?{re.escape(RECENT_END_MARKER)}",
        re.DOTALL,
    )
    recent_replacement = f"{RECENT_START_MARKER}\n{recent_block}\n{RECENT_END_MARKER}"

    if not recent_pattern.search(content):
        raise ValueError("Recently played markers not found in README.md")

    content = recent_pattern.sub(recent_replacement, content)

    # Update timestamp
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    update_pattern = re.compile(
        rf"{re.escape(UPDATE_START_MARKER)}.*?{re.escape(UPDATE_END_MARKER)}",
        re.DOTALL,
    )
    update_replacement = f"{UPDATE_START_MARKER}{now}{UPDATE_END_MARKER}"
    content = update_pattern.sub(update_replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("README.md updated successfully.")


if __name__ == "__main__":
    top_tracks = fetch_top_tracks()
    top_artists = fetch_top_artists()
    recent_tracks = fetch_recently_played()
    
    top_block = build_markdown_block(top_tracks)
    artists_block = build_artists_block(top_artists)
    recent_block = build_markdown_block(recent_tracks)
    
    update_readme(top_block, artists_block, recent_block)
