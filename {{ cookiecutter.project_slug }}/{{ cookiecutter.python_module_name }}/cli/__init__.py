import configargparse as argparse  # type: ignore
import logging
import os
import sys


logger = logging.getLogger("{{ cookiecutter.project_slug }}")


def main(argv: list[str] = []) -> int:
    """
    Main entry point for the `{{ cookiecutter.project_slug }}` command line utility.
    Args:
        argv (list[str]], optional): Arguments to use when executing `{{ cookiecutter.project_slug }}`. Defaults to `sys.argv`.
    Returns:
        int: 0 if successful. 2 for any caught exceptions.
    """

    argv = argv or sys.argv[1:]
    format = "%(asctime)s %(name)s %(levelname)s [%(filename)s:%(lineno)s:%(funcName)s] %(message)s"
    level = os.environ.get("LOG_LEVEL", logging.INFO)
    if "--debug" in argv:
        level = logging.DEBUG

    message = None
    retval = 0

    logging.basicConfig(
        encoding="utf-8", datefmt="%Y-%m-%dT%H:%M:%S%z", format=format, level=level
    )
    logger.debug(f"argv={argv}")

    parser = argparse.ArgumentParser(prog="{{ cookiecutter.project_slug }}", add_help=False)
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug level logging and output",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Enable dry run/read only testing mode",
    )
    parser.add_argument(
        "--help", action="store_true", default=False, help="Display this help message"
    )

    try:
        arguments, unknown = parser.parse_known_args(argv)  # type: ignore
        logger.debug(f"arguments={arguments}")

        if arguments.help:  # type: ignore
            print(parser.format_help(), file=sys.stderr)
        else:
            pass

    except BaseException as ex:
        retval = 2
        message = str(ex)

    if message:
        print(message, file=sys.stderr)

    return retval


if __name__ == "__main__":
    sys.exit(main())
