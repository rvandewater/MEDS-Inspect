import os
from pathlib import Path

import polars as pl

def cache_results(file_path, top_n):
    cache_dir = Path(file_path) / "cache"

    print("file_path", file_path)
    data = pl.scan_parquet(Path(file_path) / "data/*/*.parquet" )
    print("Columns in the file:", data.columns)
    # Create the cache directory if it does not exist
    cache_dir.mkdir(parents=True, exist_ok=True)

    code_count_years_path = cache_dir / "code_count_years.parquet"
    if code_count_years_path.exists():
        # Load the cached results
        code_count_years = pl.read_parquet(code_count_years_path)
    else:
        # Compute the results and save to cache
        code_count_years = (
            data
            # .select(pl.col("time"))
            .filter((pl.col("time") >= pl.datetime(2000, 1, 1)) & (pl.col("time") <= pl.datetime(2025, 12, 31)))
            .with_columns(pl.col("time").dt.strftime("%Y-%m").cast(pl.String).alias("time_str"))
            .group_by("time_str")
            .agg(pl.count("time_str").alias("count"))
            # .collect()
        )
        code_count_years.sink_parquet(code_count_years_path)

    code_count_subjects_path = cache_dir / "code_count_subjects.parquet"
    if code_count_subjects_path.exists():
        # Load the cached results
        code_count_subjects = pl.read_parquet(code_count_subjects_path)
    else:
        # Compute the results and save to cache
        code_count_subjects = (data
            .select(pl.col("subject_id"), pl.col("code"))
            .group_by("subject_id")
            .agg(pl.count("code").alias("count"))
            .collect()
        )
        code_count_subjects.write_parquet(code_count_subjects_path)
    top_codes_path = cache_dir / f"top_{top_n}_codes.parquet"
    if top_codes_path.exists():
        # Load the cached results
        top_codes = pl.read_parquet(top_codes_path)
    else:
        # Compute the results and save to cache
        top_codes = (
            data
            .group_by("code")
            .agg(pl.count("code").alias("count"))
            .sort("count", descending=True)
            .limit(top_n)
            .collect()
        )
    return code_count_years, code_count_subjects, top_codes