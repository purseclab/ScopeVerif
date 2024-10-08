import json

from loguru import logger
from enums.app_role import AppRole
from enums.operation_type import OperationType
from enums.rule_type import RuleType
from enums.storage_api import FileApi
from enums.target_enum import Scope
from libs.file_handler import FileHandler, build_param
from libs.operator import Operator
from libs.permission_setting import PermissionSetting
from libs.utilities import same_feedback, count_diff_attr, apply_replacement, extract_rand_from_path, truncate_strings


class StorageOracle:
    def __init__(self, device_handler, ui_handler, apk_path_getter, root_handler):
        self.device_handler = device_handler
        self.ui_handler = ui_handler
        self.apk_path_getter = apk_path_getter
        self.root_handler = root_handler

    def has_root(self):
        return self.root_handler.has_root()

    def perform_test(self, rule, case, payload, stop_when_fail, perm_setter, perm_setting,
                     system_version, ext, path_template):
        alpha_pname = AppRole.ALPHA.value
        beta_pname = AppRole.BETA.value
        gamma_pname = AppRole.GAMMA.value

        alpha = Operator(alpha_pname, path_template, ext, rule.attributes, case.set_case_seed)
        beta = Operator(beta_pname, path_template, ext, rule.attributes, case.set_case_seed)
        gamma = Operator(gamma_pname, path_template, ext, rule.attributes, case.set_case_seed)

        # initialize file operator for both the file alpha and the file beta
        alpha_handler = FileHandler(self.device_handler, self.ui_handler, alpha_pname, rule.attributes, alpha,
                                    self.root_handler)
        beta_handler = FileHandler(self.device_handler, self.ui_handler, beta_pname, rule.attributes, beta,
                                   self.root_handler)
        gamma_handler = FileHandler(self.device_handler, self.ui_handler, gamma_pname, rule.attributes, gamma,
                                    self.root_handler)

        logger.info(f"Setting permissions: {perm_setting.to_printable()}")
        # if we are verifying confidentiality, then we are seeking for equivalence of operation results
        # between existing file and non-existing files
        if rule.rule_type == RuleType.Confidentiality:
            for app_role in AppRole:
                pname = app_role.value
                if pname != gamma_handler.pname:
                    perm_setter(pname, system_version, ext,
                                PermissionSetting.from_array([0, 0, 0, 0, 0]), self.device_handler)
                else:
                    perm_setter(pname, system_version, ext, perm_setting, self.device_handler)

            # decide who is the victim based on the scope of the target
            if path_template.target.scope == Scope.MY_APP:
                attacker_handler = gamma_handler
                victim_handler = gamma_handler
                attacker = gamma
                victim = gamma
            else:
                attacker_handler = gamma_handler
                victim_handler = alpha_handler
                attacker = gamma
                victim = alpha

            return self.confidentiality_test(rule=rule,
                                             case=case,
                                             payload=payload,
                                             perm_setting=perm_setting,
                                             attacker_handler=attacker_handler,
                                             victim_handler=victim_handler,
                                             attacker=attacker,
                                             victim=victim,
                                             stop_when_fail=stop_when_fail)

        # if we are verifying integrity, then file attributes must be same after modification attempts
        if rule.rule_type == RuleType.Integrity:
            for app_role in AppRole:
                pname = app_role.value
                if pname != gamma_handler.pname:
                    perm_setter(pname, system_version, ext,
                                PermissionSetting.from_array([0, 0, 0, 0, 0]), self.device_handler)
                else:
                    perm_setter(pname, system_version, ext, perm_setting, self.device_handler)

            # decide who is the victim based on the scope of the target
            if path_template.target.scope == Scope.MY_APP:
                attacker_handler = gamma_handler
                victim_handler = gamma_handler
                attacker = gamma
                victim = gamma
            else:
                attacker_handler = gamma_handler
                victim_handler = alpha_handler
                attacker = gamma
                victim = alpha

            # in this case, alpha and beta are the same entity
            return self.integrity_test(rule=rule,
                                       case=case,
                                       payload=payload,
                                       perm_setting=perm_setting,
                                       attacker_handler=attacker_handler,
                                       victim_handler=victim_handler,
                                       attacker=attacker,
                                       victim=victim,
                                       stop_when_fail=stop_when_fail)

        # if we are verifying availability, then all operations must have same feedback as the alpha
        if rule.rule_type == RuleType.Availability:
            for app_role in AppRole:
                pname = app_role.value
                if pname != alpha_handler.pname:
                    perm_setter(pname, system_version, ext,
                                PermissionSetting.from_array([0, 0, 0, 0, 0]), self.device_handler)
                else:
                    perm_setter(pname, system_version, ext, perm_setting, self.device_handler)

            # decide who is the victim based on the scope of the target
            logger.info(f"case path template target scope: {path_template.target.scope}")
            if path_template.target.scope == Scope.MY_APP:
                attacker_handler = gamma_handler
                victim_handler = alpha_handler
                resource_handler = alpha_handler
                attacker = gamma
                victim = alpha
                resource = alpha
            else:
                attacker_handler = gamma_handler
                victim_handler = alpha_handler
                resource_handler = beta_handler
                attacker = gamma
                victim = alpha
                resource = beta

            # for operations that does not update file attributes
            return self.availability_test(rule=rule,
                                          case=case,
                                          payload=payload,
                                          perm_setting=perm_setting,
                                          attacker_handler=attacker_handler,
                                          victim_handler=victim_handler,
                                          resource_handler=resource_handler,
                                          attacker=attacker,
                                          victim=victim,
                                          resource=resource,
                                          stop_when_fail=stop_when_fail)
        return True, None

    def confidentiality_test(self, rule, case, payload, perm_setting, attacker_handler, victim_handler,
                             attacker, victim, stop_when_fail=False):
        replacement = {attacker.pname: victim.pname}

        # reference feedback
        param = build_param(action=case.final_action, alpha=victim, beta=attacker, api=case.api)
        result_on_non_exist_file, _ = attacker_handler.run(case, case.final_action, param)
        assert result_on_non_exist_file, "reference cannot be blank"

        for action in payload:
            if "SETUP" in str(action):
                _, setup_api = action
                # setup require getting new path!
                setup_feedback, setup_edit_path = victim_handler.create_file(case, victim.path, victim.data,
                                                                             api=setup_api, rename=True)
                # print(setup_feedback, setup_edit_path and "EXCEPTION: " not in setup_edit_path)
                # if setup_edit_path and "EXCEPTION: " not in setup_edit_path:
                #     # replacement[victim.path] = setup_feedback["result"]["edit_path"]
                #     # logger.info(f"REPLACE: {replacement}")
                #     victim.path = setup_feedback["result"]["edit_path"]
            else:
                # the gamma try to do something bad ...
                bad_move, bad_api = action
                bad_param = build_param(action=bad_move, alpha=victim, beta=attacker, api=bad_api)
                attacker_handler.run(case, bad_move, bad_param)

        param = build_param(action=case.final_action, alpha=victim, beta=attacker, api=case.api)
        result_on_exist_file, _ = attacker_handler.run(case, case.final_action, param)

        # notice the only allowable discrepancy are fname/pname
        # Ex: different pname/fname in exceptions when accessing different file,
        # we replace beta fname/pname to alpha fname/pname to reduce this special case to general case
        results = self.get_results(rule, case, payload, result_on_exist_file, result_on_non_exist_file,
                                   perm_setting, replacement)
        if stop_when_fail:
            assert same_feedback(result_on_exist_file, result_on_non_exist_file, replacement), results
        return same_feedback(result_on_exist_file, result_on_non_exist_file, replacement), results

    def availability_test(self, rule, case, payload, perm_setting, attacker_handler, victim_handler, resource_handler,
                          attacker, victim, resource, stop_when_fail=False):

        replacement = {extract_rand_from_path(resource.path): extract_rand_from_path(resource.path3),
                       extract_rand_from_path(resource.path2): extract_rand_from_path(resource.path4),
                       extract_rand_from_path(resource.path5): extract_rand_from_path(resource.path6),
                       attacker.dirpath2: attacker.dirpath,  # dirpath2 must on the left
                       victim.dirpath2: victim.dirpath}  # dirpath2 must on the left

        for action in payload:
            if "SETUP" in str(action):
                _, setup_api = action
                # step1: prepare the file (setup action)
                if case.final_action != OperationType.CREATE:
                    # previously using "case.api", but mediaStore is limited and newer Android 14 also limits SAF
                    setup_feedback1, setup1_edit_path = resource_handler.create_file(case, resource.path, resource.data,
                                                                                     api=setup_api, rename=True)
                    setup_feedback2, setup2_edit_path = resource_handler.create_file(case, resource.path3,
                                                                                     resource.data, api=setup_api,
                                                                                     rename=True)

                    if setup1_edit_path and setup1_edit_path != "false" and "EXCEPTION: " not in setup1_edit_path:
                        resource.path = setup1_edit_path
                    if setup2_edit_path and setup2_edit_path != "false" and "EXCEPTION: " not in setup2_edit_path:
                        resource.path3 = setup2_edit_path
                    replacement[extract_rand_from_path(resource.path)] = extract_rand_from_path(resource.path3)
            else:
                # step2: the gamma do bad things toward both file paths
                bad_move, bad_api = action
                if bad_move is OperationType.MOVE:
                    bad_param1 = build_param(action=bad_move, alpha=resource, beta=attacker, api=bad_api,
                                             default_param={"path": resource.path, "move_to": attacker.dirpath})
                    bad_param2 = build_param(action=bad_move, alpha=resource, beta=attacker, api=bad_api,
                                             default_param={"path": resource.path3, "move_to": attacker.dirpath2})
                elif bad_move is OperationType.RENAME:
                    bad_param1 = build_param(action=bad_move, alpha=resource, beta=attacker, api=bad_api,
                                             default_param={"path": resource.path, "move_to": resource.path5})
                    bad_param2 = build_param(action=bad_move, alpha=resource, beta=attacker, api=bad_api,
                                             default_param={"path": resource.path3, "move_to": resource.path6})
                else:
                    bad_param1 = build_param(action=bad_move, alpha=resource, beta=attacker, api=bad_api,
                                             default_param={"path": resource.path, "data": attacker.data,
                                                            "move_to": resource.path2})
                    bad_param2 = build_param(action=bad_move, alpha=resource, beta=attacker, api=bad_api,
                                             default_param={"path": resource.path3, "data": attacker.data,
                                                            "move_to": resource.path4})
                attacker_handler.run(case, bad_move, bad_param1)
                attacker_handler.run(case, bad_move, bad_param2)

        # step3: perform final action
        if case.final_action != OperationType.CREATE:
            if case.final_action == OperationType.MOVE:
                param1 = build_param(action=case.final_action, alpha=resource, beta=victim, api=case.api,
                                     default_param={"path": resource.path3, "move_to": victim.dirpath2})
                param2 = build_param(case.final_action, alpha=resource, beta=victim, api=case.api,
                                     default_param={"path": resource.path, "move_to": victim.dirpath2})

            else:
                param1 = build_param(action=case.final_action, alpha=resource, beta=victim, api=case.api,
                                     default_param={"path": resource.path3, "move_to": resource.path4})
                param2 = build_param(action=case.final_action, alpha=resource, beta=victim, api=case.api,
                                     default_param={"path": resource.path, "move_to": resource.path2})
            app_feedback, setup1_edit_path = victim_handler.run(case, case.final_action, param2)

            root_feedback, setup2_edit_path = self.root_handler.run(rule, case, case.final_action, param1,
                                                                    rename=not (
                                                                                case.api.api_name == FileApi().api_name))
        else:
            app_feedback, setup1_edit_path = victim_handler.create_file(case, resource.path, resource.data,
                                                                        api=case.api)
            root_feedback, setup2_edit_path = self.root_handler.create_file(rule, case, resource.path3, resource.data,
                                                                            rename=not (
                                                                                        case.api.api_name == FileApi().api_name))
            if setup1_edit_path and setup1_edit_path != "false" and "EXCEPTION: " not in setup1_edit_path:
                resource.path = setup1_edit_path
            if setup2_edit_path and setup1_edit_path != "false" and "EXCEPTION: " not in setup2_edit_path:
                resource.path3 = setup2_edit_path
            replacement[extract_rand_from_path(resource.path)] = extract_rand_from_path(resource.path3)

        app_feedback = self.get_root_observation(rule, case, app_feedback, resource.path)
        root_feedback = self.get_root_observation(rule, case, root_feedback, resource.path3)
        assert root_feedback, "reference cannot be blank"

        # modified_time can be different
        logger.info(root_feedback)
        modified_time1 = root_feedback.get("root-observation", root_feedback)["result"].get("modified_time", "NONE")
        modified_time2 = app_feedback.get("root-observation", app_feedback)["result"].get("modified_time", "NONE")
        if str(modified_time1).isdigit() and str(modified_time2).isdigit():
            replacement[str(modified_time1)] = str(modified_time2)

        # if READ, and root cannot access the file, then this case is trivially true
        if case.final_action == OperationType.READ and root_feedback['success'] == "FAIL":
            results = self.get_results(rule, case, payload, root_feedback, root_feedback,
                                       perm_setting, replacement)
            return True, results

        results = self.get_results(rule, case, payload, root_feedback, app_feedback,
                                   perm_setting, replacement)
        if stop_when_fail:
            assert same_feedback(root_feedback, app_feedback, replacement), results
        return same_feedback(root_feedback, app_feedback, replacement), results

    def integrity_test(self, rule, case, payload, perm_setting, attacker_handler, victim_handler,
                       attacker, victim, stop_when_fail=False):
        replacement = {}
        # note alpha and beta are the same app
        before_feedback = {}
        for action in payload:
            if "SETUP" in str(action):
                _, setup_api = action
                setup_feedback, setup_edit_path = victim_handler.create_file(case, victim.path, victim.data, api=setup_api, rename=True)
                if setup_edit_path and "EXCEPTION: " not in setup_edit_path:
                    replacement[victim.path] = setup_edit_path
                    victim.path = setup_edit_path

                file_before_modify, _ = victim_handler.read_file(case, victim.path, api=case.api)
                before_feedback = self.get_root_observation(rule, case, file_before_modify, victim.path)
                assert file_before_modify, "reference cannot be blank"
            else:
                # the gamma try to do something bad ...
                bad_move, bad_api = action
                bad_param = build_param(action=bad_move, alpha=victim, beta=attacker, api=bad_api)
                logger.info(f"bad_param: {bad_param}, action: {bad_move}")
                attacker_handler.run(case, bad_move, bad_param)

        # gamma perform the final action
        param = build_param(action=case.final_action, alpha=victim, beta=attacker, api=case.api)
        attacker_handler.run(case, case.final_action, param)

        # collect the feedback
        file_after_modify, _ = victim_handler.read_file(case, victim.path, api=case.api)
        after_feedback = self.get_root_observation(rule, case, file_after_modify, victim.path)
        results = self.get_results(rule, case, payload, before_feedback, after_feedback, perm_setting)
        if stop_when_fail:
            assert same_feedback(before_feedback, after_feedback, replacement), results
        return same_feedback(before_feedback, after_feedback, replacement), results

    def get_results(self, rule, case, payload, arg1, arg2, perm_setting, replacement=None):
        if replacement is None:
            replacement = {}
        results = {
            "type": rule.rule_type.name.upper(),
            "final_action": case.final_action.name.upper() + "_" + case.api.api_name.upper(),
            "permission": perm_setting.to_printable(),
            "payload": case.get_payload_printable(payload),
            "reproduce": case.reproduce.copy(),
            "replacement": replacement
        }

        if rule.rule_type == RuleType.Integrity:
            results.update({"file_before_modify": arg1,
                            "file_after_modify": arg2})
        elif rule.rule_type == RuleType.Confidentiality:
            results.update({"result_on_exist_file": arg1,
                            "result_on_non_exist_file": arg2})
        elif rule.rule_type == RuleType.Availability:
            results.update({"root_feedback": arg1,
                            "app_feedback": arg2})
        if replacement:
            arg1 = apply_replacement(arg1, replacement)
            arg2 = apply_replacement(arg2, replacement)

        # recursively truncate each item's value to 900 characters
        arg1 = truncate_strings(arg1, 900)
        arg2 = truncate_strings(arg2, 900)

        diff_score, diff_elements = count_diff_attr(arg1, arg2)
        results.update({"diff_attr_count": diff_score, "diff_elements": list(diff_elements)})
        return results

    def get_root_observation(self, rule, case, feedback, path):
        # READ does not need Root's help
        if case.final_action == OperationType.READ:
            return json.loads(json.dumps(feedback, sort_keys=True))
        # CREATE, RENAME, MOVE requires reading the "new" path
        if feedback["success"] == "SUCCESS" and \
                case.final_action in [OperationType.CREATE, OperationType.RENAME, OperationType.MOVE]:
            feedback_edit_path = feedback['result'].get("edit_path")
            if feedback_edit_path and feedback_edit_path != "false" and "EXCEPTION: " not in feedback_edit_path:
                path = feedback_edit_path
        observation, _ = self.root_handler.read_file(rule, case, path, log=False)
        observation = json.loads(json.dumps(observation, sort_keys=True))
        return {"root-observation": observation}
