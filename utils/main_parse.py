import os
from datetime import datetime
import logging
import glob
from .quickparser import Quickparser
from .misc_classes import ParsingError

# Validate the reference folder is valid
def validate_reference_folder(folder_path):
    logging.debug('Validating Reference Folder')
    valid_pattern = any(file.endswith(".yaml") for file in os.listdir(folder_path))
    valid_logs = any(file.endswith((".log", ".txt")) for file in os.listdir(folder_path))

    if not (valid_logs and valid_pattern):
        missing = []
        if not valid_pattern: missing.append("pattern file (.yaml)")
        if not valid_logs: missing.append("log files (.log, .txt)")
        return f"Reference Folder is not valid: missing {' and '.join(missing)}."

# Get a list of file paths from a folder path
def get_set_of_files(folder_path, exts: tuple):
    filepaths = set()
    for ext in exts:
        filepaths.update(glob.glob(os.path.join(folder_path, f"*{ext}")))
    return filepaths or None

def update_progress_bar(window, step, total_steps):
    progress = step / total_steps * 100
    window.update_progressbar(progress)

# Build the final dictionaries and strings
def build_report(detail_dict, files_without_devices, found_devices, scanned_files, counted_files, target_folder, reference_folder=None):
    logging.debug('Serializing data...')
    detail_dict = Quickparser.collapse(detail_dict)
    brief_dict = {
        "Completion Date": datetime.now().strftime(r'%I:%M %p - %B %d, %Y').lstrip("0"),
        "Devices Found": list(found_devices),
        "Devices Not Found": list(files_without_devices),
        "Folder (Reference)": (reference_folder or None), # Optional
        "Folder (Scanned)": target_folder,
        "Total Deviations": len(Quickparser.leafify(detail_dict.get("Scanned Folder", {}).get("Deviations", {}))),
        "Total Files Scanned": scanned_files,
        "Total Files Found": counted_files,
        "Verdict": ("FAIL" if (detail_dict.get("Scanned Folder", {}).get("Deviations") or files_without_devices or (scanned_files != counted_files)) else "PASS")
    }
    brief_dict = Quickparser.collapse(brief_dict)
    detail_string = Quickparser.serialize(detail_dict, 'yaml')
    brief_string = Quickparser.serialize(brief_dict, 'yaml')
    final_string = "Detailed Report:\n\n" + detail_string + "\n" + ("-"* 100) + "\n\nBrief Report:\n\n" + brief_string + "\n" + ("-"* 100)
    return final_string

# Main function for parsing
def main_parse(reference_folder_path, target_folder_path, window):
    logging.debug('Working...')

    # Validate the reference folder and handle errors
    if error_message := validate_reference_folder(reference_folder_path):
        raise ParsingError(error_message)

    # Get list of file paths
    if not (target_filepaths := get_set_of_files(target_folder_path, ('.txt', '.log'))):
        raise ParsingError("No files in the target folder can be parsed.") # Cancel if no parsable files in the target folder
    reference_filepaths = get_set_of_files(reference_folder_path, ('.txt', '.log'))
    
    # Get the total steps of the progress bar
    total_steps = len(target_filepaths) + len(reference_filepaths)
    
    # Get other variables
    files_without_devices = {os.path.basename(file) for file in target_filepaths} # As files are parsed, they get removed from here
    step_counter, scanned_files, found_devices, counted_files = 0, 0, set(), len(target_filepaths)
    detail_dict = {"Reference Folder": {}, "Scanned Folder": {"Matches": {}, "Deviations": {}}}

    # Find the pattern file
    pattern_file, = get_set_of_files(reference_folder_path, ('.yaml'))
    if not pattern_file: # Cancel if pattern file is None
        raise ParsingError(f"No pattern file found in Reference Folder: {reference_folder_path}")
    logging.info(f'Discovered Pattern File: {os.path.basename(pattern_file)}')
    
    # Iterate through reference files
    for reference_file in reference_filepaths:
        
        # Initialize reference file basename and contents
        reference_file_name = os.path.basename(reference_file)
        with open(reference_file, 'r') as file:
            reference_file_contents = file.read()
        
        # Find the device type and OS of the reference file
        if not (device_type := Quickparser.discover(reference_file_contents, pattern_file)): # Cancel if device discover returns None
            raise ParsingError(f"No device discovered within reference file: {reference_file_name}. Validate the pattern file's regex.")
        logging.info(f"Discovered '{device_type}' in referenece file: {reference_file_name}")

        # Create a parser object subject to the device contained in the pattern file
        parser = Quickparser(device_type, pattern_file, log=True)

        # Parse the Reference File
        logging.debug(f"Parsing Reference File: {reference_file_name}")
        if not (parsed_reference_dict := parser.parse(reference_file_contents, collapse=False)): # Check if the parsing returned an empty dict
            raise ParsingError(f"Failed to parse reference file: {reference_file_name}. Reference File returned nothing.")
        for key, val in parsed_reference_dict.items():  # Error if a specific variable failed to parse
            if val == "NOT FOUND":
                raise ParsingError(f"Failed to parse reference file: {reference_file_name} variable: ({key})")
            
        # Update Progress Bar
        step_counter += 1
        update_progress_bar(window, step_counter, total_steps)

        # Update detailed dict with the parsed reference file
        if not (device_check := detail_dict["Reference Folder"].get(device_type)): # Check if the device has already been found
            detail_dict["Reference Folder"][device_type] = {reference_file_name: parsed_reference_dict} # Add ref file to dict if device not already found
        else: # Error since duplicate files for the same device
            duplicate_file, = device_check.keys() # Get dupe file name
            raise ParsingError(f"Two files for the same device found:\n{reference_file}\n{duplicate_file}")
        
        # Begin parsing target files against the ref file
        for filepath in target_filepaths.copy():  # Iterate over a shallow copy
            base_file = os.path.basename(filepath)
            with open(filepath) as file:
                file_contents = file.read()

            if device_type in file_contents:
                files_without_devices.discard(base_file)
                found_devices.add(device_type)

                # Parse the target file against the reference file
                logging.debug(f'Parsing File: {base_file}')
                parsed_file_dict = parser.parse(file_contents)
                matches, mismatches = Quickparser.compare(parsed_reference_dict, parsed_file_dict)

                # Ensure the device_type dictionaries exist
                detail_dict["Scanned Folder"]["Matches"].setdefault(device_type, {})
                detail_dict["Scanned Folder"]["Deviations"].setdefault(device_type, {})
                
                # Update the device_type dictionaries with new data
                detail_dict["Scanned Folder"]["Matches"][device_type][base_file] = matches
                detail_dict["Scanned Folder"]["Deviations"][device_type][base_file] = mismatches

                target_filepaths.remove(filepath)  # Modify original list
                scanned_files += 1

                # Update Progress Bar
                step_counter += 1
                update_progress_bar(window, step_counter, total_steps)

    final_string = build_report(
        detail_dict,
        files_without_devices,
        found_devices,
        scanned_files,
        counted_files,
        target_folder_path,
        reference_folder_path
    )

    # Update Progress Bar
    update_progress_bar(window, 100, 100)

    # Display final_string
    print("Finished")
    print("\n" + "-" * 100 + "\n")
    print(final_string)

