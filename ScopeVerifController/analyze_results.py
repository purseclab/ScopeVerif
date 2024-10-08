import os
import re
import shutil
from collections import defaultdict
import json
import pandas as pd


def categorize(k, rule_id, api, detail, raw_path, case, prerequisites):
    typ = detail["type"]
    payload = detail["payload"]
    final_action = detail["final_action"]
    setup_index = -1
    for i, item in enumerate(payload):
        if "SETUP" in str(item):
            setup_index = i
            break

    if typ == "AVAILABILITY":
        root_feedback = detail['root_feedback'].get("root-observation", detail['root_feedback'])
        app_feedback = detail['app_feedback'].get("root-observation", detail['app_feedback'])

        # File API vulnerable to squatting attack: attacker create file before SETUP
        if api == "FILE" \
                and not root_feedback["target"].startswith("/sdcard/Android/data/") \
                and any([item.startswith("CREATE") or item.startswith("OVERWRITE") for item in payload]):
            print(f"Case {k} is vulnerable to Squatting Attack ({raw_path}) -> availability")
            return 'Squatting attack to File API'

        # any file created using File API cannot work with MediaStore,
        # However, SAF works perfectly with MediaStore
        if "SETUP,File" in case and api.startswith("MEDIA-STORE"):
            print(f"Case {k} is not available due to media-store vs file -> Availability ({raw_path})")
            return 'MediaStore vs File'

        # SAF cannot read EXIF in Android 12, it also cannot move file while keeping EXIF
        if "media_location" in detail['diff_elements']:
            if "READ(SAF-PICKER" in case or ("MOVE(SAF-PICKER" in case and len(detail['diff_elements']) == 2):
                print(f"Case {k} is vulnerable to Exif fail using SAF ({raw_path})")
                return 'Exif fail'

        # Auto-rename inconsistency
        suffix1 = root_feedback['target'].split(" ")[-1]
        suffix2 = app_feedback['target'].split(" ")[-1]
        prefix1 = '/'.join(root_feedback['target'].split("/")[:-1])
        prefix2 = '/'.join(app_feedback['target'].split("/")[:-1])

        if setup_index > -1 \
                and detail['diff_elements'] == ["target"] \
                and re.search("[a-z]{3} \([0-9]+\)", root_feedback['target'] + app_feedback['target']) \
                and suffix1 != suffix2 \
                and prefix1 == prefix2:
            print(f"Case {k} is vulnerable to Auto-rename inconsistency ({raw_path})")
            return 'Auto-rename inconsistency'

        # Android 14 may ban apps to access their own app-specific directory using SAF for "privacy" protection
        if final_action.split("_")[1].startswith("SAF-PICKER") \
                and root_feedback["target"].startswith("/sdcard/Android/data/"):
            # the file could be already edited by another bug
            # if any(["T1" in a for s, a in prerequisites.values() if s > 0]):
            #     return "Require manual analysis"
            if final_action.split("_")[0] not in ["MOVE"]:
                for s, a in prerequisites.values():
                    if s == 0:
                        continue
                    pre_rule_id = a[1:3]
                    pre_final_action = a.split(" ")[1].split("(")[0]
                    if not pre_rule_id.startswith("T"):
                        continue
                    actual_action = final_action.split("_")[0]
                    if pre_final_action in ["DELETE", "MOVE", "RENAME"]:
                        actual_action = pre_final_action
                    elif pre_final_action in ["CREATE", "OVERWRITE"] and actual_action not in ["MOVE", "DELETE", "RENAME"]:
                        actual_action = pre_final_action
                    if actual_action not in ["MOVE", "CREATE", "OVERWRITE", "DELETE", "RENAME"]:
                        actual_action = 'OTHER'
                    return f"SAF loophole violates Integrity ({actual_action})"
            print(f"Case {k} is restricted to access their own files using SAF -> Availability ({raw_path})")
            if final_action.split("_")[0] == "CREATE":
                return 'SAF restriction (CREATE)'
            else:
                return 'SAF restriction (OTHERS)'

        # # SAF in payload breaks availability.
        # if setup_index > -1 \
        #         and any(re.search("(DELETE|MOVE|OVERWRITE|RENAME),SafPicker", item) for item in
        #                 payload[setup_index:]):
        #     print(f"Case {k} is vulnerable to SAF Loophole (payload) -> Availability ({raw_path})")
        #     actual_action = final_action.split("_")[0]
        #     if actual_action not in ["CREATE", "DELETE"]:
        #         actual_action = 'OTHER'
        #     return f'SAF loophole violates Availability ({actual_action})'
        if rule_id == "A2":
            return "Shared storage fail"
    elif typ == "INTEGRITY":
        # Media edit ( undocumented design feature )
        if rule_id == "T1" \
                and "sdcard/Download/" in json.dumps(detail["file_after_modify"]) \
                and "appops set --uid com.abc.storage_verifier_gamma MANAGE_EXTERNAL_STORAGE allow" in detail[
            'reproduce']:
            print(f"Case {k} is vulnerable to Media edit -> Integrity ({raw_path})")
            if api == "FILE":
                return 'Media edit by FILE api (all file access)'
            elif "MEDIA-STORE" in api:
                return 'Media edit by MEDIA-STORE api (all file access)'

        # SAF in final action breaks integrity.
        actual_action = final_action.split("_")[0]
        for s, a in prerequisites.values():
            if s == 0:
                continue
            pre_rule_id = a[1:3]
            pre_final_action = a.split(" ")[1].split("(")[0]
            pre_api = a.split("(")[1].split(")")[0]
            if rule_id == pre_rule_id and "SAF-PICKER" in pre_api:
                # the file is already moved by another bug
                if pre_final_action in ["DELETE", "MOVE", "RENAME"]:
                    actual_action = pre_final_action
                elif pre_final_action in ["CREATE", "OVERWRITE"] and actual_action not in ["MOVE", "DELETE", "RENAME"]:
                        actual_action = pre_final_action
                break


        if actual_action not in ["MOVE", "CREATE", "OVERWRITE", "DELETE", "RENAME"]:
            actual_action = 'OTHER'

        return f"SAF loophole violates Integrity ({actual_action})"
    elif typ == "CONFIDENTIALITY":
        # SAF reads violates confidentiality.
        if api.startswith("SAF-PICKER"):
            if rule_id == "C3":
                print(f"Case {k} is vulnerable to Exif leak using SAF ({raw_path})")
                return 'Exif violation (saf picker)'
            if "sdcard/Android/data" in json.dumps(detail["result_on_exist_file"]):
                print(f"Case {k} is vulnerable to SAF Loophole (final action) -> Confidentiality ({raw_path})")
                actual_action = final_action.split("_")[0]
                if actual_action not in ["MOVE", "CREATE", "OVERWRITE", "DELETE"]:
                    actual_action = 'OTHER'
                return f'SAF loophole violates Confidentiality ({actual_action})'
        # if api.startswith("FILE"):
        #     create_index = -1
        #     setup_index = -1
        #     for i, item in enumerate(payload):
        #         if "CREATE" in item or "OVERWRITE" in item:
        #             create_index = i
        #         elif "SETUP" in item:
        #             setup_index = i
        #     if -1 < create_index < setup_index and setup_index > -1:
        #         print(f"Case {k} is vulnerable to Squatting Attack ({raw_path}) -> confidentiality")
        #         return "Squatting attack to File API (confidentiality)"
        # Meta leak
        if ("EACCES (Permission denied)" in json.dumps(detail) or sorted(detail['diff_elements']) in [["edit_path"],
                                                                                                      sorted([
                                                                                                          "edit_path",
                                                                                                          "success"])]) \
                and (api.startswith("FILE") or api.startswith("MEDIA-STORE")):
            print(f"Case {k} is vulnerable to Meta leak ({raw_path})")
            if "sdcard/Download/" in json.dumps(detail["result_on_exist_file"]):
                return 'Meta leak on shared storage'
            elif "sdcard/Android/data" in json.dumps(detail["result_on_exist_file"]):
                return 'Meta leak on app-specific storage'

        # Exif violation using SAF ( undocumented design feature )
        if rule_id == "C3" \
                and "media_location" in json.dumps(detail["result_on_exist_file"]) \
                and "media_location" not in json.dumps(detail["result_on_non_exist_file"]):
            if api.startswith("SAF-PICKER"):
                print(f"Case {k} is vulnerable to Exif leak using SAF ({raw_path})")
                return 'Exif violation (saf picker)'
            elif detail["permission"]["android.permission.MANAGE_EXTERNAL_STORAGE"]:
                print(f"Case {k} is vulnerable to Exif leak using AFA ({raw_path})")
                return 'Exif violation (all file access)'
            else:
                print(f"Case {k} is vulnerable to Exif leak using OTHER ({raw_path})")
                return 'Exif violation (other)'

        # Download access and edition ( undocumented design feature )
        if rule_id == "C2" \
                and "sdcard/Download/" in json.dumps(detail["result_on_exist_file"]) \
                and "sdcard/Download/" in json.dumps(detail["result_on_non_exist_file"]) \
                and api.startswith("FILE") \
                and "appops set --uid com.abc.storage_verifier_gamma MANAGE_EXTERNAL_STORAGE allow" in detail[
            'reproduce']:
            print(f"Case {k} is vulnerable to Download violation -> Confidentiality ({raw_path})")
            return 'Download leak (all file access)'
    return None


