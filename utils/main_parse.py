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

# Update the progress bar
def update_progress_bar(window, step, total_steps):
    progress = step / total_steps * 100
    window.update_progressbar(progress)

# Find a device in a file
def find_device_in_file(semaphore, file_name, pattern_file, files_devices, reference):
    with semaphore:
        with open(file_name, 'r') as f:
            device = Quickparser.discover(f.read(), pattern_file)
            if reference:
                for found_file, found_device in files_devices.items():
                    if found_device == device:
                        raise ParsingError(f"Two reference files for the same device found:\n{found_file}\n{os.path.basename(file_name)}")
            files_devices[file_name] = device

# Map devices to filenames
def get_files_devices_dict(filepaths, pattern_file, reference=False):
    files_devices = {}
    semaphore = Semaphore(multiprocessing.cpu_count()*2)
    threads = set()
    for file_name in filepaths:
        thread = Thread(target=find_device_in_file, args=(semaphore, file_name, pattern_file, files_devices, reference))
        threads.add(thread)
        thread.start()
    for thread in threads:
        thread.join()
    return files_devices

# Instantiate parsers for any discovered devices
def get_parser_objects(pattern_file, *args):
    devices = set()
    for arg in args:
        devices.update(set(arg.values()))
    parser_objects = {device: Quickparser(device, pattern_file) for device in devices}
    return parser_objects

# Parse a single file
def parse_file(semaphore, file_path, parser, collapse, parsed_files, reference):
    with semaphore:
        with open(file_path, 'r') as f:
            basename = os.path.basename(file_path)
            if (parsed_dict := parser.parse(f.read(), collapse)):
                if reference:
                    for key, val in parsed_dict.items():
                        if val == "NOT FOUND":
                            raise ParsingError(f"Failed to parse reference file: {basename} variable: ({key})")
                parsed_files.setdefault(str(parser.device), {})
                parsed_files[str(parser.device)].update({basename: parsed_dict})
            elif reference:
                raise ParsingError(f"Failed to parse reference file: {basename}. Reference File returned nothing.")

# Parse files in threads
def parse_files(device_files, parsers, reference=False, collapse=False):
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
        if (device_type := parsers.get(device)):
            thread = Thread(target=parse_file, args=(semaphore, file_path, device_type, collapse, parsed_files, reference))
            threads.add(thread)
            thread.start()
    for thread in threads:
        thread.join()
    return parsed_files

# Function to compare a single ref_dict to a targ_dict for matches or deviations
def compare_dict(ref_dict, targ_dict, filename, device):
    basename = os.path.basename(filename)
    matches, mismatches = Quickparser.compare(list(ref_dict.values())[0], targ_dict)
    return device, basename, matches, mismatches, 'Matches', 'Deviations'

# Function to process a batch of comparisons
def process_batch(batch):
    results = []
    for ref_dict, targ_dict, filename, device in batch:
        results.append(compare_dict(ref_dict, targ_dict, filename, device))
    return results

# Main function to compare dictionaries with batching and multiprocessing
def compare_dicts(ref_files_dict, targ_files_dict):
    detail_dict = {"Reference Folder": ref_files_dict, "Scanned Folder": {"Matches": {}, "Deviations": {}, "Device Not Found": {}}}
    
    args_list = []
    for device, files in targ_files_dict.items():
        if device != "Device Not Found":
            for filename, targ_dict in files.items():
                args_list.append((ref_files_dict.get(device, {}), targ_dict, filename, device))
        else:
            detail_dict["Scanned Folder"]["Device Not Found"].update(files)

    # Determine batch size based on the number of available CPU cores
    num_cores = multiprocessing.cpu_count()
    batch_size = max(1, len(args_list) // num_cores)

    # Create batches
    batches = [args_list[i:i + batch_size] for i in range(0, len(args_list), batch_size)]

    # Process batches in parallel
    with Pool(processes=num_cores) as pool:
        batch_results = pool.map(process_batch, batches)

    # Flatten the results from each batch
    results = [item for sublist in batch_results for item in sublist]

    # Update detail_dict with results from all batches
    for device, basename, matches, mismatches, match_key, deviation_key in results:
        detail_dict["Scanned Folder"][match_key].setdefault(device, {})
        detail_dict["Scanned Folder"][deviation_key].setdefault(device, {})
        detail_dict["Scanned Folder"][match_key][device][basename] = matches
        detail_dict["Scanned Folder"][deviation_key][device][basename] = mismatches

    return detail_dict

# Build the final dictionaries and strings
def build_report(detail_dict, files_without_devices, found_devices, scanned_files, counted_files, num_deviations, target_folder, reference_folder):
    detail_dict = Quickparser.collapse(detail_dict)
    brief_dict = {
        "Completion Date": datetime.now().strftime(r'%I:%M %p - %B %d, %Y').lstrip("0"),
        "Devices Found": found_devices,
        "Devices Not Found": files_without_devices,
        "Folder (Reference)": reference_folder,
        "Folder (Scanned)": target_folder,
        "Total Deviations": num_deviations,
        "Total Files Scanned": scanned_files,
        "Total Files Found": counted_files,
        "Verdict": ("FAIL" if (num_deviations or files_without_devices or (scanned_files != counted_files)) else "PASS")
    }
    brief_dict = Quickparser.collapse(brief_dict)
    detail_string = Quickparser.serialize(detail_dict, 'yaml')
    brief_string = Quickparser.serialize(brief_dict, 'yaml')
    final_string = "\n" + "-" * 100 + "\n\nDetailed Report:\n\n" + detail_string + "\n" + ("-"* 100) + "\n\nBrief Report:\n\n" + brief_string + "\n" + ("-"* 100)
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
    reference_files_devices = get_files_devices_dict(reference_filepaths, pattern_file, reference=True)
    logging.debug(f'Discovered devices from reference files: {", ".join(set(reference_files_devices.values()))}')
    target_files_devices = get_files_devices_dict(target_filepaths, pattern_file)
    logging.debug(f'Discovered devices from target files: {", ".join(set(str(device) for device in target_files_devices.values()))}')

    # Create parsers for each device discovered in dictionaries of device: parser
    logging.debug('Creating parser objects...')
    parsers = get_parser_objects(pattern_file, target_files_devices)

    # Create dictionaries in the form of {device: {filename: parsed_dict}}
    logging.debug('Parsing Reference Files...')
    parsed_reference_dict = parse_files(reference_files_devices, parsers, reference=True, collapse=False)
    logging.debug('Parsing Target Files...')
    parsed_target_dict = parse_files(target_files_devices, parsers, reference=False, collapse=True)

    # Compare the reference and target into a combined dictionary
    logging.debug('Building Data Structure...')
    final_dict = compare_dicts(parsed_reference_dict, parsed_target_dict)
    logging.debug('Cleaning Data Structure...')
    final_dict = Quickparser.collapse(final_dict)

    devices = list(parsers.keys())
    files_without_devices = list(final_dict.get("Scanned Folder", {}).get("Device Not Found", {}))
    counted_files = len(target_filepaths)
    scanned_files = sum(len(filenames) for filenames in parsed_target_dict.values())
    num_deviations = len(final_dict.get("Scanned Folder", {}).get("Deviations", {}))
    logging.debug('Building Report...')
    report = build_report(final_dict, files_without_devices, devices, scanned_files, counted_files, num_deviations, target_folder_path, reference_folder_path)
    logging.debug('Finished')
    print(report)