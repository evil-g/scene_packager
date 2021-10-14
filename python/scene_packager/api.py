# -*- coding: utf-8 -*-
import logging
import os
import pprint
import traceback
import webbrowser

from . import packagers, scene_packager_config, utils

# Globals
LOG = utils.get_logger("scene_packager.api")

# Config python file name
SP_CONFIG_NAME = "scene_packager_config.py"


def _get_config_paths(search_path=None, print_info=False):
    """
    Get paths to override config .py files found in config search path

    Args:
        search_path (str): Scene packager config search path

    Returns:
        List of config filepath str
        (In order of highest priority to lowest priority)
    """
    if print_info:
        log = utils.get_logger("scene_packager.api", logging.INFO)
    else:
        log = utils.get_logger("scene_packager.api")

    search_path = search_path or os.environ["SCENE_PACKAGER_CONFIG_PATH"]
    log.info("Config search path: {}".format(utils.clean_path(search_path)))

    paths = []
    for search_dir in search_path.split(";"):
        target = os.path.join(search_dir, SP_CONFIG_NAME)
        if os.path.isfile(target):
            paths.append(target)

    log.info("{} override config files found.".format(len(paths)))

    return paths[::-1]


def _load_config_overrides(search_path=None, print_info=False):
    """
    Load override methods from config .py files

    Args:
        search_path (str): Scene packager config search path
        debug (bool): If True, print debug info about config assembly

    Returns: None
    """
    if print_info:
        log = utils.get_logger("scene_packager.api", logging.INFO)
    else:
        log = utils.get_logger("scene_packager.api")

    log.info("*" * 50)
    log.info("Base config: {}".format(
        utils.clean_path(scene_packager_config.__file__))
    )
    log.newline()

    paths = _get_config_paths(search_path, print_info=print_info)

    # Override general config
    index = 0
    for each in paths:
        index += 1
        log.newline()
        log.info("*" * 50)
        log.info("Processing override # {}".format(index))
        log.newline()

        mod = {
            "__file__": each,
        }

        try:
            with open(each) as f:
                exec(compile(f.read(), f.name, "exec"), mod)
        except IOError:
            raise
        except Exception:
            raise ("Invalid override config: {}".format(each))
        else:
            log.info("Loading config: {}".format(utils.clean_path(each)))
            log.newline()

        for key in dir(scene_packager_config):
            if key.startswith("__"):
                continue

            try:
                value = mod[key]
            except KeyError:
                continue
            else:
                log.info("Override: {}".format(key))

            setattr(scene_packager_config, key, value)

    if paths:
        log.newline()
        log.info("*" * 50)

    return paths


def _init_backup_config():
    """
    Make backup copies of originals, with `_` prefix
    Useful for augmenting an existing value with your own config
    """

    for member in dir(scene_packager_config):
        if member.startswith("__"):
            continue

        setattr(scene_packager_config, "_%s" % member,
                getattr(scene_packager_config, member))


def get_scene_packager(scene, package_root=None, extra_files=None, verbose=0):
    """
    Get scene packager for a scene
    """
    packager = packagers.base_packager.Packager(scene,
                                                package_root=package_root,
                                                extra_files=extra_files,
                                                verbose=verbose)
    return packager


def package_scene(scene, package_root=None, extra_files=None, overwrite=False,
                  mode=False, verbose=0):
    """
    Package the given scene path
    """
    if not os.path.isfile(scene):
        raise ValueError("Scene does not exist! {0}".format(scene))

    packager = get_scene_packager(scene,
                                  package_root=package_root,
                                  extra_files=extra_files,
                                  verbose=verbose)

    return packager.run(overwrite=overwrite, mode=mode)


def package_scenes(scenes, package_root=None, extra_files=None, overwrite=False,
                   mode=False, verbose=0):
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
                package_scene(scene,
                              package_root=package_root,
                              extra_files=extra_files,
                              overwrite=overwrite,
                              mode=mode,
                              verbose=verbose)
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


def inspect_config(search_path=None):
    """
    Load config and print debug info about overrides
    """
    _load_config_overrides(search_path=search_path, print_info=True)
