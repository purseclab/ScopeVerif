import json
from collections import defaultdict
from typing import List
import os
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Input
from tensorflow.keras.optimizers import Adam

from enums.app_permission import AppPermission
from enums.operation_type import OperationType
from enums.rule_type import RuleType
from enums.sample_mode_enum import SampleMode
from enums.target_enum import Storage, Collection
from libs.path_template import PathTemplate
from libs.utilities import get_extensions_by_path
from verification.security_rule import SecurityRule
from verification.test_case import TestCase
from loguru import logger
import random
import hashlib
import statsmodels.api as sm
import pandas as pd


class InputGenerator:
    def __init__(self, average_min_cases=10, seed=1, max_cases=None,
                 max_payload_length=1, weighted_sample=True, debug_ensure_coverage=False):
        assert max_payload_length > 0, "Payload length should be greater than 0."
        self.max_cases = max_cases
        self.average_min_cases = average_min_cases
        self.max_payload_length = max_payload_length
        self.seed = seed
        self.weighted_sample = weighted_sample
        self.debug_ensure_coverage = debug_ensure_coverage
        self.scaler = StandardScaler()

    def get_filtered_paths(self, app_name, tested_api, targets):
        target_paths = []
        # enumerate all targets
        for target in targets:
            if any([not tested_api.is_valid_target(target)]):
                continue
            for path in target.get_paths(app_name):
                target_paths.append(path)
        return target_paths

    def set_seed(self):
        # set seed to ensure reproducibility of cases generated
        os.environ["PYTHONHASHSEED"] = str(self.seed)
        os.environ['TF_CUDNN_DETERMINISTIC'] = '1'
        random.seed(self.seed)
        np.random.seed(self.seed)
        tf.random.set_seed(self.seed)

    # generate all possible combinations given an initial actions
    def generate_payloads(self, available_apis, target, length=1):
        raw_payloads: List[List] = [["X"]]
        for i in range(length):
            current_payloads_length = len(raw_payloads)
            for j in range(current_payloads_length):
                p = raw_payloads[j]
                if len(p) < i + 1:
                    continue
                copy_p = p.copy()
                for act in OperationType:
                    for api in sorted(list(available_apis), key=lambda x: x.api_name, reverse=True):
                        if not api.is_valid_action(act):
                            continue
                        if not api.is_valid_target(target):
                            continue
                        # saf is expected to be privileged in shared storage
                        if target.storage == Storage.EXTERNAL_STORAGE and target.collection != Collection.APP_FOLDER:
                            if api.api_name.startswith("saf"):
                                continue
                        raw_payloads.append([(act, api)] + copy_p)
                        raw_payloads.append(copy_p + [(act, api)])

        # find available setup apis
        setup_apis = []
        for api in sorted(list(available_apis), key=lambda x: x.api_name, reverse=True):
            if not api.is_valid_action(OperationType.CREATE):
                continue
            if not api.is_valid_target(target):
                continue
            setup_apis.append(api)
        # expand the payload to support all different setup
        payloads = []
        for p in raw_payloads:
            try:
                setup_index = p.index("X")
                # add initial setup actions
                for api in sorted(list(available_apis), key=lambda x: x.api_name, reverse=True):
                    if not api.is_valid_action(OperationType.CREATE):
                        continue
                    if not api.is_valid_target(target):
                        continue
                    p[setup_index] = ("SETUP", api)
                    payloads.append(p)
            except ValueError:
                payloads.append(p)

        seen = set()
        unique_payloads = []
        for payload in payloads:
            feature = json.dumps([str(each) for each in payload])
            if feature not in seen:
                seen.add(feature)
                unique_payloads.append(payload)
        return sorted(unique_payloads, key=lambda x: (len(x), str(x)))

    def shuffle(self, l, cmp=None):
        self.set_seed()
        if cmp:
            sorted_l = sorted(list(l), key=cmp)
        else:
            sorted_l = sorted(list(l))
        random.shuffle(sorted_l)
        return sorted_l

    def weighted_random_sort(self, items, reverse=True):
        self.set_seed()
        # Assign a random score to each item based on its weight
        scored_items = [(item, (random.uniform(item.weight / 2, item.weight), item.get_case_hash())) for item in items]
        scored_items = sorted(scored_items, key=lambda x: x[1], reverse=reverse)
        # Sort the items by their scores
        sorted_items = [item for item, score in scored_items]
        return sorted_items

    def train_models(self, cases_for_rules, history):
        self.set_seed()
        cases = {}
        count = 0
        for rule in cases_for_rules.keys():
            for length in cases_for_rules[rule].keys():
                for case in cases_for_rules[rule][length]:
                    count += 1
                    if case.get_case_hash() in history:
                        cases[case.get_case_hash()] = case

        # train models to learn the weights
        data = {}
        all_attributes = {}
        for c in cases:
            for a in cases[c].get_attributes():
                all_attributes[a] = 0
        cases_data = []
        for c in cases:
            attr_count = all_attributes.copy()
            for attr in cases[c].get_attributes():
                attr_count[attr] += 1
            attr_count['Score'] = 1 if history.get(cases[c].get_case_hash(), {}).get("score", 0) > 0 else 0
            cases_data.append(attr_count)

        for c_data in cases_data:
            for a in sorted(c_data.keys()):
                if a not in data:
                    data[a] = []
                data[a].append(c_data[a])

        # Creating the DataFrame
        df = pd.DataFrame(data)

        # Adding a constant term for the intercept
        df = sm.add_constant(df)

        # Defining the independent and dependent variables
        all_attr = sorted(list(all_attributes.keys()))
        X = df[all_attr]
        y = df['Score']

        # Split the data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=self.seed)

        fit_model = "neural_network"
        model = None
        y_pred = None
        if fit_model == "decision_tree":
            # Fitting a Decision Tree model
            model = DecisionTreeClassifier(random_state=self.seed)
            model.fit(X_train, y_train)
            # Making predictions on the test set
            y_pred_probs = model.predict_proba(X_test)[:, 1]
            y_pred = (y_pred_probs > 0.5).astype(int)  # Threshold can be adjusted
        elif fit_model == "random_forest":
            model = RandomForestClassifier(random_state=self.seed)
            model.fit(X_train, y_train)
            # Making predictions on the test set
            y_pred_probs = model.predict_proba(X_test)[:, 1]
            y_pred = (y_pred_probs > 0.5).astype(int)  # Threshold can be adjusted
        elif fit_model == "neural_network":
            # Scaling the features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Building a simple neural network model
            model = Sequential([
                Input(shape=(X_train_scaled.shape[1],)),
                Dense(128, activation='relu'),
                Dense(64, activation='relu'),
                Dense(1, activation='sigmoid')  # Use 'softmax' for multiclass classification
            ])

            # Compiling the model
            model.compile(optimizer=Adam(), loss='binary_crossentropy', metrics=['accuracy'])
            # Fitting the model
            model.fit(X_train_scaled, y_train, epochs=50, batch_size=10, verbose=1)

            # Making predictions on the test set
            y_pred_probs = model.predict(X_test_scaled)
            y_pred = (y_pred_probs > 0.5).astype(int)  # Threshold can be adjusted

        # Calculating performance metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='binary')
        recall = recall_score(y_test, y_pred, average='binary')
        f1 = f1_score(y_test, y_pred, average='binary')

        logger.info(f"INPUT_GENERATOR: Model is trained with {len(y_train)} cases.")
        logger.info(
            f"INPUT_GENERATOR: Accuracy: {accuracy:.2f}, Precision: {precision:.2f}, Recall: {recall:.2f}, F1 Score: {f1:.2f}")
        return model, all_attr

    def sample_cases(self, cases_for_rules, prerequisite, required_count, sample_mode, history):
        if sample_mode != SampleMode.RANDOM:
            model, all_attr = self.train_models(cases_for_rules, history)
        else:
            model, all_attr = None, None

        case_groups = []
        required_case = []
        seen = set()
        duplicates = set()
        skipped = 0
        for rule in cases_for_rules.keys():
            for length in cases_for_rules[rule].keys():
                cases = cases_for_rules[rule][length]
                new_cases = []
                for case in cases:
                    if case.get_case_hash() in history:
                        # if not random sample, we remove cases that are already tested
                        if sample_mode != SampleMode.RANDOM:
                            skipped += 1
                            continue
                    new_cases.append(case)
                cases_for_rules[rule][length] = new_cases
        if sample_mode != SampleMode.RANDOM:
            logger.info("INPUT_GENERATOR: Smart sampling is enabled, skipping {} cases".format(skipped))

        total_cases_count = sum(
            [len(level_cases) for cases in cases_for_rules.values() for level_cases in cases.values()])
        for rule in sorted(cases_for_rules.keys(), key=lambda x: x.rule_id):
            if rule.minimum_case_required is None:
                if not self.weighted_sample:
                    rule.minimum_case_required = self.average_min_cases
                else:
                    rule_cases_count = sum([len(cases) for cases in cases_for_rules[rule].values()])
                    rule.minimum_case_required = int(
                        self.average_min_cases * len(cases_for_rules.keys()) * rule_cases_count / total_cases_count)
            min_required = rule.minimum_case_required
            rule_counts = 0
            tested_counts = 0
            length = self.max_payload_length + 1

            if sample_mode == SampleMode.RANDOM:
                cases_for_rules[rule][length] = self.shuffle(cases_for_rules[rule][length], lambda x: x.get_case_hash())
            elif model:
                all_X = pd.concat([x.get_X(all_attr) for x in cases_for_rules[rule][length]])
                if hasattr(model, "predict_proba"):
                    cases_weights = model.predict_proba(all_X)[:, 1]
                else:
                    all_X_scaled = self.scaler.transform(all_X)
                    cases_weights = model.predict(all_X_scaled)
                if sample_mode in [SampleMode.EXTENSIVE, SampleMode.EXPLORATORY]:
                    reverse = sample_mode == SampleMode.EXTENSIVE
                    for i, c in enumerate(cases_for_rules[rule][length]):
                        c.weight = cases_weights[i]
                else:
                    # POLARIZED
                    mean_weight = sum(cases_weights) / len(cases_weights)
                    abs_weights = [abs(x - mean_weight) ** 2 for x in cases_weights]
                    for i, c in enumerate(cases_for_rules[rule][length]):
                        c.weight = abs_weights[i]
                    reverse = True
                cases_for_rules[rule][length] = sorted(cases_for_rules[rule][length], key=lambda x: x.weight,
                                                       reverse=reverse)
                # cases_for_rules[rule][length] = self.weighted_random_sort(
                #     items=cases_for_rules[rule][length],
                #     reverse=reverse)

            for each in cases_for_rules[rule][length]:
                queue = [each]
                group = []
                while queue:
                    curr = queue.pop()
                    group.append(curr)
                    curr_feature = str(curr.get_feature(prerequisite=True))
                    if curr_feature in prerequisite:
                        related_cases = list(prerequisite[curr_feature].values())
                        queue += related_cases
                case_groups.append(group)
                for case in group:
                    if case.get_case_hash() not in seen:
                        seen.add(case.get_case_hash())
                        rule_counts += 1
                if rule_counts < min_required:
                    for case in group:
                        if case.get_case_hash() not in duplicates:
                            duplicates.add(case.get_case_hash())
                            required_case.append(case)
                            tested_counts += 1
            if rule_counts < min_required:
                logger.warning(
                    f"INPUT_GENERATOR: rule {rule.rule_id} does not meet requirement {rule_counts}/{min_required}")
            else:
                logger.info(f"INPUT_GENERATOR: rule {rule.rule_id} is testing {tested_counts}/{rule_counts} cases")

        if required_count is not None:
            while case_groups and len(required_case) < required_count:
                group = case_groups.pop()
                for case in group:
                    if case.get_case_hash() not in duplicates:
                        duplicates.add(case.get_case_hash())
                        required_case.append(case)
        return required_case

    def generate_testcases(self, has_root: bool, needed_cases,
                           rules: List[SecurityRule],
                           disabled_rules: List[SecurityRule],
                           sample_mode: SampleMode = SampleMode.RANDOM, history=None, full_history=None):
        duplicates = {}
        prerequisite = defaultdict(dict)
        cases_for_rules = defaultdict(lambda: defaultdict(list))
        if history is None:
            history = {}
        if full_history is None:
            full_history = {}

        # enumerate all api levels
        for rule in sorted(rules, key=lambda x: x.rule_id):
            if rule in disabled_rules:
                continue
            for api in sorted(rule.apis, key=lambda x: x.api_name):
                for final_action in sorted(rule.actions, key=lambda x: str(x)):
                    for target in sorted(rule.targets, key=lambda x: str(x)):
                        # skip incompatible target-api pairs
                        if not api.is_valid_target(target):
                            continue
                        # skip incompatible actions
                        if not api.is_valid_action(final_action):
                            continue
                        for target_path in target.get_paths():
                            path_template = PathTemplate(target_path, target)
                            applicable, _ = rule.is_applicable(api, final_action, path_template)
                            if not applicable:
                                continue
                            for ext in get_extensions_by_path(target_path.template):
                                for perm_setting in sorted(rule.permissions, key=lambda x: x.to_array()):
                                    # for external shared storage, we exclude saf-picker
                                    # because the attacker is expected to succeed with user interaction
                                    if target.storage == Storage.EXTERNAL_STORAGE and target.collection != Collection.APP_FOLDER:
                                        available_api = [api for api in rule.apis if
                                                         not api.api_name.startswith("saf-picker")]
                                    else:
                                        available_api = [api for api in rule.apis]
                                    payloads = [] + self.generate_payloads(available_api, target,
                                                                           self.max_payload_length)

                                    for payload in payloads:
                                        case = TestCase(rule, final_action, api, payload,
                                                        perm_setting, path_template, ext, self.seed)
                                        feature = str(case.get_feature())

                                        case_hash = case.get_case_hash()
                                        if case_hash not in duplicates:
                                            cases_for_rules[rule][len(case.payload)].append(case)
                                            duplicates[case.get_case_hash()] = case
                                            feature = str(case.get_feature())
                                            if case_hash not in prerequisite[feature]:
                                                if rule.rule_id.startswith("T"):
                                                    prerequisite[feature][case_hash] = case
        # if cases is not None, change to random sample mode because we just want to test a few things.
        if needed_cases is not None:
            sample_mode = SampleMode.RANDOM
        required_cases = self.sample_cases(cases_for_rules, prerequisite, self.max_cases,
                                           sample_mode, history)

        # add back the required cases
        if needed_cases is not None:
            needed = set()

            seen_cases = set()
            for c in required_cases:
                seen_cases.add(c.get_case_hash())

            if type(needed_cases) is str:
                needed.add(needed_cases)
            elif type(needed_cases) is list:
                needed = set(needed_cases)
            else:
                raise Exception("Invalid type for needed_cases")
            for r in cases_for_rules:
                for l in cases_for_rules[r]:
                    for c in cases_for_rules[r][l]:
                        if c.get_case_hash() in needed and c.get_case_hash() not in seen_cases:
                            required_cases.insert(0, c)
                            if type(needed_cases) is str:
                                break

        # IMPORTANT: we need to sort cases so that shorter cases are tested first
        # if A-B is confirmed to be an integrity violation, then
        # in that case, differential analysis would not work because root might also fail A-B-C would
        required_cases = sorted(required_cases, key=lambda x: (len(x.payload), x.get_case_hash()))

        logger.info(
            f"INPUT_GENERATOR: testing={len(required_cases)}/{len(duplicates)} ({len(required_cases) / (len(duplicates)) * 100:.1f}%)")
        case_hashes = [c.get_case_hash() for c in required_cases]
        exp_hash = hashlib.sha256(''.join(case_hashes).encode()).hexdigest()[:10]
        logger.info("Experiment Hash: {}".format(exp_hash))

        # check if File Squatting is in test cases:
        # just to evaluate the performance of the tool
        squatting_found = False
        rename_found = False
        meta_leak = False
        exif_all_access = False
        exif_normal = False
        exif_fail = False
        false_negatives = False
        download_leak = False
        known_violations = 0

        for case in required_cases:
            if full_history.get(case.get_case_hash(), {}).get("score", 0) > 0:
                known_violations += 1
            if case.rule.rule_type == RuleType.Confidentiality:
                if case.rule.rule_id == "C3" and case.api.api_name.startswith(
                        "file") and case.final_action == OperationType.READ:
                    if case.perm_setting.is_granted(AppPermission.MANAGE_EXTERNAL_STORAGE):
                        if not exif_all_access:
                            logger.success(
                                f"INPUT_GENERATOR: Exif leak (AFA) case is added -> {case.get_case_hash()} -> {case.payload}")
                        exif_all_access = True
                    else:
                        if not exif_normal:
                            logger.success(
                                f"INPUT_GENERATOR: Exif leak case is added -> {case.get_case_hash()} -> {case.payload}")
                        exif_normal = True
                elif case.rule.rule_id == "C2":
                    if case.api.api_name.startswith("file"):
                        if case.final_action == OperationType.CREATE:
                            if not meta_leak:
                                logger.success(
                                    f"INPUT_GENERATOR: Metadata leak case is added  -> {case.get_case_hash()} -> {case.payload}")
                            meta_leak = True
                        if case.path_template.target_path.template.startswith("/sdcard/Download") \
                                and case.final_action == OperationType.READ \
                                and case.perm_setting.is_granted(AppPermission.MANAGE_EXTERNAL_STORAGE):
                            if not download_leak:
                                logger.success(
                                    f"INPUT_GENERATOR: Download leak case is added -> {case.get_case_hash()} -> {case.payload}")
                            download_leak = True
                elif case.rule.rule_id == "C1" and case.api.api_name.startswith("file"):
                    if ("('SETUP', FILE), (DELETE_FILE, SAF-PICKER" in str(case.payload)
                            or "('SETUP', FILE), (RENAME_FILE, SAF-PICKER" in str(case.payload)
                            or "('SETUP', FILE), (MOVE_FILE, SAF-PICKER" in str(case.payload)):
                        if not false_negatives:
                            logger.success(
                                f"INPUT_GENERATOR: False Negative case is added -> {case.get_case_hash()} -> {case.payload}")
                        false_negatives = True

            if case.rule.rule_type == RuleType.Availability:
                if case.final_action == OperationType.READ:
                    if case.api.api_name.startswith("saf-picker") \
                            and case.path_template.target_path.template.startswith("/sdcard/Pictures"):
                        if not exif_fail:
                            logger.success("INPUT_GENERATOR: Exif fail case is added -> " + case.get_case_hash())
                        exif_fail = True
                if case.final_action == OperationType.CREATE:
                    if case.api.api_name.startswith("file") \
                            and not case.path_template.target_path.template.startswith("/data/data") \
                            and not case.path_template.target_path.template.startswith("/sdcard/Android/data/") \
                            and "CREATE" in str(case.get_payload_printable(case.payload)):
                        if not squatting_found:
                            logger.success("INPUT_GENERATOR: File Squatting case is added -> " + case.get_case_hash())
                        squatting_found = True
                    elif case.api.api_name.startswith("saf") \
                            and "CREATE" in str(case.get_payload_printable(case.payload)):
                        if not rename_found:
                            logger.success(
                                "INPUT_GENERATOR: Rename inconsistency case is added -> " + case.get_case_hash())
                        rename_found = True

        if not exif_all_access:
            logger.warning("INPUT_GENERATOR: SAF loophole (AFA) case is not found in the test cases.")
        if not exif_normal:
            logger.warning("INPUT_GENERATOR: SAF loophole case is not found in the test cases.")
        if not squatting_found:
            logger.warning("INPUT_GENERATOR: File Squatting case is not found in the test cases.")
        if not rename_found:
            logger.warning("INPUT_GENERATOR: Rename inconsistency case is not found in the test cases.")
        if not exif_fail:
            logger.warning("INPUT_GENERATOR: Exif fail case is not found in the test cases.")
        if not meta_leak:
            logger.warning("INPUT_GENERATOR: Metadata leak case is not found in the test cases.")
        if not false_negatives:
            logger.warning("INPUT_GENERATOR: False Negative case is not found in the test cases.")
        if not download_leak:
            logger.warning("INPUT_GENERATOR: Download leak case is not found in the test cases.")
        if known_violations > 0:
            logger.success(
                f"INPUT_GENERATOR: {known_violations}/{len(required_cases)} known violations are included in the test cases.")
        if self.debug_ensure_coverage:
            assert all([exif_all_access, exif_normal, exif_fail, squatting_found,
                        rename_found, meta_leak, download_leak, false_negatives]), \
                "Critical cases are missing in the test cases."

        # if no root, skipping internal storage
        if not has_root:
            filtered_cases = []
            skipped_cases = set()
            for case in required_cases:
                target = case.path_template.target
                if target.storage == Storage.INTERNAL_STORAGE:
                    skipped_cases.add(case.get_case_hash())
                    continue
                filtered_cases.append(case)
            if skipped_cases:
                logger.warning(
                    f"Skipping {len(skipped_cases)} internal storage cases as root is not available: {skipped_cases}")
            required_cases = filtered_cases

        return required_cases, prerequisite, exp_hash
