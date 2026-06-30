#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#    Copyright 2015 Rasmus Scholer Sorensen, rasmusscholer@gmail.com
#
#    Edited by Shaurita D. Hutchins
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#

# pylint: disable=C0103

"""

Check git repositories for uncommitted changes and sync status with origin.


Inspired by:
* github.com/TomHodson/Git-Status-Notifier
* github.com/natemara/git_check
* github.com/yonchu/git-check

Python git bindings (not used, but still worth mentioning):
* pypi.python.org/pypi/GitPython
* github.com/libgit2/pygit2

"""


import sys
import os
import re
import json
import yaml
import glob
import argparse
import subprocess
from fnmatch import fnmatch
from logzero import LogFormatter, setup_logger, logging


_log_format = ("%(color)s[%(levelname)s | %(name)s]:%(end_color)s %(message)s")
_formatter = LogFormatter(fmt=_log_format)

logger = setup_logger(name="GIT-STATUS-CHECKER", level=logging.INFO,
                      formatter=_formatter)

DEFAULT_LOG_LEVEL = logging.INFO
VERBOSE_LOG_LEVEL = logging.DEBUG


def parse_args(argv=None):
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description="Git status checker script.")
    parser.add_argument("--verbose", "-v", action="count", help="Increase verbosity.")
    parser.add_argument("--testing", action="store_true", help="Run app in simple test mode.")
    parser.add_argument("--loglevel", default=logging.INFO, help="Set logging output threshold level.")
    
    # Add the new argument here
    parser.add_argument("--show-outdated-only", action="store_true",
                        help="Only show repositories that are not up-to-date.")

    parser.add_argument("--recursive", action="store_true", help="Scan the given basedirs recursively. This is the default.")
    parser.add_argument("--no-recursive", action="store_false", dest="recursive", help="Disable recursive scanning.")

    parser.add_argument("--followlinks", action="store_true", help="Follow symbolic links when walking/scanning the basedirs.")
    parser.add_argument("--no-followlinks", action="store_false", dest="followlinks")
    
    parser.add_argument("--ignore-untracked", action="store_true", help="Ignore untracked files.")
    parser.add_argument("--check-fetch", action="store_true", help="Check if origin has changes that can be fetched.")

    parser.add_argument("--wait", action="store_true", help="If changes are found, wait for input before continuing.")
    parser.add_argument("--json", action="store_true", help="Output results as JSON instead of logging.")
    parser.add_argument("--config", "-c", help="Provide arguments in a yaml file (as a dictionary).")
    parser.add_argument("--dirfile", "-f", nargs="+", help="List base directories in a file.")
    parser.add_argument("--ignorefile", help="File with directories to ignore (glob patterns).")
    parser.add_argument("basedirs", nargs="*", metavar="basedir", help="Base directories to scan for git repositories.")

    return parser, parser.parse_args(argv)


def process_args(argns=None, argv=None):
    """ Process command line args and return a dict with args.

    If argns is given, this is used for processing.
    If argns is not given (or None), parse_args() is called
    in order to obtain a Namespace for the command line arguments.

    Will expand the entry "basedirs" using glob matching, and print a
    warning if a pattern does not match any files at all.

    If argns (given or obtained) contains a "config" attribute,
    this is interpreted as being the filename of a config file (in yaml format),
    which is loaded and merged with the args.

    Returns a dict.
    """
    if argns is None:
        _, argns = parse_args(argv)
    args = argns.__dict__.copy()

    # Load config with parameters:
    if args.get("config"):
        with open(args["config"]) as fp:
            cfg = yaml.safe_load(fp) or {}
        args.update(cfg)

    if args.get("loglevel"):
        try:
            args["loglevel"] = int(args.get("loglevel"))
        except ValueError:
            args["loglevel"] = getattr(logging, str(args["loglevel"]).upper())

    if args.get("verbose"):
        args["loglevel"] = VERBOSE_LOG_LEVEL

    # On windows, we have to expand glob patterns manually:
    file_pattern_matches = [(pattern, glob.glob(os.path.expanduser(pattern))) for pattern in args['basedirs']]
    for pattern in (pattern for pattern, res in file_pattern_matches if len(res) == 0):
        logger.warning("WARNING: File/pattern '%s' does not match any files." % pattern)
    args['basedirs'] = [fname for pattern, res in file_pattern_matches for fname in res]

    if args.get("ignorefile"):
        args['ignorefile'] = os.path.expanduser(args['ignorefile'])

    return args


