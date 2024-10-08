import datetime
import json
import matplotlib.pyplot as plt
from collections import OrderedDict, defaultdict
from loguru import logger
import shutil
import time
from enums.app_role import ApkRole
from enums.sample_mode_enum import SampleMode
from libs.utilities import ServerSideException
from verification.scoring import StorageFuzzingScore
import os

# change working directory to the root of the project
os.chdir("../")


class StorageVerifier:
    def __init__(self, verified_feature_name, system_version, input_generator, oracle, scoring: StorageFuzzingScore,
                 rules=None,
                 disabled_rules=None,
                 sample_mode=SampleMode.RANDOM,
                 reuse_results=False):

        self.launch_time = None
        if rules is None:
            rules = set()
        if disabled_rules is None:
            disabled_rules = set()
        self.sample_mode = sample_mode
        self.reuse_results = reuse_results
        self.system_version = system_version
        logger.add(f"logs/{verified_feature_name}-{datetime.datetime.today().strftime('%Y-%m-%d')}.log",
                   rotation="10 MB")
        self.rules = set(rules)
        self.disabled_rules = set(disabled_rules)
        self.verified_feature_name = verified_feature_name
        self.input_generator = input_generator
        self.oracle = oracle
        self.scoring = scoring
        # set up the results' directory paths
        self.results_dir_path = f"results/{self.verified_feature_name}"
        self.finished_dir_path = f"{self.results_dir_path}/finished"
        prefix = ""
        if self.sample_mode == SampleMode.EXTENSIVE:
            prefix = "ext_"
        elif self.sample_mode == SampleMode.EXPLORATORY:
            prefix = "exp_"
        elif self.sample_mode == SampleMode.POLARIZED:
            prefix = "pol_"

        self.testing_file_path = f"{self.results_dir_path}/{prefix}{verified_feature_name}_testing.json"
        # initialize the results directory
        for path in [self.results_dir_path, self.finished_dir_path]:
            if not os.path.isdir(path):
                os.makedirs(path)

    def add_rule(self, rule):
        self.rules.add(rule)

    def disable_rule(self, rule):
        self.disabled_rules.add(rule)

    def load_progress(self):
        state = {}
        if os.path.isfile(self.testing_file_path):
            state = json.loads(open(self.testing_file_path, "r", encoding="utf-8").read())
            logger.info("Loaded progress from file.")
            if state["info"]["total_cases"] == state["info"]["tested_cases"] and state['info']['total_cases'] > 0:
                self.save_progress(state)
                exit()
        if not state:
            state = {
                "info": {
                    "total_cases": 0,
                    "tested_cases": 0,
                    "failed_cases": 0,
                    "fail_rate": "0.0%",
                    "progress": "0.0%",
                    "max_score": 0
                },
                "cases": {},
            }
            logger.info("Initialized progress.")
        return state

    def plot_curve(self, violation_curve):
        # show violation curve
        X = list(range(10, len(violation_curve)+1))
        Y = [violation_curve[i]/X[i] for i in range(len(X))]
        logger.info("Plotting violation ratio: "+str(Y))
        if len(X) > 1:
            plt.figure(figsize=(10, 5))
            plt.plot(X, Y, marker='o')
            plt.title('Violation Curve')
            plt.xlabel('Index')
            plt.ylabel('Ratio (violation_curve / Index)')
            plt.grid(True)
            plt.show()

    def save_progress(self, state, est_left=None):
        if not os.path.isdir(self.results_dir_path):
            os.makedirs(self.results_dir_path)

        # calculate applied rules and failing detail
        applied_rules = defaultdict(int)
        failing_detail = defaultdict(int)
        for case_hash in state['cases']:
            rule_id = state['cases'][case_hash]['case'][1:3]
            applied_rules[rule_id] += 1
            if state['cases'][case_hash]["score"] > 0:
                failing_detail[rule_id] += 1

        state["info"]["tested_cases"] = len(state['cases'])
        state["info"]["applied_rules"] = applied_rules
        state["info"]["failing_detail"] = failing_detail

        if est_left and est_left > 0:
            state["info"]["est_time_left"] = self.get_time_str(est_left)
        elif "est_time_left" in state["info"]:
            del state["info"]["est_time_left"]

        state["info"]["failed_cases"] = len(
            [case for case in state["cases"] if state["cases"][case]['score'] > 0])
        state["info"]["progress"] = f"{state['info']['tested_cases'] / state['info']['total_cases'] * 100:.2f}%"
        state["info"]["fail_rate"] = f"{state['info']['failed_cases'] / state['info']['tested_cases'] * 100:.2f}%"
        state["info"]["max_score"] = max([state["cases"][case]['score'] for case in state["cases"]])
        cases = OrderedDict(sorted(state["cases"].items(), key=lambda x: x[1]["score"], reverse=True))
        save = {
            "info": state["info"],
            "cases": cases,
        }
        open(self.testing_file_path + "_bak", "w").write(json.dumps(save, indent=4))
        shutil.move(self.testing_file_path + "_bak", self.testing_file_path)
        logger.info(f"Saved progress to {self.testing_file_path}.")

        prefix = ""
        if self.sample_mode == SampleMode.EXTENSIVE:
            prefix = "ext_"
        elif self.sample_mode == SampleMode.EXPLORATORY:
            prefix = "exp_"
        elif self.sample_mode == SampleMode.POLARIZED:
            prefix = "pol_"

        if len(save['cases']) >= state["info"]["total_cases"] and state['info']['total_cases'] > 0:
            logger.info("All cases have been tested, save the progress.")
            finish_path = f"{self.finished_dir_path}/{prefix}{self.verified_feature_name}_{datetime.datetime.today().strftime('%Y-%m-%d')}.json"
            # if finish_path exists, rename it sequentially to avoid overwriting
            if os.path.isfile(finish_path):
                i = 1
                while True:
                    finish_path = f"{self.finished_dir_path}/{prefix}{self.verified_feature_name}_{datetime.datetime.today().strftime('%Y-%m-%d')}_{i}.json"
                    if not os.path.isfile(finish_path):
                        break
                    i += 1
                    if i > 100:
                        logger.error("Too many files with the same name, exiting.")
                        exit()
            shutil.move(self.testing_file_path, finish_path)
            exit()
        return state

    def reset_all_apps(self):
        # reset all apps
        for app_role in ApkRole:
            if app_role == ApkRole.ACCESSIBILITY_SERVICE and self.oracle.ui_handler is not None:
                continue
            pname = app_role.value
            apk_path = self.oracle.apk_path_getter(app_role)
            logger.info("resetting: " + pname)
            self.oracle.device_handler.remove_app(pname)
            time.sleep(0.3)
            self.oracle.device_handler.install_app(apk_path)
            time.sleep(0.3)

    def init_all(self):
        self.reset_all_apps()
        self.oracle.device_handler.keep_screen_on()
        if self.oracle.ui_handler is None:
            self.oracle.device_handler.refresh_accessibility()

    @classmethod
    def get_time_str(cls, seconds):
        m, s = divmod(seconds, 60)
        return f"{round(m)}:{round(s):02d}"

    def get_historical_results(self):
        historical_results = {}
        full_historical_results = {}
        # find all finished results
        for result in os.scandir(self.finished_dir_path):
            # for now, only consider "random" mode
            core_history = True
            if not result.name.startswith(self.verified_feature_name):
                core_history = False
            logger.info(f"Loading historical results from {result.path}.")
            existing_results_path = result.path
            with open(existing_results_path, "r") as f:
                existing_results = json.load(f)
                for case_hash, case_data in existing_results.get("cases", {}).items():
                    if case_hash not in full_historical_results:
                        full_historical_results[case_hash] = case_data
                    else:
                        # if score are different, we keep the one with higher score
                        if case_data["score"] > full_historical_results[case_hash]["score"]:
                            full_historical_results[case_hash] = case_data
                    if core_history:
                        if case_hash not in historical_results:
                            historical_results[case_hash] = case_data
                        else:
                            # if score are different, we keep the one with higher score
                            if case_data["score"] > historical_results[case_hash]["score"]:
                                historical_results[case_hash] = case_data
        return historical_results, full_historical_results

    def verify(self, case=None, stop_when_fail=False):
        results = self.load_progress()
        has_root = self.oracle.root_handler.has_root()

        history, full_history = self.get_historical_results()

        test_cases, prerequisite, exp_hash = self.input_generator.generate_testcases(has_root,
                                                                                     case,
                                                                                     self.rules,
                                                                                     self.disabled_rules,
                                                                                     self.sample_mode,
                                                                                     history, full_history)

        results["info"]["total_cases"] = len(test_cases)
        results["info"]["experiment_hash"] = exp_hash

        # clean invalid results
        valid_cases = set([case.get_case_hash() for case in test_cases])
        cleaned = False
        for case_hash in list(results["cases"].keys()):
            if case_hash not in valid_cases:
                results["cases"].pop(case_hash)
                cleaned = True
        if cleaned and results['cases']:
            logger.info("Cleaned invalid results, save progress.")
            self.save_progress(results)

        tested_cases_count = 0
        finished_cases_count = 0
        violation_curve = []
        # plotting the violation ratio
        total_violation = 0
        for i, test_case in enumerate(test_cases):
            case_hash = test_case.get_case_hash()
            if type(case) is str and case_hash != case:
                continue
            if type(case) is list and case_hash not in case:
                continue
            if case_hash in results["cases"]:
                if int(results["cases"][case_hash]["score"]) > 0:
                    total_violation += 1
                finished_cases_count += 1
                violation_curve.append(total_violation)
                logger.error(f"Case {case_hash} has been tested, skip.")
                continue
            if self.reuse_results and case_hash in full_history:
                results["cases"][case_hash] = full_history[case_hash]
                if int(results["cases"][case_hash]["score"]) > 0:
                    total_violation += 1
                finished_cases_count += 1
                violation_curve.append(total_violation)
                logger.error(f"Case {case_hash} has been tested, skip.")
                continue
            if finished_cases_count >= results['info']['total_cases']:
                logger.info(f"finished cases count: {finished_cases_count}, total cases: {results['info']['total_cases']}.")
                self.save_progress(results)
                return
            if self.launch_time is None:
                self.init_all()
                self.launch_time = time.time()

            logger.info(
                f"Testing case {case_hash} with rule {test_case.rule.rule_id} on " + \
                f"{test_case.path_template.target_path.template} with {test_case.ext} " + \
                f"and {test_case.perm_setting.to_array()}.")
            required_cases = prerequisite.get(test_case.get_feature(True), {})
            logger.info(f"Prerequisite: {list(required_cases.keys())}")
            for each in required_cases:
                if each not in results["cases"]:
                    logger.error(f"Prerequisite {each} not met, terminate.")
                    exit()
            start_time = time.time()
            try:
                passed, detail = test_case.check(self.oracle, i, len(test_cases), self.system_version, stop_when_fail)
            except ServerSideException as e:
                logger.error("Server side error, terminate.")
                exit()
            end_time = time.time()
            tested_cases_count += 1
            finished_cases_count += 1

            if not passed:
                logger.debug(json.dumps(detail, indent=4))
                total_violation += 1
            violation_curve.append(total_violation)

            score = self.scoring.get_strength_score([(test_case.rule.rule_id, detail)])

            spent = end_time - start_time
            all_time_spent = end_time - self.launch_time
            avg_spent = all_time_spent / tested_cases_count
            case_left = len(test_cases) - len(results["cases"].values()) - 1
            all_used_min, all_used_sec = divmod(all_time_spent, 60)
            est_left = avg_spent * case_left
            est_left_str = self.get_time_str(avg_spent * case_left)

            previous_results = {}
            for k in required_cases:
                previous_case = results["cases"][k]
                previous_results[k] = (previous_case["score"], previous_case["case"])
            results["cases"][case_hash] = {
                "score": score,
                "prerequisites": previous_results,
                "case": test_case.get_printable(),
                "time_spent": spent,
                "detail": detail
            }
            logger.info(f"Case {case_hash} finished with score {score}.")
            logger.success(
                f"Case {case_hash} finished! Score: {score}, Spent: {spent:.1f}s (avg. {avg_spent:.1f}s), Total spent: {round(all_used_min)}:{round(all_used_sec):02d}, Est. Left: {est_left_str}")
            results = self.save_progress(results, est_left)

        self.plot_curve(violation_curve)

        if tested_cases_count == 0:
            logger.error("No case to test.")
            return
        else:
            self.save_progress(results)