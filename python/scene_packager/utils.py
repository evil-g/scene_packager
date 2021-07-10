# -*- coding: utf-8 -*-
# Standard
import collections
import copy
from datetime import datetime
import errno
import getpass
from glob import glob
import json
import logging
import os
import platform
import re
import shutil
from string import Template
import subprocess
import tempfile
import traceback


# Globals
CONFIG = None
# Package metadata filenames
COPY_METADATA = "copy_files.json"
PACKAGE_METADATA = "package_metadata.json"
# Frame regex
FRAME_PAD_REGEX = r"(?<=[_\.])(?P<frame>#+|\d+|\%\d*d)$"
# Log
LOG = logging.getLogger("scene_packager.utils")


def packager_settings(reload=False):
    """
    Read packager config settings file
    Checks for json file at:
        1. $SCENE_PACKAGER_CONFIG
        2. $SCENE_PACKAGER_ROOT/config/scene_packager/scene_packager.json

    Args:
        reload (bool): If True, reload config

    Returns:
        Dict
    """
    global CONFIG

    if not CONFIG or reload:
        # Env var override
        if os.getenv("SCENE_PACKAGER_CONFIG"):
            CONFIG = load_json(
                clean_path(os.environ["SCENE_PACKAGER_CONFIG"]))
        # Pipeline config locations
        else:
            CONFIG = load_json(
                clean_path(os.path.join(os.environ["SCENE_PACKAGER_ROOT"],
                                        "config",
                                        "scene_packager",
                                        "scene_packager.json")))

    return CONFIG


def get_frame_glob_path(filepath):
    """
    Get glob style path for frames

    Args:
        filepath (str): Filepath

    Returns:
        Pipeline formatted sequence filepath
    """
    path = clean_path(filepath)
    base, ext = os.path.splitext(path)

    glob_base = re.sub(FRAME_PAD_REGEX, "*", base)
    seq_path = glob_base + ext
    LOG.debug("Found frame sequence: {0}".format(seq_path))

    # Verify glob
    glob(seq_path)

    return seq_path


def clean_path(path):
    """
    Abstract path for consistentcy
    """
    return path.replace("\\", "/")


def make_dirs(dirs):
    """
    Create a directory path if it doesn't already exist

    Args:
        dirs (str): Path of directories to make

    Raises:
        OSError if directories cannot be created
    """
    try:
        os.makedirs(dirs)
    except OSError as e:
        # Ok to continue if parent directory already exists
        if e.errno != errno.EEXIST:
            raise


def copy_file(src_file, dest_file, verbose=False, overwrite=False):
    """
    Copy textures to the publish dir relative to a Maya scene file

    Args:
        filepath (str): Source file path
        parent_dir (str): Destination parent dir
        verbose (bool): If True, print log info
        overwrite (bool): If True, allow overwriting dest file
                          when it already exists

    Returns:
        Destination file str
    """
    src_file = clean_path(src_file)
    dest_file = clean_path(dest_file)

    # Don't overwrite existing file
    if os.path.isfile(dest_file) and not overwrite:
        return dest_file

    # Make parent dir
    make_dirs(os.path.dirname(dest_file))

    # Copy
    try:
        shutil.copyfile(src_file, dest_file)
        if verbose:
            LOG.info("Copied '{0}' to {1}".format(src_file, dest_file))
    except (IOError, OSError):
        raise

    return dest_file


def save_json(path, data, overwrite=False):
    """
    Save json data

    Args:
        path (str): File path to save
        data (dict): Data to write to file
        overwrite (bool): If True, overwrite existing file
                          If False, update existing file
                          Defaults to False

    Returns: None
    """
    try:
        with open(path, mode="wb") as handle:
            json.dump(data, handle, indent=4)
    except Exception:
        traceback.print_exc()
        raise


def load_json(path, **kwargs):
    """
    Load json file. Defaults to using OrderedDict

    Args:
        path (str): Filepath to load

    Returns:
        Data dict
    """
    if "object_pairs_hook" not in kwargs:
        kwargs["object_pairs_hook"] = collections.OrderedDict

    with open(path, mode="rb") as handle:
        return json.load(handle, **kwargs)


