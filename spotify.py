import dotenv
from pathlib import Path
import pandas as pd
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from collections.abc import Sequence
import utils as u

#region Create_CSV_Backup
def get_raw_tracks(sp: spotipy.Spotify, url: str, offset: int, is_liked_songs: bool):
    if is_liked_songs:
        return sp.current_user_saved_tracks(
            limit       =   100,
            offset      =   offset,
            fields      =   "items(added_at,track(id,name,artists(name),album(name),duration_ms,external_ids(isrc))),next"
        )
    else:
        return sp.playlist_tracks(
            playlist_id =   url,
            limit       =   100,
            offset      =   offset,
            fields      =   "items(added_at,track(id,name,artists(name),album(name),duration_ms,external_ids(isrc))),next"
        )

def get_playlist_tracks(sp: spotipy.Spotify, playlist_url: str) -> pd.DataFrame:
    """Extract tracks from a url (only read permissions needed)"""
    playlist_name = sp.playlist(playlist_id = playlist_url, fields = "name")["name"]

    is_liked_songs = False
    if playlist_url == "https://open.spotify.com/collection/tracks":
        is_liked_songs = True

    # Create a list accounting for the offset
    rows, offset = [], 0
    while True:

        raw_tracks = get_raw_tracks(sp, playlist_url, offset, is_liked_songs)  
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
def get_users_playlists(sp: spotipy.Spotify) -> list[str]:
    names: list[str] = []
    playlists = sp.current_user_playlists()
    while playlists:
        for i, playlist in enumerate(playlists['items']):
            names.append(playlist["name"])
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None

    return names



def upload_csv(sp: spotipy.Spotify, playlist_name: str | None, csv_path: str) -> None:
    csv_path = Path(csv_path)

    if not playlist_name or len(playlist_name.strp()) == 0:
        playlist_name = f"Backup_{datetime.now().strftime("%d_%m_%Y")}"

    # Create new playlist and check name duplicates
    existing_names = get_users_playlists(sp)
    
    while playlist_name in existing_names:
        playlist_name = playlist_name + "_1"

    newPlaylist = sp.user_playlist_create(
        user = sp.current_user()["id"],
        name = playlist_name,
        public = False, # inconsistent (?)
        description = f"Generated from CSV Backup. Uploaded: {datetime.now().strftime("%d-%m-%Y, %H:%M:%S")}"
    )
    
    sp.user_playlist_change_details(sp.current_user()["id"], newPlaylist["id"], public=False)
    
    # Load tracks and extract id
    tracks_id = u.load_tracks_from_csv(csv_path, ORIGIN)

    # Upload tracks to new playlist
    sp.user_playlist_add_tracks(
        user = sp.current_user()["id"],
        playlist_id = newPlaylist["id"],
        tracks = tracks_id
    )

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


def spotify_handler(SAVE_URL: str | Sequence[str] | None = None, UPLOAD_NAME: str = None, BACKUP_PATH: str | None = None):
    """"""
    scope = "playlist-modify-private playlist-modify-public playlist-read-private playlist-read-collaborative user-library-read" # user-library-read : liked songs
    sp = get_credentials(scope)

    if SAVE_URL:
        urls = u.as_tuple(SAVE_URL)
        create_csv_backup(sp, urls)
    
    if BACKUP_PATH:
        upload_csv(sp, UPLOAD_NAME, BACKUP_PATH)
    
    if not SAVE_URL and not UPLOAD_NAME:
        # No action possible
        raise ValueError("Both SAVE_URL and UPLOAD_NAME are empty, so no action can be taken")
    
#endregion

#region Execution_Parameters
if __name__ == "__main__":
    ORIGIN: str = "spotify" # spotify or ytmusic
    
    # Backup
    SAVE_URL: str | Sequence[str] | None = [
        r"https://open.spotify.com/playlist/03fpAdWRT8FuAXpJ4Zgmqr",
        r"https://open.spotify.com/playlist/7tWw42qiQ5HONQFGXxx5o5"
    ]
    
    # Upload Backup to Spotify
    UPLOAD_NAME: str | None = None
    BACKUP_PATH: str = r"exports\spotify_2025-08-26_223541_domnes42.csv"

    if ORIGIN.lower() == "spotify":
        spotify_handler(SAVE_URL, UPLOAD_NAME, BACKUP_PATH)
    elif ORIGIN.lower() == "ytmusic":
        pass
    else:
        raise RuntimeError(f"Unknown origin selected: {ORIGIN}")
#endregion