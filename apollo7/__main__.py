"""Entry point for `python -m apollo7`."""

import sys

from apollo7.app import run


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
