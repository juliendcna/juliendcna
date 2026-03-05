"""
Fetches the top 5 tracks (short_term ~ last 4 weeks) from the Spotify API
and rewrites the <!-- SPOTIFY_TOP_TRACKS:START/END --> block in README.md.
"""

import base64
import os
import re
import requests

README_PATH = "README.md"
START_MARKER = "<!-- SPOTIFY_TOP_TRACKS:START -->"
END_MARKER = "<!-- SPOTIFY_TOP_TRACKS:END -->"
API_URL = "https://api.spotify.com/v1/me/top/tracks"


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
        API_URL,
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


def update_readme(new_block: str) -> None:
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}",
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{new_block}\n{END_MARKER}"

    if not pattern.search(content):
        raise ValueError("Spotify markers not found in README.md")

    updated = pattern.sub(replacement, content)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print("README.md updated successfully.")


if __name__ == "__main__":
    tracks = fetch_top_tracks()
    block = build_markdown_block(tracks)
    update_readme(block)
