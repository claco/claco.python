import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from {{ cookiecutter.python_module_name }}.app.main import app as application
from {{ cookiecutter.python_module_name }}.cli import main as command


@pytest.fixture()
def app() -> FastAPI:
    return application


@pytest.fixture
def cli():
    return command


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(application)
