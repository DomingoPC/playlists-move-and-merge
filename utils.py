from collections.abc import Sequence
import pandas as pd
import warnings

def as_tuple(x: str | Sequence[str]) -> tuple[str, ...]:
    return (x,) if isinstance(x, str) else tuple(x)

def load_tracks_from_csv(csv_path: str, origin: str) -> list[str]:
    backup = pd.read_csv(csv_path)
    
    skip_flag = (backup["origin"] != origin)
    n_skip = backup.loc[skip_flag].shape[0]
    if n_skip > 0:
        warnings.warn(f"Origin mismatch: {n_skip} tracks skipped", UserWarning)
    
    if backup.loc[~skip_flag, :].shape[0] == 0:
        raise RuntimeError("Execution stopped: no tracks can be uploaded, due to origin mismatch")
    
    return backup.loc[~skip_flag, "track_id"].tolist()