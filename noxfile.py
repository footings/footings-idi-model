import nox

PYTHON_TEST_VERSIONS = ["3.6", "3.7", "3.8"]


@nox.session(python=PYTHON_TEST_VERSIONS, venv_backend="conda")
def tests(session):
    session.run(
        "conda",
        "env",
        "update",
        "--prefix",
        session.virtualenv.location,
        "--file",
        "environment.yml",
        # options
        silent=False,
    )
    session.install("--no-deps", "footings")
    session.install("-e", ".", "--no-deps")
    session.run("pytest")


@nox.session(python="3.7", venv_backend="none")
def docs(session):
    session.install(".")
    session.run("sphinx-build", "-E", "-v", "-b", "html", "docs", "docs/_build")


@nox.session(python="3.7", venv_backend="none")
def changelog(session):
    session.run(
        "auto-changelog",
        "--output",
        "docs/changelog.md",
        "--unreleased",
        "true",
        "--commit-limit",
        "false",
    )
