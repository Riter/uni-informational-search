import sys

from config import load_config
from crawler import SearchBot
from logging_conf import setup_logging


def main():
    if len(sys.argv) != 2:
        print("Usage:\n  python run_crawler.py config.yaml")
        sys.exit(1)
    cfg = load_config(sys.argv[1])
    setup_logging()
    bot = SearchBot(cfg)
    bot.run()


if __name__ == "__main__":
    main()
