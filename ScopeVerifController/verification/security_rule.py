from enums.attribute import Attribute
from enums.rule_type import RuleType
from enums.operation_type import OperationType
from enums.storage_api import StorageApiBase
from libs.target import *
from libs.permission_setting import PermissionSetting
import itertools


class SecurityRule:
    def __init__(self, rule_type: RuleType, rule_id: str,
                 actions: List[OperationType],
                 targets: List[Target],
                 attributes: List[Attribute],
                 storage_apis: List[StorageApiBase],
                 permissions: List[PermissionSetting],
                 minimum_case_required=None):
        self.rule_id = rule_id
        self.actions = set(actions)
        self.targets = set(targets)
        self.attributes = set(attributes)
        self.apis = set(storage_apis)
        self.permissions = set(permissions)
        self.rule_type = rule_type
        self.minimum_case_required = minimum_case_required

    def is_applicable(self, api, final_action, path_template):
        if api not in self.apis:
            return False, "API not applicable"
        if not any([api.is_valid_target(target) for target in self.targets]):
            return False, "Target not applicable to api"
        if path_template.target_path.template not in list(
                map(lambda x: x.template, itertools.chain(*[t.get_paths() for t in self.targets]))):
            return False, "Target path not applicable"
        if final_action not in self.actions:
            return False, "Action not applicable"
        return True, ""

    def __repr__(self):
        return f"[{self.rule_type.name}-{self.rule_id}]"
