import os
from datetime import datetime
import logging
import glob
from .quickparser import Quickparser
from .misc_classes import ParsingError
import multiprocessing
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor
import re
import time

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

# Update the progress bar
def update_progress_bar(window, step, total_steps):
    progress = step / total_steps * 100
    window.update_progressbar(progress)

# Find a device in a file
def find_device_in_file(file_name, pattern, files_devices, discovered_devices, reference):
    with open(file_name, 'r') as f:
        device = Quickparser.discover(f.read(), pattern)
    if reference and not device:
        raise ParsingError(f"No device found in reference file: {file_name}")
    if reference and (device in discovered_devices):
        raise ParsingError(f"Duplicate reference file for device found: {device}")
    discovered_devices.add(device)
    files_devices[file_name] = device

# Map devices to filenames
def get_files_devices_dict(filepaths, pattern, reference=False):
    files_devices = {}
    discovered_devices = set()
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count() * 2) as executor:
        futures = []
        for file_name in filepaths:
            futures.append(executor.submit(find_device_in_file, file_name, pattern, files_devices, discovered_devices, reference))
        for future in futures:
            future.result()
    return files_devices, discovered_devices

# Instantiate parsers for any discovered devices
def get_parser_objects(pattern_file, devices):
    parser_objects = {device: Quickparser(device, pattern_file) for device in devices}
    return parser_objects

# Parse single file
def parse_file(file_path, parser, collapse, reference):
    basename = os.path.basename(file_path)
    with open(file_path) as f:
        parsed_dict = parser.parse(f.read(), collapse)
        if parsed_dict:
            if reference and any(val == "NOT FOUND" for val in parsed_dict.values()):
                raise ParsingError(f"Failed to parse reference file: {basename}. Regex failed to parse.")
            return {str(parser.device): {basename: parsed_dict}}
        elif reference:
            raise ParsingError(f"Failed to parse reference file: {basename}. Reference File returned nothing.")

# Parse multiple files
def parse_files(device_files, parsers, reference=False, collapse=False):
    parsed_files = {}
    def process_file(file_path, device):
        if device and (parser := parsers.get(device)):
            result = parse_file(file_path, parser, collapse, reference)
            return result
        elif not reference:
            return {"Device Not Found": {os.path.basename(file_path): "Device Not Found"}}
        
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = [executor.submit(process_file, fp, dev) for fp, dev in device_files.items()]
        for future in futures:
            result = future.result()
            if result:
                for device, files in result.items():
                    parsed_files.setdefault(device, {}).update(files)
    return parsed_files

# Function to compare a single ref_dict to a targ_dict for matches or deviations
def compare_dict(ref_dict, targ_dict, filename, device):
    basename = os.path.basename(filename)
    # Check if ref_dict is not empty before accessing the first element
    if ref_dict:
        ref_value = list(ref_dict.values())[0]
        matches, mismatches = Quickparser.compare(ref_value, targ_dict)
    else:
        matches, mismatches = {}, {}
    return device, basename, matches, mismatches, 'Matches', 'Deviations'

def compare_dicts(ref_files_dict, targ_files_dict):
    detail_dict = {"Reference Folder": ref_files_dict, "Scanned Folder": {"Matches": {}, "Deviations": {}, "Device Not Found": {}}}
    
    for device, files in targ_files_dict.items():
        if device != "Device Not Found":
            for filename, targ_dict in files.items():
                ref_dict = ref_files_dict.get(device, {})
                device, basename, matches, mismatches, match_key, deviation_key = compare_dict(ref_dict, targ_dict, filename, device)
                
                # Update detail_dict with results
                detail_dict["Scanned Folder"][match_key].setdefault(device, {})
                detail_dict["Scanned Folder"][deviation_key].setdefault(device, {})
                detail_dict["Scanned Folder"][match_key][device][basename] = matches
                detail_dict["Scanned Folder"][deviation_key][device][basename] = mismatches
        else:
            detail_dict["Scanned Folder"]["Device Not Found"].update(files)

    return detail_dict