def get_supported_keys(scene, config_keys=None):
    """
    Get supported keys by packager config.
    These include scene context, date, filename, etc

    Args:
        scene (str): Scene filepath
        config_keys (dict): User provided keys for config sub

    Returns:
        Dict of keys
    """
    if not config_keys:
        config_keys = {}

    # Date
    if "date" not in config_keys:
        config_keys["date"] = datetime.now().strftime(
            config_keys.get("date_format", "%Y-%m-%d_%H%M%S"))

    # User
    if "user" not in config_keys:
        config_keys["user"] = getpass.get_user()

    # Filename
    if "filename" not in config_keys:
        config_keys["filename"] = os.path.splitext(os.path.basename(scene))[0]

    return config_keys


def get_package_settings(scene, config_keys, config_settings, extra_files=None):
    """
    Format scene path context, etc, into packager config settings

    Args:
        scene (str): Scene filepath
        config_keys (dict): Keys used in format str substitution in
                            config settings dict
        config_settings (dict): Config settings dict
        extra_files (dict): Dict of { source file glob path : dest dir }

    Returns:
        Dict of string formatted settings
    """
    cfg = copy.deepcopy(config_settings)

    # Extra files
    if extra_files and "extra_files" in cfg:
        cfg["extra_files"].update(extra_files)
    elif extra_files:
        cfg["extra_files"] = extra_files

    # Add user
    if "user" not in cfg:
        cfg["user"] = getpass.getuser()

    # For str formatting
    cfg_str = json.dumps(cfg)

    # Keys to sub into config
    format_keys = get_supported_keys(scene, config_keys)

    # Expand package root dir first
    package_root = Template(cfg["package_root"])
    format_keys["package_root"] = package_root.substitute(**format_keys)

    # Expand remaining settings
    settings = Template(cfg_str)
    result = json.loads(settings.substitute(**format_keys))

    # TODO: Validate dir settings all start at package root

    return result


def get_relative_path(package_scene, package_dependency, package_root):
    """
    Get relative path (Eg: '../../images/test.1001.exr')

    Args:
        package_scene (str): Path to package scene file
        package_dependency (str): Dependency file path
                                  (get relative path for this path)
        package_root (str): Root directory of the package

    Returns:
        Relative path str
    """
    # Clean
    package_scene = clean_path(package_scene)
    package_dependency = clean_path(package_dependency)
    package_root = clean_path(package_root)

    # Must start with package root
    assert(package_dependency.startswith(package_root))
    assert(package_scene.startswith(package_root))

    dep_stub = re.sub(package_root, "", package_dependency)
    dep_stub = dep_stub.strip("/")
    scene_stub = re.sub(package_root, "", package_scene)
    # Dependency must be in a subdir within the package
    if not dep_stub:
        raise ValueError("Scene file dependency must be in a subdir. "
                         "Currently it is directly in the package root: {0}"
                         "".format(package_dependency))

    scene_dirs = [s for s in scene_stub.split("/") if s]
    # Scene is directly in package root dir
    # No directory up syntax needed
    if 1 == len(scene_dirs):
        return clean_path(os.path.join(".", dep_stub))
    # Add '..' for each directory up
    else:
        dirs_up = "/".join([".." for x in range(len(scene_dirs) - 1)])
        return clean_path(os.path.join(dirs_up, dep_stub))


def basic_package_dst_path(src_path, dst_dir):
    """
    Get dependency subdirs

    Args:
        src_path (str): Source filepath str
        dst_dir (str): Destination parent dir str

    Returns:
        File path str
    """
    src_path = clean_path(src_path)
    dst_dir = clean_path(dst_dir)

    # Use subdirs from version dir down
    match = re.search("\/v\d+\/", src_path)
    if match:
        return clean_path(
            os.path.join(dst_dir, src_path[match.start() + 1:]))

    # If no version dir, use subdir named after file
    base = os.path.splitext(os.path.basename(src_path))[0]
    return clean_path(
        os.path.join(dst_dir, base, os.path.basename(src_path)))


