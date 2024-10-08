import string
from typing import List
from enums.attribute import Attribute
from libs.path_template import PathTemplate
from libs.utilities import random_data


class Operator:
    def __init__(self, pname: str, path_template: PathTemplate, extension: str, attributes: List[Attribute], seeder):
        app_path = path_template.render(pname)
        self.data = random_data(extension, attributes, seeder=lambda: seeder(f"{pname}-data"))
        self.data2 = random_data(extension, attributes, seeder=lambda: seeder(f"{pname}-data2"))
        self.data3 = random_data(extension, attributes, seeder=lambda: seeder(f"{pname}-data3"))
        self.data4 = random_data(extension, attributes, seeder=lambda: seeder(f"{pname}-data4"))
        self.dirpath = "/sdcard/Android/data/" + pname + "/"
        self.dirpath2 = "/sdcard/Android/data/" + pname + "/files/"
        self.path = app_path + random_data(seeder=lambda: seeder(f"{pname}-path")) + extension
        self.path2 = app_path + random_data(seeder=lambda: seeder(f"{pname}-path2")) + extension
        self.path3 = app_path + random_data(seeder=lambda: seeder(f"{pname}-path3")) + extension
        self.path4 = app_path + random_data(seeder=lambda: seeder(f"{pname}-path4")) + extension
        self.path5 = app_path + random_data(seeder=lambda: seeder(f"{pname}-path5")) + extension
        self.path6 = app_path + random_data(seeder=lambda: seeder(f"{pname}-path6")) + extension
        # weird hack here, because path prefix could be "Pictures/com.abc.storage_verifier_a_"
        self.fname = self.path.split("/")[-1]
        self.fname2 = self.path2.split("/")[-1]
        self.fname3 = self.path3.split("/")[-1]
        self.fname4 = self.path4.split("/")[-1]
        self.fname5 = self.path5.split("/")[-1]
        self.fname6 = self.path6.split("/")[-1]
        self.pname = pname
        self.attributes = attributes
