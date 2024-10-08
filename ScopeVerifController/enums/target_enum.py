import enum


class Storage(enum.Enum):
    INTERNAL_STORAGE = ["/data/data"]
    EXTERNAL_STORAGE = ["/sdcard"]


class Collection(enum.Enum):
    SHARED_DOWNLOAD = ["/Download"]
    SHARED_IMAGE = ["/Pictures"]
    SHARED_VIDEO = ["/Movies"]
    SHARED_AUDIO = ["/Music"]
    APP_FOLDER = ["/Android/data"]


class Scope(enum.Enum):
    MY_APP = [1]
    OTHER_APPS = [2]


class All:
    name = "ALL"

    def __init__(self, arr):
        value = []
        for v in arr:
            value += v.value
        self.value = value
