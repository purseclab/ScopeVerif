import enum


class Attribute(enum.Enum):
    FILE_PATH = "edit_path"
    FILE_CONTENT = "content"
    FILE_SIZE = "size"
    MODIFIED_TIME = "modified_time"
    MEDIA_LOCATION = "media_location"
    TARGET = "target"
    SUCCESS = "success"
    EXCEPTION = "exception"
    NEW_PATH = "edit_path"
