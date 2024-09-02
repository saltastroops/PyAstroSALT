import argparse
import os

import nox

os.environ.update({"PDM_IGNORE_SAVED_PYTHON": "1"})


nox.options.sessions = ["test", "docs"]


@nox.session
def lint(session):
    session.run_install("pdm", "install", "-G", "lint", external=True)
    session.run("pdm", "test", external=True)


@nox.session(python=["3.9", "3.10", "3.11", "3.12"])
def test(session):
    session.run_install("pdm", "install", "-G", "test", external=True)
    session.run("pdm", "test", external=True)


@nox.session
def build_docs(session):
    session.run_install("pdm", "install", "-G", "docs", external=True)
    session.run("pdm", "build_docs", external=True)


@nox.session
def publish_docs(session):
    session.run_install("pdm", "install", "-G", "docs", external=True)
    session.run("pdm", "publish_docs", external=True)


@nox.session
def check_version(session):
    """
    Check the package version against a given expected version.

    The expected version must start with a "v", which is ignored when comparing it to
    the package version.

    An error is raised if the package version differs from the expected version.

    Usage:
    $nox -s check_version -- expected_version
    """
    # Get the expected version.
    parser = argparse.ArgumentParser(description="Release a semver version.")
    parser.add_argument(
        "version",
        type=str,
        nargs=1,
        help="The type of semver release to make.",
    )
    args: argparse.Namespace = parser.parse_args(args=session.posargs)
    version: str = args.version.pop()

    # Check that the expected version starts with "v" (and then discard the "v").
    if not version.startswith("v"):
        session.error(f"The expected version ({version}) does not start with 'v'")
    version = version[1:]

    session.run_install("pdm", "install", external=True)
    command = """\
import argparse
import sys

import pyastrosalt


parser = argparse.ArgumentParser()
parser.add_argument("expected_version")
args = parser.parse_args()

package_version = pyastrosalt.__version__
expected_version = args.expected_version
if package_version != expected_version:
    print(f"The package version ({package_version}) differs from the expected version ({expected_version}).")
    sys.exit(1)
"""
    session.run("python", "-c", command, version)
