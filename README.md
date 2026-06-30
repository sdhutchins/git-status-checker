# git-status-checker

Yet another git status checker, in python. Because none of the bash-based ones were working on my Windows box with git-bash...

Most of this was thankfully created by [@scholer](https://github.com/scholer). I've repurposed it a bit and beautified it.

## Installation

```bash
pip install git+https://github.com/sdhutchins/git-status-checker.git
```

This will place `git-status-checker` in a python executables folder that
should be in your path.

You can also install this by cloning this repository and installing it using `pip install .` in the top level directory of the repository.

If you are using `uv`, create the virtual environment with seed packages so `pip` is available inside the venv:

```bash
uv venv --seed venv
source venv/bin/activate
python -m pip install .
```

## What it does

* Finds git repositories given a list of base directories
* Checks if any of the repositories have uncommitted changes or need to be updated with origin, i.e. if it has changes that have not been pushed, or if origin has changes that have not been pulled.

## Usage

1. Produce a list of places (base-dirs) where you have git repositories and save it to a file. It might look something like below...

   ```console
   ~/Dev/src-repos
   ~/Documents/Projects
   ~/Documents/Personal_stuff/My_project_A
    ```

2. Run `git-status-checker -f <file-with-list-of-basedirs>`.

The script will walk each base-dir, searching for git repositories, then print the status for all
repositories with outstanding commits or that can be pushed or fetched to/from origin.

### git-status-checker help message

```console
$ git-status-checker -h
usage: git-status-checker [-h] [--verbose] [--testing] [--loglevel LOGLEVEL] [--show-outdated-only] [--recursive]
                          [--no-recursive] [--followlinks] [--no-followlinks] [--ignore-untracked] [--check-fetch] [--wait]
                          [--json] [--config CONFIG] [--dirfile DIRFILE [DIRFILE ...]] [--ignorefile IGNOREFILE]
                          [basedir ...]

Git status checker script.

positional arguments:
  basedir               Base directories to scan for git repositories.

options:
  -h, --help            show this help message and exit
  --verbose, -v         Increase verbosity.
  --testing             Run app in simple test mode.
  --loglevel LOGLEVEL   Set logging output threshold level.
  --show-outdated-only  Only show repositories that are not up-to-date.
  --recursive           Scan the given basedirs recursively. This is the default.
  --no-recursive        Disable recursive scanning.
  --followlinks         Follow symbolic links when walking/scanning the basedirs.
  --no-followlinks
  --ignore-untracked    Ignore untracked files.
  --check-fetch         Check if origin has changes that can be fetched.
  --wait                If changes are found, wait for input before continuing.
  --json                Output results as JSON instead of logging.
  --config CONFIG, -c CONFIG
                        Provide arguments in a yaml file (as a dictionary).
  --dirfile DIRFILE [DIRFILE ...], -f DIRFILE [DIRFILE ...]
                        List base directories in a file.
  --ignorefile IGNOREFILE
                        File with directories to ignore (glob patterns).
```

### Other usage options

The script provides for a range of choices based on how you use it:

* You can provide base-dirs directly at the command line
* You can use multiple base-dirs-files.
* You can provide a `--config` file with command line args (if you don't want to specify them on the command line).
* You can use `--no-recursive` command line argument to disable recursive walking (it is then assumed that all "basedirs" are git repositories).
* If `--ignorefile` is not given but the current directory contains a file ".git_checker_ignore", this is used as ignorefile. (Similar to how git automatically ignores files in .gitignore).

### Configuration File

You can use a YAML configuration file to specify command-line arguments instead of typing them each time. Create a YAML file with your preferred options:

Example `config.yaml`:

```yaml
basedirs:
  - ~/Dev/src-repos
  - ~/Documents/Projects
ignore_untracked: true
check_fetch: true
show_outdated_only: true
json: false
```

Then run:

```bash
git-status-checker --config config.yaml
```

Command-line arguments will override any values specified in the config file. The config file accepts the same argument names as command-line options (using underscores instead of hyphens, e.g., `ignore_untracked` instead of `--ignore-untracked`).

### JSON Output

Use the `--json` flag to output results in JSON format instead of logging messages. This is useful for programmatic processing or integration with other tools.

Example:

```bash
git-status-checker --json ~/Dev/src-repos
```

When `--json` is enabled, the JSON payload is written to `stdout` and log messages are written to `stderr`.

The JSON output includes:
* `repositories`: Array of repository status objects, each containing:
  * `path`: Repository path
  * `local_changes`: List of uncommitted file changes
  * `ahead`: Boolean indicating if local branch is ahead of remote
  * `behind`: Boolean indicating if local branch is behind remote
  * `has_remote_changes`: Boolean indicating if there are changes to fetch
  * `up_to_date`: Boolean indicating if repository is fully up-to-date
  * `error`: Error message if status check failed, null otherwise
* `total`: Total number of repositories scanned
* `outdated`: Number of repositories that are not up-to-date

The `--show-outdated-only` flag works with JSON output, filtering to only include repositories that are not up-to-date.

## Notes

The way I've set my stuff up is that I have a .git_checker_ignore in my main "repository" folder, ~/Dev/src-repos/, which lists all
non-git repositories/folders. (I have more git repositories than non-git folders, so this is easiest for me).
I then simply run:
    `git-status-checker --ignore-untracked ~/Dev/src-repos`

Oh, and yes, you can use `~` and `*` to specify files, even on Windows.
