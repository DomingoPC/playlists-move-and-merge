import dotenv
from pathlib import Path
import pandas as pd
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections.abc import Sequence
import utils as u

#region Create_CSV_Backup
def get_playlist_tracks(sp: spotipy.Spotify, playlist_url: str) -> pd.DataFrame:
    """Extract tracks from a url (only read permissions needed)"""
    playlist_name = sp.playlist(playlist_id = playlist_url, fields = "name")["name"]

    # Create a list accounting for the offset
    rows, offset = [], 0
    while True:
            
        raw_tracks  =   sp.playlist_tracks(
            playlist_id =   playlist_url,
            limit       =   100,
            offset      =   offset,
            fields      =   "items(added_at,track(id,name,artists(name),album(name),duration_ms,external_ids(isrc))),next"
        )

        for row in raw_tracks["items"]:
            date = str(row["added_at"])
            info = row["track"]
            track_info = {
                "origin":           "spotify",
                "playlist_name":    playlist_name,
                "playlist_url":     playlist_url,
                "track_name":       info["name"],
                "track_id":         info["id"],
                "artist":           ", ".join([artist["name"] for artist in info["artists"]]),
                "album":            info["album"]["name"],
                "duration_ms":      info["duration_ms"],
                "added_at":         date
            }

            rows.append(track_info)
        
        if not raw_tracks["next"]: break # exit if there is no more tracks to add
        offset += 100
        
    return pd.DataFrame(rows)

def save_data(data: pd.DataFrame, user_id: str) -> None:
    today = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    output_dir = Path("exports")
    output_dir.mkdir(parents = True, exist_ok = True)

    data.to_csv(output_dir / f"spotify_{today}_{user_id}.csv", index = False)

def create_csv_backup(sp: spotipy.Spotify, urls: tuple[str, ...]) -> None:
    data: pd.DataFrame = pd.DataFrame
    concat_flag: bool = False
    for url in urls:
        playlist_data = get_playlist_tracks(sp, url)
        
        if concat_flag:
            data = pd.concat([data, playlist_data], axis = 0)
        else:
            data = playlist_data
            concat_flag = True
    
    save_data(data, user_id = sp.current_user()["id"])
#endregion


#region Upload_CSV_Backup

#endregion


#region Spotify_Handler
def get_credentials(scope: str) -> spotipy.Spotify:
    # Get credentials
    # TODO: from .env to actual writing your info. Maybe looking for a .env, if not found, ask for the data.
    envPath = ".env"

    Path(envPath).exists()
    if not dotenv.load_dotenv(envPath):
        raise RuntimeError(f"Environment Variables not found in {envPath}")

    # Connect with read permissions
    sp = spotipy.Spotify(
        auth_manager = spotipy.SpotifyOAuth(
            scope = scope,
            cache_path=".cache-playlists",
            show_dialog=True
        )
    )
    return sp


def spotify_handler(SAVE_URL: str | Sequence[str] | None = None, UPLOAD_URL: str = None):
    """"""
    
    if SAVE_URL:
        # Only read permissions
        make_backup = True
        urls = u.as_tuple(SAVE_URL)
        scope = "playlist-read-private playlist-read-collaborative user-library-read" # user-library-read : liked songs
    elif UPLOAD_URL:
        # Write permissions
        make_backup = False
        scope = "playlist-modify-private playlist-modify-public"
    else:
        # No action possible
        raise ValueError("Both SAVE_URL and UPLOAD_URL are empty, so no action can be taken")
    
    sp = get_credentials(scope)

    if make_backup:
        create_csv_backup(sp, urls)
    else:
        pass
#endregion

#region Execution_Parameters
if __name__ == "__main__":
    ORIGIN: str = "spotify" # spotify or ytmusic
    SAVE_URL: str | Sequence[str] | None = [
        r"https://open.spotify.com/playlist/03fpAdWRT8FuAXpJ4Zgmqr",
        r"https://open.spotify.com/playlist/7tWw42qiQ5HONQFGXxx5o5"
    ]
    UPLOAD_URL: str | None = None

    if ORIGIN.lower() == "spotify":
        spotify_handler(SAVE_URL, UPLOAD_URL)
    elif ORIGIN.lower() == "ytmusic":
        pass
    else:
        raise RuntimeError("Unknown origin selected: {ORIGIN}")
#endregion