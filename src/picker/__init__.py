__version__ = "2.5.0"
VERSION = tuple(int(i) for i in __version__.split("."))

default_app_config = "picker.apps.PickerConfig"


def get_version():
    return __version__
