# -*- coding: utf-8 -*-
"""
Nuke scene package config, default implementation.

To override, create your own config.py and
set $SCENE_PACKAGER_CONFIG to its location.
Any functions not overridden will use the default implementations below.
"""


def project_directory(packaged_scene, package_root, source_scene):
    """
    Project directory to use in scene settings

    Returns:
        str
    """
    return " project_directory \"[python nuke.script_directory()]\"\n"


def load_scene_data(packaged_scene, package_root, source_scene):
    """
    Returns dict of scene data

    Args:
        packaged_scene (str): Packaged scene path
        package_root (str): Package root path
        source_scene (str): Source scene path
    """
    import logging
    import os
    import scene_packager
    import nuke_packager_utils as utils

    LOG = logging.getLogger(__name__)

    dep_data = {}
    root = None
    start = None
    end = None

    for node in utils.parse_nodes(source_scene):
        # Found root
        if "Root" == node.Class():
            root = node

        # Process node files
        if (not utils.exclude_node_files(node)) and node.files():
            for file in node.files():
                # Get target file path
                dst = scene_packager.scene_packager_config.get_packaged_path(
                    file,
                    os.path.join(
                        package_root, utils.get_node_subdir(node)
                    )
                )
                rel = ""
                if scene_packager.scene_packager_config.use_relative_paths():
                    try:
                        rel = scene_packager.utils.get_relative_path(
                            packaged_scene, dst, package_root
                        )
                    except AssertionError:
                        LOG.error(
                            "Error getting relative path: {}".format(
                                node.knob_value("name")
                            )
                        )
                        LOG.error("packaged root: {}".format(package_root))
                        LOG.error("packaged scene: {}".format(packaged_scene))
                        LOG.error("dependency: {}".format(dst))
                        raise

                # Node already logged
                curr_start = None
                curr_end = None
                if file in dep_data:
                    # # Check
                    # LOG.info("packaged_path: {}".format(dst))
                    # print("packaged_path: {}".format(dst))
                    # print("dep_data path: {}".format(dep_data[file]["packaged_path"]))
                    # assert(dep_data[file]["packaged_path"] == dst)
                    # if rel:
                    #     LOG.info("relative_path: {}".format(rel))
                    #     print("relative_path: {}".format(rel))
                    #     print("dep_data path: {}".format(dep_data[file]["packaged_path"]))
                    #     assert(dep_data[file]["relative_path"] == rel)

                    curr_start = dep_data[file].get("start")
                    curr_end = dep_data[file].get("end")
                    # Start frame
                    try:
                        start = node.knob_value("first")
                    except KeyError:
                        pass
                    else:
                        if curr_start is None or int(start) < int(curr_start):
                            dep_data[file]["start"] = int(start)
                    # End frame
                    try:
                        end = node.knob_value("last")
                    except KeyError:
                        pass
                    else:
                        if curr_end is None or int(end) > int(curr_end):
                            dep_data[file]["end"] = int(end)
                # New node
                else:
                    data = {
                        "packaged_path": dst,
                        "relative_path": rel
                    }

                    # Start frame
                    try:
                        data["start"] = int(node.knob_value("first"))
                    except KeyError:
                        pass
                    else:
                        if start is None or data["start"] < start:
                            start = data["start"]
                    # End frame
                    try:
                        data["end"] = int(node.knob_value("last"))
                    except KeyError:
                        pass
                    else:
                        if end is None or data["end"] > end:
                            end = data["end"]

                    dep_data[file] = data

    # Raise error if no root found
    if root is None:
        raise ValueError("Error: no Root node found!")

    return root, dep_data


def write_packaged_scene(source_scene, dst_scene, dep_data, root,
                         project_dir, start, end, relative_paths=False):
    """
    Write packaged scene. Can be reimplemented per application
    """
    import logging
    import os
    import re
    import scene_packager
    import nuke_packager_utils as utils

    LOG = logging.getLogger(__name__)

    # Load backup scene text
    with open(source_scene, "r") as handle:
        scene_data = handle.read()

    raw_scene_data = r"{0}".format(scene_data)

    # Clean root
    new_root = utils.clean_root(
        root.data,
        project_dir,
        start,
        end
    )
    if new_root:
        match = re.search(r"Root \{\n.*(| +)\}$", raw_scene_data)
        if match:
            raw_scene_data = re.sub(
                re.escape(root.data),
                new_root.decode("utf8"),
                raw_scene_data,
                flags=re.UNICODE
            )
        # Add new root
        else:
            raw_scene_data += "\n" + new_root.decode("utf8")

    # Sub new files
    for file, data in dep_data.items():
        if relative_paths:
            if not data.get("relative_path"):
                raise ValueError(
                    "No relative path data: {} {}".format(
                        file, data))

            dst_file = data["relative_path"]
        else:
            dst_file = data["packaged_path"]

        LOG.debug("Replacing: {} {}".format(file, dst_file))
        raw_scene_data = re.sub(file,
                                dst_file,
                                raw_scene_data,
                                flags=re.UNICODE)

    # Write
    LOG.info("Writing packaged file: {}".format(dst_scene))
    scene_packager.utils.make_dirs(os.path.dirname(dst_scene))
    with open(dst_scene, "w") as handle:
        if isinstance(raw_scene_data, bytes):
            handle.write(raw_scene_data.decode("utf8"))
        else:
            handle.write(raw_scene_data)
