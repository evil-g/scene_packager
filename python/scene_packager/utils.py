# -*- coding: utf-8 -*-
# Standard
from datetime import datetime
import errno
from glob import glob
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
import traceback
import types


# Globals
CONFIG = None

# Frame regex
FRAME_PAD_REGEX = r"(?<=[_\.])(?P<frame>#+|\d+|\%\d*d)$"
FRAME_PAD_FMT_REGEX = r"(?<=[_\.])(?P<frame>#+|\%\d*d)$"

# Default log level
SCENE_PACKAGER_LOG_LEVEL = logging.WARNING


def log_blank_line(self, count=1):
    """
    Log x number of blank lines
    """
    # Switch to blank handler
    self.removeHandler(self.output_handler)
    self.addHandler(self.blank_handler)

    # Output lines
    for i in range(count):
        self.info("")

    # Switch to output handler
    self.removeHandler(self.blank_handler)
    self.addHandler(self.output_handler)


def get_logger(logger_name, level=None):
    """
    Get logger

    Args:
        logger_name (str): Logger name
        level (int): Logger level (logging.WARNING, etc)

    Returns:
        Logger obj
    """
    if level is None:
        level = SCENE_PACKAGER_LOG_LEVEL

    log = logging.getLogger(logger_name)
    log.setLevel(level)
    log.propagate = False

    if log.handlers:
        for handler in log.handlers:
            handler.setLevel(level)
    else:
        # Add output handler
        handler = logging.StreamHandler()
        handler.setLevel(level)

        if level == logging.DEBUG:
            formatter = logging.Formatter(
                "%(name)-15s %(levelname)-8s: %(message)s"
            )
        else:
            formatter = logging.Formatter("%(levelname)-8s: %(message)s")

        handler.setFormatter(formatter)
        log.addHandler(handler)

    # Add blank line handler
    blank_handler = logging.StreamHandler()
    blank_handler.setLevel(level)
    blank_handler.setFormatter(logging.Formatter(fmt=""))

    # Add log.newline() method
    log.output_handler = handler
    log.blank_handler = blank_handler
    log.newline = types.MethodType(log_blank_line, log)

    return log


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
    log = get_logger(__name__)

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
            log.info("Copied '{0}' to {1}".format(src_file, dest_file))
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
        with open(path, mode="w") as handle:
            json.dump(data, handle, indent=4)
    except Exception:
        traceback.print_exc()
        raise


def load_json(path, **kwargs):
    """
    Load json file

    Args:
        path (str): Filepath to load

    Returns:
        Data dict
    """
    with open(path, mode="rb") as handle:
        return json.load(handle, **kwargs)


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
    # Remove frame pad (#### or %04d style only)
    base = os.path.splitext(os.path.basename(src_path))[0]
    # Glob style
    if "*" == base:
        subdir = ""
    else:
        subdir = re.sub(FRAME_PAD_FMT_REGEX, "", base)

    return clean_path(
        os.path.join(dst_dir, subdir, os.path.basename(src_path)))


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
    log = get_logger(__name__)

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
        log.error("-" * 50)
        msg = "Source path has multiple pattern matches: {0}".format(src_path)
        log.error(msg)
        log.error("-" * 50)
        for m, d in matched:
            log.error("Description: {0}".format(m.get("desc", "")))
            log.error("Regex:       {0}".format(m.get("regex", "")))
            log.error("Match dict:  {0}".format(d))
            log.error("-" * 50)
        raise ValueError(msg)

    return renamed


def write_filecopy_metadata(metadata, metadata_path):
    """
    Write file copy metadata

    Args:
        metadata (dict): Metadata dict
        metadata_path (str): Path to write metadata to

    Returns:
        File path str
    """
    path = clean_path(metadata_path)
    save_json(path, metadata)

    return path


