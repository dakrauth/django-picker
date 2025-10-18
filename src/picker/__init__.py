__version__ = "3.0.1"
VERSION = tuple(int(i) for i in __version__.split("."))

default_app_config = "picker.apps.PickerConfig"


def get_version():
    return __version__
