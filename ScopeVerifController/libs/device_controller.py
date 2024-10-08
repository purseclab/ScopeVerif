from loguru import logger
from adbutils import adb
import os


class DeviceController:
    def __init__(self):
        self.device = None
        # get device id from env
        device_id = os.environ.get('ANDROID_DEVICE', None)
        # get device version from env
        test_version = os.environ.get('ANDROID_SYSTEM', None)
        if test_version is None and device_id is None:
            self.device = adb.device()
        elif device_id is not None:
            self.device = adb.device(device_id)
        else:
            all_devices = adb.device_list()
            for d in all_devices:
                cmd = "getprop ro.build.version.release"
                device_version = d.shell(cmd)
                if device_version == test_version.strip():
                    logger.info(f"Found device ({d.serial}) with version {device_version}")
                    self.device = d
                    break
            if self.device is None:
                raise Exception("No device with the specified version")
        self.system_version = self.__get_system_version()
        self.api_level = self.__get_api_level()
        self.is_google_version = self.check_google_version()
        self.is_emulator = self.__is_emulator()
        if self.is_emulator:
            logger.info("Emulator detected, root the device")
            self.device.root()

    def install_app(self, path):
        logger.info("install..." + path)
        res = self.device.install(path)
        logger.info(res)

    def check_google_version(self):
        fingerprint = self.shell("getprop ro.build.fingerprint")
        is_google = "google" in fingerprint
        logger.info(f"Device fingerprint: {fingerprint}, isGoogle: {is_google}")
        return is_google

    def __is_emulator(self):
        cmd = "su -c 'ls'"
        res = self.device.shell(cmd)

        if "su: invalid uid/gid" in res:
            return True
        return False

    def __get_api_level(self):
        cmd = "getprop ro.build.version.sdk"
        res = self.shell(cmd)
        return int(res.strip())

    def __get_system_version(self):
        cmd = "getprop ro.build.version.release"
        version = self.shell(cmd)
        cmd = "getprop ro.vendor_dlkm.build.fingerprint"
        build = self.shell(cmd).split("/")[3].replace(".", '-')
        return f"{version}-{build}"

    def remove_app(self, pname):
        logger.info("uninstall..." + pname)
        res = self.device.uninstall(pname)
        logger.info(res)

    def back_to_home(self):
        self.device.shell("input keyevent KEYCODE_HOME")

    def shell(self, cmd):
        return self.device.shell(cmd)

    def keep_screen_on(self):
        self.device.shell("svc power stayon true")

    def refresh_accessibility(self):
        disable_cmd = f"am force-stop com.example.storage_accessibility_service"
        enable_cmd = f"settings put secure enabled_accessibility_services com.example.storage_accessibility_service/com.example.storage_accessibility_service.StorageAccessibilityService"
        self.device.shell(disable_cmd)
        self.device.shell(enable_cmd)
