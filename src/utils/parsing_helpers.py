import os
from datetime import datetime
import glob
from src.utils.quickparser import Quickparser
from multiprocessing import cpu_count
from concurrent.futures import ThreadPoolExecutor
import time

class ParsingError(Exception):
    def __init__(self, message=""):
        super().__init__(message)

# Get a set of file paths from a folder path
def get_set_of_files(folder_path, exts: tuple):
    filepaths = set()
    for ext in exts:
        filepaths.update(
            glob.glob(
                os.path.join(
                    folder_path, 
                    f"*{ext}"
                )
            )
        )
    return filepaths or None

# Update the progress bar
def update_progress_bar(step, total_steps, window=None):
    progress = step / total_steps * 100
    if window is not None:
        window.update_progressbar(progress)

# Find a keyword in a file
def __find_keyword_in_file(
        file_name,
        possible_devs,
        file_dev_dict,
        discovered_keywords,
        ref_bool
):
    with open(file_name, 'r', encoding='utf-8-sig') as f:
        keyword = Quickparser.discover(f.read(), possible_devs) # Find keyword
    if ref_bool and not keyword:
        print(possible_devs)
        raise ParsingError( # Error if no keyword found in reference file
            f"No keyword found in reference file: {file_name}. "
            "Validate a keyword is in present in the text file and pattern file."
        )
    if ref_bool and (keyword in discovered_keywords): 
        raise ParsingError( # Error if duplicate reference keywords
            f"Duplicate reference file for keyword found: {keyword}"
        )
    discovered_keywords.add(keyword) # Prevent rediscovery
    file_dev_dict[file_name] = keyword # Update dict with findings

# Map a dictionary as {filename: keyword}
def get_file_keyword_dict(
        filepaths,
        possible_devs,
        ref_bool=False
):
    file_dev_dict = {} # Updates with file: keyword
    discovered_keywords = set() # Track already discovered keywords
    with ThreadPoolExecutor(max_workers=cpu_count() * 2) as executor:
        futures = []
        for file_name in filepaths:
            futures.append(
                executor.submit(
                    __find_keyword_in_file,
                    file_name,
                    possible_devs,
                    file_dev_dict,
                    discovered_keywords,
                    ref_bool
                )
            )
        for future in futures:
            future.result() # Wait for threads to finish
    return file_dev_dict, discovered_keywords

# Instantiate parsers for any discovered keywords into a dict
def get_parser_objects(pattern_file, keywords):
    parser_objects = {
        keyword: Quickparser(keyword, pattern_file) for keyword in keywords
    }
    return parser_objects

# Parse single file
def parse_file(file_path, parser, collapse_bool, ref_bool, keyword):
    basename = os.path.basename(file_path)
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        parsed_dict = parser.parse(f.read(), collapse_bool)
        if parsed_dict:
            if ref_bool: # Error if any ref values are NOT FOUND
                if any(val == "NOT FOUND" for val in parsed_dict.values()):
                    raise ParsingError(
                        f"Failed to parse reference file: {basename}. " +
                        "Regex failed to parse."
                    )
            parsed_dict[str(keyword)] = parser.keyword # Add keyword to dict
            return { # Healthy return of a parsed dict
                str(parser.keyword): {basename: parsed_dict}
             }
        elif ref_bool: # Error if ref fails to parse anything
            raise ParsingError(
                f"Failed to parse reference file: {basename}. " +
                "Reference File returned nothing."
            )

# Parse multiple files
def parse_files(file_dev_dict, parsers, keyword, ref_bool=False, collapse_bool=False):
    master_dict = {} # Dict to hold {keyword: {file: parsed_dict}} pairs

    # Helper function for processing
    def __process_file(file_path, keyword, file_keyword, master_dict):
        # Get the parser object that corresponds to the file's found keyword
        if file_keyword and (parser := parsers.get(file_keyword)):
            result = parse_file(file_path, parser, collapse_bool, ref_bool, keyword)
        elif not ref_bool:
            # Keyword is None if keyword not found for target files
            result = {None: os.path.basename(file_path)}

        # Update master dictionary
        for file_keyword, files in result.items():
            if file_keyword:
                # Add keyword to parsed_dict
                master_dict.update(files)
            else: # Keyword key for None type keywords
                master_dict.setdefault(f"{keyword} Not Found", []).append(files)
        
    with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
        futures = []
        for file_path, file_keyword in file_dev_dict.items():
            futures.append(
                executor.submit(
                    __process_file, 
                    file_path, 
                    keyword,
                    file_keyword,
                    master_dict
                )
            )

        for future in futures:
            future.result()
    
    # Final dictionary
    return master_dict

