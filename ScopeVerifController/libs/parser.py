import string
from enums.operation_type import OperationType
from enums.rule_type import RuleType
from enums.storage_api import StorageAPI
from libs.path_template import PathTemplate
from verification.security_rule import SecurityRule

mem = {}


def parse_rule(rule_id):
    if rule_id in mem:
        return mem[rule_id]
    if rule_id.startswith("T"):
        rule_type = RuleType.Integrity
    elif rule_id.startswith("C"):
        rule_type = RuleType.Confidentiality
    elif rule_id.startswith("A"):
        rule_type = RuleType.Availability
    else:
        raise Exception("Unknown rule type: " + rule_id)
    mem[rule_id] = SecurityRule(rule_type=rule_type, rule_id=rule_id,
                                actions=[], targets=[], attributes=[], storage_apis=[], permissions=[])
    return mem[rule_id]


def parse_action(action):
    if action in mem:
        return mem[action]
    for each_action in OperationType:
        if each_action.name == action:
            mem[action] = each_action
            return each_action
    if action == "SETUP":
        mem[action] = "SETUP"
        return mem[action]
    raise Exception("Unknown action: " + action)


def parse_api(api_name):
    if api_name in mem:
        return mem[api_name]
    for each_api in StorageAPI:
        if each_api.api_name.upper().replace("-", '') == api_name.upper().replace("-", ''):
            mem[api_name] = each_api
            return each_api
    raise Exception("Unknown api: " + api_name)


def parse_payloads(payload):
    payload_l = eval(payload)
    parsed_payloads = []
    for each in payload_l:
        raw_action, raw_api = each.split(",")
        action = parse_action(raw_action)
        api = parse_api(raw_api)
        parsed_payloads.append((action, api))
    return parsed_payloads


def parse_template(template):
    return PathTemplate(target_path=string.Template(template), target=None)
