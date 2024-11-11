import click
import logging
import os
import sys

from .cookiecutter import commands


logger = logging.getLogger("{{ cookiecutter.python_script_name }}")


@click.group
@click.option("--debug", is_flag=True)
def cli(debug: bool):
    pass


def main():
    format = "%(levelname)s: %(message)s"
    level = os.environ.get("LOG_LEVEL", logging.INFO)

    if "--debug" in sys.argv:
        format = "%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)s:%(funcName)s] %(message)s"
        sys.argv.remove("--debug")
        level = logging.DEBUG

    logging.basicConfig(encoding="utf-8", datefmt="%Y-%m-%dT%H:%M:%S%z", format=format, level=level)

    cli.add_command(commands.cli)

    cli()


if __name__ == "__main__":
    sys.exit(main())
