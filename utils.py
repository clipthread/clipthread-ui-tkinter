import os


def get_working_dir():
    return os.path.join(os.path.expanduser("~"), ".clipthread")


def get_configuration_file():
    return os.path.join(get_working_dir(), "config.store")