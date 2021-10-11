# -*- coding: utf-8 -*-
import logging
import os
import pprint
import traceback
import webbrowser

from . import packagers, utils


def get_scene_packager(scene, config_keys, extra_files=None):
    """
    Get scene packager for a scene
    """
    packager = packagers.base_packager.Packager(scene,
                                                config_keys,
                                                extra_files)
    return packager


def package_scene(scene, config_keys, extra_files=None, overwrite=False,
                  mode=False):
    """
    Package the given scene path
    """
    if not os.path.isfile(scene):
        raise ValueError("Scene does not exist! {0}".format(scene))

    packager = get_scene_packager(scene, config_keys, extra_files)
    return packager.run(overwrite=overwrite, mode=mode)


def package_scenes(scenes, config_keys, extra_files=None, overwrite=False,
                   mode=False):
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
                              overwrite=overwrite, mode=mode)
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


def inspect(root_dir, open_root_dir=False, open_scene_dir=False, verbose=0):
    """
    Inspect - print package data and open direc

    Args:
        root_dir (str): Dir to check
        open_root_dir (bool): Open each package root
        open_scene_dir (bool): Open parent dir of the packaged scene
        verbose (int): If 0, print package root dirs and number of packages
                       If 1, print each package scene/user/date packaged
                       If 2, print entire contents of each package metadata dict
    """
    log = utils.get_logger(__name__, logging.INFO)

    existing = utils.find_existing_packages(root_dir, "package_metadata.json")
    log.info("Searching root dir... [{}]".format(root_dir))
    log.info("Found {} packages".format(len(existing)))

    to_open = []  # Dirs to open
    for metadata_file in existing:
        # Load data
        data = utils.load_json(metadata_file)

        # Basic print
        log.newline()
        log.info("*" * 50)
        log.info("{:15} {}".format(
            "Package root:", data.get("package_settings", {}).get(
                "package_root"))
        )
        # -v
        if 1 <= verbose:
            log.info("{:15} {}".format(
                "Packaged scene:", data.get("package_settings", {}).get(
                    "packaged_scene"))
            )
            log.info("{:15} {}".format("User:", data.get("user")))
            log.info("{:15} {}".format("Date:", data.get("date")))

        # -vv
        if verbose >= 2:
            log.info("Package metadata: ")
            log.info("\n" + pprint.pformat(data))

        # Dir open check
        if open_root_dir:
            root = data.get("package_settings", {}).get("package_root")
            if root:
                to_open.append(root)
        if open_scene_dir:
            scene = data.get("package_settings", {}).get("packaged_scene")
            if scene:
                to_open.append(os.path.dirname(scene))

    # Open dirs
    for subdir in to_open:
        webbrowser.open(subdir)
