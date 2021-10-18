# Scene Packager
## Overview
The scene packager consolidates a scene and its file dependencies under a single directory.
It copies file dependencies to a new package parent directory, and updates the packaged scene file to reference the new dependency paths.
## Setup
### Installation
TODO
### Environment
SCENE_PACKAGER_CONFIG_PATH
## Usage
### Mode: run
Run mode will package a scene file and its file dependencies under a single directory.
Uses config implementations found in $SCENE_PACKAGER_CONFIG_PATH.

```
$ scene-packager run --help
usage: scene-packager run [-h] -s INPUT_SCENE [--search-path SEARCH_PATH]
                          [-r PACKAGE_ROOT]
                          [--extra-files EXTRA_FILES [EXTRA_FILES ...]]
                          [--dryrun] [--nocopy] [-o] [--ui] [-v] [--version]

optional arguments:
  -h, --help            show this help message and exit
  -s INPUT_SCENE, --scene INPUT_SCENE
                        Either 1. Filepath of scene to package, or 2.
                        Directory to search for scenes to package. If a
                        directory is provided, finds and lists scenes that can
                        be packaged. If -s is used with --ui mode, scenes are
                        loaded into the ui when it is launched.
  --search-path SEARCH_PATH
                        Overrides env search path
                        ($SCENE_PACKAGER_CONFIG_PATH)
  -r PACKAGE_ROOT, --package-root PACKAGE_ROOT
                        Target root directory for this package. Overrides any
                        implementation in scene_packager_config.package_root()
  --extra-files EXTRA_FILES [EXTRA_FILES ...]
                        List of extra filepaths to copy to the final package.
                        Useful for adding references files that are not used
                        by the scene.
  --dryrun              Dryrun mode. Prints info and source/dest file
                        dependencies.
  --nocopy              Runs packager without packaging the file dependencies.
                        Writes packaged scene with updated paths and metadata.
                        Prints a log of source/dest paths for file
                        dependencies, but does not actually copy them.
  -o, --overwrite       If target package destination is already a package,
                        overwrite it.
  --ui                  Launch Scene Packager ui.
  -v, --verbose         Increase verbosity of Scene Packager. Use -v for basic
                        info, -vv for debug messages.
  --version             Print version and exit
```
### Mode: inspect
Inspect mode lets you:
1. Print information about packages under an input directory.
2. Print information about the config and any active overrides.

```
$ scene-packager inspect --help
usage: scene-packager inspect [-h] [--config] [--search-path SEARCH_PATH]
                              [--dir INSPECT_DIR] [-r] [-s] [-v]

optional arguments:
  -h, --help            show this help message and exit
  --config              Print info about config overrides.
  --search-path SEARCH_PATH
                        Overrides env search path
                        ($SCENE_PACKAGER_CONFIG_PATH)
  --dir INSPECT_DIR     Search this directory for existing scene packages.
  -r, --open-root-dir   Open root directory of each package.
  -s, --open-scene-dir  Open parent directory of each packaged scene.
  -v, --verbose         Print info about found packages. Use -v to print
                        scene/user/date, -vv to print all package metadata.
```
### Command examples:
Package a nuke script (overwrite existing)
```
$ scene-packager run -s /projects/test/shots/001/my_test_script_v001.nk --overwrite -v
```

Only writes out packaged scene with updated paths and metadata (skips copying file dependencies)
```
$ scene-packager run -s /projects/test/shots/001/my_test_script_v001.nk --overwrite --no-copy
```

Dryrun with max log output
```
$ scene-packager run -s /projects/test/shots/001/my_test_script_v001.nk --overwrite --dryrun -vv
```

Print config override information
```
$ scene-packager inspect --config
```

Print package information under directory
```
$ scene-packager inspect --dir /projects/test/delivery/scene_packager
```

Print config + package information and open the root directory of each package
```
$ scene-packager inspect --dir /projects/test/delivery/scene_packager
--open-root-dir --config
```

## Config
TODO


### Required Implementation
TODO Required DCC implementation, etc.