def analyze_json(raw_path):
    use_raw_cluster = "clusters" in raw_path
    raw = json.loads(open(raw_path, "r", encoding="utf-8").read())
    report_path = os.path.join(os.path.dirname(os.path.dirname(raw_path)),
                               f"reports/{os.path.basename(raw_path).replace('.json', '.csv')}")
    if use_raw_cluster:
        rows = list(raw['cases'].values())[0]["all_clusters"] + [
            # "Require manual analysis",
            "Unknown violation types",
            "Total violations",
            "Total tests"]
    else:
        rows = ['Squatting attack to File API',
                # 'SAF loophole violates Availability (CREATE)',
                # 'SAF loophole violates Availability (DELETE)',
                # 'SAF loophole violates Availability (OTHER)',
                'SAF loophole violates Integrity (MOVE)',
                'SAF loophole violates Integrity (CREATE)',
                'SAF loophole violates Integrity (OVERWRITE)',
                'SAF loophole violates Integrity (DELETE)',
                'SAF loophole violates Integrity (RENAME)',
                'SAF loophole violates Confidentiality (MOVE)',
                'SAF loophole violates Confidentiality (CREATE)',
                'SAF loophole violates Confidentiality (OVERWRITE)',
                'SAF loophole violates Confidentiality (DELETE)',
                'SAF loophole violates Confidentiality (OTHER)',
                "SAF restriction (CREATE)",
                "SAF restriction (OTHERS)",
                "Auto-rename inconsistency",
                'Meta leak on shared storage',
                'Meta leak on app-specific storage',
                "Exif violation (all file access)",
                "Exif violation (saf picker)",
                "Exif violation (other)",
                "Exif fail",
                "Shared storage fail",
                "MediaStore vs File",
                "Download leak (all file access)",
                "Media edit by FILE api (all file access)",
                "Media edit by MEDIA-STORE api (all file access)",
                # "Require manual analysis",
                "Unknown violation types",
                "Total violations",
                "Total tests"]
    cases = raw["cases"]
    report = pd.DataFrame(columns=["violation types", "counts"])
    report["violation types"] = rows
    report["counts"] = [0] * len(rows)
    report.index = rows

    filtered_cases = {}
    analyzed_cases = {}
    report.loc['Total tests', 'counts'] = len(cases)

    unknown_failing_detail = defaultdict(int)
    for k, v in cases.items():
        detail = v['detail']
        rule_id = v['case'][1:3]
        case = v['case']
        prerequisites = v.get('prerequisites', {})

        if v["score"] > 0:
            new_score = 0
            api = v["case"].split("(")[1].split(")")[0]
            report.loc['Total violations', 'counts'] += 1

            if use_raw_cluster:
                violation_type = v['cluster']
            else:
                violation_type = categorize(k, rule_id, api, detail, raw_path, case, prerequisites)

            anayzed_v = v.copy()
            anayzed_v["violation_type"] = violation_type
            analyzed_cases[k] = anayzed_v
            if violation_type is not None:
                report.loc[violation_type, "counts"] += 1
                continue
            report.loc['Unknown violation types', "counts"] += 1
            new_score += detail['diff_attr_count']
            unknown_failing_detail[rule_id] += 1
            if new_score == 0:
                continue
            new_v = {
                "score": new_score,
                "case": v["case"],
                "detail": detail
            }
            filtered_cases[k] = new_v
    new_info = raw["info"]
    new_info["failing_detail"] = {items[0]: items[1] for items in
                                  sorted(new_info["failing_detail"].items(), key=lambda x: x[0])}
    new_info["unknown_failing_detail"] = {items[0]: items[1] for items in
                                          sorted(unknown_failing_detail.items(), key=lambda x: x[0])}
    new_info["unknown_cases"] = len(filtered_cases)
    new_info["unknown_rate"] = f"{len(filtered_cases) / len(cases) * 100:.2f}%"

    # Rows to be sorted
    rows_to_sort = rows[:-3]
    rows_not_to_sort = rows[-3:]

    # Sorting the rows to be sorted

    sorted_subset = report.loc[rows_to_sort].sort_values(by="violation types", ascending=False)

    # Extracting the rows not to be sorted
    unsorted_subset = report.loc[rows_not_to_sort]

    # Concatenating back together
    sorted_report = pd.concat([sorted_subset, unsorted_subset])

    # write report
    sorted_report.to_csv(report_path, index=False)

    # categories
    categories = defaultdict(list)
    for k, each in analyzed_cases.items():
        if each["violation_type"] is not None:
            categories[each["violation_type"]].append(k)
        else:
            categories["unknown"].append(k)
    # sort items in categories
    categories = {k: sorted(v) for k, v in categories.items()}

    return {
        "info": new_info,
        "unknown_cases": filtered_cases
    }, {
        "info": raw["info"],
        "analyzed_cases": analyzed_cases
    }, categories


