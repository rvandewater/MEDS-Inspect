import argparse
import logging

from .cache_results import cache_results


def main():
    parser = argparse.ArgumentParser(
        description="Run caching for the MEDS INSPECT app with a specified file path."
    )
    parser.add_argument("file_path", type=str, help="The path to the MEDS data folder")
    args = parser.parse_args()

    file_path = args.file_path if args.file_path else None
    cache_results(file_path)


if __name__ == "__main__":
    logging.format = "%(asctime)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    main()
