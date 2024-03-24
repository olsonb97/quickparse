import os
import argparse
from datetime import datetime
from resources.parse_utils import QuickParser

new_pattern_file = r"""
# Define devices (name must appear in the log) and variables:
#
# DeviceName:  # Use device name from logs
#   variableName: 'regexPattern'  # Use one () group in regex
#
# For multiple regex patterns per variable:
#   variableName:
#     - 'pattern1'  # One () group
#     - 'pattern2'  # One () group

---
C1100TGX:
    Version: 'Cisco IOS XE Software, Version (.*)'
C9200L:
    Version: 
    - 'Cisco IOS XE Software, Version (.*)'
    - 'Cisco IOS XE Software Version (.*)'
C93180:
    Version: 'NXOS:\s+version (.*)'
C9336:
    Version: 'NXOS:\s+version (.*)'
N8560:
    Version: 'Software version\s+: (.*)'
FS S3900:
    Version: '(Version\s+\S+\s+Build\s+\d+)'
S5850:
    Version: 'S5850,\s+Version\s+(.*)'
PA-3260:
    Version: 'sw-version:\s+(.*)'
...
"""

# Validate the reference folder is valid
def validate_reference_folder(folder_path):
    valid_pattern = False
    valid_logs = False
    for file in os.listdir(folder_path):
        if str(file).endswith(".yaml"):
            valid_pattern = True
        elif str(file).endswith(".log") or file.endswith(".txt"):
            valid_logs = True

    if valid_logs and valid_pattern:
        return True

    if not valid_logs and not valid_pattern:
        error_message = "both pattern file (.yaml) and log files (.log, .txt)"
    elif not valid_logs:
        error_message = "log files (.log, .txt)"
    elif not valid_pattern:
        error_message = "pattern file (.yaml)"
    return f"Reference Folder is not valid: missing {error_message}."

# Progress bar
def update_progress(current, total, bar_length=20):
    fraction = current / total
    filled_length = int(bar_length * fraction)
    bar = "#" * filled_length + "-" * (bar_length - filled_length)
    print(f"\r[{bar}] ", end="")
    if fraction == 1:
        print()

