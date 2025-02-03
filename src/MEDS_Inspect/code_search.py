from functools import reduce
from operator import or_

import polars as pl


def load_code_metadata(file_path):
    metadata = pl.scan_parquet(file_path)
    return metadata


def search_codes(metadata, search_term, search_options):
    if isinstance(search_term, list):
        search_term = " ".join(search_term)
    else:
        search_term = str(search_term).lower()
    search_term = f"(?i){search_term}"
    filters = [
        (
            pl.col(option).list.contains(search_term)
            if option == "parent_codes"
            else pl.col(option).str.contains(search_term, literal=False)
        )
        for option in search_options
    ]
    combined_filter = reduce(or_, filters)

    result = (
        metadata.lazy()
        .filter(combined_filter)
        .select(["code", "description", "parent_codes"])
        .limit(1000)
        .collect()
    )
    return result