def read_ignorefile(ignorefile):
    """ Read file with glob patterns specifying files to ignore. """
    if ignorefile is None:
        if os.path.isfile(".git_checker_ignore"):
            logger.debug("ignorefile is None, using .git_checker_ignore in current working directory.")
            ignorefile = ".git_checker_ignore"
        else:
            logger.debug("ignorefile is None, returning empty list")
            return []
    logger.debug("Reading ignoreglobs from %s", ignorefile)
    with open(ignorefile) as fp:
        ignoreglobs = [line.strip() for line in fp if line.strip()]
    logger.debug("ignoreglobs: %s", ignoreglobs)
    return ignoreglobs


def read_basedirfiles(basedirfiles):
    """  Read one or more basedir files and return combined list of basedirs.
    Each basedirfile has a list of base directories to start from.
    """
    basedirs = []
    for basedirfile in basedirfiles:
        with open(basedirfile) as fp:
            basedirs += [line.strip() for line in fp if line.strip()]
    return basedirs


def is_git_workdir_or_repo(dirpath, dirnames, filenames):
    """ Returns 1 if dirpath is a git repository, 2 if dirpath is a git workdir, and 0 otherwise.
    (based solely on the directories and files in the directory).

    Args:
        dirpath: Directory (path).
        dirnames: List of child directory names within `dirpath` (just the names - not the path).
        filenames: List of file names within `dirpath` (just the names - not the path).

    Returns:
        True if dirpath is a git working directory (has a `.git` file or directory)
        or if dirpath is a git repository (has `config`, `HEAD`, `index` files).

    The equivalent `git` command is:
        git rev-parse --is-inside-git-dir || git rev-parse --is-inside-work-tree

    """
    if ".git" in dirnames or ".git" in filenames:
        # A git working directory can be linked with an external git repository, linked with a `.git` text file.
        return 2
    if "HEAD" in filenames and "config" in filenames and "refs" in dirnames:
        return 1
    return 0


def scan_gitrepos(basedirs, ignoreglobs=None, followlinks=False):
    """ Scan the list of basedirs for git repositories, traversing each basedir recursively.
    """
    if ignoreglobs is None:
        ignoreglobs = []
    if isinstance(basedirs, str):
        basedirs = [basedirs]
    gitrepos = []
    # first = 5  # True
    for basedir in basedirs:
        if basedir == ".":
            basedir = os.getcwd()
        basedir_gitrepos = [] # make a list for each basedir (to see if any basedir are void of git repos)
        logger.debug("Walking basedir %s", basedir)
        for dirpath, dirnames, filenames in os.walk(basedir, followlinks=followlinks):
            # if first and first > 0:
            #    print("dirpath, dirnames, filenames) =", (dirpath, dirnames, filenames))
            #    first -= 1
            ignoredirs = [dirname for dirname in dirnames if any(fnmatch(dirname, pat) for pat in ignoreglobs)]
            if ignoredirs:
                logger.debug("Ignoring the following directories in %s: %s", dirpath, ignoredirs)
            for dirname in ignoredirs:
                dirnames.remove(dirname)
            # if ".git" in dirnames or ".git" in filenames:
            if is_git_workdir_or_repo(dirpath, dirnames, filenames):
                logger.debug("Git repository found: %s", dirpath)
                # Add git repo dir to list of repos and abort further recursion by emptying the dirnames list:
                basedir_gitrepos.append(dirpath)
                del dirnames[:]
        logger.info("%s git repositories found for basedir %s", len(basedir_gitrepos), basedir)
        gitrepos += basedir_gitrepos
    logger.info("%s git repositories found for all (%s) basedirs\n", len(gitrepos), len(basedirs))
    return gitrepos


