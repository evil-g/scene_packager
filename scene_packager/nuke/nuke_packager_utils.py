# -*- coding: utf-8 -*-
# Standard
import io
import os
import re

# Scene packager
from scene_packager import utils


# Global
NODE_PARSE_REGEX = r"(?P<node>(?P<start>(^(?P<class>.*)\ \{))" \
    "(?P<knobs>(?:.*\n)+)(?P<end>^(| +)}$))"
INVALIDS = [r"^add_layer", r"^define_window_layout"]


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


def get_node_subdir(node):
    """
    Get package subdir that a node should be copied to

    Returns:
        dir str
    """
    if node.Class() in ["DeepWrite", "Write"]:
        return "images/outputs"

    return "images/inputs"


def get_node_file_knobs(node_class):
    """
    Get list of knobs whose files should be copied

    Returns:
        list of knob name str
    """
    if node_class in ["Vectorfield"]:
        return ["vfield_file"]

    return ["file"]


def exclude_node_files(node):
    """
    Determine whether a node's file, etc knobs should be ignored

    Args:
        node (nuke.Node): Nuke node

    Returns:
        bool
    """
    if node.Class() in ["DeepWrite", "Write"]:
        return True

    return False


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
    with io.open(scene, "r", encoding="utf8") as handle:
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
    inserted = root_data

    # Check project directory
    if "project_directory" in inserted:
        parsed_root = ParsedNode(root_data)
        # If project directory setting is empty, remove it
        if not parsed_root.knob_value("project_directory"):
            inserted = re.sub("(^| +)project_directory.*\n", "", inserted)

    # Add project directory
    if "project_directory" not in inserted:
        pdir_match = re.search("Root \{\n", inserted)
        if pdir_match:
            before = inserted[0:pdir_match.end()]
            after = inserted[pdir_match.end():]
            try:
                inserted = r"%s" % before + \
                    r"%s" % pdir + \
                    r"%s" % after
            except AttributeError:
                inserted = r"%s" % before + r"%s" % pdir + r"%s" % after

    # Root start
    if "first_frame" not in inserted:
        first_match = re.search("Root \{\n", inserted)
        if first_match:
            first_frame = " first_frame {0}\n".format(start)

            before = inserted[0:first_match.end()]
            after = inserted[first_match.end():]
            inserted = r"%s" % before + \
                r"%s" % first_frame + \
                r"%s" % after

    # Root end
    if "last_frame" not in inserted:
        last_match = re.search("Root \{\n", inserted)
        if last_match:
            last_frame = " last_frame {0}\n".format(end)
            before = inserted[0:last_match.end()]
            after = inserted[last_match.end():]
            inserted = r"%s" % before + \
                r"%s" % last_frame + \
                r"%s" % after

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

        value = self.knobs[knob_name]
        # Clean empty str settings
        if value in ["''", '""']:
            return ""
        else:
            return value

    def files(self):
        """
        Returns: List of file path str
        """
        files = []
        for knob in get_node_file_knobs(self.Class()):
            try:
                files.append(self.knob_value(knob))
            except KeyError:
                pass

        return files
