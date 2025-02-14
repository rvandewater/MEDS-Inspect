import argparse
import logging
import shutil
from datetime import datetime
from pathlib import Path

import polars as pl

from ..utils import get_folder_size, is_valid_path, return_data_path


def get_cache_dir(file_path):
    return Path(file_path) / ".meds_inspect_cache"


def get_metadata_dir(file_path):
    return Path(file_path) / "metadata"


def invalidate_cache(file_path):
    cache_dir = get_cache_dir(file_path)
    if cache_dir.exists() and cache_dir.is_dir():
        shutil.rmtree(cache_dir)
        logging.info(f"Cache directory {cache_dir} has been removed.")
    else:
        logging.info(f"No cache directory found at {cache_dir}.")


def get_metadata(file_path):
    if not is_valid_path(file_path):
        logging.error(f"Invalid path: {file_path}")
        return None
    metadata_dir = get_metadata_dir(file_path)
    metadata = pl.read_json(metadata_dir / "dataset.json")
    return metadata


def cache_results(file_path):
    logging.info(f"Attempting to load cached results on {file_path}")
    if not is_valid_path(file_path):
        logging.error(f"Invalid path: {file_path}")
        return None

    cache_dir = get_cache_dir(file_path)
    cache_files = {
        "general_statistics": cache_dir / "general_statistics.parquet",
        "code_count_years": cache_dir / "code_count_years.parquet",
        "code_count_subjects": cache_dir / "code_count_subjects.parquet",
        "top_codes": cache_dir / "top_codes.parquet",
        "coding_dict": cache_dir / "coding_dict.parquet",
        "numerical_code_data": cache_dir / "numerical_code_data.parquet",
    }

    # Check if all cached files exist
    cached_results = {}
    if all(path.exists() for path in cache_files.values()):
        cached_results = load_generated_cache(cache_dir, cache_files)
        return cached_results

    logging.info(f"Running cache_results on {file_path}")
    folder_size = get_folder_size(file_path)
    size_in_mb = folder_size / (1024 * 1024)
    logging.info(f"(Size: {size_in_mb:.2f} MB)")

    data_path = (
        return_data_path(file_path)
        if return_data_path(file_path)
        else Exception("Data could not be loaded: check your file setup")
    )
    data = pl.scan_parquet(data_path)

    logging.info(f"Columns in the file {data.collect_schema().names()}")
    # Create the cache directory if it does not exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not cache_files["general_statistics"].exists():
        # Compute the results and save to cache
        unique_subjects = data.select(pl.col("subject_id")).unique().count().collect()
        unique_codes = data.select(pl.col("code")).unique().count().collect()

        general_statistics = pl.DataFrame(
            {
                "Unique subjects": unique_subjects.item(),
                "Unique events": unique_codes.item(),
                "Total events": data.select(pl.len()).collect().item(),
                "Columns": [data.collect_schema().names()],
                "Size (MB)": round(size_in_mb, 2),
            }
        )
        general_statistics.write_parquet(cache_files["general_statistics"])

    if not cache_files["code_count_years"].exists():
        # Compute the results and save to cache
        code_count_years = (
            data.with_columns(pl.col("time").dt.strftime("%Y-%m").cast(pl.String).alias("Date"))
            .group_by("Date")
            .agg(pl.count("Date").alias("Amount of codes"))
            .collect()
        )
        # Get the start and end dates from the `code_count_years` DataFrame
        start_date = datetime.strptime(code_count_years.select(pl.col("Date").min()).item(), "%Y-%m")
        end_date = datetime.strptime(code_count_years.select(pl.col("Date").max()).item(), "%Y-%m")

        # Create a complete date range for the desired period
        date_range = pl.date_range(start=start_date, end=end_date, interval="1mo", closed="both", eager=True)
        date_range_df = pl.DataFrame(date_range.alias("Date")).with_columns(
            pl.col("Date").dt.strftime("%Y-%m").cast(pl.String)
        )

        # Merge with the existing data
        complete_code_count_years = date_range_df.join(code_count_years, on="Date", how="left")

        # Fill missing values with zeros
        complete_code_count_years = complete_code_count_years.fill_null(0)

        complete_code_count_years.write_parquet(cache_files["code_count_years"])

    if not cache_files["code_count_subjects"].exists():
        # Compute the results and save to cache
        code_count_subjects = (
            data.select(pl.col("subject_id"), pl.col("code"))
            .group_by(pl.col("subject_id").alias("Subject ID"))
            .agg(pl.count("code").alias("Code count"))
            .collect()
        )
        code_count_subjects.write_parquet(cache_files["code_count_subjects"])

    if not cache_files["top_codes"].exists():
        # Compute the results and save to cache
        top_codes = (
            data.group_by("code")
            .agg(pl.count("code").alias("count"))
            .sort("count", descending=True)
            .collect()
        )
        top_codes.write_parquet(cache_files["top_codes"])

    if not cache_files["coding_dict"].exists():
        # Compute the results and save to cache
        coding_dict = (
            data.with_columns(pl.col("code").str.split("/").list.first().alias("coding_dict"))
            .group_by("coding_dict")
            .agg(pl.count("coding_dict").alias("count"))
            .sort("count", descending=True)
            .collect()
        )
        coding_dict.write_parquet(cache_files["coding_dict"])

    if not cache_files["numerical_code_data"].exists():
        numerical_code_data = data.filter(
            (pl.col("numeric_value").is_not_null() & pl.col("code").is_not_null())
            & pl.col("numeric_value").is_not_nan()
        ).select(pl.col("code"), pl.col("numeric_value"))
        numerical_code_data.sink_parquet(cache_files["numerical_code_data"])

    # Load the results if they were not loaded from cache

    logging.info(f"Caching completed. Saved cache to: {cache_dir}")
    return load_generated_cache(cache_dir, cache_files)


def load_generated_cache(cache_dir, cache_files):
    cached_results = {}
    for key, path in cache_files.items():
        if key == "numerical_code_data":
            cached_results[key] = pl.scan_parquet(path)
        else:
            cached_results[key] = pl.read_parquet(path)
    logging.info(f"Cached results already available. Loaded cached results at {cache_dir}")
    return cached_results


def main():
    parser = argparse.ArgumentParser(description="Run cache_results with a specified file path.")
    parser.add_argument("--file_path", type=str, help="The path to the MEDS data folder")
    parser.add_argument("--invalidate", action="store_true", help="Invalidate the cache")
    args = parser.parse_args()

    file_path = args.file_path
    if args.invalidate:
        invalidate_cache(file_path)
    cache_results(file_path)


if __name__ == "__main__":
    logging.format = "%(asctime)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    main()
