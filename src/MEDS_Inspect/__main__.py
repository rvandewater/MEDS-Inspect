import argparse
import logging

from .app import run_app


def main():
    parser = argparse.ArgumentParser(description="Run the MEDS INSPECT app with a specified file path.")
    parser.add_argument("--file_path", type=str, help="The path to the MEDS data folder")
    parser.add_argument("--port", type=int, help="The port to run the app on", default=8050)
    args = parser.parse_args()

    file_path = args.file_path if args.file_path else None
    run_app(file_path, args.port)


if __name__ == "__main__":
    logging.format = "%(asctime)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    main()