# Main function for parsing
def main_parse(reference_folder_path, folder_path, log_choice=False):

    error_message = validate_reference_folder(reference_folder_path)
    if error_message != True:
        print(error_message)
        return
    
    print("\nWorking...")

    # Get list of file paths
    filepaths = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, file)) and (file.endswith('.log') or file.endswith('.txt'))]
    num_files_to_scan = len(filepaths)
    files_without_devices = filepaths.copy()

    total_loading_steps = num_files_to_scan + sum(1 for file in os.listdir(reference_folder_path) if file.endswith(".txt") or file.endswith(".log"))
    
    # Get other variables
    total_completed_steps = 0
    scanned_files = 0
    errors = []
    found_devices = set()
    detail_dict = {
        "Reference Folder": {},
        "Scanned Folder": {
            "Matches": {},
            "Deviations": {}
        }
    }

    # Cancel if no parsable files in the parse folder
    if not filepaths:
        print("Cancelled: No files in the selected folder can be parsed.")
        return
    
    # Find the pattern file
    pattern_file = None
    for file in os.listdir(reference_folder_path):
        if str(file).endswith(".yaml"):
            pattern_file = os.path.join(reference_folder_path, file)
    if not pattern_file:
        print(f"No pattern file found in Reference Folder: {reference_folder_path}")
        return
    
    # Iterate through reference files
    for reference_file in os.listdir(reference_folder_path):

        # Verify the reference file
        if not reference_file.endswith(".yaml") and not reference_file.endswith(".txt") and reference_file.endswith(".log"):
            print("Reference Folder not valid. Please make sure the Reference Folder only has logs and a pattern file.")
            return
        
        # Initialize reference variables for reference file
        reference_file_path = os.path.join(reference_folder_path, reference_file)
        reference_file_name = os.path.basename(reference_file_path)
        with open(reference_file_path, 'r') as file:
            reference_file_string = file.read()

        # Cancel if reference file is not valid
        if not reference_file_path.endswith('.txt') and not reference_file_path.endswith('.log'):
            continue
        
        # Find the device type and OS of the reference file
        device_type = QuickParser.discover(reference_file_string, pattern_file)
        if not device_type:
            print(f"No device discovered within reference file: {reference_file_name}. Validate the pattern file's regex.")
            return
        
        # Create a parser object for the device
        parser = QuickParser(device_type, pattern_file, log_bool=log_choice)

        # Parse the Reference File
        parser.log('debug', f"Parsing Reference File: {reference_file_name}")
        parsed_reference_dict = parser.parse(reference_file_string, collapse=False)

        # Update Progress Bar
        if log_choice:
            total_completed_steps += 1
            update_progress(total_completed_steps, total_loading_steps)

        # Handle any issues
        if not parsed_reference_dict:
            print(f"Failed to parse reference file: {reference_file_name}. Reference File returned no matches.")
            return
        for key, val in parsed_reference_dict.items(): # Error if reference fails to parse
            if val == "NOT FOUND":
                errors.append(f"Failed to parse reference file: {reference_file_name} variable: ({key})")

        # Update detailed dict
        ref_already_exists = detail_dict["Reference Folder"].get(device_type)
        if not ref_already_exists:
            detail_dict["Reference Folder"][device_type] = {reference_file_name: parsed_reference_dict}
        else: # Check if duplicate files exist
            dupe_file = list(ref_already_exists.keys())[0] # Get dupe file name
            print(f"Duplicate reference files for the same device found:\n{reference_file}\n{dupe_file}")
            return

        # Find files that have same device as the reference file
        for filepath in filepaths.copy(): # Copy so that we can simultaneously iterate and remove elements
            base_file = os.path.basename(filepath)
            with open(filepath, 'r') as file:
                file_string = file.read()
            if device_type in file_string:
                # Device is found, so remove it from the "Device Not Found" list
                if filepath in files_without_devices:
                    files_without_devices.remove(filepath)
                found_devices.add(device_type)
                parser.log('debug', f'Parsing File: {base_file}')
                parsed_file_dict = parser.parse(file_string)
                matches, mismatches = QuickParser.compare(parsed_reference_dict, parsed_file_dict) # Compare the two
                detail_dict["Scanned Folder"]["Matches"].update({base_file: matches})
                detail_dict["Scanned Folder"]["Deviations"].update({base_file: mismatches})
                filepaths.remove(filepath) # Remove from original list to shorten future operations
                scanned_files += 1

                # Update Progress Bar
                if log_choice:
                    total_completed_steps += 1
                    update_progress(total_completed_steps, total_loading_steps)
    
    # Add devices not found to the errors list
    if files_without_devices:
        for file in files_without_devices:
            errors.append(f"Device Not Found: {os.path.basename(file)}")

    # Build the final dictionaries and strings
    detail_dict = QuickParser.collapse(detail_dict)
    brief_dict = {
        "Completion Date": datetime.now().strftime(r'%I:%M %p - %B %d, %Y').lstrip("0"),
        "Errors": errors,
        "Folder (Reference)": reference_folder_path,
        "Folder (Scanned)": folder_path,
        "Found Devices": list(found_devices),
        "Total Errors": len(errors),
        "Total Deviations": len(QuickParser.leafify(detail_dict.get("Scanned Folder", {}).get("Deviations", {}))),
        "Total Files Scanned": scanned_files,
        "Total Files Found": num_files_to_scan,
        "Verdict": ("FAIL" if (detail_dict.get("Scanned Folder", {}).get("Deviations") or errors or (scanned_files != num_files_to_scan)) else "PASS")
    }
    brief_dict = QuickParser.collapse(brief_dict)
    detail_string = QuickParser.serialize(detail_dict, 'yaml')
    brief_string = QuickParser.serialize(brief_dict, 'yaml')
    final_string = "Detailed Report:\n\n" + detail_string + "\n" + ("-"* 100) + "\n\nBrief Report:\n\n" + brief_string + "\n" + ("-"* 100)

    # Print final_string
    print("Finished")
    print("\n" + "-" * 100 + "\n")
    print(final_string)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse log files and compare against reference files.")
    parser.add_argument("reference_folder", help="Path to the reference folder containing pattern file and reference logs")
    parser.add_argument("target_folder", help="Path to the folder containing files to be scanned and parsed")
    parser.add_argument("-l", "--log", action="store_true", help="Include logging details")
    args = parser.parse_args()

    main_parse(os.path.abspath(args.reference_folder), os.path.abspath(args.target_folder), args.log)