# type: ignore


def test_help(cli, capsys):
    result = cli(["--help"])
    output = capsys.readouterr().err.rstrip()

    assert result == 0
    assert "usage: {{ cookiecutter.python_script_name }}" in output