for parent in os.scandir("./"):
    if not parent.name.startswith("results"):
        continue
    for d in os.scandir(parent.path):
        if os.path.isdir(d.path) and os.path.isdir(os.path.join(d.path, "finished")):
            filtered_path = os.path.join(d.path, "filtered")
            reports_path = os.path.join(d.path, "reports")
            analyzed_path = os.path.join(d.path, "analyzed")
            categorized_path = os.path.join(d.path, "categorized")
            if os.path.isdir(filtered_path):
                shutil.rmtree(filtered_path)
            if os.path.isdir(reports_path):
                shutil.rmtree(reports_path)
            if os.path.isdir(analyzed_path):
                shutil.rmtree(analyzed_path)
            if os.path.isdir(categorized_path):
                shutil.rmtree(categorized_path)
            os.mkdir(filtered_path)
            os.mkdir(reports_path)
            os.mkdir(analyzed_path)
            os.mkdir(categorized_path)
            for f in os.scandir(os.path.join(d.path, "finished")):
                if os.path.isfile(f.path) and f.name.endswith(".json"):
                    print("analyze " + f.path)
                    filtered_file_path = os.path.join(filtered_path, f.name)
                    analyzed_file_path = os.path.join(analyzed_path, f.name)
                    categorized_file_path = os.path.join(categorized_path, f.name)
                    cluster_file_path = os.path.join(d.path, "clusters", f.name)
                    if os.path.isfile(cluster_file_path):
                        filtered_json, analyzed_json, categorized_json = analyze_json(cluster_file_path)
                    else:
                        filtered_json, analyzed_json, categorized_json = analyze_json(f.path)
                    if filtered_json:
                        with open(filtered_file_path, "w") as f:
                            f.write(json.dumps(filtered_json, indent=4))
                    if analyzed_json:
                        with open(analyzed_file_path, "w") as f:
                            f.write(json.dumps(analyzed_json, indent=4))
                    if categorized_json:
                        with open(categorized_file_path, "w") as f:
                            f.write(json.dumps(categorized_json, indent=4))
