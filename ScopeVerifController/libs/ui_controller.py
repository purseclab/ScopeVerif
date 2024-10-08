import re
import time
from typing import Optional
from loguru import logger
from libs.device_controller import DeviceController
from lxml import etree

from libs.root_handler import RootHandler


class Element:
    def __init__(self, device, class_name=None, text=None,
                 clickable=None, package=None, max_wait=3,
                 default_coordinate=None,
                 case_sensitive=True):
        self.device_controller = device
        self.root_controller = RootHandler(device)
        self.class_name = class_name
        self.text = text
        self.clickable = clickable
        self.package = package
        self.max_wait = max_wait
        self.case_sensitive = case_sensitive
        self.refreshed = False
        self.node = None
        self.default_coordinate = default_coordinate

    def __get_screen_xml(self):
        screen_xml = self.device_controller.shell("rm -f /data/local/tmp/uidump.xml &> /dev/null; " + \
                                                      "uiautomator dump /data/local/tmp/uidump.xml &> /dev/null; " + \
                                                      "cat /data/local/tmp/uidump.xml")
        logger.debug(f"Screen: {screen_xml.encode()}")
        parsed_xml = etree.fromstring(screen_xml.encode())
        return parsed_xml

    def __find_node(self,):
        attempt = 0
        while attempt < self.max_wait:
            screen_xml = self.__get_screen_xml()

            # find the element
            condition = []
            if self.class_name:
                condition.append(f"@class='{self.class_name}'")
            if self.text:
                if not self.case_sensitive:
                    condition.append(f're:test(@text, "^{self.text}$", "i")')
                else:
                    condition.append(f"@text='{self.text}'")
            if self.clickable:
                condition.append(f"@clickable='{str(self.clickable).lower()}'")
            if self.package:
                # condition.append(f"@package='{self.package}'")
                condition.append(f're:test(@package, "com\.(android|google\.android)\.documentsui", "i")')
            xpath_query = f"//node[{' and '.join(condition)}]"
            logger.info(f"Finding element: {xpath_query}")
            elements = screen_xml.xpath(xpath_query, namespaces={"re": "http://exslt.org/regular-expressions"})
            logger.info(f"Device controller: found {len(elements)} elements")
            for ele in elements:
                return ele
            if self.max_wait == 1:
                break
            logger.info(f"Device controller: element not found, retrying...{attempt + 1}")
            attempt += 1
        return None

    def is_present(self):
        if self.node is None:
            self.refresh_node()
            if self.node is None:
                return None
        return True

    def refresh_node(self):
        if not self.refreshed:
            self.node = self.__find_node()
            self.refreshed = True

    def __get_coordinates(self, node=None):
        if node is None:
            node = self.node
            if not self.is_present():
                return None

        coordinate = re.search("\[(\d+),(\d+)]\[(\d+),(\d+)]", node.get("bounds"))
        logger.info(f"Device controller: found element at ({coordinate.group(1)}, {coordinate.group(2)})")
        x1 = int(coordinate.group(1))
        y1 = int(coordinate.group(2))
        x2 = int(coordinate.group(3))
        y2 = int(coordinate.group(4))
        x, y = (x1 + x2) / 2, (y1 + y2) / 2
        if x + y == 0:
            logger.warning("Device controller: invalid coordinates")
            if self.default_coordinate is not None:
                logger.warning(f"Device controller: using default coordinates: {self.default_coordinate}")
                return self.default_coordinate
            logger.error("Device controller: invalid coordinates, default coordinates are not set")
            exit()
        return x, y

    def click(self):
        if not self.is_present():
            logger.error("Device controller: element is not clickable")
            return
        coordinate = self.__get_coordinates()
        assert coordinate is not None
        x, y = coordinate
        self.click_at(x, y)

    def click_at(self, x, y):
        self.device_controller.shell(f"input tap {x} {y}")
        logger.info(f"Device controller: click at ({x}, {y})")


class UIController:
    def __init__(self, device: DeviceController):
        self.device_controller = device
        self.system_version = self.device_controller.system_version.split("-")[0]
        self.height, self.width = self.get_screen_size()
        if self.device_controller.is_google_version:
            self.android_package_name = "com.google.android"
        else:
            self.android_package_name = "com.android"

    def get_screen_size(self):
        size = self.device_controller.shell("wm size")
        found = re.search("Physical size: (\d+)x(\d+)", size)
        if found:
            return int(found.group(2)), int(found.group(1))
        return 0, 0

    def find_element(self, class_name=None, text=None, clickable=None,
                     package=None, max_wait=3, default_coordinate=None,
                     case_sensitive=True) -> Optional[Element]:
        return Element(self.device_controller,
                       class_name=class_name,
                       text=text,
                       clickable=clickable,
                       package=package,
                       max_wait=max_wait,
                       default_coordinate=default_coordinate,
                       case_sensitive=case_sensitive)

    def click_save(self, max_wait=1):
        save_button = self.find_element(package=f"{self.android_package_name}.documentsui",
                                        class_name="android.widget.Button",
                                        text='SAVE',
                                        max_wait=max_wait,
                                        default_coordinate=(self.width // 8 * 7, self.height // 16 * 15),
                                        case_sensitive=False)
        if save_button.is_present():
            save_button.click()
            logger.info(f"UI controller: clicked Button: SAVE")
            return True
        return False

    def click_file(self, filename, max_wait=1):
        file_element = self.find_element(class_name="android.widget.TextView",
                                         text=filename,
                                         max_wait=max_wait)
        if file_element.is_present():
            file_element.click()
            logger.info(f"UI controller: clicked file: {filename}")
            return True
        return False

    def click_allow(self, max_wait=1):
        print(self.height, self.width)
        allow_button = self.find_element(class_name="android.widget.Button",
                                         text='Allow',
                                         max_wait=max_wait,
                                         default_coordinate=(self.width // 12 * 9, self.height // 12 * 7),
                                         case_sensitive=False)
        if allow_button.is_present():
            allow_button.click()
            logger.info(f"UI controller: clicked Button: Allow")
            return True
        return False

    def click_use_folder(self, max_wait=1):
        use_folder_button = self.find_element(class_name="android.widget.Button",
                                              text='Use this folder',
                                              max_wait=max_wait,
                                              default_coordinate=(self.width // 2, self.height // 16 * 15),
                                              case_sensitive=False)
        if use_folder_button.is_present():
            use_folder_button.click()
            logger.info(f"UI controller: clicked Button: Use this folder")
            return True
        return False

    def close_saf(self):
        time.sleep(0.5)
        self.device_controller.shell(f"am force-stop {self.android_package_name}.documentsui")


if __name__ == "__main__":
    device = DeviceController()
    ui = UIController(device)
    ui.click_allow()
    # ui.click_file("mznPQ1coCJ.pdf")
