# -*- coding: utf-8 -*-
# Standard
import sys

# Third party
from Qt import QtWidgets


def main():
    """
    Standalone QApplication app launch
    """
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    win = ui.show(parent=None)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
