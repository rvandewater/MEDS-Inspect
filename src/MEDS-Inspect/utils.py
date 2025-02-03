import logging
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


def return_data_path(file_path):
    # Check if data is one or two levels deep
    data_path_1 = Path(file_path) / "data/*/*.parquet"
    data_path_2 = Path(file_path) / "data/*.parquet"

    if list(Path(file_path).glob("data/*/*.parquet")):
        return data_path_1
    elif list(Path(file_path).glob("data/*.parquet")):
        return data_path_2
    else:
        logging.error("No data found in the specified paths.")
        return None
