import json
import os
from loguru import logger
import re
import time
from enums.operation_type import OperationType
from enums.operation_variable import OperationVariable
from enums.storage_api import FileApi, SafPickerApi
from libs.utilities import Result, add_param


class FileHandler:
    def __init__(self, driver, ui, pname, attributes, operator, root):
        self.driver = driver
        self.ui = ui
        self.pname = pname
        self.attributes = attributes
        self.operator = operator
        self.root = root

    def get_base_cmd(self, action: OperationType):
        return f"am start -W -n {self.pname}/com.abc.storage_verifier.OperationActivity -a {action.value['flag']}"

    def _run_cmd(self, case, cmd, action):
        logger.debug(f"running cmd: {cmd}")
        case.reproduce.append(cmd)
        self.driver.back_to_home()
        self.driver.shell("logcat -c")
        try:
            self.driver.shell(cmd)
            # if saf involved, use UI controller to handle
            if f"\"{SafPickerApi().api_name}" in cmd:
                path = os.path.basename(re.search(r'--es path "(.*?)" ', cmd).group(1))
                if action in {OperationType.DELETE, OperationType.READ, OperationType.OVERWRITE, OperationType.RENAME}:
                    logger.info(f"asking UI to click file: {path}")
                    self.ui.click_file(path)
                elif action == OperationType.CREATE:
                    logger.info(f"asking UI to save file.")
                    self.ui.click_save()
                elif action == OperationType.MOVE:
                    logger.info(f"asking UI to click file: {path}")
                    if self.ui.click_file(path):
                        if self.ui.click_use_folder():
                            self.ui.click_allow()
                else:
                    input("Please handle the UI and press Enter to continue")
        except Exception as e:
            logger.info(e)
            logger.info("REPRODUCE: " + str(case.reproduce))
            logger.info("Server-side Exception")
            return {
                "action": f"EXCEPTION: Server-side Exception: {str(e)}"
            }, None
        time.sleep(1)
        wait_time = 2
        # if using saf, wait longer
        if f"\"{SafPickerApi().api_name}" in cmd and self.ui is None:
            # if MOVE, wait longer
            if action == OperationType.MOVE:
                logger.info("wait longer for SAF: 6s")
                wait_time = 6
            else:
                logger.info("wait longer for SAF: 3s")
                wait_time = 4
        result, edit_path = None, None
        for each in range(wait_time):
            time.sleep(1)
            log_collected = self.driver.shell(f"logcat -d -s {action.value['flag']}")
            result, edit_path = Result(
                log_collected,
                self.attributes,
            ).build_feature()
            if "Timeout" not in json.dumps(result):
                break

        if not result:
            raise Exception("Unknown Error")

        logger.debug(json.dumps(result, indent=4))

        # if using saf, close the saf
        self.ui.close_saf()

        return result, edit_path

    def run(self, case, action: OperationType, param: dict):
        cmd = self.get_base_cmd(action)
        cmd = add_param(cmd, param, self.operator)
        result, edit_path = self._run_cmd(case, cmd, action)
        if "EXCEPTION: No result, maybe Timeout?" not in json.dumps(result):
            return result, edit_path
        return {
            "action": action.value['flag'],
            "result": {
                "content" if action.value['flag'] == "READ_FILE" else "edit_path": "false"
            },
            "success": "FAIL",
            "target": param['path']
        }, edit_path

    def create_file(self, case, path, data, api=FileApi(), default_param=None, rename=False):
        if default_param is None:
            default_param = {}
        action = OperationType.CREATE
        cmd = self.get_base_cmd(action)

        if rename:
            available_path = self.root.get_available_name(path)
        else:
            available_path = path

        param = {"path": available_path, "data": data, "api": api}
        param.update(default_param)
        cmd = add_param(cmd, param, self.operator)
        return self._run_cmd(case, cmd, action)

    def rename_file(self, case, path, move_to, api=FileApi(), default_param=None):
        if default_param is None:
            default_param = {}
        action = OperationType.RENAME
        cmd = self.get_base_cmd(action)
        param = {"path": path, "move_to": move_to, "api": api}
        param.update(default_param)
        cmd = add_param(cmd, param, self.operator)
        return self._run_cmd(case, cmd, action)

    def move_file(self, case, path, move_to, api=FileApi(), default_param=None):
        if default_param is None:
            default_param = {}
        action = OperationType.MOVE
        cmd = self.get_base_cmd(action)
        param = {"path": path, "move_to": move_to, "api": api}
        param.update(default_param)
        cmd = add_param(cmd, param, self.operator)
        return self._run_cmd(case, cmd, action)

    def overwrite_file(self, case, path, data, api=FileApi(), default_param=None):
        if default_param is None:
            default_param = {}
        action = OperationType.OVERWRITE
        cmd = self.get_base_cmd(action)
        param = {"path": path, "data": data,
                 "api": api}
        param.update(default_param)
        cmd = add_param(cmd, param, self.operator)
        return self._run_cmd(case, cmd, action)

    def read_file(self, case, path, api=FileApi(), default_param=None):
        if default_param is None:
            default_param = {}
        action = OperationType.READ
        cmd = self.get_base_cmd(action)
        param = {"path": path, "api": api}
        param.update(default_param)
        cmd = add_param(cmd, param, self.operator)
        result, edit_path = self._run_cmd(case, cmd, action)

        if "EXCEPTION: No result, maybe Timeout?" not in json.dumps(result):
            return result, edit_path
        return {
            "action": "READ_FILE",
            "result": {
                "content": "false"
            },
            "success": "SUCCESS",
            "target": path
        }, edit_path

    def delete_file(self, case, path, api=FileApi(), default_param=None):
        if default_param is None:
            default_param = {}
        action = OperationType.DELETE
        cmd = self.get_base_cmd(action)
        param = {"path": path, "api": api}
        param.update(default_param)
        cmd = add_param(cmd, param, self.operator)
        return self._run_cmd(case, cmd, action)


def build_param(action: OperationType, alpha, beta, api=FileApi(), param_set: dict = None, default_param=None):
    if default_param is None:
        default_param = {}
    if param_set is None or action not in param_set:
        param = action.value["default_param"].copy()
    else:
        param = param_set[action]
    for k, v in param.items():
        if type(v) is OperationVariable and re.search("(alpha|beta)_(.+)", v.value):
            target, key = v.value.split("_")
            if target == "alpha":
                param[k] = default_param.get(k, getattr(alpha, key))
            else:
                param[k] = default_param.get(k, getattr(beta, key))
        else:
            param[k] = v
    param["api"] = api
    return param