def write_package_metadata(metadata, metadata_path):
    """
    Write package metadata

    Args:
        metadata (dict): Metadata dict
        metadata_path (str): Path to write metadata to

    Returns:
        File path str
    """
    path = clean_path(metadata_path)
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
    Return True if directory is available for use
    (Either exists and is empty, or does not exist)

    Args:
        root (str): Dir to check

    Returns:
        bool
    """
    try:
        if os.listdir(root):
            return False
    except OSError as e:  # DNE
        if e.errno != errno.ENOENT:
            raise e

    return True


def find_existing_packages(root_dir, metadata_file):
    """
    Find existing package metadata under directory root

    Args:
        package_root (str): Root dir
        metadata_file (str): Metadata file basename

    Returns:
        List of package metadata paths
    """
    # Doesn't exist yet
    if not os.path.exists(root_dir):
        raise OSError("{} does not exist".format(root_dir))

    # Find existing package metadatas
    existing = []
    name = metadata_file
    for root, dirs, files in os.walk(root_dir):
        if name in files:
            existing.append(os.path.join(root, name))

    return existing


def check_existing_package(package_root, metadata_file):
    """
    Check if this dir is a package root.
    Requirements: Must have 1 package_metadata.json file, in which
                  the 'package_root' key = package_root arg

    Args:
        package_root (str): Dir path to check
        metadata_file (str): Metadata file basename

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
    log = get_logger(__name__)
    package_root = os.path.abspath(package_root)

    # Get existing package metadata files
    try:
        existing = find_existing_packages(package_root, metadata_file)
    except OSError:
        return False

    MANUAL_REQ = "Manually delete this dir to use it as a package root."
    # No packages found in this dir
    if 0 == len(existing) and os.listdir(package_root):
        # No packages found, but there is something else in this dir.
        # Tool can't resolve this.
        msg = "No existing {0} found in package root dir.\nI can't tell " \
            "if this is an old package or not.\n{1}\n{2}".format(
                metadata_file, MANUAL_REQ, package_root)
        # Log
        log.newline()
        log.error("*" * 50)
        log.error("Failed Package Overwrite")
        log.newline()
        for m in msg.split("\n"):
            log.error(m)
            log.newline()
        log.error("*" * 50)
        log.newline()

        raise RuntimeError(msg)
    # More than 1 package found in this dir.
    # Tool can't resolve this. User should manually delete this dir or
    # packages inside it, or choose another package destination.
    elif len(existing) > 1:
        msg = "Multiple {0} files found in package root dir.\n{1}\n{2}".format(
            metadata_file, MANUAL_REQ, package_root)
        # Log
        log.newline()
        log.error("*" * 50)
        log.error("Failed Package Overwrite")
        log.newline()
        for m in msg.split("\n"):
            log.error(m)
            log.newline()
        log.error("Existing packages:")
        for e in existing:
            log.error(e)
        log.newline()
        log.error("*" * 50)
        log.newline()

        raise RuntimeError(msg)

    # Only 1 package found
    # Check package root entry in metadata
    data = load_json(existing[0])
    if package_root != os.path.abspath(
            data.get("package_settings", {}).get("package_root")):
        msg = "Found a package, but its root is different than the current " \
            "package root.\n{0}\nInput root: {1}\nFound root: {2}".format(
                MANUAL_REQ, package_root, os.path.abspath(
                    data.get("package_settings", {}).get("package_root")
                )
            )
        # Log
        log.newline()
        log.error("*" * 50)
        log.error("Failed Package Overwrite")
        log.newline()
        for m in msg.split("\n"):
            log.error(m)
            log.newline()
        log.error("*" * 50)
        log.newline()

        raise RuntimeError(msg)

    return True


def remove_existing_package(package_root, metadata_file, tmp_dir=None,
                            subproc=False):
    """
    Delete existing package
    Find existing package metadata to confirm dir should be deleted

    Args:
        package_root (str): Root dir of package
        metadata_file (str): Package metadata file name
        tmp_dir (str, optional): Temp dir.
                                 Package is moved here and then removed.
                                 Used if there specific project tmp area, etc.
                                 Defaults to tempfile.mkdtemp()
        subproc (bool, optional): If True, start removal script in its own
                                  thread, to continue even if program exits.

    Returns:
        None
    """
    log = get_logger(__name__)
    # TODO - Temporary
    if "Windows" != platform.system():
        raise NotImplementedError(
            "{} platform scene package removal not supported".format(
                platform.system()))

    package_root = clean_path(package_root)
    # Doesn't exist yet
    if not os.path.exists(package_root):
        raise OSError("Package root does not exist: {}".format(package_root))

    # Check root is a scene package
    check_existing_package(package_root, metadata_file)

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
        raise OSError("Cannot rename existing package dir. Destination tmp "
                      "dir already exists: {0}".format(tmp_package_root))

    # Rename to tmp
    log.newline()
    log.info("Renaming package root: {0} --> {1}".format(package_root,
                                                         tmp_package_root))
    make_dirs(os.path.dirname(tmp_package_root))
    os.rename(package_root, tmp_package_root)

    # Remove tmp
    log.info("Removing package at: {0}".format(tmp_package_root))
    if subproc:
        spawn_remove_subprocess(tmp_package_root)
    else:
        shutil.rmtree(tmp_package_root)


def spawn_remove_subprocess(remove_dir):
    """
    Start removal subprocess for the provided dir

    Args:
        remove_dir (str): Dir to remove
    """
    log = get_logger(__name__)

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

    log.info("SUBPROC: {}".format(args))
    log.newline()

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
        log.error("Failed to start subprocess: {0}".format(" ".join(args)))
        raise
