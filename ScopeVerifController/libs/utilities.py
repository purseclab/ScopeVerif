import base64
import random
import json

import numpy as np
from loguru import logger
import os
import string
import re
import tempfile
from GPSPhoto import gpsphoto
from PIL import Image
from enums.api_level import TargetSdk
from enums.attribute import Attribute
from enums.target_enum import Collection, All
import random
from libs.target import Target


def get_all_attributes(cases):
    all_attributes = {}
    for c in cases:
        for a in c.get_attributes():
            all_attributes[a] = 0
    return sorted(list(all_attributes.keys()))


def get_pname_by_path(path: str):
    found = re.search(r"(com.abc.storage_verifier_\d{2})/", path)
    if found:
        return found.group(1)
    return None


def get_api_by_path(path: str):
    found = re.search(r"storage_verifier_(\d{2})", path)
    if found:
        return int(found.group(1))
    return None


class Result:
    def __init__(self, raw_result: str, attributes: dict):
        self.raw_result = raw_result
        lines = self.raw_result.splitlines()
        results = []
        for line in lines:
            found = re.search(r"D (.*?): ([\s\S]*)", line)
            if line.strip() == "--------- beginning of main":
                continue
            if not found:
                results.append(line.strip())
            else:
                results.append(found.group(2).strip())

        # combine lines
        self.clean_result = '\n'.join(results)

        # extract json if possible
        extracted_result = re.search("({[\s\S]+})", self.clean_result)
        if extracted_result:
            self.clean_result = extracted_result.group(1)

        try:
            self.json_result = json.loads(self.clean_result)
            logger.info(self.clean_result)
            # normalize path
            if "/storage/emulated/0" in self.json_result["result"].get("edit_path", ""):
                self.json_result["result"]["edit_path"] = self.json_result["result"]["edit_path"].replace(
                    "/storage/emulated/0", "/sdcard")
            if "/data/data" in self.json_result["result"].get("edit_path", ""):
                self.json_result["result"]["edit_path"] = self.json_result["result"]["edit_path"].replace(
                    "/data/user/0",
                    "/data/data")
        except Exception as e:
            if str(e) != "Expecting value: line 1 column 1 (char 0)":
                logger.warning(e)
            self.json_result = {"success": "EXCEPTION: No result, maybe Timeout?", "result": {}}

        # fill media location
        try:
            if Attribute.MEDIA_LOCATION in attributes:
                if "target" in self.json_result \
                        and Attribute.FILE_CONTENT.value in self.json_result["result"]:
                    loc = get_pic_location(self.json_result["result"][Attribute.FILE_CONTENT.value])
                    if loc != "" and loc != "EXCEPTION: Exif Stripped":
                        self.json_result["result"][Attribute.MEDIA_LOCATION.value] = loc
        except:
            logger.error("Error when fill media location")
            pass
        self.attributes_filter = {attr.value for attr in attributes}

    def build_feature(self):
        results = self.json_result.copy()
        results['result'] = {}
        edit_path = None
        for k in self.json_result["result"]:
            if k == Attribute.FILE_PATH.value:
                edit_path = self.json_result["result"][k]
            if k in self.attributes_filter:
                if str(self.json_result["result"][k]).startswith("EXCEPTION: "):
                    if Attribute.EXCEPTION.value not in self.attributes_filter:
                        continue
                if type(self.json_result["result"][k]) != dict:
                    results['result'][k] = str(self.json_result['result'][k]).replace("\r\n", "\n")
                else:
                    results['result'][k] = self.json_result['result'][k]
                    if k == "content":
                        results['result'][k] = results['result'][k].replace("\\r\n", "\n")
                # reading content might have an additional new line at the end
                if k == "content" and results['result'][k].endswith("\n"):
                    results['result'][k] = results['result'][k][:-1]
        if "success" in results and Attribute.SUCCESS.value not in self.attributes_filter:
            results.pop("success")
        return results, edit_path


def apply_replacement(feedback, replacement):
    feedback_str = json.dumps(feedback)
    for k, v in replacement.items():
        original = feedback_str
        feedback_str = feedback_str.replace(k, v)
        try:
            # ensure the replacement is valid json
            json.loads(feedback_str)
        except:
            feedback_str = original
    feedback = json.loads(feedback_str)
    return feedback


def truncate_strings(d, limit=900):
    for key, value in d.items():
        if isinstance(value, str):
            d[key] = value[:limit]
        elif isinstance(value, dict):
            truncate_strings(value, limit)
    return d


