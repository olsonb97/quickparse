import logging
from src.utils.quickparser import Quickparser
from src.utils.parsing_helpers import *
import time

def single_parse(
    pattern_file,
    target_folder_path,
    window,
    keyword
):
    try:
        # Start a timer
        start_time = time.perf_counter()

        logging.debug('Working...')

        # Get the total steps of the progress bar
        total_steps = 5

        # Get list of target file paths
        target_filepaths = get_set_of_files(
            folder_path=target_folder_path,
            exts=('.txt', '.log')
        )
        if not target_filepaths:
            raise ParsingError('No files in the target folder can be parsed.')

        # Load the pattern file
        ext = pattern_file.split('.')[-1]
        if not (pattern_dict := Quickparser.load(pattern_file, ext)):
            raise ParsingError(f'Failed to load pattern file: {pattern_file}')
        possible_devs = [keyword for keyword in pattern_dict]

        # Create target dictionary in the form of filepath: keyword
        logging.debug('Discovering keywords...')
        targ_file_dev_dict, found_keywords = get_file_keyword_dict(
            filepaths = target_filepaths, 
            possible_devs = possible_devs,
            ref_bool = False
        )
        found_keywords.discard(None) # Discard None keywords (no keyword found)

        # Log what keywords have been discovered
        keywords_str = ', '.join(found_keywords)
        logging.debug(f'Discovered keywords from target files: {keywords_str}')
        update_progress_bar(1, total_steps, window)

        # Create parsers for each keyword discovered in pairs of keyword: parser
        logging.debug('Creating parser objects...')
        parsers = get_parser_objects(pattern_file, found_keywords)
        update_progress_bar(2, total_steps, window)

        # Create dictionary in the form of {keyword: {filename: parsed_dict}}
        logging.debug('Parsing Target Files...')
        parsed_target_dict = parse_files(
            file_dev_dict = targ_file_dev_dict, 
            parsers = parsers,
            keyword = keyword,
            ref_bool = False,
            collapse_bool = False,
        )
        update_progress_bar(3, total_steps, window)

        # Collapse the parsed dictionary
        logging.debug('Cleaning Data Structure...')
        parsed_target_dict = Quickparser.collapse(parsed_target_dict)
        update_progress_bar(4, total_steps, window)

        # Get variables ready for the brief report
        counted_files = len(target_filepaths)
        found_keywords = list(found_keywords)
        num_files_without_keywords = (
            len(parsed_target_dict.get(f'{keyword} Not Found', {}))
        )

        # Build the report
        logging.debug('Building Report...')
        report = build_report(
            detail_dict = parsed_target_dict,
            found_keywords = found_keywords,
            counted_files = counted_files,
            target_folder = target_folder_path,
            keyword = keyword,
            num_files_without_keywords = num_files_without_keywords,
            start_time = start_time,
        )
        update_progress_bar(5, total_steps, window)
        logging.debug('Finished')
        print(report)

        # Return results
        return parsed_target_dict
    
    except Exception as e:
        print(f'{type(e).__name__}: {str(e)}')
    finally:
        print('='*100)

