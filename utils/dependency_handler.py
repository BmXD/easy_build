#!/usr/bin/env python3

import os
import configparser
import subprocess
import shutil
from utils.utils import exec_cmd
from utils.git_utils import Git


class DependencyHandler:
    working_dir = os.getcwd()
    source_dir = os.sep.join(working_dir.split(os.sep)[:-1])
    installed_prebuilts = None
    installed_daily_builds = None
    latest_daily = None

    def __init__(self, working_dir):
        self.working_dir = working_dir

    @classmethod
    def get_installed_prebuilts(cls, platform):
        config_path = "{working_dir}/prebuilt/{platform}/installed".format(working_dir=cls.working_dir, platform=platform)
        if not os.path.isfile(config_path):
            return {}

        with open(config_path) as f:
            installed = {}
            for line in f.readlines():
                k, v = line.split("=")
                installed[k.rstrip()] = v.strip()

        return installed

    @classmethod
    def install_project_prebuilts(cls, project, platform):
        if cls.installed_prebuilts is None:
            cls.installed_prebuilts = cls.get_installed_prebuilts(platform)

        dir_path = "{working_dir}/prebuilt/{platform}".format(working_dir=cls.working_dir, platform=platform)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        _, prebuilts, _ = cls.get_dependency(project)
        for project, version in prebuilts.items():
            if cls.installed_prebuilts.get(project) != version:
                cls.install_prebuilt(platform, project, version)

    @classmethod
    def install_prebuilt(cls, platform, prebuilt, version):
        print("install: {} version: {}".format(prebuilt, version))

        filename = "{}_{}_{}.tar.xz".format(prebuilt, version, platform)
        ret = exec_cmd("curl",
                       "ftp://10.58.65.3//prebuilt/easy_build/{}/{}".format(prebuilt, filename),
                       "--output",
                       "prebuilt/{}/{}".format(platform, filename),
                       cwd=cls.working_dir)

        if ret.returncode != 0:
            return

        download = "{}/prebuilt/{}/{}".format(cls.working_dir, platform, filename)
        dest_dir = "{}/prebuilt/{}".format(cls.working_dir, platform)
        exec_cmd("tar", "-xf", download, "-C", dest_dir)
        exec_cmd("rm", download)

        installed = cls.get_installed_prebuilts(platform)
        installed[prebuilt] = version
        config = "{}/prebuilt/{}/installed".format(cls.working_dir, platform)
        with open(config, "w+") as f:
                for _prebuilt, _version in installed.items():
                    f.write("{} = {}\n".format(_prebuilt, _version))

    @classmethod
    def install_project_daily_builds(cls, project, platform):
        if cls.installed_daily_builds is None:
            cls.installed_daily_builds = cls.get_installed_daily_builds(platform)

        dir_path = "{working_dir}/prebuilt/{platform}".format(working_dir=cls.working_dir, platform=platform)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        _, prebuilts, daily_builds = cls.get_dependency(project)

        # prebuilts
        for project, version in prebuilts.items():
            if cls.installed_prebuilts.get(project) != version:
                cls.install_prebuilt(platform, project, version)

        # daily_builds
        cls.latest_daily = cls.get_lastest_daily_build()
        for build in daily_builds:
            if cls.latest_daily and cls.installed_daily_builds.get(build) != cls.latest_daily:
                cls.install_daily_build(platform, build)

    @classmethod
    def get_installed_daily_builds(cls, platform):
        config_path = "{working_dir}/prebuilt/{platform}/installed_daily".format(working_dir=cls.working_dir, platform=platform)
        if not os.path.isfile(config_path):
            return {}

        with open(config_path) as f:
            installed = {}
            for line in f.readlines():
                k, v = line.split("=")
                installed[k.rstrip()] = v.strip()

        return installed

    @classmethod
    def get_lastest_daily_build(cls):
        with exec_cmd("curl", "-l", "ftp://10.58.65.3/sw_rls/cv1835/daily_build/cv183x_master/", stdout=subprocess.PIPE) as proc:
            dates = sorted([_.strip() for _ in proc.stdout.read().decode("utf-8").rstrip().split("\n")])
            if dates:
                return dates[-1]

        return None

    @classmethod
    def install_daily_build(cls, platform, project):
        script = "daily_build/{}".format(project)
        dest_dir = "prebuilt/{}/daily_build/{}".format(platform, project)

        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)

        os.makedirs(dest_dir)
        ret = exec_cmd(script, cls.latest_daily, platform, dest_dir)
        if ret.returncode != 0:
            print("install daily build", project, "failed")
            return

        installed = cls.get_installed_daily_builds(platform)
        installed[project] = cls.latest_daily
        config = "{}/prebuilt/{}/installed_daily".format(cls.working_dir, platform)
        with open(config, "w+") as f:
                for _project, _date in installed.items():
                    f.write("{} = {}\n".format(_project, _date))

    @classmethod
    def get_dependency(cls, project):
        depends = configparser.ConfigParser(allow_no_value=True)
        depends.optionxform = str

        config = "{}/{}/BuildConf/depends".format(cls.source_dir, project)
        depends.read(config)

        try:
            dependents = {project: branch for project, branch in depends.items("dependent")}
        except configparser.NoSectionError as e:
            dependents = {}

        try:
            prebuilts = {project: version for project, version in depends.items("prebuilt")}
        except configparser.NoSectionError as e:
            prebuilts = {}

        try:
            daily_build = [project for project, _ in depends.items("daily_build")]
        except configparser.NoSectionError as e:
            daily_build = []

        return dependents, prebuilts, daily_build

    @classmethod
    def handle_dependency(cls, project, platform, depth, branch=None, update=False):
        if cls.installed_prebuilts is None:
            cls.installed_prebuilts = cls.get_installed_prebuilts(platform)

        if cls.installed_daily_builds is None:
            cls.installed_daily_builds = cls.get_installed_daily_builds(platform)

        # handle prebuilt
        dependents, prebuilts, daily_builds = cls.get_dependency(project)
        for prebuilt, version in prebuilts.items():
            if cls.installed_prebuilts.get(prebuilt) != version:
                cls.install_prebuilt(platform, prebuilt, version)

        # handle daily build
        cls.latest_daily = cls.get_lastest_daily_build()
        for build in daily_builds:
            if cls.latest_daily and cls.installed_daily_builds.get(build) != cls.latest_daily:
                cls.install_daily_build(platform, build)

        dependent_list = [item for item in dependents.items()]
        record = {}
        build_list = []

        if depth == 0:
            return []
        elif depth < 0:
            depth = 1024  # limit

        for _ in range(depth):
            # BFS traverse depend list
            traverse_num = len(dependent_list)
            if traverse_num == 0:
                break

            for _ in range(traverse_num):
                dependent, depend_branch = dependent_list.pop(0)
                if not depend_branch:
                    depend_branch = branch

                Git.setup_repo(dependent, branch=depend_branch, update=update)
                if dependent in record:
                    continue

                record[dependent] = depend_branch
                build_list.insert(0, dependent)  # push front

                next_level_dependents, dep_prebuilts, daily = cls.get_dependency(dependent)

                for prebuilt, version in dep_prebuilts.items():
                    if cls.installed_prebuilts.get(prebuilt) != version:
                        cle.install_prebuilt(platform, prebuilt, version)

                for builds in daily_builds:
                    if cls.latest_daily and cls.installed_daily_builds.get(build) != cls.latest_daily:
                        cls.install_daily_build(platform, build)

                dependent_list += [i for i in next_level_dependents.items()]

        return build_list
