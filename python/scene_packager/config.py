# -*- coding: utf-8 -*-
"""
Scene package config, default implementation.

To override, create your own config.py and
set $SCENE_PACKAGER_CONFIG to its location.
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
    # return "S:/ANIMA/projects/${project}/user/${user}/delivery/" \
    #     "scene_packager/${application}/${date}/${shot}".format(kwargs)

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


def scene_backup_path(source_scene, package_root):
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
        "source_file": scene,
        "user": getpass.getuser(),
    }

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


def project_directory(scene):
    """
    Project directory to use in scene settings

    Returns:
        str
    """
    return " project_directory \"[python nuke.script_directory()]\"\n"


# -------------------------------------------------------
# File naming
# -------------------------------------------------------
def rename_src_file(filepath):
    """
    Rename source file

    Args:
        filepath (str): Dependency filepath from source scene

    Returns:
        Dest filepath str
    """
    rename_patterns = [
        {
            "#": "Ex: LUA001.bg_crytpo_material_A_.v1_%04d.exr, LUA001.bg_crytpo_material_A_.v1.%04d.exr",
            "desc": "Image publish + Square Enix naming",
            "regex": "^(?!.*houdini\/images.*).*\/(?P<layer>[a-zA-Z0-9_]+)\/([0-9]+)\/img\/full\/data\/(?P<aov>[a-zA-Z0-9_]+)\/(?P<shot>[a-zA-Z]+[0-9]+)([a-zA-Z]+|)[.](?P<desc>[a-zA-Z0-9_]+(?=_[a-zA-Z]+_))_(?P<colorspace>[a-zA-Z]+)_[.]v(?P<version>[0-9]+)[._](?<=[_.])(?P<frame>#+|[0-9]+|%[0-9]*d)(?P<ext>(?!(.autosave|~$$))[.][a-zA-Z0-9]+$$)",
            "format_str": "{shot}.{layer}{desc}_{colorspace}_.v{version:0>1d}.{frame}{ext}",
            "sub_chars": {"desc": {"_" : ""}, "layer": {"_": ""}}
        },
        {
            "#": "Ex: ../lighting/chara/02/img/full/data/specular_01/main_siva_LUA001_lighting_chara_####.exr",
            "desc": "Image publish + Anima naming",
            "regex": "\/(?P<version>[0-9]+)\/img\/full\/data\/(?P<aov>[a-zA-Z0-9_]+)\/(?P<episode>[a-zA-Z0-9]+)_(?P<sequence>[a-zA-Z0-9]+)_(?P<shot>[a-zA-Z0-9]+)([a-zA-Z]+|)_(?P<datatype>[a-zA-Z0-9]+)_(?P<layer>[a-zA-Z0-9]+)_(?<=[_.])(?P<frame>#+|[0-9]+|%[0-9]*d)(?P<ext>(?!(.autosave|~$$))[.][a-zA-Z0-9]+$$)",
            "format_str": "{shot}.{layer}{aov}_AG_.v{version:0>1d}.{frame}{ext}",
            "sub_chars": {"aov": {"_": ""}, "layer": {"_": ""}}
        },
        {
            "#": "Ex: ../images/v24/fxChain_after/deep/LUA001.effectfxChain_afterDeep_R_.24.####.exr, ../images/v24/fxChain_after/deep/LUA001.effectfxChain_afterDeep_R_.v24_####.exr",
            "desc": "Work area FX images",
            "regex": "\/images\/(v|)([0-9]+)\/(?P<aov>[a-zA-Z0-9_]+)\/((?P<pass>[a-zA-Z0-9_]+)\/|)(?P<shot>[a-zA-Z]+[0-9]+)([a-zA-Z]+|)[.](?P<desc>[a-zA-Z0-9_]+(?=_[a-zA-Z]+_))_(?P<colorspace>[a-zA-Z]+)_[.](v|)(?P<version>[0-9]+)[._](?<=[_.])(?P<frame>#+|[0-9]+|%[0-9]*d)(?P<ext>(?!(.autosave|~$$))[.][a-zA-Z0-9]+$$)",
            "format_str": "{shot}.{desc}{version:0>1d}_{colorspace}_.v{version:0>1d}.{frame}{ext}",
            "sub_chars": {"desc": {"_" : ""}}
        },
        {
            "#": "Ex: LUA001.bg_crytpo_material_A_.v1_%04d.exr, LUA001.bg_crytpo_material_A_.v1.%04d.exr",
            "desc": "Tmp area + Square Enix naming",
            "regex": "^.*\/tmp\/(.+\/|)(?P<shot>[a-zA-Z]+[0-9]+)([a-zA-Z]+|)[.](?P<desc>[a-zA-Z0-9_]+(?=_[a-zA-Z]+_))_(?P<colorspace>[a-zA-Z]+)_[.]v(?P<version>[0-9]+)[._](?<=[_.])(?P<frame>#+|[0-9]+|%[0-9]*d)(?P<ext>(?!(.autosave|~$$))[.][a-zA-Z0-9]+$$)",
            "format_str": "{shot}.{desc}_{colorspace}_.v{version:0>1d}.{frame}{ext}",
            "sub_chars": {"desc": {"_" : ""}}
        }
    ]

    return scene_packager.utils.get_renamed_dst_path(
        scene_packager.utils.clean_path(filepath), rename_patterns
    )


def get_packaged_path(filepath, parent_dir):
    """
    Args:
        filepath (str): Dependency filepath from source scene
        parent_dir (str): Destination parent dir

    Returns:
        Dest filepath str
    """
    # Found rename pattern match
    renamed = rename_src_file(filepath)
    if renamed:
        # Rename has extra dir already
        if os.path.dirname(renamed):
            return scene_packager.utils.clean_path(
                os.path.join(parent_dir, renamed)
            )
        # Rename is filename only
        # Add filename dir
        else:
            return scene_packager.utils.clean_path(
                os.path.join(
                    parent_dir,
                    os.path.splitext(os.path.basename(renamed))[0],
                    renamed
                )
            )

    # Get basic packaged path
    return scene_packager.utils.basic_package_dst_path(filepath, parent_dir)


def load_scene_data(packaged_scene, package_root, source_scene):
    """
    Implement per DCC
    Returns dict of scene data

    Args:
        packaged_scene (str): Packaged scene path
        package_root (str): Package root path
        source_scene (str): Source scene path
    """
    raise NotImplementedError()


def write_packaged_scene(source_scene, dst_scene, dep_data, root,
                         project_dir, start, end, relative_paths=False):
    """
    Implement per DCC
    Write packaged scene. Can be reimplemented per application
    """
    raise NotImplementedError()


# -------------------------------------------------------
# Pre/post hooks
# -------------------------------------------------------
def pre_package(scene):
    """
    Run before packaging
    Implementation optional
    """
    pass


def post_package(scene):
    """
    Run after packaging
    Implementation optional
    """
    pass
