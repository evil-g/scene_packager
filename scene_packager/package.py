# -*- coding: utf-8 -*-
import os

name = "scene_packager"

tool_manager_version = os.environ.get("REZ_TM_PACKAGE_VERSION")
version = tool_manager_version or "1.0.0"

build_command = "python -m rezutils build {root}"
private_build_requires = ["rezutils-1"]

author = "gabriella"
category = "ext"

requires = [
    "Qt.py-1",
    "future-0",
    "python-2|3",
    "PySide2"
]

tools = [
    "scene-packager"
    "batch_copy"
]

_ignore = [
    "doc,docs,*.pyc,.cache,__pycache__,*.pyproj,*.sln,.vs,.idea"
]


def commands():

    global env
    global expandvars

    env.NUKE_PATH.append(expandvars("{root}/nuke;{root}/python"))
    env.PATH.prepend(expandvars("{root}/bin"))
    env.PYTHONPATH.append(expandvars("{root}/nuke;{root}/python"))

    env.SCENE_PACKAGER_ROOT = expandvars("{root}")

    # Config setting
    env.SCENE_PACKAGER_CONFIG_PATH.append("{root}/nuke")