def same_feedback(feedback1, feedback2, replacement=None):
    if replacement is None:
        replacement = {}
    if replacement:
        feedback1 = apply_replacement(feedback1, replacement)
        feedback2 = apply_replacement(feedback2, replacement)

    # recursively truncate each item's value to 900 characters
    feedback1 = truncate_strings(feedback1, 900)
    feedback2 = truncate_strings(feedback2, 900)

    com1 = json.dumps(feedback1.get("result", feedback1), sort_keys=True)
    com2 = json.dumps(feedback2.get("result", feedback2), sort_keys=True)
    # constant_com1 = re.sub("[^a-zA-Z0-9]([a-zA-Z0-9]{10})\.", "", com1)
    # constant_com2 = re.sub("[^a-zA-Z0-9]([a-zA-Z0-9]{10})\.", "", com2)
    # return constant_com1 == constant_com2
    if "Server-side Exception" in com1 or "Server-side Exception" in com2:
        raise ServerSideException()
    return com1 == com2


def get_random_jpg():
    im_array = np.random.rand(100, 100, 3) * 10
    im = Image.fromarray(im_array.astype('uint8')).convert('RGB')
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        im.save(f.name, "JPEG")
        photo = gpsphoto.GPSPhoto(f.name)
        info = gpsphoto.GPSInfo((random.uniform(-90, 90), random.uniform(-180, 180)),
                                alt=10, timeStamp='1970:01:01 09:05:05')
        photo.modGPSData(info, f.name)
    result = open(f.name, 'rb').read()
    os.unlink(f.name)
    return "Base64:" + base64.b64encode(result).decode().replace("\r\n", "\n")


def get_pic_location(content):
    if "EXCEPTION" not in content:
        if content.startswith("Base64:"):
            content = content[7:]
        try:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(base64.b64decode(content.encode()))
            exif = gpsphoto.getGPSData(f.name)
        except ValueError:
            exif = "EXCEPTION: Exif Stripped"
        os.unlink(f.name)
        if not exif:
            logger.warning("No exif data.")
            return ""
        return exif
    logger.warning("No exif data.")
    return ""


def random_data(extension=None, attributes=None, n=10, seeder=None):
    if seeder:
        seeder()
    # if generating data for picture, and we are testing MEDIA_LOCATION
    if extension and extension in [".jpg", ".png"]:
        if attributes and Attribute.MEDIA_LOCATION in attributes:
            return get_random_jpg()
    a = string.ascii_lowercase
    b = string.ascii_uppercase
    c = string.ascii_letters
    d = string.digits
    char_set = a + b + c + d
    return ''.join(random.choice(list(char_set)) for _ in range(n))


def add_param(cmd, param, operator):
    for k, v in param.items():
        if type(v) is str:
            cmd += f" --es {k} \"{v}\""
        elif type(v) is bool:
            cmd += f" --ez {k} {str(v).lower()}"
        elif type(v) is int:
            cmd += f" --el {k} {v}"
        elif k.lower().strip() == "api":
            cmd += f" --es {k} \"{v.api_name}\""
    return cmd


def get_extensions_by_path(path: str):
    extensions = []
    if any([each in path for each in All([Collection.SHARED_DOWNLOAD, Collection.APP_FOLDER]).value]):
        extensions += [".pdf", ".txt"]
    if any([each in path for each in Collection.SHARED_IMAGE.value]):
        extensions += [".jpg"]
    if any([each in path for each in Collection.SHARED_AUDIO.value]):
        extensions += [".mp3"]
    if any([each in path for each in Collection.SHARED_VIDEO.value]):
        extensions += [".mp4"]
    # internal storage
    if not extensions:
        extensions += [".txt"]
    return sorted(list(set(extensions)))


def count_diff_attr(arg1, arg2):
    count = 0
    obs1 = arg1.get("root-observation", arg1)
    obs2 = arg2.get("root-observation", arg2)
    res1 = obs1.get("result", obs1)
    res2 = obs2.get("result", obs2)
    diff = set()
    for k in set(res1.keys()).union(set(res2.keys())):
        if k not in res2 or k not in res1:
            count += 1
            diff.add(k)
            continue
        if res1[k] != res2[k]:
            diff.add(k)
            count += 1
    target1 = obs1.get("target", {})
    target2 = obs2.get("target", {})
    if target1 and target2 and target1 != target2 and "target" not in diff:
        count += 1
        diff.add("target")

    success1 = obs1.get("success", {})
    success2 = obs2.get("success", {})
    if success1 and success2 and success1 != success2 and "success" not in diff:
        count += 1
        diff.add("success")
    return count, diff


def extract_rand_from_path(path):
    try:
        rand_str = re.findall("[^a-zA-Z0-9]([a-zA-Z0-9]{10})(.| )", path)
        if rand_str:
            return rand_str[0][0]
        print("NO!", rand_str)
        exit()
    except:
        print("NO!", path)
        exit()


class ServerSideException(Exception):
    pass
