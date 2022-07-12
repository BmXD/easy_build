#!/usr/bin/env python3

import subprocess
from utils.utils import exec_cmd


class DockerImage:
    def exist(platform, version):
        image = "{}:{}".format(platform, version)
        with exec_cmd("sudo", "docker", "images", image, stdout=subprocess.PIPE) as proc:
            images = proc.stdout.read().decode('utf-8').rstrip().split("\n")

        return len(images) == 2

    def build(platform, version):
        image = "{}:{}".format(platform, version)
        docker_file = "docker/Dockerfile.{}".format(platform)
        exec_cmd("sudo", "docker", "build", "-t", image, "-f", docker_file, ".")
