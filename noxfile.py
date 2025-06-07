import nox

nox.options.default_venv_backend = "venv"
nox.options.reuse_existing_virtualenvs = True

PYPROJECT = nox.project.load_toml("pyproject.toml")
PYTHON_VERSIONS = nox.project.python_versions(PYPROJECT)


@nox.session(python=PYTHON_VERSIONS[0])
def lint(session):
    session.install(".[dev,test]")
    session.run("ruff", "format", "--check", "src", "tests")
    session.run("ruff", "check", "src", "tests")
    session.run("mypy", "src")


@nox.session(python=PYTHON_VERSIONS)
def test(session):
    session.install(".[test]")
    session.run(
        "pytest",
        "--cov=memoized_lambda",
        "tests",
    )
