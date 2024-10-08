import hashlib
import random
from collections import OrderedDict

import numpy as np
import pandas as pd
from loguru import logger
import time
from enums.app_permission import AppPermission
from enums.app_role import AppRole
from enums.operation_type import OperationType
from enums.storage_api import StorageApiBase
from enums.target_enum import Storage, Collection
from libs.path_template import PathTemplate
from libs.permission_setting import PermissionSetting
from verification.security_rule import SecurityRule


class TestCase:
    def __init__(self,
                 rule: SecurityRule,
                 final_action: OperationType,
                 api: StorageApiBase,
                 payload: list,
                 permission_setting: PermissionSetting,
                 path_template: PathTemplate,
                 ext: str = None,
                 experiment_seed: int = 1,
                 weight=0):
        self.rule = rule
        self.api = api
        self.final_action = final_action
        self.payload = payload
        self.reproduce = []
        self.perm_setting = permission_setting
        self.path_template = path_template
        self.ext = ext
        self.experiment_seed = experiment_seed
        self.weight = weight

    @classmethod
    def get_payload_printable(cls, payload):
        payload = [
            action[0].name + "," + action[1].get_printable_name() if not "SETUP" in str(
                action) else f"SETUP,{action[1].get_printable_name()}"
            for action in payload
        ]
        return payload

    def get_feature(self, prerequisite=False):
        # convert payload to a payload prefix
        feature = []
        for i, (action, api) in enumerate(self.payload):
            if action == "SETUP":
                # if self.final_action == OperationType.CREATE:
                #     continue
                # else:
                feature.append(("CREATE_FILE", api))
                continue
            else:
                feature.append((action, api))
        if not prerequisite:
            feature.append((self.final_action, self.api))
        return f"{self.path_template.target_path.template}({self.ext})_{str(feature)}"

    def get_printable(self):
        return f"[{self.rule.rule_id}] {self.final_action.name}({self.api.api_name.upper()})->{self.path_template.target_path.template}({self.ext})_{self.get_payload_printable(self.payload)}_{self.perm_setting.to_array()}_{self.experiment_seed}"

    def get_attributes(self):
        results = set()
        results.add(f"RULE:{self.rule.rule_id}")
        results.add(f"FINAL:{self.final_action.name}")
        results.add(f"API:{self.api.api_name.upper()}")
        perm_setting = self.perm_setting.to_printable()
        results.add(f"PERM:{str(perm_setting)}")
        results.add(f"PATH:{self.path_template.target_path.template}")
        results.add(f"EXT:{self.ext}")
        payloads = self.get_payload_printable(self.payload)
        results.add(f"PAYLOADS:{str(payloads)}")
        return results

    def get_X(self, all_attr, additional=None):
        X = {}
        for attr in all_attr:
            X[attr] = [0]
        for attr in self.get_attributes():
            X[attr][0] += 1
        if additional:
            X.update(additional)
        return pd.DataFrame(X)

    def get_case_hash(self, length=11) -> str:
        return hashlib.sha256(self.get_printable().encode()).hexdigest()[:11]

    def set_permissions(self, pname, system_version, ext, perm_setting, driver):
        if perm_setting.is_granted(AppPermission.MANAGE_EXTERNAL_STORAGE):
            cmd = f"appops set --uid {pname} MANAGE_EXTERNAL_STORAGE allow"
        else:
            cmd = f"appops set --uid {pname} MANAGE_EXTERNAL_STORAGE deny"
        self.reproduce.append(cmd)
        driver.shell(cmd)

        if int(system_version[:2]) < 13:
            if perm_setting.is_granted(AppPermission.READ_EXTERNAL_STORAGE):
                cmd = f"pm grant {pname} {AppPermission.READ_EXTERNAL_STORAGE.value}"
            else:
                cmd = f"pm revoke {pname} {AppPermission.READ_EXTERNAL_STORAGE.value}"
            self.reproduce.append(cmd)
            driver.shell(cmd)
        else:
            # deal with Android 13+, read media permission is split into 3
            for this_ext, perm_name in [(".jpg", "READ_MEDIA_IMAGES"),
                                        (".mp4", "READ_MEDIA_VIDEO"),
                                        (".mp3", "READ_MEDIA_AUDIO")]:
                if ext == this_ext and perm_setting.is_granted(AppPermission.READ_EXTERNAL_STORAGE):
                    cmd = f"pm grant {pname} android.permission.{perm_name}"
                else:
                    cmd = f"pm revoke {pname} android.permission.{perm_name}"
                self.reproduce.append(cmd)
                driver.shell(cmd)

        if perm_setting.is_granted(AppPermission.ACCESS_MEDIA_LOCATION):
            cmd = f"pm grant {pname} {AppPermission.ACCESS_MEDIA_LOCATION.value}"
        else:
            cmd = f"pm revoke {pname} {AppPermission.ACCESS_MEDIA_LOCATION.value}"
        self.reproduce.append(cmd)
        driver.shell(cmd)

        if perm_setting.is_granted(AppPermission.WRITE_MEDIA_STORAGE):
            cmd = f"pm grant {pname} {AppPermission.WRITE_MEDIA_STORAGE.value}"
        else:
            cmd = f"pm revoke {pname} {AppPermission.WRITE_MEDIA_STORAGE.value}"
        self.reproduce.append(cmd)
        driver.shell(cmd)

        if perm_setting.is_granted(AppPermission.WRITE_EXTERNAL_STORAGE):
            cmd = f"pm grant {pname} {AppPermission.WRITE_EXTERNAL_STORAGE.value}"
        else:
            cmd = f"pm revoke {pname} {AppPermission.WRITE_EXTERNAL_STORAGE.value}"
        self.reproduce.append(cmd)
        driver.shell(cmd)

        time.sleep(0.3)

    def reset_shared_storage(self, driver):
        for storage_path in Storage.EXTERNAL_STORAGE.value:
            for collection in Collection:
                if collection == Collection.APP_FOLDER:
                    continue
                for collection_path in collection.value:
                    path = storage_path + collection_path
                    shell = f"rm -rf {path}/*"
                    result = driver.shell(shell).strip()
                    logger.info(f"Cleaning shared storage...{path}: {'Success' if not result else result}")

    @classmethod
    def reset_apps_storage(cls, driver):
        for app_role in AppRole:
            pname = app_role.value
            cmd = f"pm clear {pname}"
            feedback = driver.shell(cmd)
            logger.info(f"Cleaning app storage...{pname}: {feedback.strip()}")

    def set_case_seed(self, additional_input=""):
        case_str = f"{self.experiment_seed}{self.get_printable()}{additional_input}"
        # set seeds to ensure each case+rule is reproducible
        hash_object = hashlib.sha256(case_str.encode())
        hex_hash = hash_object.hexdigest()
        case_int = int(hex_hash, 16) % (10 ** 8)
        # logger.info(f"Setting seed: {case_int} <- {case_str}")
        random.seed(case_int)
        np.random.seed(case_int)

    def check(self, oracle, i, total, system_version, stop_when_fail):
        self.reset_shared_storage(oracle.device_handler)
        self.reset_apps_storage(oracle.device_handler)

        logger.info(
            f"[{i}/{total}-{self.get_case_hash()}] " +
            f"Verifying: {self.get_printable()} ...")
        result = oracle.perform_test(self.rule, self, self.payload, stop_when_fail, self.set_permissions,
                                     self.perm_setting, system_version, self.ext, self.path_template)
        logger.info(
            f"[{i + 1}/{total}-{self.get_case_hash()}] " +
            f"Verified: {self.get_printable()} !")
        # clear reproduce after test finished, ready for next test
        self.reproduce = []
        return result
