# -*- coding: utf-8 -*-
# Standard
from datetime import datetime
import logging
import os

# Scene packager
from scene_packager import config, utils


class Packager(object):
    """
    Base packager.
    Provide default hooks to set scene file,
    save metadata, and initialize packager settings.

    Args:
        scene (str): Scene filepath
    """
    def __init__(self, scene, config_keys, extra_files=None):

        if not os.path.exists(scene):
            raise ValueError("Scene does not exist!")

        # Log
        self.log = logging.getLogger("scene_packager")

        self.scene = None
        self.settings = None
        self.extra_files = None

        # Scene attrs
        # Script start/end
        self.scene_start = None
        self.scene_end = None
        self.scene_root = None

        # Keys for config substitution
        self.config_keys = {}

        # If 1, packaged scene will use relative path references
        # (Relative to the packaged scene path
        # If 0, use full disk path
        self.relative_paths = 0

        # If 1, only copy specific dependency files
        # If 0, copy all files that match the dependency glob path
        # Example: Nuke Read node has frame range limit knob.
        #          If test_%04d.exr has frames 1001-1100 on disk,
        #          but the Read node only uses frames 1001-1005,
        #          we may want to skip copying frames 1006-1100.
        self.frame_limit = 0

        # File copy metadata to be used by Deadline job
        self.file_copy_metadata = {}

        # Metdata paths
        self.package_metadata = ""
        self.file_copy_metadata = ""

        # File dependency data dict
        self.dep_data = {}

        # Scene file text backup
        self._scene_txt = ""
        # TODO - Nuke specific
        # Skip node classes when copying files
        self.exclude_node_files = []

        # Source scene
        self.set_scene_file(scene, config_keys, extra_files)

    def _config_settings(self):
        """
        Config settings dict
        """
        return utils.get_package_settings(self.scene,
                                          self.config_keys,
                                          utils.packager_settings(),
                                          self.extra_files)

    def set_scene_file(self, scene, config_keys=None, extra_files=None):
        """
        Set scene file for package
        """
        scene = utils.clean_path(scene)

        if not os.path.isfile(scene):
            raise ValueError("Scene does not exist: {0}")

        # Clear node data
        self.dep_data = {}

        # Update scene (required), config keys (optional)
        # and extra files (optional)
        self.scene = scene
        if config_keys is not None:
            self.config_keys = config_keys
        if extra_files is not None:
            self.extra_files = extra_files

        # Update settings
        self.settings = self._config_settings()

        # Metdata paths
        self.package_metadata = ""
        self.file_copy_metadata = ""

        # Relative path setting
        self.set_relative_path_mode(self.settings.get("use_relative_path", 0))

        # Frame limit setting
        self.set_frame_limit_mode(self.settings.get("use_frame_limit", 0))

        # TODO Check file data
        # Load file text
        with open(self.scene, "r") as handle:
            self._scene_txt = handle.read()

    def set_relative_path_mode(self, relative):
        """
        Set relative path mode on/off
        """
        self.relative_paths = relative

    def set_frame_limit_mode(self, limit):
        """
        Set frame range limit mode on/off
        """
        self.frame_limit = limit

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
        return utils.clean_path(
            os.path.join(self.settings["package_scene_dir"],
                         self.settings["package_scene_filename"])
        )

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

    def get_file_copy_metadata(self):
        """
        Get file copy metadata dict

        Returns:
            Dict
        """
        to_copy = {}

        for src_path, data in self.dep_data.items():
            # Glob style source/dst for each node
            src_glob = utils.get_frame_glob_path(src_path)
            dst_glob = utils.get_frame_glob_path(data["packaged_path"])

            # Specific frames
            frames = []
            if self.frame_limit:
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
            # Glob style for dst
            dst_glob = utils.get_frame_glob_path(dst)

            # Update metadata
            if src_glob in to_copy:
                self.log.info("Skipping extra file copy. Already found in "
                              "dependency list: {0}".format(src_glob))
            else:
                to_copy[src_glob] = {
                    "dst": dst_glob,
                    "frames": []
                }

        return to_copy

    def load_scene_data(self):
        """
        Load scene data into dict

        Expected scene dict format:
            { src_file_path:  {"packaged_path": dst_file_path,
                               "relative_path": relative_file_path,
                               "start": start_frame,
                               "end": end_frame} }
        """
        config.load_scene_data()

    def dependency_files(self):
        """
        Get scene dependency file paths

        Returns:
            List of filepath str
        """
        return self.dep_data.keys()

    def write_file_copy_metadata(self):
        """
        Save file data for file metadata to be used by file copy
        """
        self.file_copy_metadata = utils.write_file_copy_metadata(
            self.get_file_copy_metadata(),
            self.settings["file_copy_metadata_dir"]
        )

    def write_package_metadata(self):
        """
        Save packager settings to metadata path
        """
        metadata = {
            "date": datetime.now().strftime("%Y-%m-%d_%H%M%S"),
            "package_settings": self.settings,
            "source_file": self.scene,
            "user": self.settings["user"],
        }

        self.package_metadata = utils.write_package_metadata(
            metadata, self.settings["metadata_dir"]
        )

    def write_packaged_scene(self):
        """Write packaged scene with new filepaths"""
        return config.write_packaged_scene(
            self.package_source_scene,
            self.packaged_scene,
            self.dep_data,
            self.root,
            self.scene_start,
            self.scene_end,
            self.relative_paths
        )

    def pre_package(self):
        """
        Pre package ops:
        1. Copy source scene to backup location
        2. Export package metadata
        3. Export file copy metadata
        """
        # Copy original scene to package backup dir
        scene_copy = os.path.join(self.settings["scene_source_dir"],
                                  os.path.basename(self.scene))
        self.package_source_scene = utils.copy_file(self.scene, scene_copy)

        # Write packager metadata
        self.write_package_metadata()
        self.write_file_copy_metadata()

    def submit(self):
        """
        Hook for farm submission
        Typically called inside self.run implementation
        """
        raise NotImplementedError

    def run(self, overwrite=False, dryrun=False):
        """
        Run packager

        TODO: If needed, add local flag support.
              For now, just call self.submit()

        Args:
            overwrite (bool): If True, ok to overwrite existing
                              package dir
            dryrun (bool): If True, do not submit copy job,
                        only write packaged scene and metadata.
        """
        # Check for existing package
        exists = utils.check_available_dir(self.package_root)
        # Already exists
        if exists and not overwrite:
            raise RuntimeError(
                "Package already exists at: {0}".format(self.package_root))
        # Remove existing (skip on dryrun)
        elif exists and overwrite and not dryrun:
            self.log.info(
                "Removing existing package... overwrite={0}".format(overwrite))
            packager_tmp = self.settings.get("package_tmp_dir")
            utils.remove_existing_package(
                self.package_root, tmp_dir=packager_tmp, subproc=True)

        # Load scene data
        self.load_scene_data()

        self.log.info("Running scene packager... dryrunrun={0}".format(dryrun))

        # Prep package
        self.pre_package()

        # Write scene with relative paths
        self.write_packaged_scene()

        # Submit copy job
        if not dryrun:
            self.submit()
