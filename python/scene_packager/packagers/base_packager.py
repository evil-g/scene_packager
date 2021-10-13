# -*- coding: utf-8 -*-
# Standard
import logging
import os
import pprint

# Scene packager
from scene_packager import batch_copy, scene_packager_config, utils


class Packager(object):
    """
    Base packager.
    Provide default hooks to set scene file,
    save metadata, and initialize packager settings.

    Args:
        scene (str): Scene filepath
    """
    def __init__(self, scene, settings, extra_files=None):

        if not os.path.exists(scene):
            raise ValueError("Scene does not exist!")

        # Log
        self.log = utils.get_logger(__name__, settings.get("verbose", 0))
        # Set log verbosity
        self.set_verbosity(settings.get("verbose", 0))

        # Mode
        # Available levels:
        #     Level 0: (Default) Executes full packaging.

        #     Level 1: No-copy mode.
        #              Repaths packaged scene, writes metadata.
        #              Does not execute file copy.

        #     Level 2: Dryrun on. Debug messages only.
        self.mode = 0

        self.scene = None
        self.settings = {}
        self.extra_files = None

        # Scene attrs
        # Script start/end
        self.scene_start = None
        self.scene_end = None
        self.scene_root = None

        # File copy metadata to be used by Deadline job
        self.filecopy_metadata = {}

        # File dependency data dict
        self.dep_data = {}

        # Scene file text backup
        self._scene_txt = ""
        # TODO - Nuke specific
        # Skip node classes when copying files
        self.exclude_node_files = []

        # Source scene
        self.set_scene_file(scene, settings, extra_files)

    def _init_settings(self, settings):
        """
        Initialize settings.
        If no key is provided, use config implementation.

        Args:
            settings (dict): Settings dict
        """
        self.settings = {}

        # Defaults
        # Override of root (since it's used by others below)
        self.settings["package_root"] = settings.get("package_root") or \
            scene_packager_config.package_root(self.scene)

        self.settings["packaged_scene"] = \
            scene_packager_config.packaged_scene_path(self.scene,
                                                      self.package_root)

        self.settings["source_scene_backup"] = \
            scene_packager_config.backup_scene_path(self.scene,
                                                    self.package_root)

        self.settings["metadata_path"] = scene_packager_config.metadata_path(
            self.package_root
        )

        self.settings["filecopy_metadata_path"] = \
            scene_packager_config.filecopy_metadata_path(self.package_root)

        self.settings["use_frame_limit"] = \
            scene_packager_config.use_frame_limit()

        self.settings["use_relative_paths"] = \
            scene_packager_config.use_relative_paths()

        self.settings["project_dir"] = scene_packager_config.project_directory(
            self.packaged_scene, self.package_root, self.scene
        )

        start, end = scene_packager_config.get_scene_frange(self.scene)
        self.settings["start"] = start
        self.settings["end"] = end
        self.scene_start = start
        self.scene_end = end

        # Overrides
        for key, val in settings.items():
            if val is not None:
                self.log.debug(
                    "Input setting: {}={}".format(key, val)
                )
                self.settings[key] = val

        return self.settings

    def set_scene_file(self, scene, settings=None, extra_files=None):
        """
        Set scene file for package
        """
        scene = utils.clean_path(scene)
        if not os.path.isfile(scene):
            raise ValueError("Scene does not exist: {0}")

        # Clear node data
        self.dep_data = {}

        # Update scene
        self.scene = scene

        # Initialize package settings
        self._init_settings(settings or {})

        # Extra files
        if extra_files is not None:
            self.extra_files = extra_files

        # Load file text
        with open(self.scene, "r") as handle:
            self._scene_txt = handle.read()

    def set_mode(self, mode):
        """
        Set packager mode

        Available levels:
            Level 0: (Default) Executes full packaging.

            Level 1: No-copy mode.
                     Repaths packaged scene, writes metadata.
                     Does not execute file copy.

            Level 2: Dryrun on. Debug messages only.

        Args:
            mode (int)

        Returns: None
        """
        if not isinstance(mode, int):
            raise TypeError("Invalid mode type: '{}'. Must be int".format(
                type(mode))
            )

        self.mode = mode

        if 0 == self.mode:
            self.log.debug("Package mode==0 ({} mode)".format(self.mode_str))
        elif 1 == self.mode:
            self.log.debug("Package mode==1 ({} mode)".format(self.mode_str))
        elif 2 <= self.mode:
            self.log.debug("Package mode<=2 ({} mode)".format(self.mode_str))

    @property
    def mode_str(self):
        """
        Get description str of packager mode
        """
        if 0 == self.mode:
            return "normal"
        elif 1 == self.mode:
            return "nocopy"
        elif 2 <= self.mode:
            return "debug"
        else:
            raise ValueError("Invalid mode: {}".format(self.mode))

    def set_verbosity(self, verbose=0):
        """
        Set logging level
        """
        if 0 == verbose:
            self.log.setLevel(logging.WARNING)
            utils.SCENE_PACKAGER_LOG_LEVEL = logging.WARNING
        elif 1 == verbose:
            self.log.setLevel(logging.INFO)
            utils.SCENE_PACKAGER_LOG_LEVEL = logging.INFO
        elif 2 <= verbose:
            self.log.setLevel(logging.DEBUG)
            utils.SCENE_PACKAGER_LOG_LEVEL = logging.DEBUG

    @property
    def package_root(self):
        """
        Root dir of this package
        """
        return self.settings["package_root"]

    @property
    def packaged_scene(self):
        """
        Path of packaged scene
        """
        return self.settings["packaged_scene"]

    @property
    def source_scene_backup(self):
        """
        Path of packaged scene
        """
        return self.settings["source_scene_backup"]

    @property
    def package_metadata_path(self):
        """
        Path of packaged scene
        """
        return self.settings["metadata_path"]

    @property
    def package_filecopy_metadata_path(self):
        """
        Path of packaged scene
        """
        return self.settings["filecopy_metadata_path"]

    @property
    def project_dir(self):
        return self.settings["project_dir"]

    @property
    def use_frame_limit(self):
        """
        Whether to use frame limit

        If 1, only copy specific dependency files
        If 0, copy all files that match the dependency glob path
        Example: Nuke Read node has frame range limit knob.
                 If test_%04d.exr has frames 1001-1100 on disk,
                 but the Read node only uses frames 1001-1005,
                 we may want to skip copying frames 1006-1100.
        """
        return self.settings["use_frame_limit"]

    @property
    def use_relative_paths(self):
        """
        Path of packaged scene

        TODO get old comment
        """
        return self.settings["use_relative_paths"]

    def get_packaged_path(self, filepath, parent_dir):
        """
        Get target filepath for dependency file

        Args:
            filepath (str): Dependency filepath
            parent_dir (str): Package dependency subdir

        Returns:
            Filepath str
        """
        # Check for rename format pattern
        patterns = self.settings.get("rename_patterns", [])
        renamed = utils.get_renamed_dst_path(utils.clean_path(filepath),
                                             patterns)
        # Rename matched
        if renamed:
            # Rename has extra dir already
            if os.path.dirname(renamed):
                return utils.clean_path(os.path.join(parent_dir, renamed))
            # Rename is filename only
            # Add filename dir
            else:
                return utils.clean_path(
                    os.path.join(
                        parent_dir,
                        os.path.splitext(os.path.basename(renamed))[0],
                        renamed
                    )
                )

        # Get basic packaged path
        return utils.basic_package_dst_path(filepath, parent_dir)

    def get_filecopy_metadata(self, reload=False):
        """
        Get file copy metadata dict

        Returns:
            Dict
        """
        # Return Existing
        if reload is False and self.filecopy_metadata:
            return self.filecopy_metadata

        # Load fresh
        to_copy = {}

        # TODO Logging
        # print(self.dep_data)

        if self.log.level == logging.DEBUG:
            self.log.newline()
        self.log.debug("Finding scene file dependencies...")

        for src_path, data in self.dep_data.items():
            if self.log.level == logging.DEBUG:
                self.log.newline()

            # Glob style source/dst for each node
            src_glob = utils.get_frame_glob_path(src_path)
            self.log.debug("{:24}: {}".format("Source frame sequence",
                                              src_glob))

            dst_glob = utils.get_frame_glob_path(data["packaged_path"])
            self.log.debug("{:24}: {}".format("Packaged frame sequence",
                                              dst_glob))

            # Specific frames
            frames = []
            if self.use_frame_limit:
                start = data.get("start")
                end = data.get("end")
                if start is not None and end is not None:
                    frames = list(range(start, end + 1))

            # Update metadata
            to_copy[src_glob] = {
                "dst": dst_glob,
                "frames": frames
            }

        # Add extra files
        for src_glob, dst in self.settings.get("extra_files", {}).items():
            if self.log.level == logging.DEBUG:
                self.log.newline()

            # Glob style for dst
            dst_glob = utils.get_frame_glob_path(dst)
            self.log.debug("Extra file sequence: {}".format(dst_glob))

            # Update metadata
            if src_glob in to_copy:
                self.log.debug("Skipping extra file copy. Already found in "
                               "dependency list: {0}".format(src_glob))
            else:
                to_copy[src_glob] = {
                    "dst": dst_glob,
                    "frames": []
                }

        self.log.newline()
        self.log.info(
            "Found {} file dependencies".format(len(to_copy.items()))
        )

        self.filecopy_metadata = to_copy
        return self.filecopy_metadata

    def package_metadata(self):
        """
        Package metadata dict

        Returns:
            Dict
        """
        metadata = scene_packager_config.package_metadata(
            self.scene, self.settings
        )

        # Required keys (used by inspect mode)
        required = ["date",
                    "SCENE_PACKAGER_CONFIG_PATH",
                    "source_scene",
                    "package_settings",
                    "user"]
        missing = [k for k in required if k not in metadata]
        if missing:
            msg = "Missing required metadata keys: {}\nDouble check that " \
                "scene_packager_config.package_metadata is returning the " \
                "correct keys.".format(", ".join(missing))
            self.log.error(msg)
            raise ValueError(msg)

        return metadata

    def load_scene_data(self):
        """
        Load scene data into dict

        Expected scene dict format:
            { src_file_path:  {"packaged_path": dst_file_path,
                               "relative_path": relative_file_path,
                               "start": start_frame,
                               "end": end_frame} }
        """
        self.log.debug("Loading scene data...")

        self.root, self.dep_data, self.scene_start, self.scene_end = \
            scene_packager_config.load_scene_data(
                self.packaged_scene, self.package_root, self.scene
            )

        self.log.debug("Finished.")

    def dependency_files(self):
        """
        Get scene dependency file paths

        Returns:
            List of filepath str
        """
        return self.dep_data.keys()

    def write_filecopy_metadata(self):
        """
        Save file data for file metadata to be used by file copy
        """
        self.log.newline()

        if self.mode < 2:
            self.log.info("Writing file copy metadata:")
            self.log.info(self.package_filecopy_metadata_path)

            utils.write_filecopy_metadata(self.get_filecopy_metadata(),
                                          self.package_filecopy_metadata_path)
        # Dryrun mode
        else:
            self.log.info("Filecopy metadata path:")
            self.log.info(self.package_filecopy_metadata_path)
            filecopy_data = self.get_filecopy_metadata()
            self.log.debug(
                "Filecopy metadata:\n" + pprint.pformat(filecopy_data)
            )

    def write_package_metadata(self):
        """
        Save packager settings to metadata path
        """
        self.log.newline()

        if self.mode < 2:
            self.log.info("Writing package metadata:")
            self.log.info(self.package_metadata_path)

            utils.write_package_metadata(
                self.package_metadata(), self.package_metadata_path
            )
        # Dryrun mode
        else:
            self.log.info("Package metadata path:")
            self.log.info(self.package_metadata_path)
            self.log.debug(
                "Package metadata:\n" + pprint.pformat(self.package_metadata())
            )

    def write_packaged_scene(self):
        """
        Write packaged scene with updated filepaths
        """
        self.log.newline()
        self.log.info("Writing packaged scene:")
        self.log.info(self.packaged_scene)

        return scene_packager_config.write_packaged_scene(
            self.source_scene_backup,
            self.packaged_scene,
            self.dep_data,
            self.root,
            self.project_dir,
            self.scene_start,
            self.scene_end,
            relative_paths=self.use_relative_paths
        )

    def pre_package(self):
        """
        Pre package ops:
        1. Copy source scene to backup location
        2. Export package metadata
        3. Export file copy metadata
        """
        self.log.newline()
        self.log.debug("Start pre_package")
        self.log.info("Input scene:")
        self.log.info(self.scene)

        self.log.newline()
        self.log.info("Source scene copy:")
        self.log.info(self.source_scene_backup)

        # Copy original scene to package backup dir
        # Not in dryrun mode
        if self.mode < 2:
            utils.copy_file(self.scene, self.source_scene_backup)

        # Write packager metadata
        # (They should take care of dryrun on their own)
        self.write_package_metadata()
        self.write_filecopy_metadata()

        # Override config pre-package
        scene_packager_config.pre_package(self.scene, mode=self.mode)

        self.log.debug("End pre_package")

    def package(self):
        """
        Main package ops
        """
        self.log.debug("Start packaging")

        # Repath scene
        # Modes 0, 1
        if self.mode < 2:
            self.write_packaged_scene()

        # Copy file dependencies
        # Mode 0 only
        if 0 == self.mode:
            batch_copy.copy_files(
                self.filecopy_metadata, log_level=self.log.level
            )
        else:
            self.log.newline()
            self.log.info(
                "Skipping file copy for packager mode {} ({} mode)".format(
                    self.mode, self.mode_str)
            )

        self.log.debug("End packaging")

    def post_package(self):
        """
        Post package ops
        Override can be implemented in user config
        """
        self.log.debug("Start post_package")

        scene_packager_config.post_package(self.scene, mode=self.mode)

        self.log.debug("End post_package")

    def run(self, overwrite=False, mode=0):
        """
        Run packager

        TODO: If needed, add local flag support.
              For now, just call self.submit()

        Args:
            overwrite (bool): If True, ok to overwrite existing
                              package dir
            mode (bool): If True, do not submit copy job,
                        only write packaged scene and metadata.
        """
        self.log.info(
            "Running scene packager [overwrite={0}]".format(overwrite)
        )
        self.set_mode(mode)

        # Check for existing package
        avail = utils.check_available_dir(self.package_root)
        # Already exists
        if not avail and not overwrite:
            raise RuntimeError(
                "Package already exists at: {0}\nUse --overwrite flag to "
                "force overwrite.".format(self.package_root)
            )
        # Remove existing (skip on dryrun/mode 2)
        elif (not avail) and overwrite and self.mode < 2:
            packager_tmp = scene_packager_config.package_tmp_dir(self.scene)
            utils.remove_existing_package(
                self.package_root,
                os.path.basename(self.package_metadata_path),
                tmp_dir=packager_tmp
            )

        # Load scene data
        self.load_scene_data()

        # Prep package
        self.pre_package()

        # Write scene with relative paths
        self.package()

        # Post packaging
        self.post_package()

        # Finished!
        # Print confirmation for normal, nocopy modes
        self.log.newline()
        self.log.info("*" * 50)
        if self.mode < 2:
            self.log.info("Package complete!")
            self.log.info("Completed package root: {}".format(
                self.package_root))
            # Open scene
            scene_packager_config.open_packaged_scene(self.packaged_scene)
        else:
            self.log.info("Dryrun finished!")
        self.log.info("*" * 50)
