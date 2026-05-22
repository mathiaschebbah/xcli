"""Permet `python -m xa ...` en plus du binaire `xa`."""

import sys

from .cli import cli

if __name__ == "__main__":
    sys.exit(cli())
