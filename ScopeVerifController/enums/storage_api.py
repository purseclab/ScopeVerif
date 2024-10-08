from typing import Iterator
from enums.operation_type import OperationType
from enums.target_enum import Storage, Collection, All, Scope
from libs.target import Target
import re
import itertools


class StorageApiBase:
    def __init__(self, api_name: str, invalid_targets=None, invalid_actions=None):
        if invalid_actions is None:
            invalid_actions = set()

        if type(invalid_targets) is not set:
            invalid_targets_set = set()
            if invalid_targets is not None:
                for target in invalid_targets:
                    pattern = []
                    for attr, Klass in [("storage", Storage), ("collection", Collection), ("scope", Scope)]:
                        if getattr(target, attr) == All:
                            pattern.append(f"({'|'.join([each.name for each in Klass] + ['ALL'])})")
                        else:
                            pattern.append(getattr(target, attr).name)
                    invalid_targets_set.add('-'.join(pattern))
            self.invalid_target = invalid_targets_set
        else:
            self.invalid_target = invalid_targets

        if type(invalid_actions) is not set:
            invalid_actions_set = set()
            if invalid_actions is not None:
                for action in invalid_actions:
                    invalid_actions_set.add(action.name)
            self.invalid_action = invalid_actions_set
        else:
            self.invalid_action = invalid_actions

        self.api_name = api_name

    def __repr__(self):
        return self.api_name.upper()

    def is_valid_action(self, action: OperationType):
        return action.name not in self.invalid_action

    def is_valid_target(self, target: Target):
        for pat in self.invalid_target:
            if re.match(f"^{pat}$", '-'.join([target.storage.name, target.collection.name, target.scope.name])):
                return False
        return True

    def get_printable_name(self):
        return ''.join(map(lambda x: x.title(), self.api_name.split('-')))


class FileApi(StorageApiBase):
    def __init__(self):
        super().__init__("file",
                         invalid_actions=[],
                         invalid_targets=[])


class MediaStoreApi(StorageApiBase):
    def __init__(self):
        super().__init__("media-store",
                         invalid_actions=[OperationType.MOVE],
                         invalid_targets=[Target(storage=Storage.INTERNAL_STORAGE),
                                          Target(collection=Collection.APP_FOLDER)])


class SafPickerApi(StorageApiBase):
    def __init__(self):
        super().__init__("saf-picker",
                         invalid_actions=[],
                         invalid_targets=[Target(storage=Storage.INTERNAL_STORAGE)]
                         )


class ContentResolverApi(StorageApiBase):
    def __init__(self):
        super().__init__("content-resolver",
                         invalid_actions=[],
                         invalid_targets=[Target(storage=Storage.INTERNAL_STORAGE)]
                         )


class DocumentFileApi(StorageApiBase):
    def __init__(self):
        super().__init__("document-file",
                         invalid_actions=[],
                         invalid_targets=[Target(storage=Storage.INTERNAL_STORAGE)]
                         )


class DocumentsContractApi(StorageApiBase):
    def __init__(self):
        super().__init__("documents-contract",
                         invalid_actions=[],
                         invalid_targets=[Target(storage=Storage.INTERNAL_STORAGE)]
                         )


class FileDescriptorApi(StorageApiBase):
    def __init__(self):
        super().__init__("file-descriptor",
                         invalid_actions=[],
                         invalid_targets=[]
                         )


class IOStreamApi(StorageApiBase):
    def __init__(self):
        super().__init__("io-stream",
                         invalid_actions=[],
                         invalid_targets=[]
                         )


class ComboApi(StorageApiBase):
    def __init__(self, get_uri_api: StorageApiBase, manage_uri_api: StorageApiBase, access_uri_api: StorageApiBase):
        api_name = get_uri_api.api_name + '@' + manage_uri_api.api_name + '@' + access_uri_api.api_name
        invalid_target = get_uri_api.invalid_target | access_uri_api.invalid_target | manage_uri_api.invalid_target
        invalid_action = get_uri_api.invalid_action | access_uri_api.invalid_action | manage_uri_api.invalid_action
        super().__init__(api_name,
                         invalid_actions=invalid_action,
                         invalid_targets=invalid_target
                         )


GET_URI_API = [MediaStoreApi(), SafPickerApi()]
MANAGE_URI_API = [ContentResolverApi(), DocumentFileApi(), DocumentsContractApi()]
ACCESS_URI_API = [FileDescriptorApi(), IOStreamApi()]
# MediaStore has to be used together with ContentResolver
# SafPicker has to be used together with DocumentFile and DocumentsContract
# In total, there are 6 combinations for URI APIs
PATH_API = [FileApi()]
URI_API = []
for get_uri_api, manage_uri_api, access_uri_api in itertools.product(GET_URI_API, MANAGE_URI_API, ACCESS_URI_API):
    # DocumentFile and DocumentsContract are mutually binds with SAF
    if (manage_uri_api.api_name in [DocumentFileApi().api_name, DocumentsContractApi().api_name]
        and get_uri_api.api_name != SafPickerApi().api_name) or (manage_uri_api.api_name in [ContentResolverApi().api_name]
                                                                 and get_uri_api.api_name == SafPickerApi().api_name):
        continue
    combo_api = ComboApi(get_uri_api, manage_uri_api, access_uri_api)
    URI_API.append(combo_api)



class StorageIterator(type):
    def __iter__(self) -> Iterator[StorageApiBase]:
        for path_api in PATH_API:
            yield path_api
        for combo_api in URI_API:
            yield combo_api


class StorageAPI(metaclass=StorageIterator):
    pass
