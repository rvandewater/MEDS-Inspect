import os
from pathlib import Path


def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def is_valid_path(path):
    if path is None or path == "":
        return False
    if not os.path.isdir(path):
        return False

    data_dir = Path(path) / "data"
    metadata_dir = Path(path) / "metadata"

    if not data_dir.is_dir() or not metadata_dir.is_dir():
        return False

    data_files = list(data_dir.rglob("*.parquet"))
    metadata_files = list(metadata_dir.rglob("*.parquet"))

    return len(data_files) > 0 and len(metadata_files) > 0