#!/usr/bin/env python3

import subprocess


def exec_cmd(*args, **kwargs):
    child = subprocess.Popen(args, **kwargs)
    child.wait()
    return child
