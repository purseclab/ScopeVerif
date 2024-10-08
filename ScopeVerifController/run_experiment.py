from enums.attribute import Attribute
from enums.operation_type import OperationType
from enums.rule_type import RuleType
from enums.sample_mode_enum import SampleMode
from enums.storage_api import StorageAPI, SafPickerApi
from enums.target_enum import Storage, Collection, Scope, All
from libs.device_controller import DeviceController
from libs.ui_controller import UIController
from verification.input_generator import InputGenerator
from libs.permission_setting import PermissionSetting
from libs.root_handler import RootHandler
from verification.storage_oracle import StorageOracle
from libs.target import Target
from verification.scoring import StorageFuzzingScore
from verification.security_rule import SecurityRule
from verification.storage_verifier import StorageVerifier

rules = []

# A1: Unrestricted access to your own app internal and external storage
actions = [op for op in OperationType]
targets = [
    Target(storage=Storage.EXTERNAL_STORAGE, collection=Collection.APP_FOLDER, scope=Scope.MY_APP),
    # Target(storage=Storage.INTERNAL_STORAGE, collection=Collection.APP_FOLDER, scope=Scope.MY_APP) # disable internal storage testing
]
attributes = [attr for attr in Attribute]
category = RuleType.Availability
apis = [api for api in StorageAPI]
permissions = [PermissionSetting().from_array([0, 0, 0, 0, 0])]

rules.append(SecurityRule(
    rule_id="A1",
    actions=actions,
    targets=targets,
    attributes=attributes,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category))

# A2: Unrestricted access to contribute files to media and download collection
actions = [op for op in OperationType]
targets = [
    Target(
        storage=Storage.EXTERNAL_STORAGE,
        collection=All([Collection.SHARED_IMAGE, Collection.SHARED_DOWNLOAD]),
        scope=Scope.MY_APP
    )
]
attributes = [attr for attr in Attribute]
category = RuleType.Availability
apis = [api for api in StorageAPI]
permissions = [PermissionSetting().from_array([0, 0, 0, 0, 0])]

rules.append(SecurityRule(
    rule_id="A2",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# A3: Media collections can be read by other apps using storage permission.
actions = [OperationType.READ]
targets = [
    Target(storage=Storage.EXTERNAL_STORAGE,
           collection=All([Collection.SHARED_IMAGE, Collection.SHARED_VIDEO,
                           Collection.SHARED_AUDIO]),
           scope=Scope.OTHER_APPS
    )
]
# beta cannot access EXIF with READ_EXTERNAL_STORAGE permission
attributes = [attr for attr in Attribute if attr != Attribute.MEDIA_LOCATION]

category = RuleType.Availability
apis = [api for api in StorageAPI]
permissions = [PermissionSetting.from_array([0, 1, 0, 0, 0])]

rules.append(SecurityRule(
    rule_id="A3",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# C1: Cannot access files in any other app’s dedicated specific directory in external storage for Android 11 and above
actions = [op for op in OperationType]  # we do all actions because they could also leak information
targets = [
    Target(Storage.EXTERNAL_STORAGE, Collection.APP_FOLDER, Scope.OTHER_APPS)
]
category = RuleType.Confidentiality
attributes = [attr for attr in Attribute]

apis = [api for api in StorageAPI]
permissions = [PermissionSetting.from_array([1, 1, 1, 1, 1])]

rules.append(SecurityRule(
    rule_id="C1",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# C2. Reading outside of collections (media collections and own app directories) requires user interaction.
actions = [op for op in OperationType]  # we do all actions because they could also leak information
targets = [
    Target(storage=Storage.EXTERNAL_STORAGE, collection=Collection.SHARED_DOWNLOAD, scope=Scope.OTHER_APPS)
]
category = RuleType.Confidentiality
attributes = [attr for attr in Attribute]
apis = [api for api in StorageAPI if not api.api_name.startswith("saf-picker")]  # do not ask for user interaction
permissions = [
    PermissionSetting.from_array([1, 1, 1, 1, 1]),  # stronger attacker
    # PermissionSetting.from_array([0, 0, 0, 0, 0])  # weaker attacker
]

rules.append(SecurityRule(
    rule_id="C2",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# C3. Location permission need to be declared in manifest,
# and approved by metadata requires declaration in permission from the user.
actions = [op for op in OperationType]  # we do all actions because they could also leak information
targets = [
    Target(storage=Storage.EXTERNAL_STORAGE, collection=Collection.SHARED_IMAGE, scope=Scope.OTHER_APPS)
]
category = RuleType.Confidentiality
attributes = [Attribute.MEDIA_LOCATION]
apis = [api for api in StorageAPI]
# all permissions that do not have ACCESS_MEDIA_LOCATION permission
permissions = [PermissionSetting.from_array([i % 2, i // 2 % 2, i // 4 % 2] + [0, 0]) for i in range(8) if i % 2 == 0]

rules.append(SecurityRule(
    rule_id="C3",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# T1. Writing outside of collections (media collections and own app directories) requires user interaction.
actions = [action for action in OperationType if action != OperationType.READ]
targets = [
    Target(storage=Storage.EXTERNAL_STORAGE, collection=Collection.SHARED_DOWNLOAD, scope=Scope.OTHER_APPS),
]
category = RuleType.Integrity
attributes = [attr for attr in Attribute]
apis = [api for api in StorageAPI if not api.api_name.startswith("saf-picker")]  # do not ask for user interaction
permissions = [PermissionSetting.from_array([1, 1, 0, 1, 1])] # no ALL FILE ACCESS


rules.append(SecurityRule(
    rule_id="T1",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# T2: Cannot access files in any other app’s dedicated specific directory in external storage for Android 11 and above
actions = [action for action in OperationType if action != OperationType.READ]
targets = [
    Target(Storage.EXTERNAL_STORAGE, Collection.APP_FOLDER, Scope.OTHER_APPS)
]
category = RuleType.Integrity
attributes = [attr for attr in Attribute]

apis = [api for api in StorageAPI]
permissions = [PermissionSetting.from_array([1, 1, 1, 1, 1])]

rules.append(SecurityRule(
    rule_id="T2",
    actions=actions,
    targets=targets,
    storage_apis=apis,
    permissions=permissions,
    rule_type=category,
    attributes=attributes))

# step 1: init input generator
# 314 average min cases leads to ~2500 total cases, 61 average min cases leads to ~500 total cases
input_generator = InputGenerator(average_min_cases=61, seed=10, debug_ensure_coverage=True) 

# step 2: init oracle
device = DeviceController()
ui_handler = UIController(device)
root_handler = RootHandler(device)
from personal_config import my_apk_path_getter

oracle = StorageOracle(device, ui_handler, apk_path_getter=my_apk_path_getter, root_handler=root_handler)

# step 3: init a verifier
scoring = StorageFuzzingScore()
version = device.system_version


verifier = StorageVerifier(f"scoped_storage_{version}", version, input_generator,
                           oracle, scoring, rules, sample_mode=SampleMode.RANDOM, reuse_results=False)

# step 4: start verification
verifier.verify()