import os
from datetime import datetime
import logging
import glob
from .quickparser import Quickparser
from .misc_classes import ParsingError
import multiprocessing
from multiprocessing import Pool
from threading import Thread, Semaphore

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

def find_device_in_file(semaphore, file_name, pattern_file, device_files):
    with semaphore:
        with open(file_name, 'r') as f:
            device = Quickparser.discover(f.read(), pattern_file)
            device_files[file_name] = device

def get_files_devices_dict(filepaths, pattern_file):
    files_devices = {}
    semaphore = Semaphore(multiprocessing.cpu_count()*2)
    threads = set()
    for file_name in filepaths:
        thread = Thread(target=find_device_in_file, args=(semaphore, file_name, pattern_file, files_devices))
        threads.add(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return files_devices

def get_parser_objects(pattern_file, *args):
    devices = set()
    for arg in args:
        devices.update(set(arg.values()))
    parser_objects = {device: Quickparser(device, pattern_file) for device in devices}
    return parser_objects

def parse_file(semaphore, file_path, parser, collapse, parsed_files):
    with semaphore:
        if parser:
            with open(file_path, 'r') as f:
                basename = os.path.basename(file_path)
                if (parsed_dict := parser.parse(f.read(), collapse)):
                    parsed_files.setdefault(str(parser.device), {})
                    parsed_files[str(parser.device)].update({basename: parsed_dict})

def parse_files(device_files, parsers, reference=False):
    parsed_files = {}
    semaphore = Semaphore(multiprocessing.cpu_count()*2)
    threads = set()
    for file_path, device in device_files.items():
        if not device and reference:
            raise ParsingError(f"No device discovered within reference file: {os.path.basename(file_path)}. Validate the pattern file's regex.")
        elif not device and not reference:
            basename = os.path.basename(file_path)
            parsed_files.setdefault("Device Not Found", {})
            parsed_files["Device Not Found"].update({basename: "Not Found"})
            continue
        thread = Thread(target=parse_file, args=(semaphore, file_path, parsers.get(device), False, parsed_files))
        threads.add(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return parsed_files

def compare_dict(ref_dict, targ_dict, filename, device):
    basename = os.path.basename(filename)
    matches, mismatches = Quickparser.compare(list(ref_dict.values())[0], targ_dict)
    return device, basename, matches, mismatches, 'Matches', 'Deviations'

def compare_dicts(ref_files_dict, targ_files_dict):
    detail_dict = {"Reference Folder": ref_files_dict, "Scanned Folder": {"Matches": {}, "Deviations": {}, "Device Not Found": {}}}
    
    args_list = []
    for device, files in targ_files_dict.items():
        if device != "Device Not Found":
            for filename, targ_dict in files.items():
                args_list.append((ref_files_dict.get(device, {}), targ_dict, filename, device))
        else:
            detail_dict["Scanned Folder"]["Device Not Found"].update(files)
    
    # Replace threading with multiprocessing.Pool
    with Pool(processes=multiprocessing.cpu_count()) as pool:
        results = pool.starmap(compare_dict, args_list)
    
    # Apply changes to detail_dict
    for device, basename, matches, mismatches, match_key, deviation_key in results:
        detail_dict["Scanned Folder"][match_key].setdefault(device, {})
        detail_dict["Scanned Folder"][deviation_key].setdefault(device, {})
        detail_dict["Scanned Folder"][match_key][device][basename] = matches
        detail_dict["Scanned Folder"][deviation_key][device][basename] = mismatches

    return detail_dict

# Build the final dictionaries and strings
def build_report(detail_dict, files_without_devices, found_devices, scanned_files, counted_files, target_folder, reference_folder=None):
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

    # Find the pattern file
    if not (pattern_file := glob.glob(os.path.join(reference_folder_path, "*.yaml"))[0]): # Cancel if pattern file is None
        raise ParsingError(f"No pattern file found in Reference Folder: {reference_folder_path}")
    logging.debug(f'Discovered Pattern File: {os.path.basename(pattern_file)}')

    # Create dictionaries in the form of filepath: device
    reference_files_devices = get_files_devices_dict(reference_filepaths, pattern_file)
    logging.debug(f'Discovered devices from reference files: {", ".join(set(reference_files_devices.values()))}')
    target_files_devices = get_files_devices_dict(target_filepaths, pattern_file)
    logging.debug(f'Discovered devices from target files: {", ".join(set(str(device) for device in target_files_devices.values()))}')

    # Create parsers for each device discovered in dictionaries of device: parser
    logging.debug('Creating parser objects...')
    parsers = get_parser_objects(pattern_file, reference_files_devices, target_files_devices)

    # Create dictionaries in the form of {device: {filename: parsed_dict}}
    logging.debug('Parsing Reference Files...')
    parsed_reference_dict = parse_files(reference_files_devices, parsers, reference=True)
    logging.debug('Parsing Target Files...')
    parsed_target_dict = parse_files(target_files_devices, parsers, reference=False)

    # Compare the reference and target into a combined dictionary
    logging.debug('Building Data Structure...')
    final_dict = compare_dicts(parsed_reference_dict, parsed_target_dict)
    logging.debug('Cleaning Data Structure...')
    final_dict = Quickparser.collapse(final_dict)
    logging.debug('Finished')
    print(Quickparser.serialize(final_dict, 'yaml'))