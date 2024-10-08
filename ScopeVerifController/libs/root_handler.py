import base64
import os
import re
from loguru import logger
from enums.attribute import Attribute
from enums.operation_type import OperationType
from libs.utilities import get_pic_location

class RootHandler:
    def __init__(self, controller):
        self.controller = controller
        self.root_enabled = False

    def has_root(self):
        if self.controller.is_emulator:
            self.root_enabled = True
            return True

        cmd = f"su -c 'ls'"
        res = self.controller.shell(cmd)

        if "su: inaccessible or not found" in res:
            self.root_enabled = False
            return False
        self.root_enabled = True
        return True

    def build_feature(self, target, result, rule):
        results = {}
        attributes_filter = {attr.value for attr in rule.attributes}
        edit_path = None
        for k in result:
            if edit_path == Attribute.FILE_PATH.value:
                edit_path = result[k]
            if k in attributes_filter:
                if type(result[k]) is str and re.search("^(cat: |stat: |rm: |mv: |/system/bin/sh: )", result[k]):
                    if Attribute.EXCEPTION.value not in attributes_filter:
                        continue
                    results[k] = "EXCEPTION: " + result[k]
                else:
                    results[k] = str(result[k]).replace("\r\n", "\n")
                    # reading content might have an additional new line at the end
                    if k == "content" and results[k].endswith("\n"):
                        results[k] = results[k][:-1]

        # fill media location
        if Attribute.MEDIA_LOCATION in rule.attributes:
            if Attribute.FILE_CONTENT.value in results:
                loc = get_pic_location(results[Attribute.FILE_CONTENT.value])
                if loc != "" and loc != "EXCEPTION: Exif Stripped":
                    results[Attribute.MEDIA_LOCATION.value] = loc
        return results, edit_path

    def shell(self, cmd, root=False):
        self.controller.back_to_home()
        if root and self.root_enabled and not self.controller.is_emulator:
            cmd = f"su -c '{cmd}'"
        res = self.controller.shell(cmd)
        if "su: inaccessible or not found" in res:
            raise Exception("Root permission is required")
        return res

    def __fix_root_delete_bug(self, path):
        # this is a bug in Android.
        # when root delete a file (or move it away), the path becomes invalid for normal apps.
        if not path.startswith("/data/data"):
            # We fix it by asking the "shell" user to create a new file and then delete it.
            self.shell(f"touch \"{path}\"; rm \"{path}\"", root=False)
        return True

    def __fix_root_write_bug(self, path):
        # When moving a file from /data/data to /Android/data
        # before Android 13, /Android/data will set file 660 and make it owned by sdcard_rw group
        # Since Android 13, /Android/data will keep its original permission and owner (600, owned by app)
        # Therefore shell user cannot access the file anymore
        if "/Android/data/" in path:
            # We fix it by asking the "shell" user to create a new file and then delete it.
            self.shell(f"chgrp ext_data_rw \"{path}\"; chmod 660 \"{path}\"", root=True)
        return True

    def read_file(self, rule, case, path, log=True):
        if log:
            case.reproduce.append(f"ROOT-SHELL read {path}")

        # If the path is in internal storage, we use root.
        use_root = path.startswith("/data/data")
        content = self.shell(f"cat \"{path}\"", root=use_root)
        if len(content) > 100 and "exception" not in content.lower():
            content = "Base64:" + self.shell(f"base64 \"{path}\"", root=use_root)
        size = self.shell(f"wc -c < \"{path}\"", root=use_root)
        modified_time = self.shell(f"stat -c %Y \"{path}\"", root=use_root)
        feedback, edit_path = self.build_feature(path, {"content": content, "size": size, "modified_time": modified_time}, rule)
        results = {
            "success": "FAIL" if any([v.startswith("EXCEPTION") or v.startswith("FAIL") for v in feedback.values() if
                                      type(v) is str]) else "SUCCESS",
            "target": path,
            "action": OperationType.READ.value["flag"],
            "result": feedback
        }
        attributes_filter = {attr.value for attr in rule.attributes}
        if Attribute.SUCCESS.value not in attributes_filter:
            results.pop("success")
        return results, edit_path

    def check_file(self, path):

        cmd = f"""if [ -d "{path}" ] ; then
    echo "directory";
else
    if [ -f "{path}" ]; then
        echo "file";
    else
        echo "invalid";
        exit 1
    fi
fi"""
        # If the path is in internal storage, we use root.
        use_root = path.startswith("/data/data")

        existed = self.shell(
            cmd, root=use_root)
        return existed

    def get_available_name(self, path, filename=None):
        count = 0
        check = self.check_file(path)
        isdir = check == "directory"
        if isdir and filename:
            dir_path = path
            path = os.path.join(dir_path + filename)
            check = self.check_file(path)
        while check != "invalid":
            count += 1
            if check == "file":
                elements = path.split(".")
                prefix, ext = '.'.join(elements[:-1]), elements[-1]
                suffix = re.match(r" \(\d+\)", prefix)
                if suffix:
                    prefix = prefix[:-len(suffix.group(1)) + 1]
                path = prefix + f" ({count})." + ext
            elif check == "directory":
                raise Exception("Unknown issue")
            check = self.check_file(path)
            if count > 100:
                raise Exception(f"Unknown issue: {path} {check} {count}")
        logger.info("Available name: {}", path)
        return path

    def __get_writable_content(self, content):
        if content.startswith("Base64:"):
            base64_data = content[7:]
            bytes_data = base64.b64decode(base64_data)
            content = "".join(["\\x{:02x}".format(b) for b in bytes_data])
        return content

    def create_file(self, rule, case, path, content, rename=True, log=True):
        if log:
            case.reproduce.append(f"ROOT-SHELL create {path} (rename={rename}) with content {content}")
        content = self.__get_writable_content(content)
        if rename:
            available_path = self.get_available_name(path)
        else:
            available_path = path

        # If the path is in internal storage, we use root.
        use_root = path.startswith("/data/data")

        self.shell(f"mkdir -p \"{os.path.dirname(available_path)}\"", root=use_root)
        created = self.shell(f"echo -ne \"{content}\" > \"{available_path}\"", root=use_root)
        success = "SUCCESS" if not created.strip() else "FAIL"

        return {"success": success, "target": path, "action": OperationType.CREATE.value["flag"],
                "result": {"edit_path": available_path}}, path

    def delete_file(self, rule, case, path, log=True):
        if log:
            case.reproduce.append(f"ROOT-SHELL delete {path}")

        # If the path is in internal storage, we use root.
        use_root = path.startswith("/data/data")

        deleted = self.shell(f"rm \"{path}\"", root=use_root)

        success = "SUCCESS" if not deleted.strip() else deleted.strip()

        # Since root involve only when the path is in internal storage (/data/data),
        # we don't need to fix the bug

        result, edit_path = self.read_file(rule, case, path, log=False)

        result = {"success": success, "target": path, "action": OperationType.DELETE.value["flag"],
                  "result": result["result"]}

        attributes_filter = {attr.value for attr in rule.attributes}
        if Attribute.SUCCESS.value not in attributes_filter:
            result.pop("success")
        return result, edit_path

    def move_file(self, rule, case, path, move_to, rename=True, log=True):
        if log:
            case.reproduce.append(f"ROOT-SHELL move {path} -> {move_to} (rename={rename})")

        # if the source file does not exist, we don't need to find available name
        check = self.check_file(path)
        filename = path.split("/")[-1]

        # If the path is in internal storage, we use root.
        use_root = move_to.startswith("/data/data") or path.startswith("/data/data")

        if rename and check != "invalid":
            self.shell(f"mkdir -p \"{os.path.dirname(os.path.join(move_to, filename))}\"", root=use_root)
            available_move_to = self.get_available_name(move_to, filename)
        else:
            available_move_to = os.path.join(move_to, filename)

        moved = self.shell(f"mv \"{path}\" \"{available_move_to}\"", root=use_root)
        success = "SUCCESS" if not moved.strip() else moved.strip()

        # FIX ANDROID BUG: reset the problematic state caused by root
        if success == "SUCCESS" and use_root:
            self.__fix_root_delete_bug(path)
            # For Android 13+, shell is limited, so we need to make sure the file is accessible by normal apps
            if int(self.controller.system_version.split("-")[0]) >= 13:
                self.__fix_root_write_bug(available_move_to)

        result = {"success": success, "target": path, "action": OperationType.MOVE.value["flag"],
                  "result": {"edit_path": available_move_to}}

        attributes_filter = {attr.value for attr in rule.attributes}
        if Attribute.SUCCESS.value not in attributes_filter:
            result.pop("success")
        return result, path

    def rename_file(self, rule, case, path, move_to, rename=True, log=True):
        if log:
            case.reproduce.append(f"ROOT-SHELL rename {path} -> {move_to} (rename={rename})")

        # if the source file does not exist, we don't need to find available name
        check = self.check_file(path)
        if rename and check != "invalid":
            available_move_to = self.get_available_name(move_to)
        else:
            available_move_to = move_to

        # If the path is in internal storage, we use root.
        use_root = path.startswith("/data/data")

        moved = self.shell(f"mv \"{path}\" \"{available_move_to}\"", root=use_root)
        success = "SUCCESS" if not moved.strip() else moved.strip()

        # FIX ANDROID BUG: reset the problematic state caused by root
        if moved == "SUCCESS" and use_root and self.root_enabled:
            self.__fix_root_delete_bug(path)

        result = {"success": success, "target": path, "action": OperationType.RENAME.value["flag"],
                  "result": {"edit_path": available_move_to}}

        attributes_filter = {attr.value for attr in rule.attributes}
        if Attribute.SUCCESS.value not in attributes_filter:
            result.pop("success")
        return result, path

    def overwrite_file(self, rule, case, path, content, log=True):
        if log:
            case.reproduce.append(f"ROOT-SHELL overwrite {path} with content {content}")
        content = self.__get_writable_content(content)

        # If the path is in internal storage, we use root.
        use_root = path.startswith("/data/data")

        overwritten = self.shell(f"[ -f \"{path}\" ] && echo -ne \"{content}\" > \"{path}\"", root=use_root)
        success = "SUCCESS" if not overwritten.strip() else overwritten.strip()
        result, edit_path = self.read_file(rule, case, path, log=False)
        result = {"success": success, "target": path, "action": OperationType.OVERWRITE.value["flag"],
                  "result": result["result"]}

        attributes_filter = {attr.value for attr in rule.attributes}
        if Attribute.SUCCESS.value not in attributes_filter:
            result.pop("success")
        return result, edit_path

    def run(self, rule, case, operation, param, rename=True):
        if operation == OperationType.READ:
            return self.read_file(rule, case, param["path"])
        elif operation == OperationType.CREATE:
            return self.create_file(rule, case, param["path"], param["data"], rename)
        elif operation == OperationType.DELETE:
            return self.delete_file(rule, case, param["path"])
        elif operation == OperationType.RENAME:
            return self.rename_file(rule, case, param["path"], param["move_to"], rename)
        elif operation == OperationType.MOVE:
            return self.move_file(rule, case, param["path"], param["move_to"], rename)
        elif operation == OperationType.OVERWRITE:
            return self.overwrite_file(rule, case, param["path"], param['data'], rename)
