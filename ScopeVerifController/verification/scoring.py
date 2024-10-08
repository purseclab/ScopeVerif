from typing import List


class StorageFuzzingScore:
    def __init__(self, failed_rules: List = None):
        if failed_rules is None:
            self.__failed_rules = []
        else:
            self.__failed_rules = failed_rules

    def get_priority_score(self, payload, failed_rules: List):
        self.__failed_rules = failed_rules
        return round(self.__count_total_violated_attributes() - len(payload) * 0.9, 2)  # a weak attack will be given one more chance

    def get_strength_score(self, failed_rules: List):
        self.__failed_rules = failed_rules
        return self.__count_total_violated_attributes()

    def get_useless_operations(self, payload, failed_rules: List):
        self.__failed_rules = failed_rules
        return self.__count_useless_operations(payload)

    def __count_max_violated_attributes(self):
        max_count = 0
        for rule, detail in self.__failed_rules:
            max_count = max(max_count, detail["diff_attr_count"])
        return max_count

    def __count_useless_operations(self, payload):
        attempted = len(payload) + 1
        useless_action = attempted - self.__count_total_violated_attributes()
        return useless_action

    def __count_violated_rules(self):
        return len(self.__failed_rules)

    def __count_total_violated_attributes(self):
        total_count = 0
        for rule, detail in self.__failed_rules:
            total_count += detail["diff_attr_count"]
        return total_count
