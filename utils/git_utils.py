#!/usr/bin/env python3

import os
import subprocess
from utils.utils import exec_cmd


class Git:
    git_server = "10.34.33.3:8422"
    working_dir = os.getcwd()
    source_dir = os.sep.join(working_dir.split(os.sep)[:-1])

    @classmethod
    def clone_repo(cls, repo):
        exec_cmd("git", "clone",
                 "ssh://git@{}/sys_app/{}".format(cls.git_server, repo),
                 "{}/{}".format(cls.source_dir, repo))

    @classmethod
    def checkout_branch(cls, *, repo, branch):
        repo_dir = "{}/{}".format(cls.source_dir, repo)

        with exec_cmd("git", "branch", stdout=subprocess.PIPE, cwd=repo_dir) as proc:
            branches = [_.strip() for _ in proc.stdout.read().decode("utf-8").rstrip().split("\n")]

        for br in branches:
            if br[0] == "*":
                branch_name = br.split()
                current_branch = branch_name[-1]

        if branch == current_branch:
            return

        exec_cmd("git", "stash", cwd=repo_dir)
        if branch in branches:
            exec_cmd("git", "checkout", branch, cwd=repo_dir)
        else:
            exec_cmd("git", "checkout", "-b", branch, "origin/" + branch, cwd=repo_dir)

    @classmethod
    def update_repo(cls, repo):
        repo_dir = "{}/{}".format(cls.source_dir, repo)
        exec_cmd("git", "stash", cwd=repo_dir)
        exec_cmd("git", "pull", cwd=repo_dir)
        exec_cmd("git", "stash", "pop", cwd=repo_dir)

    @classmethod
    def setup_repo(cls, repo, *, branch=None, update=False):
        print("repo: {}, branch: {}, update: {}".format(repo, branch, update))

        repo_path = "{}/{}".format(cls.source_dir, repo)
        if not os.path.exists(repo_path):
            Git.clone_repo(repo)

        if branch:
            Git.checkout_branch(repo=repo, branch=branch)

        if update:
            Git.update_repo(repo)