def get_renamed_dst_path(src_path, patterns):
    """
    Rename based on config regexes

    Args:
        src_path (str): Source path
        patterns (dict): Regex pattern and sub format str data
                         From Scene Packager config

    Returns:
        Subbed filepath str if there was a match
    """
    renamed = ""
    matched = []
    for data in patterns:
        match = re.search(data["regex"], src_path)
        # Only use first available match
        if match and not renamed:
            # Sub chars
            match_dict = {}
            subs = data.get("sub_chars", {})
            for grp_name, match_str in match.groupdict().items():
                if subs.get(grp_name):
                    subbed_str = match_str
                    for k, v in subs[grp_name].items():
                        subbed_str = re.sub(k, v, subbed_str)

                    try:
                        match_dict[grp_name] = int(subbed_str)
                    except ValueError:
                        match_dict[grp_name] = subbed_str
                else:
                    try:
                        match_dict[grp_name] = int(match_str)
                    except ValueError:
                        match_dict[grp_name] = match_str

            renamed = data["format_str"].format(**match_dict)

        # Track all matches for error
        if match:
            matched.append((data, match.groupdict()))

    # Cannot resolve multiple pattern matches
    if matched and len(matched) > 1:
        LOG.error("-" * 50)
        msg = "Source path has multiple pattern matches: {0}".format(src_path)
        LOG.error(msg)
        LOG.error("-" * 50)
        for m, d in matched:
            LOG.error("Description: {0}".format(m.get("desc", "")))
            LOG.error("Regex:       {0}".format(m.get("regex", "")))
            LOG.error("Match dict:  {0}".format(d))
            LOG.error("-" * 50)
        raise ValueError(msg)

    return renamed


def write_file_copy_metadata(metadata, metadata_dir):
    """
    Write file copy metadata

    Args:
        metadata (dict): Metadata dict
        metadata_dir (str): Parent dir for metadata

    Returns:
        File path str
    """
    path = clean_path(os.path.join(metadata_dir, COPY_METADATA))
    save_json(path, metadata)

    return path


def write_package_metadata(metadata, metadata_dir):
    """
    Write package metadata

    Args:
        metadata (dict): Metadata dict
        metadata_dir (str): Parent dir for metadata

    Returns:
        File path str
    """
    path = clean_path(os.path.join(metadata_dir, PACKAGE_METADATA))
    save_json(path, metadata)

    return path


def check_package_exists(packager):
    """
    Check whether a package exists

    Args:
        packager (scene packager obj): Scene packager

    Returns:
        True if the packager destination dir exists
    """
    # Check for existing package
    try:
        if os.listdir(packager.package_root):
            return True
    except OSError as e:  # DNE
        if e.errno != errno.ENOENT:
            raise e

    return False


def check_available_dir(root):
    """
    Returns True if dir DNE or exists but is empty
    """
    try:
        if os.listdir(root):
            return True
    except OSError as e:  # DNE
        if e.errno != errno.ENOENT:
            raise e

    return False


def check_existing_package(package_root):
    """
    Check if this dir is a package root.
    Requirements: Must have 1 package_metadata.json file, in which
                  the 'package_root' key = package_root arg

    Args:
        package_root (str): Dir path to check

    Raises:
        RuntimeError

        In the following cases:
            1. No package_metadata.json found
            2. Multiple package_metadata.json found
            3. No 'package_root' key in json --> Invalid package metadata

    Returns:
        True if package metdata is found
        False if no package metadata is found or dir does not exist
    """
    package_root = os.path.abspath(package_root)

    # Doesn't exist yet
    if not os.path.exists(package_root):
        return False

    # Find existing package metadatas
    existing = []
    name = PACKAGE_METADATA
    for root, dirs, files in os.walk(package_root):
        if name in files:
            existing.append(os.path.join(root, name))

    # No packages found in this dir
    if 0 == len(existing) and os.listdir(package_root):
        # No packages found, but there is something else in this dir.
        # Tool can't resolve this.
        raise RuntimeError(
            "No existing {0} found in parent dir.\nManually delete dir to use "
            "it as a packager destination.\n{1}".format(
                PACKAGE_METADATA, package_root))
    # More than 1 package found in this dir.
    # Tool can't resolve this. User should manually delete this dir or
    # packages inside it, or choose another package destination.
    elif len(existing) > 1:
        for e in existing:
            print(e)
        raise RuntimeError(
            "Multiple {0} found in parent dir.\nManually delete/resolve to "
            "use this dir as a packager destination.\n{1}".format(
                PACKAGE_METADATA, package_root))

    # Only 1 package found
    # Check package root entry in metadata
    data = load_json(existing[0])
    if package_root != os.path.abspath(
            data.get("package_settings", {}).get("package_root")):
        raise RuntimeError(
            "{0} != {1}".format(package_root, os.path.abspath(
                data.get("package_settings", {}).get("package_root"))))

    return True


