# -*- coding: utf-8 -*-
"""
Scene package config, default implementation.

To override, create your own scene_packager_config.py and prepend
it to $SCENE_PACKAGER_CONFIG_PATH.

Any functions not overridden will use the default implementations below.
"""

# Standard
from datetime import datetime
import getpass
import os

# Scene packager
import scene_packager


# -------------------------------------------------------
# Package paths
# -------------------------------------------------------
def package_root(source_scene):
    """
    Get root directory of a new scene package
    """
    return os.path.join(
        os.path.expandvars("S:/ANIMA/projects/$LAUNCHAPP_PROJECT/user"),
        getpass.getuser(),
        "scene_packager",
        "nuke",
        datetime.now().strftime("%Y-%m-%d_%H%M%S")
    )


def package_tmp_dir(source_scene):
    """
    When overwriting a package, it will be moved to
    this tmp directory and deleted from there.

    Returns:
        str
    """
    return os.path.expandvars(
        "S:/ANIMA/projects/$LAUNCHAPP_PROJECT/tmp/scene_packager"
    )


def packaged_scene_path(source_scene, package_root):
    """
    Get path where packaged scene will be written to

    Args:
        source_scene (str): Path to source scene being packaged
        package_root (str): Package root directory

    Returns:
        str
    """
    return os.path.join(
        package_root, "nk", os.path.basename(source_scene)
    )


def backup_scene_path(source_scene, package_root):
    """
    Get path where packaged copy of source scene will be written to

    Args:
        source_scene (str): Path to source scene being packaged
        package_root (str): Package root directory

    Returns:
        str
    """
    return os.path.join(
        package_root, "nk", "package_info", os.path.basename(source_scene)
    )


def metadata_path(package_root):
    """
    Get package subdirectory where metadata should be written to

    Returns:
        str
    """
    return os.path.join(
        package_root, "nk", "package_info", "package_metadata.json"
    )


def filecopy_metadata_path(package_root):
    """
    Get package subdirectory where file copy data should be written to

    Returns:
        str
    """
    return os.path.join(
        package_root, "nk", "package_info", "copy_files.json"
    )


# -------------------------------------------------------
# Package data settings
# -------------------------------------------------------
def package_metadata(scene, settings):
    """
    Add keys to the package metadata file
    """
    metadata = {
        "date": datetime.now().strftime("%Y-%m-%d_%H%M%S"),
        "package_settings": settings,
        "source_scene": scene,
        "user": getpass.getuser(),
    }
    # Add search path for config files
    try:
        metadata["SCENE_PACKAGER_CONFIG_PATH"] = \
            os.environ["SCENE_PACKAGER_CONFIG_PATH"]
    except KeyError:
        raise RuntimeError("$SCENE_PACKAGER_CONFIG_PATH is not set.")

    return metadata


def use_frame_limit():
    """
    If True, limit copied frames to those used in the scene
    If False, copy all available frames

    Returns:
        bool
    """
    return False


def use_relative_paths():
    """
    If True, use relative paths in final scene
    If False, full path is used
    """
    return True


# -------------------------------------------------------
# File naming
# -------------------------------------------------------
def get_packaged_path(filepath, parent_dir):
    """
    Args:
        filepath (str): Dependency filepath from source scene
        parent_dir (str): Destination parent dir

    Returns:
        Dest filepath str
    """
    # Get basic packaged path
    return scene_packager.utils.basic_package_dst_path(filepath, parent_dir)


# -------------------------------------------------------
# *** Must be implemented per-DCC ***
# *** Nuke implementation: scene_packager/nuke/scene_packager_config.py ***
# -------------------------------------------------------
def project_directory(packaged_scene, package_root, source_scene):
    """
    Project directory for packaged scene

    Args:
        packaged_scene (str): Packaged scene path
        package_root (str): Package root path
        source_scene (str): Source scene path

    Returns:
        str
    """
    raise NotImplementedError()


def get_scene_frange(scene):
    """
    Returns:
        (start (int), end (int)) tuple
    """
    raise NotImplementedError()


def load_scene_data(packaged_scene, package_root, source_scene):
    """
    Implement per DCC
    Returns dict of scene data

    Args:
        packaged_scene (str): Packaged scene path
        package_root (str): Package root path
        source_scene (str): Source scene path

    Returns:
        root_data (str), dep_data (dict), start (int), end (int)
    """
    raise NotImplementedError()


def write_packaged_scene(source_scene, dst_scene, dep_data, root,
                         project_dir, start, end, relative_paths=False):
    """
    Implement per DCC
    Write packaged scene. Can be reimplemented per application

    Returns:
    """
    raise NotImplementedError()


# -------------------------------------------------------
# Pre/post hooks
# -------------------------------------------------------
def pre_package(scene, mode=0):
    """
    Run before packaging
    Implementation optional
    """
    pass


def post_package(scene, mode=0):
    """
    Run after packaging
    Implementation optional
    """
    pass