def configure_logging(args):
    """Apply CLI logging settings to the shared logger."""
    log_level = args.get("loglevel", DEFAULT_LOG_LEVEL)
    logger.setLevel(log_level)
    for handler in logger.handlers:
        handler.setLevel(log_level)


def find_gitrepos(basedirs, ignoreglobs=None, recursive=True, followlinks=False):
    """Return git repositories using the requested scan strategy."""
    if recursive:
        return scan_gitrepos(basedirs, ignoreglobs=ignoreglobs, followlinks=followlinks)

    gitrepos = []
    for basedir in basedirs:
        resolved_basedir = os.getcwd() if basedir == "." else basedir
        absolute_basedir = os.path.abspath(resolved_basedir)
        if not os.path.isdir(absolute_basedir):
            logger.warning("WARNING: Directory '%s' does not exist.", basedir)
            continue

        dirnames = []
        filenames = os.listdir(absolute_basedir)
        if is_git_workdir_or_repo(absolute_basedir, dirnames, filenames):
            gitrepos.append(absolute_basedir)

    logger.info("%s git repositories found for all (%s) basedirs\n", len(gitrepos), len(basedirs))
    return gitrepos


def get_local_changes(gitrepo, ignore_untracked=False):
    """Return git porcelain lines describing uncommitted local changes."""
    status_output = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=gitrepo,
        text=True
    ).splitlines()

    if ignore_untracked:
        return [line for line in status_output if line and not line.startswith("??")]
    return [line for line in status_output if line]


def check_repo_status_detailed(gitrepo, fetch=False, ignore_untracked=False):
    """
    Checks the status of git repository and returns detailed status information.
    
    Returns a dictionary with:
        - path: Repository path
        - local_changes: List of uncommitted changes, or empty list if none
        - ahead: Boolean indicating if local branch is ahead of remote
        - behind: Boolean indicating if local branch is behind remote
        - has_remote_changes: Boolean indicating if there are changes to fetch
        - up_to_date: Boolean indicating if repository is fully up-to-date
        - error: Error message if status check failed, None otherwise
    """
    result = {
        "path": gitrepo,
        "local_changes": [],
        "ahead": False,
        "behind": False,
        "has_remote_changes": False,
        "up_to_date": True,
        "error": None
    }

    try:
        result["local_changes"] = get_local_changes(
            gitrepo,
            ignore_untracked=ignore_untracked
        )
    except subprocess.CalledProcessError as e:
        result["error"] = str(e)
        return result

    # Check branch status (ahead, behind, up-to-date with origin)
    try:
        branch_status = subprocess.check_output(
            ["git", "status", "-b", "--porcelain"],
            cwd=gitrepo,
            text=True
        ).splitlines()[0]
        ahead_match = re.search(r'\[ahead (\d+)\]', branch_status)
        behind_match = re.search(r'\[behind (\d+)\]', branch_status)

        if ahead_match:
            result["ahead"] = True
        if behind_match:
            result["behind"] = True
    except subprocess.CalledProcessError as e:
        result["error"] = str(e)
        return result

    # Fetch status (check if there are changes to fetch from the remote)
    if fetch:
        try:
            fetch_status = subprocess.check_output(
                ["git", "fetch", "--dry-run"],
                cwd=gitrepo,
                text=True,
                stderr=subprocess.STDOUT
            ).strip()
            result["has_remote_changes"] = bool(fetch_status)
        except subprocess.CalledProcessError as e:
            result["error"] = str(e)
            return result

    # Determine if repository is up-to-date
    result["up_to_date"] = (
        len(result["local_changes"]) == 0 and
        not result["ahead"] and
        not result["behind"] and
        not result["has_remote_changes"]
    )

    return result