# Compare a dict against another and return a matches/deviations dict
def __compare_dict(ref_dict, targ_dict):
    matches, mismatches = Quickparser.compare(ref_dict, targ_dict)
    return matches, mismatches

# Function to build a dictionary of matches/deviations between folders
def compare_dicts(master_ref_dict, master_targ_dict, keyword):
    detail_dict = { # Final dictionary
        "Reference Folder": master_ref_dict,
        "Target Folder": {}
    }

    for filename, targ_dict in master_targ_dict.items():
        if isinstance(targ_dict, dict):
            targ_keyword = targ_dict.get(keyword, f"{keyword} Not Found")
            if targ_keyword != f"{keyword} Not Found":
                # Get ref_dict for the equivalent keyword type of target
                for filepath, dictionary in master_ref_dict.items():
                    if dictionary.get(keyword) == targ_keyword:
                        # Remove keyword for comparison
                        targ_dict.pop(keyword)
                        ref_dict = master_ref_dict.get(filepath)
                        ref_dict.pop(keyword)
                        # Compare
                        matches, mismatches = __compare_dict(
                            ref_dict, 
                            targ_dict
                        )
                        # Add back keywords
                        targ_dict[keyword] = targ_keyword
                        ref_dict[keyword] = targ_keyword

                if not 'matches' in locals() and not 'mismatches' in locals():
                    raise ParsingError(f"No valid reference file found for target keyword: {targ_keyword}")

                # Get basename
                basename = os.path.basename(filename)
                # Update detail_dict with results
                detail_dict["Target Folder"].setdefault(basename, {})
                detail_dict["Target Folder"][basename]["Matches"]= matches
                detail_dict["Target Folder"][basename]["Deviations"] = mismatches
                # Add back keyword
                detail_dict["Target Folder"][basename][keyword] = targ_keyword

                # Reset matches/mismatches
                del matches; del mismatches
            else:
                detail_dict["Target Folder"].setdefault(f"{keyword} Not Found", [])
                detail_dict["Target Folder"][f"{keyword} Not Found"].append(targ_dict.get(keyword))


    return detail_dict

# Build the final dictionaries and strings
def build_report(
    detail_dict,
    found_keywords,
    counted_files,
    target_folder,
    num_files_without_keywords,
    start_time,
    keyword,
    num_deviations=None,
    reference_folder=None,
):
    date = datetime.now().strftime(r'%I:%M %p - %B %d, %Y').lstrip("0")
    brief_dict = {
        "Completion Date": date,
        f"{keyword}(s) Found": found_keywords,
        f"Files Where {keyword} Not Found": num_files_without_keywords,
        "Folder (Reference)": reference_folder,
        "Folder (Target)": target_folder,
        "Total Deviations": num_deviations,
        "Total Files Found": counted_files,
        "Total Time": f"{(time.perf_counter() - start_time):.3f} seconds",
        "Verdict": ( # Evaluate Fail or Pass
            "FAIL" if (
                num_deviations or 
                num_files_without_keywords
                )
            else "PASS"
        ) if reference_folder else None # Only evaluate verdict if comparing
    }

    # Release Falsy values
    brief_dict = Quickparser.collapse(brief_dict)
    detail_dict = Quickparser.collapse(detail_dict)

    # Stringify dictionaries
    brief_string = Quickparser.stringify(brief_dict, 'yaml')
    detail_string = Quickparser.stringify(detail_dict, 'yaml')
    
    final_string = (
    "-" * 100 + "\nDetailed Report:\n\n" + detail_string + "\n" +
    "-" * 100 + "\nBrief Report:\n\n" + brief_string
)

    return final_string