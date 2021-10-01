# -*- coding: utf-8 -*-
# Standard
import sys

# Third party
from Qt import QtWidgets

# Pipeline
from core_pipeline import setup
from core_pipeline_ui import utils


def main():
    """
    Standalone QApplication app launch
    """
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


    win = ui.show(parent=None)
    utils.widgets.set_styleseet(win)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
