# -*- coding: utf-8 -*-
"""
Default implementation of Nuke scene packager config.

To override, create your own config.py and
set $SCENE_PACKAGER_CONFIG to its location.
Any functions not overridden will use the default implementations below.
"""


def project_directory(packaged_scene, package_root, source_scene):
    """
    Project directory to use in scene settings

    Returns:
        Project directory str
    """
    return " project_directory \"[python nuke.script_directory()]\"\n"


def get_scene_frange(scene):
    """
    Get start/end for scene

    Raises:
        RuntimeError if Root node cannot be found

    Returns:
        (start (int), end (int)) tuple
    """
    import scene_packager
    import nuke_packager_utils as utils

    log = scene_packager.utils.get_logger(__name__)

    start = None
    end = None

    # Check root nodes
    nodes = utils.parse_nodes(scene)
    roots = [n for n in nodes if "Root" == n.Class()]
    # (There shouldn't really be more than 1 Root...)
    if len(roots) > 1:
        log.warning(
            "Multiple Roots. Using first available frange settings."
        )
    # Get start/end from first available root
    for root in roots:
        try:
            start = int(root.knob_value("first_frame"))
            end = int(root.knob_value("last_frame"))
        except KeyError:
            log.debug(
                "Failed to get Root first_frame/last_frame", exc_info=True
            )
            log.debug(root.data)
        else:
            log.info("Using Root first_frame/last_frame")
            return start, end

    log.warning(
        "Failed to get Root first_frame/last_frame. "
        "Checking node frame ranges..."
    )

    # No root start/end. Let's try to figure it out from the node settings.
    # Use lowest start frame and highest end frame overall.
    for node in [n for n in nodes if n not in roots]:
        # Start
        try:
            node_start = int(node.knob_value("first"))
        except Exception:
            log.debug("No {}.first".format(node.knob_value("name")))
        else:
            if start is None or node_start < start:
                start = node_start

        # End
        try:
            node_end = int(node.knob_value("last"))
        except Exception:
            log.debug("No {}.last".format(node.knob_value("name")))
        else:
            if end is None or node_end > end:
                end = node_end

    # Found start/end
    if start is not None and end is not None:
        log.info("Start: {} | End: {}".format(start, end))
        return start, end

    raise RuntimeError("Could not figure out scene start/end. [Check whether "
                       "Root node has first_frame/last_frame set]")


def load_scene_data(packaged_scene, package_root, source_scene):
    """
    Returns dict of scene data

    Args:
        packaged_scene (str): Packaged scene path
        package_root (str): Package root path
        source_scene (str): Source scene path

    Returns:
        root_data (str), dep_data (dict), start (int), end (int)
    """
    import os
    import scene_packager
    import nuke_packager_utils as utils

    log = scene_packager.utils.get_logger(__name__)

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
                    os.path.join(package_root,
                                 utils.get_node_subdir(node),
                                 node.knob_value("name"))
                )
                rel = ""
                if scene_packager.scene_packager_config.use_relative_paths():
                    try:
                        rel = scene_packager.utils.get_relative_path(
                            packaged_scene, dst, package_root
                        )
                    except AssertionError:
                        log.error(
                            "Error getting relative path: {}".format(
                                node.knob_value("name")
                            )
                        )
                        log.error("packaged root: {}".format(package_root))
                        log.error("packaged scene: {}".format(packaged_scene))
                        log.error("dependency: {}".format(dst))
                        raise

                # Node already logged
                curr_start = None
                curr_end = None
                if file in dep_data:
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

    return root, dep_data, start, end


def write_packaged_scene(source_scene, dst_scene, dep_data, root,
                         project_dir, start, end, relative_paths=False):
    """
    Write packaged scene. Can be reimplemented per application
    """
    import os
    import re
    import scene_packager
    import nuke_packager_utils as utils

    log = scene_packager.utils.get_logger(__name__)
    log.info("relative paths={}".format(relative_paths))

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
        raw_scene_data = re.sub(
            re.escape(root.data),
            new_root.decode("utf8"),
            raw_scene_data,
            flags=re.UNICODE
        )

    if "project_directory" not in raw_scene_data:
        log.error("project_directory not found in output scene data.")

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

        log.debug("Replacing: {} {}".format(file, dst_file))
        raw_scene_data = re.sub(file,
                                dst_file,
                                raw_scene_data,
                                flags=re.UNICODE)

    # Write
    scene_packager.utils.make_dirs(os.path.dirname(dst_scene))
    with open(dst_scene, "w") as handle:
        if isinstance(raw_scene_data, bytes):
            handle.write(raw_scene_data.decode("utf8"))
        else:
            handle.write(raw_scene_data)
