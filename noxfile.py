import os
import shutil
import nox


@nox.session(venv_backend="none")
def run_tests(session):
    session.run("poetry", "install")
    session.run("poetry", "run", "pip", "show", "footings")
    session.run("poetry", "run", "pytest", "-vv")


@nox.session(venv_backend="none")
def run_coverage(session):
    session.run("poetry", "install")
    session.run("poetry", "run", "pip", "show", "footings")
    session.run("poetry", "run", "pytest", "--cov=./", "--cov-report=xml")


@nox.session(venv_backend="none")
def create_docs(session):
    if os.path.exists("./docs/jupyter_execute"):
        shutil.rmtree("./docs/jupyter_execute")
    if os.path.exists("./docs/_build"):
        shutil.rmtree("./docs/_build")
    session.run("poetry", "install")
    session.run("poetry", "run", "pip", "show", "footings")
    session.run(
        "poetry", "run", "sphinx-build", "-E", "-v", "-b", "html", "docs", "docs/_build"
    )


@nox.session(venv_backend="none")
def update_changelog(session):
    session.run(
        "auto-changelog",
        "--output",
        "docs/changelog.md",
        "--unreleased",
        "true",
        "--commit-limit",
        "false",
    )
