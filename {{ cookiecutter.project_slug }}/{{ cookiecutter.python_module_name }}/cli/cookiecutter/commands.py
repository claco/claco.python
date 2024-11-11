import click
import glob
import json
import logging
import pathlib
import os
import pty
import re
import shutil
import subprocess

from click import Context, Parameter
from cookiecutter.main import cookiecutter
from enum import auto, StrEnum
from io import TextIOWrapper
from pathlib import Path
from typing import Self, Hashable
from os import PathLike


logger = logging.getLogger("{{ cookiecutter.python_script_name }}")


class TemplateFileAction(StrEnum):
    """Action to take for the template file being processed"""

    COPY = auto()
    """Copy the project file to the template path without modification"""

    PATCH = auto()
    """Patch the template path with the project file contents using git interactive patch process"""

    IGNORE = auto()
    """Add the file to .gitignore"""

    SKIP = auto()
    """Skip the project file and take no further action"""

    @classmethod
    def from_click_action(cls, action: str) -> Self:
        """Convert an action prompt response to the corresponding enum"""

        action = action.strip().lower()[0:]

        return list(filter(lambda n: n.startswith(action), cls))[0]


class ExpandedPathParamType(click.Path):
    """Custom click.Path ParamType that expands user paths and path variables"""

    def convert(self, value: str | PathLike[str], param: Parameter | None, ctx: Context | None):
        logger.debug(f"value={value}, paran={param}, ctx={ctx}")

        if isinstance(value, int):
            return value

        value = os.path.expandvars(value)
        value = str(Path(value).expanduser())

        return super().convert(value, param, ctx)


@click.group("cookiecutter")
def cli():
    pass


# region apply


@click.command
@click.pass_context
@click.option(
    "--project-path",
    default=".",
    help="Path of the project being updated",
    type=click.Path(exists=True, file_okay=False, readable=True, resolve_path=True, path_type=pathlib.Path),
)
@click.option(
    "--replay-file", help="Path of the cookiecutter replay file", default=".cookiecutter.json", type=click.File()
)
@click.option(
    "--template-path",
    help="Path of the cookiecutter template to apply",
    type=click.Path(exists=True, file_okay=False, readable=True, resolve_path=True, path_type=pathlib.Path),
)
def apply(ctx: Context, template_path: Path, project_path: Path, replay_file: TextIOWrapper):
    """Apply cookiecutter template to the project"""

    logger.debug(f"template_path={template_path}, project_path={project_path}, replay_file={replay_file.name}")

    replay_content = json.load(replay_file).get("cookiecutter", {})

    # get the cookiecutter template url and ensure we have an https connection for ourselves
    if not template_path:
        repository_url = replay_content.get("_repository_url").strip().lower()
        repository_url = re.sub(r"(git@|git://|https://)(.*?)(:|/)", rf"https://\2/", repository_url, flags=re.DOTALL)
        template_path = repository_url
        logger.debug(f"repository_url={repository_url}")

    cookiecutter(
        template_path,
        no_input=True,
        extra_context=replay_content,
        output_dir="..",
        skip_if_file_exists=False,
        overwrite_if_exists=True,
    )


# endregion


# region integrate


