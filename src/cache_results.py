import logging
from pathlib import Path
import polars as pl
import argparse
from utils import get_folder_size, is_valid_path


def cache_results(file_path):
    cache_dir = Path(file_path) / ".meds_inspect_cache"
    logging.info(f"Attempting to load cached results on {file_path}")
    if not is_valid_path(file_path):
        logging.error(f"Invalid path: {file_path}")
        return None
    # Check if all cached files exist
    code_count_years_path = cache_dir / "code_count_years.parquet"
    code_count_subjects_path = cache_dir / "code_count_subjects.parquet"
    top_codes_path = cache_dir / "top_codes.parquet"
    coding_dict_path = cache_dir / "coding_dict.parquet"

    if (code_count_years_path.exists() and
        code_count_subjects_path.exists() and
        top_codes_path.exists() and
        coding_dict_path.exists()):
        # Load the cached results
        code_count_years = pl.read_parquet(code_count_years_path)
        code_count_subjects = pl.read_parquet(code_count_subjects_path)
        top_codes = pl.read_parquet(top_codes_path)
        coding_dict = pl.read_parquet(coding_dict_path)
        logging.info(f"Cached results already available. Loaded cached results at {cache_dir}")
        return code_count_years, code_count_subjects, top_codes, coding_dict

    logging.info(f"Running cache_results on {file_path}")
    folder_size = get_folder_size(file_path)
    size_in_mb = folder_size / (1024 * 1024)
    logging.info(f'(Size: {size_in_mb:.2f} MB)')

    # Check if data is one or two levels deep
    data_path_1 = Path(file_path) / "data/*/*.parquet"
    data_path_2 = Path(file_path) / "data/*.parquet"

    if list(Path(file_path).glob("data/*/*.parquet")):
        data = pl.scan_parquet(data_path_1)
        logging.info(f"Loading data from {data_path_1}")
    elif list(Path(file_path).glob("data/*.parquet")):
        data = pl.scan_parquet(data_path_2)
        logging.info(f"Loading data from {data_path_2}")
    else:
        logging.error("No data found in the specified paths.")
        return None

    logging.info(f"Columns in the file {data.collect_schema().names()}")
    # Create the cache directory if it does not exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Initialize variables
    code_count_years = None
    code_count_subjects = None
    top_codes = None
    coding_dict = None

    if not code_count_years_path.exists():
        # Compute the results and save to cache
        code_count_years = (
            data
            # .filter((pl.col("time") >= pl.datetime(2000, 1, 1)) & (pl.col("time") <= pl.datetime(2025, 12, 31)))
            .with_columns(pl.col("time").dt.strftime("%Y-%m").cast(pl.String).alias("Month/Year"))
            .group_by("Month/Year")
            .agg(pl.count("Month/Year").alias("Amount of codes"))
        )
        code_count_years.sink_parquet(code_count_years_path)

    if not code_count_subjects_path.exists():
        # Compute the results and save to cache
        code_count_subjects = (
            data
            .select(pl.col("subject_id"), pl.col("code"))
            .group_by("subject_id")
            .agg(pl.count("code").alias("count"))
            .collect()
        )
        code_count_subjects.write_parquet(code_count_subjects_path)

    if not top_codes_path.exists():
        # Compute the results and save to cache
        top_codes = (
            data
            .group_by("code")
            .agg(pl.count("code").alias("count"))
            .sort("count", descending=True)
            .collect()
        )
        top_codes.write_parquet(top_codes_path)

    if not coding_dict_path.exists():
        # Compute the results and save to cache
        coding_dict = (
            data
            .with_columns(pl.col("code").str.split("/").list.first().alias("coding_dict"))
            .group_by("coding_dict")
            .agg(pl.count("coding_dict").alias("count"))
            .sort("count", descending=True)
            .collect()
        )
        coding_dict.write_parquet(coding_dict_path)

    # Load the results if they were not loaded from cache
    if code_count_years is None:
        code_count_years = pl.read_parquet(code_count_years_path)
    if code_count_subjects is None:
        code_count_subjects = pl.read_parquet(code_count_subjects_path)
    if top_codes is None:
        top_codes = pl.read_parquet(top_codes_path)
    if coding_dict is None:
        coding_dict = pl.read_parquet(coding_dict_path)

    logging.info(f"Caching completed. Saved cache to: {cache_dir}")
    return code_count_years, code_count_subjects, top_codes, coding_dict

def main():
    parser = argparse.ArgumentParser(description='Run cache_results with a specified file path.')
    parser.add_argument('file_path', type=str, help='The path to the MEDS data folder')
    args = parser.parse_args()

    file_path = args.file_path

    cache_results(file_path)

if __name__ == '__main__':
    logging.format = '%(asctime)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    main()