def remove_existing_package(package_root, tmp_dir=None, subproc=False):
    """
    Delete existing package
    Find existing package metadata to confirm dir should be deleted

    Args:
        package_root (str): Root dir of package
        tmp_dir (str, optional): Temp dir.
                                 Package is moved here and then removed.
                                 Used if there specific project tmp area, etc.
                                 Defaults to tempfile.mkdtemp()
        subproc (bool, optional): If True, start removal script in its own
                                  thread, to continue even if program exits.

    Returns:
        None
    """
    # TODO - Temporary
    if "Windows" != platform.system():
        raise NotImplementedError(
            "{0} platform scene package removal not supported".format(
                platform.system()))

    package_root = clean_path(package_root)
    # Doesn't exist yet
    if not os.path.exists(package_root):
        raise OSError("Package root does not exist: {0}".format(package_root))

    # Check root is a scene package
    check_existing_package(package_root)

    # Rename existing package to tmp location and delete it
    # Get tmp dir
    rename_dir = "{0}_{1}".format(os.path.basename(package_root.rstrip("/")),
                                  datetime.now().strftime("%Y-%m-%d_%H%M%S"))
    # Remove renamed subdir under tmp_dir
    if tmp_dir:
        to_remove = os.path.join(os.path.abspath(tmp_dir), rename_dir)
        tmp_package_root = to_remove
    # Remove full tmp dir
    else:
        to_remove = tempfile.mkdtemp()
        tmp_package_root = os.path.join(to_remove, rename_dir)
    # Clean
    to_remove = clean_path(to_remove)
    tmp_package_root = clean_path(tmp_package_root)

    if os.path.exists(tmp_package_root):
        raise OSError("Cannot rename existing package dir. Destination "
                      "dir already exists: {0}".format(tmp_package_root))

    # Rename to tmp
    print("Renaming package root: {0} --> {1}".format(package_root,
                                                      tmp_package_root))
    make_dirs(os.path.dirname(tmp_package_root))
    os.rename(package_root, tmp_package_root)

    # Remove tmp
    print("Removing package at: {0}".format(tmp_package_root))
    if subproc:
        print("Using subprocess")
        spawn_remove_subprocess(tmp_package_root)
    else:
        shutil.rmtree(tmp_package_root)


def spawn_remove_subprocess(remove_dir):
    """
    Start removal subprocess for the provided dir

    Args:
        remove_dir (str): Dir to remove
    """
    if "Windows" == platform.system():
        kwargs = {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
        }
    # TODO
    else:
        raise NotImplementedError(
            "{0} platform scene package removal not supported".format(
                platform.system()))

    # Create command
    exe = clean_path(os.path.join(
        os.getenv("SCENE_PACKAGER_ROOT"), "bin", "remove_scene_package.py"))
    args = ["python", exe, remove_dir]

    print("SUBPROC:", args)

    # Run
    try:
        with open(os.devnull, "w") as out_pipe:
            subprocess.Popen(
                args,
                stdout=out_pipe,
                stderr=out_pipe,
                **kwargs
            )
    except Exception:
        print("Failed to start subprocess: {0}".format(" ".join(args)))
        raise
