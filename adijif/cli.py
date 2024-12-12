"""Console script for adijif."""

import sys
from typing import List

import click


@click.command()
def main(args: List[str] = None) -> None:
    """Console script for adijif.

    Args:
        args (List[str]): List of input argument
    """
    click.echo("Replace this message by putting your code into " "adijif.cli.main")
    click.echo("See click documentation at https://click.palletsprojects.com/")


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
