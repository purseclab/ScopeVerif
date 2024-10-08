from enums.app_role import ApkRole


def my_apk_path_getter(app_role: ApkRole):
    return rf"D:\ScopeVerifWorkers\{app_role.value.split('.')[-1]}\app\build\intermediates\apk\debug\app-debug.apk"