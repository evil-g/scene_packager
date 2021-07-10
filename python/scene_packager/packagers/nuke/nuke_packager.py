# -*- coding: utf-8 -*-
# Standard
import os
import re

# Scene packager
from .. import base_packager
from . import utils
from scene_packager import utils as base_utils


class NukePackager(base_packager.Packager):
    """
    Nuke Packager

    Parse a nuke script to get filepaths.
    Does not require commandline.
    """
    def __init__(self, scene, config_keys, extra_files=None):
        """
        """
        self._scene_txt = ""  # Scene file text
        self.dep_data = {}   # Nuke node data
        self.exclude_node_files = []  # Skip node classes when copying files

        # Script start/end
        self.start = None
        self.end = None
        self.root = None

        super(NukePackager, self).__init__(scene, config_keys, extra_files)

    def set_scene_file(self, scene, config_keys=None, extra_files=None):
        """
        Set scene file
        """
        super(NukePackager, self).set_scene_file(scene,
                                                 config_keys,
                                                 extra_files)

        # Load file text
        with open(self.scene, "r") as handle:
            self._scene_txt = handle.read()

        # Exclude nodes
        self.exclude_node_files = self.settings.get("exclude_node_files", [])

    def load_scene_data(self):
        """
        Load node file data into dict
        """
        for node in utils.parse_nodes(self.scene):
            # Root
            if "Root" == node.Class():
                self.root = node
            # Node has files
            if node.Class() not in self.exclude_node_files and node.files():
                for file in node.files():
                    # Get target file path
                    dst = self.get_packaged_path(
                        file, utils.get_node_dir(node.Class(), self.settings))
                    rel = ""
                    if self.relative_paths:
                        try:
                            rel = base_utils.get_relative_path(
                                self.packaged_scene,
                                dst,
                                self.settings["package_root"]
                            )
                        except AssertionError:
                            self.log.error("Error getting relative path: {0}"
                                           "".format(node.knob_value("name")))
                            self.log.error("packaged root: {0}".format(
                                self.settings["package_root"]))
                            self.log.error("packaged scene: {0}".format(
                                self.packaged_scene))
                            self.log.error("dependency: {0}".format(dst))
                            raise

                    # Node already logged
                    curr_start = None
                    curr_end = None
                    if file in self.dep_data:
                        # Check
                        assert(self.dep_data[file]["packaged_path"] == dst)
                        if rel:
                            assert(self.dep_data[file]["relative_path"] == rel)

                        curr_start = self.dep_data[file].get("start")
                        curr_end = self.dep_data[file].get("end")
                        # Start frame
                        try:
                            start = node.knob_value("first")
                        except KeyError:
                            pass
                        else:
                            if curr_start is None or int(start) < int(curr_start):
                                self.dep_data[file]["start"] = int(start)
                        # End frame
                        try:
                            end = node.knob_value("last")
                        except KeyError:
                            pass
                        else:
                            if curr_end is None or int(end) > int(curr_end):
                                self.dep_data[file]["end"] = int(end)
                    # New node
                    else:
                        data = {
                            "packaged_path": dst,
                            "relative_path": rel
                        }

                        # Start frame
                        try:
                            start = node.knob_value("first")
                            data["start"] = int(start)
                        except KeyError:
                            pass
                        else:
                            if self.start is None or start < self.start:
                                self.start = start
                        # End frame
                        try:
                            end = node.knob_value("last")
                            data["end"] = int(end)
                        except KeyError:
                            pass
                        else:
                            if self.end is None or end > self.end:
                                self.end = end

                        self.dep_data[file] = data

        # Raise error if no root found
        if not self.root:
            raise ValueError("Error: no Root node found!")

    def write_packaged_scene(self):
        """
        Write out scene with packaged paths
        """
        # Load backup scene text
        with open(self.package_source_scene, "r") as handle:
            scene_data = handle.read()

        raw_scene_data = r"{0}".format(scene_data)

        # TODO Better cleaning support
        # Clean root
        new_root = utils.clean_root(
            self.root._data,
            self.settings.get("project_directory"),
            self.start,
            self.end
        )
        if new_root:
            raw_scene_data = re.sub(
                ur"%s" % self.root.data.decode("utf8"),
                ur"%s" % new_root.decode("utf8"),
                raw_scene_data.decode("utf8"),
                flags=re.UNICODE).encode("utf8")

        # Sub new files
        for file, data in self.dep_data.items():
            if self.relative_paths:
                if not data.get("relative_path"):
                    raise ValueError(
                        "No relative path data: {0} {1}".format(
                            file, data))

                dst_file = data["relative_path"]
            else:
                dst_file = data["packaged_path"]

            self.log.debug("Replacing: {0} {1}".format(file, dst_file))
            raw_scene_data = re.sub(ur"%s" % file.decode("utf8"),
                                    ur"%s" % dst_file.decode("utf8"),
                                    raw_scene_data.decode("utf8"),
                                    flags=re.UNICODE).encode("utf8")

        # Write
        self.log.info("Writing packaged file: {0}".format(self.packaged_scene))
        base_utils.make_dirs(os.path.dirname(self.packaged_scene))
        with open(self.packaged_scene, "w") as handle:
            handle.write(raw_scene_data)
