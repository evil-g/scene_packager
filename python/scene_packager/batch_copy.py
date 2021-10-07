"""
Deadline script for basic file copy operations
Python dependency only
"""
# Standard imports
import argparse
import errno
import glob
import json
import logging
import os
import re
import subprocess

# Scene packager
from . import utils


def parse_args():
    """
    Parse input args
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--file", dest="file", required=True)
    parser.add_argument("--force",
                        action="store_true",
                        default=False,
                        dest="force")

    return parser.parse_args()


def clean_path(path):
    """
    CLean path

    Args:
        path (str): Clean path

    Returns:
        Path str
    """
    # Y drive == nas0
    # S drive == main
    DRIVE_MAP = {
        "Y:": ["project", "tools"],
        "S:": ["ANIMA", "common", "ILCA"]
    }
    # Strip out these drives to normalize for OS mapping
    STRIP_DRIVES = {
        "//studioanima.local/nas0": "Y:",
        "//studioanima.local/main": "S:",
        "/mnt/main": "S:"
    }

    try:
        path = path.replace("\\", "/")
    except UnicodeDecodeError:  # Decode unicode
        path = path.decode("UTF-8").replace("\\", "/")

    # Strip any explicit drives
    for drive_path, drive in STRIP_DRIVES.items():
        if path.startswith(drive_path):
            path = re.sub("^" + re.escape(drive_path), "", path)

    # Windows
    if "nt" == os.name:
        # Path does not start with a drive
        if path[0] == "/":
            # Search for first dir in mount point entries
            dir_name = path.split("/")[1]
            for drive, mounts in DRIVE_MAP.items():
                # Match found
                if dir_name in mounts:
                    path = drive + path
            # TODO No match found - raise here later
    # Posix
    elif path[0].isalpha() and path[1] == ":":
        path = path[2:]

    return path


def copy_files(data, force=False, log_level=logging.WARNING):
    """
    Copy files

    Args:
        data (dict):
        force (bool): If True, overwrite

    Returns: None
    """
    log = utils.get_logger(__name__, level=log_level)
    log.info("Starting file copy...")

    # Copy each
    failed = []
    FRAME_REGEX = r"(?<=[_\.])(?P<frame>#+|\d+|\%\d*d)$"
    for src, data in data.items():
        # Clean inputs
        src = clean_path(src)
        # Dst is parent directory
        if data["dst"].endswith("/"):
            dst = clean_path(os.path.join(data["dst"], os.path.basename(src)))
        # Dst is filepath
        else:
            dst = clean_path(os.path.join(data["dst"]))
        dst_dir = os.path.dirname(dst)

        # Get all source files
        globbed = glob.glob(src)
        # Create parent dirs
        if globbed:
            try:
                os.makedirs(dst_dir)
            except OSError as e:
                # Ok to continue if parent directory already exists
                if e.errno != errno.EEXIST:
                    raise

            # Copy
            if "nt" == os.name:
                # Copy command
                cwd = os.path.dirname(src)
                # Force /Y
                if force:
                    cmd = "xcopy /Y/f \"{0}\" \"{1}\"".format(
                        os.path.basename(src), dst_dir)
                # No force
                else:
                    cmd = "xcopy /f \"{0}\" \"{1}\"".format(
                        os.path.basename(src), dst_dir)

                # Rename after copy
                to_rename = {}
                if os.path.basename(src) != os.path.basename(dst):
                    # Dest frame & ext
                    frame_base, ext = os.path.splitext(os.path.basename(dst))
                    error = False

                    for each in globbed:
                        # Get frame from source path
                        match = re.search(FRAME_REGEX,
                                          os.path.splitext(each)[0])
                        if match:
                            # Orig dest file (with src basename)
                            orig_file = clean_path(os.path.join(
                                dst_dir, os.path.basename(each)))

                            # Sub src frame into dest path
                            subbed = re.sub(r"\*",
                                            match.group("frame"),
                                            frame_base)
                            dst_file = clean_path(os.path.join(
                                dst_dir, subbed + ext))

                            # Add to remove dict
                            to_rename[orig_file] = dst_file
                        else:
                            error = True
                            break

                    # Frames could not be processed
                    if error:
                        failed.append("Error creating single frame copy "
                                      "commands: {0}".format(src))
                        continue
            else:
                # TODO Linux
                # cmd = "cp {0} {1}"
                failed.append("Posix not implemented: {0}".format(src))
                continue

            # Logging
            if len(globbed) > 1:
                log.info("Copying {0} files...".format(len(globbed)))
            else:
                log.info("Copying {0} file...".format(len(globbed)))
            log.info(cmd)

            # Run copy
            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    shell=True,
                                    cwd=cwd)

            stdout, stderr = proc.communicate()

            # TODO outputs
            log.debug(stdout)
            if stderr:
                log.error(stderr)
            log.debug(proc.returncode)

            if to_rename:
                log.info("-" * 50)
                log.info("Renaming: {0} --> {1}".format(clean_path(
                    os.path.join(os.path.dirname(dst), os.path.basename(src))),
                    dst)
                )
                for orig_dst in sorted(to_rename.keys()):
                    renamed_dst = to_rename[orig_dst]
                    # File exists
                    # Replace if force=True
                    if os.path.isfile(renamed_dst):
                        if force:
                            try:
                                os.rename(orig_dst, renamed_dst)
                            except OSError as e:
                                # Windows does not support forced renaming
                                # errno.EEXIST is raised
                                # https://docs.python.org/3/library/os.html#os.rename
                                if e.errno == errno.EEXIST:
                                    # Remove + rename
                                    # Windows os.remove may error if file is in use
                                    # In this case, raise
                                    # https://docs.python.org/3/library/os.html#os.remove
                                    os.remove(renamed_dst)
                                    os.rename(orig_dst, renamed_dst)
                                else:
                                    raise e
                        else:
                            raise RuntimeError(
                                "Cannot rename target, file already exists: "
                                "{0}\nUse --force to overwrite existing files"
                                "".format(renamed_dst)
                            )
                    # Doesn't exist yet
                    else:
                        os.rename(orig_dst, renamed_dst)

            # Check
            if glob.glob(dst):
                log.info("Ok!")
            else:
                failed.append("Failed to copy files: {0}".format(dst_dir))
        else:
            failed.append("No files found: {0}".format(src))

    if failed:
        log.error("-" * 50)
        log.error("Copy errors:")
        log.error("\n".join(failed))
        raise RuntimeError("{0} errors copying files".format(len(failed)))
    else:
        log.info("Copy finished!")


def main():
    """
    Copy files to destination dir in metadata
    """
    args = parse_args()

    # Validate scene data file
    try:
        metadata = args.file
    except IndexError:
        raise RuntimeError("No json file provided!")
    else:
        if not os.path.isfile(metadata):
            raise OSError("Copy data json does not exist at '{0}'!"
                          "".format(metadata))

    # Force flag overwrites rename if on
    force = args.force

    # Load files
    with open(metadata, mode="rb") as handle:
        data = json.load(handle)

    # Run
    copy_files(data, force=force)


if "__main__" == __name__:
    main()
