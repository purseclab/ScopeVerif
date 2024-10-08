# ScopeVerifController
This folder contains the source code for the Controller component of the ScopeVerif project, a tool designed to run on a PC and send commands to Android devices to conduct experiments, collect results, and analyze them.

- `libs`: This folder contains various utility modules that facilitate device interaction, UI control, and root access handling. It includes classes like `DeviceController`, `UIController`, and `RootHandler` to manage device operations and interactions programmatically.
- `verification`: This folder is responsible for the core verification logic of the application. It includes modules for generating inputs, scoring, and verifying storage rules, ensuring that the experiments adhere to the defined security and storage policies.
- `enums`: This folder defines various enumerations used throughout the application to categorize attributes, operation types, rule types, and storage APIs. These enums will be used for test case generation.

# ScopeVerifWorker
This folder contains worker apps that run on Android devices to perform the actual tasks. Three workers contain identical code, except for their package name. You should not need to modify anything in this folder unless you want to test new storage-related APIs that the current workers do not support.

# Quick Start
1. Ensure adb is in the PATH.
2. Turn on USB debugging on your Android devices. If you intend to test internal storage, root access is required.
3. Build the artifacts for each worker app using Android Studio to generate the APK files.
4. Go to `ScopeVerifController` and set up `personal_config.py`, so that the controller knows the path to the worker apps' APK files.
5. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```
6. Activate the virtual environment:
   - On Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - On macOS and Linux:
     ```bash
     source venv/bin/activate
     ```
7. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
8. Run `python run_experiment.py` to start the experiment and collect results.
9. Run `python analyze_results.py` to analyze the results, cluster violations, and generate reports.