# Build the final dictionaries and strings
def build_report(detail_dict, found_devices, scanned_files, counted_files, num_deviations, target_folder, reference_folder, files_without_devices, start_time):
    detail_dict = Quickparser.collapse(detail_dict)
    errors = {
        "Files Where Device Not Found": files_without_devices
    }
    errors = Quickparser.collapse(errors)
    brief_dict = {
        "Completion Date": datetime.now().strftime(r'%I:%M %p - %B %d, %Y').lstrip("0"),
        "Devices Found": found_devices,
        "Errors": errors,
        "Folder (Reference)": reference_folder,
        "Folder (Scanned)": target_folder,
        "Total Deviations": num_deviations,
        "Total Files Scanned": scanned_files,
        "Total Files Found": counted_files,
        "Total Time": f"{(time.perf_counter() - start_time):.3f} seconds",
        "Verdict": ("FAIL" if (num_deviations or errors or (scanned_files != counted_files)) else "PASS")
    }
    brief_dict = Quickparser.collapse(brief_dict)
    detail_string = Quickparser.serialize(detail_dict, 'yaml')
    brief_string = Quickparser.serialize(brief_dict, 'yaml')
    final_string = "\n" + "-" * 100 + "\n\nDetailed Report:\n\n" + detail_string + "\n" + ("-"* 100) + "\n\nBrief Report:\n\n" + brief_string + "\n" + ("-"* 100)
    return final_string

# Main function for parsing
def main_parse(reference_folder_path, target_folder_path, window):
    logging.debug('Working...')
    start_time = time.perf_counter()

    # Validate the reference folder and handle errors
    if error_message := validate_reference_folder(reference_folder_path):
        raise ParsingError(error_message)

    # Get list of file paths
    if not (target_filepaths := get_set_of_files(target_folder_path, ('.txt', '.log'))):
        raise ParsingError("No files in the target folder can be parsed.") # Cancel if no parsable files in the target folder
    reference_filepaths = get_set_of_files(reference_folder_path, ('.txt', '.log'))
    
    # Get the total steps of the progress bar
    total_steps = 7

    # Find the pattern file
    if not (pattern_file := glob.glob(os.path.join(reference_folder_path, "*.yaml"))[0]): # Cancel if pattern file is None
        raise ParsingError(f"No pattern file found in Reference Folder: {reference_folder_path}")
    logging.debug(f'Discovered Pattern File: {os.path.basename(pattern_file)}')
    if not (pattern_dict := Quickparser.load(pattern_file, 'yaml')):
        raise ParsingError(f"Failed to load pattern file: {pattern_file}")
    devices_pattern = re.compile('|'.join(re.escape(device) for device in pattern_dict))

    # Create dictionaries in the form of filepath: device
    logging.debug('Discovering')
    reference_files_devices, ref_devices = get_files_devices_dict(reference_filepaths, devices_pattern, reference=True)
    logging.debug(f'Discovered devices from reference files: {", ".join(set(reference_files_devices.values()))}')
    update_progress_bar(window, 1, total_steps)
    target_files_devices, targ_devices = get_files_devices_dict(target_filepaths, devices_pattern)
    logging.debug(f'Discovered devices from target files: {", ".join(set(str(device) for device in target_files_devices.values()))}')
    update_progress_bar(window, 2, total_steps)

    # Create parsers for each device discovered in dictionaries of device: parser
    logging.debug('Creating parser objects...')
    parsers = get_parser_objects(pattern_file, ref_devices)

    # Create dictionaries in the form of {device: {filename: parsed_dict}}
    logging.debug('Parsing Reference Files...')
    parsed_reference_dict = parse_files(reference_files_devices, parsers, reference=True, collapse=False)
    update_progress_bar(window, 3, total_steps)
    logging.debug('Parsing Target Files...')
    parsed_target_dict = parse_files(target_files_devices, parsers, reference=False, collapse=False)
    update_progress_bar(window, 4, total_steps)

    # Compare the reference and target into a combined dictionary
    logging.debug('Building Data Structure...')
    final_dict = compare_dicts(parsed_reference_dict, parsed_target_dict)
    update_progress_bar(window, 5, total_steps)

    # Final touches
    logging.debug('Cleaning Data Structure...')
    final_dict = Quickparser.collapse(final_dict)
    update_progress_bar(window, 6, total_steps)
    targ_devices.discard(None)
    devices = list(targ_devices)
    files_without_devices = len(final_dict.get("Scanned Folder", {}).get("Device Not Found", {}))
    counted_files = len(target_filepaths)
    scanned_files = sum(len(filenames) for filenames in parsed_target_dict.values())
    num_deviations = len(Quickparser.leafify(final_dict.get("Scanned Folder", {}).get("Deviations", {})))

    # Build the Brief Report
    logging.debug('Building Report...')
    report = build_report(final_dict, devices, scanned_files, counted_files, num_deviations, target_folder_path, reference_folder_path, files_without_devices, start_time)
    update_progress_bar(window, 7, total_steps)
    logging.debug('Finished')
    print(report)