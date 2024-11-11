# type: ignore


def test_help(cli, capsys):
    result = cli(["--help"])
    output = capsys.readouterr().err.rstrip()

    assert result == 0
    assert "usage: {{ cookiecutter.project_slug }}" in output
