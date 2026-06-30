import json
import subprocess
import sys
from pathlib import Path


MODULE_NAME = "git_status_checker.git_status_checker"


def run_cli(*args, cwd=None):
    """Run the CLI and capture stdout/stderr separately."""
    return subprocess.run(
        [sys.executable, "-m", MODULE_NAME, *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def init_repo(path, bare=False):
    """Create a git repository that the CLI can inspect."""
    repo_args = ["git", "init", "-q", str(path)]
    if bare:
        repo_args.insert(2, "--bare")
    subprocess.run(repo_args, check=True)


def configure_repo(path):
    """Set local git identity so commits work in temp repos."""
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "tester"],
        check=True,
    )


def commit_file(path, name="file.txt", contents="data\n", message="commit"):
    """Write and commit one file into the repository."""
    (path / name).write_text(contents)
    subprocess.run(["git", "-C", str(path), "add", name], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", message], check=True)


def test_config_file_is_loaded(tmp_path):
    repo_path = tmp_path / "repo"
    init_repo(repo_path)

    config_path = tmp_path / "config.yml"
    config_path.write_text(f"basedirs:\n  - {repo_path}\njson: true\n")

    result = run_cli("--config", str(config_path))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert payload["repositories"][0]["path"] == str(repo_path)


def test_json_output_stays_on_stdout(tmp_path):
    repo_path = tmp_path / "repo"
    init_repo(repo_path)

    result = run_cli("--json", str(repo_path))

    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert "Basedir:" in result.stderr


def test_no_recursive_only_checks_given_directories(tmp_path):
    parent_path = tmp_path / "parent"
    child_repo_path = parent_path / "child"
    child_repo_path.mkdir(parents=True)
    init_repo(child_repo_path)

    result = run_cli("--json", "--no-recursive", str(parent_path))

    assert result.returncode == 127
    assert result.stdout == ""
    assert "No git repositories found!" in result.stderr


def test_human_output_reports_ahead_status(tmp_path):
    remote_repo_path = tmp_path / "remote.git"
    work_repo_path = tmp_path / "work"

    init_repo(remote_repo_path, bare=True)
    init_repo(work_repo_path)
    configure_repo(work_repo_path)
    commit_file(work_repo_path, message="initial")

    subprocess.run(["git", "-C", str(work_repo_path), "branch", "-M", "main"], check=True)
    subprocess.run(
        ["git", "-C", str(work_repo_path), "remote", "add", "origin", str(remote_repo_path)],
        check=True,
    )
    subprocess.run(["git", "-C", str(work_repo_path), "push", "-qu", "origin", "main"], check=True)

    commit_file(work_repo_path, contents="more\n", message="ahead")

    result = run_cli(str(work_repo_path))

    assert result.returncode == 1
    assert "Local branch is ahead of upstream." in result.stderr
    assert "\nTrue\n" not in result.stderr


def test_verbose_enables_debug_logging(tmp_path):
    repo_path = tmp_path / "repo"
    init_repo(repo_path)

    result = run_cli("--verbose", str(repo_path))

    assert result.returncode == 0
    assert "[DEBUG | GIT-STATUS-CHECKER]:" in result.stderr
    assert "Scanning 1 basedirs" in result.stderr
