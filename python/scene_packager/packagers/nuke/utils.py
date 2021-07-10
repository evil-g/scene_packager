# -*- coding: utf-8 -*-
# Standard
import os
import re

# Scene packager
from scene_packager import utils


# Global
NODE_PARSE_REGEX = r"(?P<node>(?P<start>(^(?P<class>.*)\ \{))" \
    "(?P<knobs>(?:.*\n)+)(?P<end>^(| )}$))"
INVALIDS = [r"^add_layer", r"^define_window_layout"]


def get_file_knob_settings(node_class):
    """
    Get setting for

    Returns:
        List of knob name strs
    """
    config = utils.packager_settings() or {}
    knobs = config.get("node_file_knobs", {}).get(node_class)
    if not knobs:
        return config.get("node_file_knobs", {}).get("default", [])


def get_node_class(data):
    """
    Return node class from parsed data

    Returns:
        Class str
    """
    match = re.search("^(?P<node_class>.*) {", data)
    if match:
        return match.group("node_class")


def get_node_knobs(data):
    """
    Get dict of node knobs from parsed data
    """
    match = re.search(NODE_PARSE_REGEX, data, re.MULTILINE)
    if not match:
        raise ValueError("Could not parse node data! {0}".format(data))

    # Parse knobs
    knobs = {}
    knob_data = match.group("knobs")
    # print("*" * 30)
    # print("knob data", knob_data)
    for line in knob_data.splitlines():
        # Skip blank line
        if not line:
            continue

        knob_match = re.search("(?P<name>[a-zA-Z0-9_.]+) (?P<value>.+)$",
                               line.strip(" "))
        if knob_match:
            # print("knob", knob_match.group("name"), knob_match.group("value"))
            knobs[knob_match.group("name")] = knob_match.group("value")
        # else:
            # print("no match", line)

    # Add class
    knobs["Class"] = match.group("class")

    return knobs


def get_node_dir(node_class, settings):
    """
    Get node dir

    Args:
        node_class (str): Node class
        settings (dict): Packager settings
    """
    for subdir, classes in settings.get("subdirs", {}).items():
        if node_class in classes:
            return subdir

    return utils.clean_path(settings["default_subdir"])


def _parse_nodes(lines):
    """
    Get nodes from input lines
    """
    unmatched = 0  # Count of unmatched brackets

    node_txt = ""
    for line in lines:
        # Brackets for active line
        l_bracket = len([c for c in line if "{" == c])
        r_bracket = len([c for c in line if "}" == c])

        # No node start -- skip
        if not node_txt and not l_bracket:
            continue

        unmatched += l_bracket
        unmatched -= r_bracket

        if unmatched < 0:
            raise ValueError("Unmatched bracket count went below 0")

        # Add line text
        node_txt += line

        # Found complete node
        if 0 == unmatched and node_txt:
            new_node = node_txt
            node_txt = ""

            # Check for invalid node
            if any([re.search(regex, new_node) for regex in INVALIDS]):
                continue

            yield new_node


def parse_nodes(scene):
    """
    Parse nodes from a scene

    Args:
        scene (str): Scene filepath

    Returns:
        List of ParsedNode objs
    """
    # Validate scene
    scene = utils.clean_path(scene)
    if not os.path.isfile(scene):
        raise ValueError("Scene does not exist: {0}".format(scene))
    elif ".nk" != os.path.splitext(scene)[-1]:
        raise ValueError("Scene is not a nukescript: {0}".format(scene))

    # Load data
    data = ""
    with open(scene, "r") as handle:
        data = handle.readlines()

    # Parse nodes from script
    parsed_nodes = []
    for node_txt in _parse_nodes(data):
        parsed_nodes.append(ParsedNode(node_txt))

    return parsed_nodes


def clean_root(root_data, pdir, start, end):
    """
    Clean root node and make sure project directory is set
    """
    # Sub new files
    raw_root_data = r"{0}".format(root_data)

    inserted = raw_root_data
    if "project_directory" not in inserted:
        match = re.search("Root \{\n", inserted)
        if match:
            before = inserted[0:match.end()]
            after = inserted[match.end():]
            inserted = ur"%s" % before.decode("utf8") + \
                ur"%s" % pdir.decode("utf8") + \
                ur"%s" % after.decode("utf8")

    # Root start
    if "first_frame" not in inserted:
        match = re.search("Root \{\n", inserted)
        if match:
            first_frame = " first_frame {0}\n".format(start)

            before = inserted[0:match.end()]
            after = inserted[match.end():]
            inserted = ur"%s" % before.decode("utf8") + \
                ur"%s" % first_frame.decode("utf8") + \
                ur"%s" % after.decode("utf8")
    # Root end
    if "last_frame" not in inserted:
        match = re.search("Root \{\n", inserted)
        if match:
            last_frame = " last_frame {0}\n".format(end)
            before = inserted[0:match.end()]
            after = inserted[match.end():]
            inserted = ur"%s" % before.decode("utf8") + \
                ur"%s" % last_frame.decode("utf8") + \
                ur"%s" % after.decode("utf8")

    return inserted.encode("utf8")


class ParsedNode(object):
    """
    Helper class for parsed node data from nuke script
    """
    def __init__(self, data):
        """
        Initialize node
        """
        self._data = data
        self.knobs = get_node_knobs(self._data)

    @property
    def data(self):
        return self._data

    def Class(self):
        """
        Get node class
        """
        try:
            return self.knobs["Class"]
        except KeyError:
            if self._data.startswith("Root"):
                return "Root"
            else:
                raise

    def knob_value(self, knob_name):
        """
        Get knob value

        Args:
            knob_name (str): Knob name

        Returns:
            Str value
        """
        if knob_name not in self.knobs:
            raise KeyError("No knob called: {0}".format(knob_name))

        return self.knobs[knob_name]

    def files(self):
        """
        Returns: List of file path str
        """
        files = []
        for knob in get_file_knob_settings(self.Class()):
            try:
                files.append(self.knob_value(knob))
            except KeyError:
                pass

        return files