def print_report(repo_status):
    """Emit a human-readable report for one repository status."""
    logger.info("Git repository: %s", repo_status["path"])

    if repo_status["error"]:
        logger.error("Failed to inspect repository: %s", repo_status["error"])
        print("\n")
        return

    if repo_status["ahead"] and repo_status["behind"]:
        logger.info("Branch has diverged from upstream.")
    elif repo_status["ahead"]:
        logger.info("Local branch is ahead of upstream.")
    elif repo_status["behind"]:
        logger.info("Local branch is behind upstream.")

    if repo_status["has_remote_changes"]:
        logger.info("Outstanding fetches from origin detected.")

    if repo_status["local_changes"]:
        logger.warning("Outstanding commits:")
        for change in repo_status["local_changes"]:
            logger.warning(change)
    elif repo_status["up_to_date"]:
        logger.info("Repository is fully up-to-date.")

    print("\n")


def main(argv=None):
    """Main driver."""
    args = process_args(None, argv)

    configure_logging(args)

    if args['basedirs'] is None:
        args['basedirs'] = []
    if args['dirfile']:
        args['basedirs'] += read_basedirfiles(args['dirfile'])
    logger.debug("Scanning %s basedirs", len(args['basedirs']))

    ignoreglobs = read_ignorefile(args['ignorefile'])

    if not args['basedirs']:
        args['basedirs'] = ["."]

    dirs = [os.path.abspath(path) for path in args['basedirs']]
    if len(dirs) > 1:
        logger.info("Basedirs: %s" % dirs)
    else:
        logger.info("Basedir: %s" % dirs[0])
    exit_status = 0     # exit 0 = "No dirty repositories."

    gitrepos = find_gitrepos(
        args['basedirs'],
        ignoreglobs=ignoreglobs,
        recursive=args.get("recursive", True),
        followlinks=args.get("followlinks", False)
    )

    if not gitrepos:
        logger.error("No git repositories found!")
        sys.exit(127)   # exit 127 = "Error: No repositories found."

    repositories = []
    for gitrepo in gitrepos:
        repo_status = check_repo_status_detailed(
            gitrepo,
            fetch=args.get("check_fetch", False),
            ignore_untracked=args.get("ignore_untracked")
        )
        repositories.append(repo_status)
        if not repo_status["up_to_date"]:
            exit_status = 1

    # JSON output mode
    if args.get("json"):
        repositories_to_report = repositories
        if args.get("show_outdated_only"):
            repositories_to_report = [
                repo_status for repo_status in repositories
                if not repo_status["up_to_date"]
            ]

        output = {
            "repositories": repositories_to_report,
            "total": len(repositories),
            "outdated": sum(1 for r in repositories if not r["up_to_date"])
        }
        print(json.dumps(output, indent=2))
    else:
        for repo_status in repositories:
            if args.get("show_outdated_only") and repo_status["up_to_date"]:
                continue
            print_report(repo_status)

    if exit_status > 0 and args.get('wait'):
        input("\nPress ENTER to continue... ")
    sys.exit(exit_status)

def test():
    """Primitive test. """
    logging.basicConfig(level=10,  # , style="{")
                        format="%(asctime)s %(levelname)-5s %(name)20s:%(lineno)-4s%(funcName)20s() %(message)s")
    testbasedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # package root dir
    ignorefile = os.path.join(testbasedir, "test", "testfiles", "ignore.txt")
    testbasedir = os.path.dirname(testbasedir) # go up one level, to the folder that contains this project.
    testbasedir = os.path.join(testbasedir, "SublimeText_plugins")
    argv = [testbasedir, "--ignorefile", ignorefile] + sys.argv[2:]
    print("test argv:", argv)
    main(argv)


if __name__ == '__main__':
    if "--test" in sys.argv:
        test()
    else:
        main()
