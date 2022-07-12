#!/usr/bin/env python3

import os
import argparse
from utils.builder import Builder
from utils.git_utils import Git
from utils.dependency_handler import DependencyHandler
from utils.docker_image import DockerImage


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('platform', help='platform')
    parser.add_argument('project', help='project')
    parser.add_argument("-u", "--update", action="store_true", help="update project")
    parser.add_argument("-b", "--branch", help="project branch")
    parser.add_argument("-r", "--reset", action="store_true", help="reset platform prebuilts")
    parser.add_argument("-d", "--prebuilt_only", action="store_true", help="No build, only install project prebuilt")
    parser.add_argument("-i", "--install", action="store_true", help="install project")
    parser.add_argument("-p", "--package", action="store_true", help="package project")
    parser.add_argument("-x", "--dependency_depth", type=int, default=0, help="build dependent depth")
    args = parser.parse_args()

    try:
        platform, version = args.platform.split(":")
    except ValueError as e:
        platform = args.platform
        version = "latest"

    if not DockerImage.exist(platform, version):
        DockerImage.build(platform, version)

    if args.reset:
        Builder.reset_env(args.platform)

    if args.prebuilt_only:
        DependencyHandler.install_project_prebuilts(args.project, args.platform)
        DependencyHandler.install_project_daily_builds(args.project, args.platform)
        os._exit(0)

    builder = Builder(
        platform,
        args.project,
        update=args.update, branch=args.branch,
        install=args.install, package=args.package,
        dependency_depth=args.dependency_depth,
        env_ver=version
    )

    builder.build()