@click.command
@click.pass_context
@click.option(
    "--project-path",
    default=".",
    help="Path of the project to reintegrate",
    type=click.Path(exists=True, file_okay=False, readable=True, resolve_path=True, path_type=pathlib.Path),
)
@click.option(
    "--replay-file", help="Path of the cookiecutter replay file", default=".cookiecutter.json", type=click.File()
)
@click.option(
    "--template-path",
    help="Path of the cookiecutter template to integrate changes into",
    type=click.Path(exists=True, file_okay=False, readable=True, resolve_path=True, path_type=pathlib.Path),
)
@click.option("--ignore-unstaged-changes", help="Ignore unstaged changes in template path", type=bool, is_flag=True)
def integrate(
    ctx: Context, template_path: Path, project_path: Path, replay_file: TextIOWrapper, **kwargs: dict[str, object]
):
    """Reintegrate project changes into cookiecutter template"""

    logger.debug(f"template_path={template_path}, project_path={project_path}, replay_file={replay_file.name}")

    # get cookiecutter replay configuration for project path
    replay_configuration = get_replay_configuration(replay_file)

    # set template path from replay configuration if not specified
    if not template_path:
        template_path = get_template_path(replay_configuration)

    # ensure no unstaged content in template path before we reintegrate changes
    ignore_unstaged_changes = kwargs.get("ignore_unstaged_changes", False)
    if not ignore_unstaged_changes:
        if has_unstaged_changes(template_path):
            logger.error(
                f"cookiecutter template '{template_path}' has unstaged changes. stage or stash your changes or pass '--ignore-unstaged-changes'"
            )
            ctx.exit(1)

    # get list of project files to reintegrate, honoring .gitignore
    project_files = get_project_files(project_path)

    # get a list of all templated paths, converted to their project path values
    templated_paths = get_templated_paths(project_path, template_path, replay_configuration)

    # process project files
    click.echo("Integrating project into template:\n")
    click.echo(f"   project: {click.style(project_path, fg="cyan", bold=True)}")
    click.echo(f"  template: {click.style(template_path, fg="cyan", bold=True)}")
    click.echo(f"     files: {click.style(len(project_files), bold=True)}")

    for project_file in project_files:
        template_file = templated_paths.get(project_file)

        # if there is no existing template path, search up through parents
        if not template_file:
            for parent in project_file.parents:
                template_parent_path = templated_paths.get(parent)
                if template_parent_path:
                    relate_template_path = project_file.relative_to(parent)
                    template_file = template_parent_path.joinpath(relate_template_path)
                    break

        logger.debug(f"project_file={project_file}, template_file={template_file}")

        if not has_changes(project_file, template_file):
            click.echo(f"\n      skipping '{project_file}' has not changed")
            continue

        template_file_action = prompt_file_action(project_file, template_file)
        logger.debug(f"template_file_action={template_file_action.name}")

        match template_file_action:
            case TemplateFileAction.COPY:
                template_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(project_file), str(template_file))
                click.echo(f"\n      copied '{project_file}' to '{template_file}'")

            case TemplateFileAction.IGNORE:
                git_ignore_entry = ignore_template_file(template_path, template_file)
                click.echo(f"\n      added '{git_ignore_entry}' to '{template_path.joinpath(".gitignore")}'")

            case TemplateFileAction.PATCH:
                template_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(str(project_file), str(template_file))
                click.echo()
                subprocess.call(
                    f"git add --all --patch '{template_file}'",
                    cwd=template_path,
                    stdin=click.get_text_stream("stdin"),
                    stdout=click.get_text_stream("stdout"),
                    stderr=click.get_text_stream("stderr"),
                    shell=True,
                )

            case TemplateFileAction.SKIP:
                click.echo(f"\n      skipping '{project_file}'")
                continue

    click.echo("\nfinished integrating project! 🚀\n")


# endregion


def get_project_files(project_path: Path, resolve_paths: bool = True) -> list[Path]:
    """Returns a list of all files in the project path that are not matched by .gitignore."""

    logger.debug(f"project_path='{project_path}'")

    # ensure project path is a repo, init is idempotent
    subprocess.run(f"git init --quiet '{project_path}'", shell=True, check=True)

    project_files = [
        project_path.joinpath(file) if resolve_paths else Path(file)
        for file in subprocess.check_output(
            "git ls-files --cached --modified --deduplicate --others --exclude-standard -- :",
            cwd=project_path,
            encoding="utf8",
            shell=True,
        )
        .strip()
        .split("\n")
    ]

    logger.debug(f"project_files={project_files}")

    return project_files


def get_replay_configuration(replay_file: TextIOWrapper) -> dict[str, str]:
    """Returns the cookiecutter replay configuration"""

    logger.debug(f"replay_file={replay_file.name}")

    replay_configuration = json.load(replay_file).get("cookiecutter", {})

    logger.debug(f"replay_configuration={replay_configuration}")

    return replay_configuration


def get_template_path(replay_configuration: dict[str, Path]) -> Path:
    """Get the template path from replay configuration, prompting the user for a default if necessary"""

    template_path_setting = replay_configuration.get("_template")
    template_path: Path

    if template_path_setting:
        template_path_setting = os.path.expandvars(template_path_setting)
        template_path = Path(template_path_setting).resolve()
        template_path = template_path.expanduser()
    else:
        template_path = click.prompt(
            "template path",
            type=ExpandedPathParamType(
                exists=True, file_okay=False, dir_okay=True, writable=True, resolve_path=True, allow_dash=False
            ),
        )

    logger.debug(f"template_path={template_path}")

    return template_path


