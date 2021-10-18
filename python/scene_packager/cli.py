# -*- coding: utf-8 -*-
"""
Scene packager command line interface
"""
# Standard
import argparse
import os
import logging

# Scene packager
from . import api


# Log
LOG = logging.getLogger("scene_packager.cli")


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

    subparsers = parser.add_subparsers(dest="subparser_command",
                                       help="sub-command help")

    # --------------------------------------------------------------------
    # Run subcommand
    parser_run = subparsers.add_parser("run", help="run --help")

    parser_run.add_argument(
        "-s", "--scene", dest="input_scene", type=str, required=True,
        help=(
            "Either 1. Filepath of scene to package, or 2. Directory to search "
            "for scenes to package. If a directory is provided, finds and "
            "lists scenes that can be packaged. If -s is used with --ui mode, "
            "scenes are loaded into the ui when it is launched."
        )
    )

    # Packager overrides
    parser_run.add_argument(
        "--search-path", dest="search_path", type=str, help=(
            "Overrides env search path ($SCENE_PACKAGER_CONFIG_PATH)")
    )
    parser_run.add_argument(
        "-r", "--package-root", dest="package_root", type=str,
        help=("Target root directory for this package. Overrides any "
              "implementation in scene_packager_config.package_root()")
    )

    # Extra files
    parser_run.add_argument(
        "--extra-files", dest="extra_files", nargs="+",
        help=("List of extra filepaths to copy to the final package. Useful "
              "for adding references files that are not used by the scene.  ")
    )

    # Testing modes
    parser_run.add_argument(
        "--dryrun", dest="dryrun", action="store_true",
        help=("Dryrun mode. Prints info and source/dest file dependencies.")
    )
    parser_run.add_argument(
        "--nocopy", dest="nocopy", action="store_true",
        help=("Runs packager without packaging the file dependencies. "
              "Writes packaged scene with updated paths and metadata. "
              "Prints a log of source/dest paths for file "
              "dependencies, but does not actually copy them.")
    )
    # Overwrite existing
    parser_run.add_argument(
        "-o", "--overwrite", dest="overwrite", action="store_true",
        help=(
            "If target package destination is already a package, overwrite it."
        )
    )
    # UI mode
    parser_run.add_argument(
        "--ui", dest="ui", action="store_true",
        help=("Launch Scene Packager ui.")
    )
    # Verbosity
    parser_run.add_argument(
        "-v", "--verbose", dest="verbose", action="count", default=0,
        help=("Increase verbosity of Scene Packager.\n"
              "Use -v for basic info, -vv for debug messages.")
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
        "--config", dest="config", action="store_true",
        help=("Print info about config overrides.")
    )

    parser_inspect.add_argument(
        "--search-path", dest="search_path", type=str, help=(
            "Overrides env search path ($SCENE_PACKAGER_CONFIG_PATH)")
    )

    parser_inspect.add_argument(
        "--dir", dest="inspect_dir", type=str,
        help=("Search this directory for existing scene packages.")
    )

    parser_inspect.add_argument(
        "-r", "--open-root-dir", dest="open_root_dir", action="store_true",
        help=("Open root directory of each package.")
    )

    parser_inspect.add_argument(
        "-s", "--open-scene-dir", dest="open_scene_dir", action="store_true",
        help=("Open parent directory of each packaged scene.")
    )

    parser_inspect.add_argument(
        "-v", "--verbose", dest="verbose", action="count", default=0,
        help=("Print info about found packages.\n"
              "Use -v to print scene/user/date, "
              "-vv to print all package metadata.")
    )

    # --------------------------------------------------------------------

    opts = parser.parse_args()

    # --- Inspect mode ---
    if "inspect" == opts.subparser_command:
        # Cannot use open root and open scene dir at the same time
        if opts.open_root_dir and opts.open_scene_dir:
            raise RuntimeError(
                "Argument conflict. Cannot use --open-root-dir and "
                "--open-scene-dir at the same time."
            )
        if opts.search_path and not opts.config:
            raise RuntimeError(
                "--search-path override must be used with --config"
            )

        # Config inspection
        if opts.config:
            api.inspect_config(opts.search_path)

        # Dir inspection
        if opts.inspect_dir:
            api.inspect(
                opts.inspect_dir, open_root_dir=opts.open_root_dir,
                open_scene_dir=opts.open_scene_dir, verbose=opts.verbose
            )
        return

    # --- Run mode --
    if "run" != opts.subparser_command:
        raise RuntimeError(
            "Invalid subparser command: {0}".format(opts.subparser_command)
        )

    if opts.dryrun and opts.nocopy:
        raise RuntimeError(
            "Argument conflict. Cannot use --dryrun and --no-copy "
            "at the same time."
        )

    # Directory mode
    if os.path.isdir(opts.input_scene):
        files = []
    # Single scene
    else:
        files = [opts.input_scene]

    # No scenes
    if not files:
        raise RuntimeError("No input scenes found.")
    # Multiple scenes
    elif len(files) > 1:
        # No root override allowed with multiple files
        if opts.package_root:
            raise RuntimeError(
                "Cannot use --package-root when packaging multiple files. "
                "Update the config .py if you need to adjust the package root."
            )

        # TODO User input required
        LOG.info("Continue packaging {} scene files?".format(len(files)))

    # TODO extra files subdir

    # ----------------------------------
    # Initialize config
    # ----------------------------------
    api.load_config(search_path=opts.search_path)

    # Dryrun level
    if opts.dryrun:
        mode = 2
    elif opts.nocopy:
        mode = 1
    else:
        mode = 0

    # Launch UI
    if opts.ui:
        LOG.info("Starting Scene Packager UI...")
        pass
    # Package immediately
    else:
        LOG.info("Packaging {} scenes...".format(len(files)))

        api.package_scenes(files,
                           package_root=opts.package_root,
                           extra_files=opts.extra_files,
                           overwrite=opts.overwrite,
                           mode=mode,
                           verbose=opts.verbose)
