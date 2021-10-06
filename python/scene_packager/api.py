# -*- coding: utf-8 -*-
import os
import traceback

from . import packagers


def get_scene_packager(scene, config_keys, extra_files=None):
    """
    Get scene packager for a scene
    """
    packager = packagers.base_packager.Packager(scene,
                                                config_keys,
                                                extra_files)
    return packager


def package_scene(scene, config_keys, extra_files=None, overwrite=False,
                  dryrun=False):
    """
    Package the given scene path
    """
    if not os.path.isfile(scene):
        raise ValueError("Scene does not exist! {0}".format(scene))

    packager = get_scene_packager(scene, config_keys, extra_files)
    return packager.run(overwrite=overwrite, dryrun=dryrun)


def package_scenes(scenes, config_keys, extra_files=None, overwrite=False,
                   dryrun=False):
    """
    Create packager and run for each scene

    Args:
        scenes (list): List of scene paths
    """
    dne = []
    ids = []
    for scene in scenes:
        try:
            ids.append(
                package_scene(scene, config_keys, extra_files,
                              overwrite=overwrite, dryrun=dryrun)
            )
        except ValueError as e:
            tb_message = "".join(traceback.format_exception(type(e), e, None))
            if tb_message.startswith("Scene does not exist"):
                dne.append(scene)
            else:
                raise e

    if dne:
        msg = "\n".join(sorted(dne))
        raise ValueError(
            "The following input scenes did not exist: {0}".format(msg))

    return ids