def comparison_parse(
    pattern_file, 
    target_folder_path, 
    reference_folder_path, 
    window, 
    keyword
):
    try:
        # Start a timer
        start_time = time.perf_counter()

        logging.debug('Working...')

        # Get the total steps of the progress bar
        total_steps = 8

        # Get list of target file paths
        target_filepaths = get_set_of_files(
            folder_path=target_folder_path, 
            exts=('.txt', '.log')
        )
        if not target_filepaths:
            raise ParsingError('No files in the target folder can be parsed.')
        
        # Get list of reference file paths
        reference_filepaths = get_set_of_files(
            folder_path=reference_folder_path, 
            exts=('.txt', '.log')
        )
        if not reference_filepaths:
            raise ParsingError('No files in the reference folder can be parsed.')

        # Load the pattern file
        ext = pattern_file.split('.')[-1]
        if not (pattern_dict := Quickparser.load(pattern_file, ext)):
            raise ParsingError(f'Failed to load pattern file: {pattern_file}')
        possible_devs = [keyword for keyword in pattern_dict]

        # Create reference dictionary in the form of filepath: keyword
        logging.debug('Discovering...')
        ref_file_dev_dict, ref_keywords = get_file_keyword_dict(
            filepaths=reference_filepaths,
            possible_devs=possible_devs,
            ref_bool=True
        )
        ref_keywords.discard(None) # Discard None keywords (no keyword found)

        # Log reference keywords
        ref_keywords_str = ', '.join(ref_keywords)
        logging.debug(f'Discovered keywords from reference files: {ref_keywords_str}')
        update_progress_bar(1, total_steps, window)

        # Create target dictionary in the form of filepath: keyword
        targ_file_dev_dict, targ_keywords = get_file_keyword_dict(
            filepaths=target_filepaths,
            possible_devs=possible_devs,
            ref_bool=False
        )
        targ_keywords.discard(None) # Discard None keywords (no keyword found)

        # Log target keywords
        targ_keywords_str = ', '.join(targ_keywords)
        logging.debug(f'Discovered keywords from target files: {targ_keywords_str}')
        update_progress_bar(2, total_steps, window)

        # Create parsers for each keyword discovered in pairs of keyword: parser
        logging.debug('Creating parser objects...')
        total_keywords = ref_keywords | targ_keywords # Join keyword sets
        parsers = get_parser_objects(pattern_file, total_keywords)
        update_progress_bar(3, total_steps, window)

        # Create dictionaries in the form of {keyword: {filename: parsed_dict}}
        logging.debug('Parsing Reference Files...')
        parsed_reference_dict = parse_files(
            ref_file_dev_dict,
            parsers,
            keyword = keyword,
            ref_bool = True,
            collapse_bool = False,
        )
        update_progress_bar(4, total_steps, window)
        logging.debug('Parsing Target Files...')
        parsed_target_dict = parse_files(
            targ_file_dev_dict,
            parsers,
            keyword = keyword,
            ref_bool = False,
            collapse_bool = False,
        )
        update_progress_bar(5, total_steps, window)

        # Compare the reference and target into a combined dictionary
        logging.debug('Comparing reference and target...')
        final_dict = compare_dicts(
            master_ref_dict = parsed_reference_dict, 
            master_targ_dict = parsed_target_dict,
            keyword = keyword
        )
        update_progress_bar(6, total_steps, window)

        # Collapse the parsed dictionary
        logging.debug('Cleaning Data Structure...')
        final_dict = Quickparser.collapse(final_dict)
        update_progress_bar(7, total_steps, window)

        # Get variables ready for the brief report
        found_keywords = list(targ_keywords)
        counted_files = len(target_filepaths)
        num_files_without_keywords = len(
            final_dict.get(
                'Target Folder', {}
            ).get(
                f'{keyword} Not Found', {}
            )
        )
        num_deviations = 0
        for vals in final_dict.get('Target Folder', {}).values():
            if isinstance(vals, dict):
                new_deviations = Quickparser.leafify(vals.get('Deviations', {}))
                num_deviations += len(new_deviations)

        # Build the Brief Report
        logging.debug('Building Report...')
        report = build_report(
            detail_dict = final_dict,
            found_keywords = found_keywords,
            counted_files = counted_files,
            target_folder = target_folder_path,
            num_files_without_keywords = num_files_without_keywords,
            start_time = start_time,
            keyword = keyword,
            num_deviations = num_deviations,
            reference_folder = reference_folder_path,
        )
        update_progress_bar(8, total_steps, window)
        logging.debug('Finished')
        print(report)

        # Return results
        return final_dict
    
    except Exception as e:
        print(f'{type(e).__name__}: {str(e)}')
    finally:
        print('='*100)

def main_parse(
    pattern_file,
    target_folder_path,
    reference_folder_path=None,
    window=None,
    keyword="Keyword"
):
    parse_function = (
        single_parse if reference_folder_path is None else comparison_parse
    )
    if reference_folder_path:
        return parse_function(
            pattern_file=pattern_file,
            target_folder_path=target_folder_path,
            reference_folder_path=reference_folder_path,
            window=window,
            keyword=keyword
        )
    else:
        return parse_function(
            pattern_file=pattern_file,
            target_folder_path=target_folder_path,
            window=window,
            keyword=keyword
        )