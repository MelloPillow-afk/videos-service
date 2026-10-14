"""Run Yoyo explicitly using the application's environment configuration."""

import argparse
import os
import subprocess
from pathlib import Path

from src.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["apply", "list"])
    args = parser.parse_args()
    config = Path.cwd() / "yoyo.ini"
    if not config.is_file():
        parser.error("Run migrations from the videos-service repository root")

    url = Settings().database_url.get_secret_value()
    remainder = url.split("://", 1)[1]
    environment = {**os.environ, "YOYO_DATABASE_URL": f"postgresql+psycopg://{remainder}"}
    subprocess.run(["yoyo", "--config", str(config), args.command], env=environment, check=True)


if __name__ == "__main__":
    main()
