import enum


class AppPermission(enum.Enum):
    ACCESS_MEDIA_LOCATION = "android.permission.ACCESS_MEDIA_LOCATION"
    READ_EXTERNAL_STORAGE = "android.permission.READ_EXTERNAL_STORAGE"
    MANAGE_EXTERNAL_STORAGE = "android.permission.MANAGE_EXTERNAL_STORAGE"
    WRITE_EXTERNAL_STORAGE = "android.permission.WRITE_EXTERNAL_STORAGE"
    WRITE_MEDIA_STORAGE = "android.permission.WRITE_MEDIA_STORAGE"