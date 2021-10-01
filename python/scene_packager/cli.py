# -*- coding: utf-8 -*-
"""
Scene packager command line interface
"""
# Standard
import argparse
import os
import logging

# Scene packager
from . import config


# Log
LOG = logging.getLogger("scene_packager.cli")


def _load_config_override(path=None):
    """
    """
    path = path or os.getenv(
        "SCENE_PACKAGER_CONFIG",
        os.path.expanduser("~/scene_packager_config.py")
    )

    mod = {
        "__file__": path,
    }

    try:
        with open(path) as f:
            exec(compile(f.read(), f.name, "exec"), mod)
    except IOError:
        raise
    except Exception:
        raise ("Invalid override config: {}".format(path))

    for key in dir(config):
        if key.startswith("__"):
            continue

        try:
            value = mod[key]
        except KeyError:
            continue

        setattr(config, key, value)

    return path


def _init_backup_config():
    """Make backup copies of originals, with `_` prefix
    Useful for augmenting an existing value with your own config
    """

    for member in dir(config):
        if member.startswith("__"):
            continue

        setattr(config, "_%s" % member,
                getattr(config, member))


def main():
    """
    Scene packager commandline interface

    Subcommands:
        1. scene-packager run
           Executes scene packager
        2. scene-packager inspect
           Inspects target directory for existing packages, lists their info
    """
    parser = argparse.ArgumentParser("scene-packager", description=(
        "An application to package scene and its dependencies under a target "
        "directory. See details with scene-packager --help"
    ))

    subparsers = parser.add_subparsers(help="sub-command help")

    # --------------------------------------------------------------------
    # Run subcommand
    parser_run = subparsers.add_parser("run", help="run --help")

    parser_run.add_argument(
        "-s", "--scene", dest="input_scene", type=str, required=True,
        help(
            "Either 1. Filepath of scene to package, or 2. Directory to search "
            "for scenes to package. If a directory is provided, finds and "
            "lists scenes that can be packaged. If -s is used with --ui mode, "
            "scenes are loaded into the ui when it is launched."
        )
    )

    # UI mode
    parser_run.add_argument(
        "--ui", dest="ui", action="store_true",
        help("Launch Scene Packager ui.")
    )

    # Packager overrides
    parser_run.add_argument("--config", dest="config", type=str, help=(
        "Path to a config .py file. Overrides $SCENE_PACKAGER_CONFIG_FILE"
    ))
    parser_run.add_argument(
        "-r", "--package-root", dest="package_root", type=str,
        help("Target root directory for this package. "
             "Overrides config.package_root() function.")
    )

    # Extra files
    parser_run.add_argument(
        "--extra-files", dest="extra_files", type=list,
        help("List of extra files to copy to the final package. Useful for "
             "adding references files that may not be used by the scene. ")
    )
    # Extra files dest copy dir
    parser_run.add_argument(
        "--extra-subdir", dest="extra_subdir", type=str,
        help(
            "Subdir to package extra files under. Eg: 'reference_images', etc."
        )
    )

    # Overwrite existing
    parser_run.add_argument(
        "-o", "--overwrite", dest="overwrite", action="store_true",
        help(
            "If target package destination is already a package, overwrite it."
        )
    )

    # Testing modes
    parser_run.add_argument(
        "--no-copy", dest="no_copy", action="store_true",
        help("Runs packager without packaging the file dependencies. "
             "Outputs packaged scene with updated paths and package metadata. "
             "Prints a log of source/dest paths for file dependencies, but "
             "does not actually copy them.")
    )
    parser_run.add_argument(
        "--dryrun", dest="dryrun", action="store_true",
        help=("Dryrun mode. Prints al log of source/dest file dependencies.")
    )
    # Verbosity
    parser_run.add_argument(
        "-v", "--verbose", dest="verbose", action="count", default=0,
        help=("Increase verbosity of Scene Packager. "
              "Use -v for extra file copy info, -vv for debug messages.")
    )
    # Scene Packager version info
    parser_run.add_argument(
        "--version", dest="version", action="store_true",
        help=("Print version and exit")
    )

    # --------------------------------------------------------------------
    # Inspect subcommand
    parser_inspect = subparsers.add_parser("inspect", help="inspect --help")

    parser_inspect.add_argument(
        "--dir", dest="inspect_dir", type=str, required=True,
        help=("Search this directory for existing scene packages")
    )

    # --------------------------------------------------------------------

    opts = parser.parse_args()

    # --- Inspecting ---
    if opts.get("inspect_dir"):

        return

    # --- Running --

    # TODO Load config

    # Directory mode
    if os.path.isdir(opts["input_scene"]):
        files = []
    # Single scene
    else:
        files = [opts["input_scene"]]

    # No scenes
    if not files:
        raise RuntimeError("No input scenes found.")
    # Multiple scenes
    elif len(files) > 1:
        # No root override allowed with multiple files
        if opts.get("package_root"):
            raise RuntimeError(
                "Cannot use --package-root when packaging multiple files. "
                "Update the config .py if you need to adjust the package root."
            )

        # TODO User input required
        LOG.info("Continue packaging {} scene files?".format(len(files)))

    # Extra files
    extra_files = opts.get("extra_files", [])
    # TODO extra files subdir

    overwrite = opts.get("overwrite", False)
    dryrun = opts.get("dryrun", False)
    # TODO dryrun vs. nocopy

    # Launch UI
    if opts.get("ui"):
        LOG.info("Starting Scene Packager UI...")
        pass
    # Package immediately
    else:
        LOG.info("Packaging {} scenes...".format(len(files)))
        api.package_scenes(files, opts, overwrite=overwrite, dryrun=dryrun)