def get_templated_paths(
    project_path: Path, template_path: Path, replay_configuration: dict[str, str]
) -> dict[Path, Path]:
    """Returns a dict of all known project paths converted to template paths using cookiecutter replay configuration"""

    logger.debug(f"template_path={template_path}, replay_configuration={replay_configuration}")

    templated_paths: dict[Path, Path] = dict()

    project_slug_path = get_project_slug_path(template_path)

    cookiecutter_file_paths = get_project_files(project_slug_path, resolve_paths=False)
    for cookiecutter_file_path in cookiecutter_file_paths:
        template_file_path = str(cookiecutter_file_path)

        for k, v in replay_configuration.items():
            # using raw here to deal with multipkle escapings and cookiecutter proccessing jinja
            # {% raw %}
            cookiecutter_key = f"{{{{ cookiecutter.{str(k)} }}}}"

            template_file_path = str(re.sub(rf"{cookiecutter_key}", str(v), template_file_path))

            logger.debug(f"s/{{{{ cookiecutter.{k} }}}}/{v}/={template_file_path}")
            # {% endraw %}

        profile_file_path = project_path.joinpath(template_file_path)
        templated_paths[profile_file_path] = project_slug_path.joinpath(cookiecutter_file_path)
        templated_paths[profile_file_path.parent] = project_slug_path.joinpath(cookiecutter_file_path).parent

    logger.debug(f"templated_paths={templated_paths}")

    return templated_paths


def get_project_slug_path(template_path: Path) -> Path:
    """Returns the path to to main project folder in the template path. Defaults to 'cookiecutter.project_slug'."""

    # using raw here to deal with multipkle escapings and cookiecutter proccessing jinja
    # {% raw %}
    project_slug_path = "{{ cookiecutter.project_slug }}"
    # {% endraw %}

    return template_path.joinpath(project_slug_path)


def has_changes(project_file: Path, template_file: Path | None) -> bool:
    """Returns True if the the project and template files differ or the file is new"""

    logger.debug(f"project_file={project_file}, template_file={template_file}")

    # if the file exists, git diff, otherwise, assume new file
    if template_file.exists():
        retval = subprocess.call(
            f"git diff --exit-code '{project_file}' '{template_file}' > /dev/null", encoding="utf8", shell=True
        )

        return retval != 0
    else:
        return True


def has_unstaged_changes(template_path: Path) -> bool:
    """Returns True if the template path contains unstaged changes"""

    logger.debug(f"template_path={template_path}")

    unstaged_changes = list(
        filter(
            None,
            subprocess.check_output(
                "git ls-files --deleted --modified --others --exclude-standard -- :",
                cwd=template_path,
                encoding="utf8",
                shell=True,
            ).split("\n"),
        )
    )

    logger.debug(f"unstaged_changes={unstaged_changes}")

    return len(unstaged_changes) > 0


def ignore_template_file(template_path: Path, template_file: Path) -> str:
    """Adds the relative template file path to .gitignore and returns the .gitignore entry"""

    ignore_file_path = str(template_file).removeprefix(str(template_path) + os.path.sep)

    logger.debug(f"template_path={template_path}, template_file={template_file}, ignore_file_path={ignore_file_path}")

    with open(template_path.joinpath(".gitignore"), "a+") as gitignore:
        gitignore.seek(0)
        git_ignore_patterns = gitignore.read().split("\n")
        if ignore_file_path in git_ignore_patterns:
            logger.debug(f"'{ignore_file_path}' already in .gitignore")
        else:
            gitignore.write(f"{ignore_file_path}\n")

    return ignore_file_path


def prompt_file_action(project_file: Path, template_file: Path | None) -> TemplateFileAction:
    """Prompts the user for the desired project file action"""

    choices = ["[c]opy", "[s]kip"]

    logger.debug(f"project_file={project_file}, template_file={template_file}")

    # only interactive on existing files
    if template_file and template_file.exists():
        if has_changes(project_file, template_file):
            choices.append("[p]atch")
        else:
            return TemplateFileAction.SKIP
    elif template_file and not template_file.exists():
        choices.append("[i]gnore")

    choices.sort()
    click.echo()

    action = click.prompt(
        f" integrate: {click.style(project_file, fg="cyan")}\n      into: {click.style(template_file, fg="cyan")} ?\n\n      {', '.join(choices)}",
        default="s",
        show_choices=False,
        show_default=True,
        type=click.Choice([c[1] for c in choices], case_sensitive=False),
    )

    return TemplateFileAction.from_click_action(action)
