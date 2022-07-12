
import os
import shutil
from utils.utils import exec_cmd
from utils.git_utils import Git
from utils.dependency_handler import DependencyHandler


class Builder:
    uid = os.getuid()
    working_dir = os.getcwd()
    source_dir = os.sep.join(working_dir.split(os.sep)[:-1])

    def __init__(self, platform, project, *,
                 update=False, branch=None, install=False, package=False,
                 dependency_depth=0,
                 env_ver="latest"):
        self.platform = platform
        self.project = project
        self.env_ver = env_ver
        self.update = update
        self.branch = branch
        self.package = package
        self.install = install
        self.dependency_depth = dependency_depth

    @classmethod
    def reset_env(cls, platform):
        installed_prebuilt = "{working_dir}/prebuilt/{platform}/installed".format(working_dir=cls.working_dir, platform=platform)
        if os.path.exists(installed_prebuilt):
            os.remove(installed_prebuilt)

        installed_daily = "{working_dir}/prebuilt/{platform}/installed_daily".format(working_dir=cls.working_dir, platform=platform)
        if os.path.exists(installed_daily):
            os.remove(installed_daily)

        try:
            for entry in os.scandir("{working_dir}/prebuilt/{platform}/system".format(working_dir=cls.working_dir, platform=platform)):
                shutil.rmtree(entry.path, ignore_errors=True)
        except FileNotFoundError as e:
            pass

        try:
            for entry in os.scandir("{working_dir}/prebuilt/{platform}/daily_build".format(working_dir=cls.working_dir, platform=platform)):
                shutil.rmtree(entry.path, ignore_errors=True)
        except FileNotFoundError as e:
            pass

    @classmethod
    def prepare_dir(cls, directory):
        dir_path = "{working_dir}/{directory}".format(working_dir=cls.working_dir, directory=directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    @classmethod
    def install_prebuilt(cls, platform, prebuilt, version):
        print("install: {} version: {}".format(prebuilt, version))

        filename = "{}_{}_{}.tar.xz".format(prebuilt, version, platform)
        exec_cmd("curl",
                 "ftp://10.34.33.5/prebuilt/easy_build/{}/{}".format(prebuilt, filename),
                 "--output",
                 "prebuilt/{}/{}".format(platform, filename),
                 cwd=cls.working_dir)

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
    def get_dependency(cls, project):
        depends = configparser.ConfigParser(allow_no_value=True)
        depends.optionxform = str

        config = "{}/{}/BuildConf/depends".format(cls.source_dir, project)
        depends.read(config)

        try:
            dependents = {project: branch for project, branch in depends.items("dependent")}
            prebuilts = {project: version for project, version in depends.items("prebuilt")}
        except configparser.NoSectionError as e:
            return {}, {}

        return dependents, prebuilts

    @classmethod
    def handle_dependencies(cls, platform, project):
        installed_prebuilts = cls.get_installed_prebuilts(platform)
        dependents, prebuilts = cls.get_dependency(project)

        for project, version in prebuilts.items():
            if installed_prebuilts.get(project) != version:
                cls.install_prebuilt(platform, project, version)

        return dependents

    def build(self):
        # we mkdir manually because we want to keep permission
        prebuilt_dir = "prebuilt/" + self.platform
        package_dir = "package/" + self.platform

        self.prepare_dir(prebuilt_dir)
        self.prepare_dir(package_dir)

        Git.setup_repo(self.project, branch=self.branch, update=self.update)
        dependent_list = DependencyHandler.handle_dependency(self.project, self.platform, self.dependency_depth)

        cmd = "sudo docker run --rm -it -a stdout -a stderr "
        cmd += "-u {uid}:{uid} ".format(uid=self.uid)
        cmd += "-v {dir}:/source ".format(dir=self.source_dir)
        cmd += "-v {dir}/package/{platform}:/package ".format(dir=self.working_dir, platform=self.platform)
        cmd += "-v {dir}/prebuilt/{platform}/system:/system ".format(dir=self.working_dir, platform=self.platform)
        cmd += "-v {dir}/prebuilt/{platform}/daily_build:/daily_build ".format(dir=self.working_dir, platform=self.platform)
        cmd += "{platform}:{ver}".format(platform=self.platform, ver=self.env_ver)

        script = ""
        for dependent in dependent_list:
            _cmd = "cd /source/{dependent}; sh /source/{dependent}/BuildConf/build; sh /source/{dependent}/BuildConf/install;".format(dependent=dependent)
            script += _cmd

        script += "cd /source/{project}; sh /source/{project}/BuildConf/build;".format(project=self.project)
        if self.install:
            script += "/source/{project}/BuildConf/install;".format(project=self.project)

        package_cmd = ""
        if self.package:
            package_cmd += "cd /source/{project}; sh /source/{project}/BuildConf/package;".format(project=self.project)
            package_cmd += "tar -cvJf /package/{project}_$(cat /source/{project}/BuildConf/version)_{platform}.tar.xz -C /package/tmp . ;".format(
                project=self.project,
                platform=self.platform)
            package_cmd += "rm -rf /package/tmp;"

        cmd = cmd.split()
        exec_cmd(*cmd, "/bin/bash", "-c", script + package_cmd)
