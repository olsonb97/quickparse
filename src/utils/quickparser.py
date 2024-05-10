import re
import yaml
import json
import logging
from typing import IO, Optional, Literal

class QuickparserError(Exception):
    def __init__(self, message=''):
        super().__init__(message)

class Quickparser:

    def __init__(
        self, 
        keyword: str, 
        pattern_file: str, 
        ext: Optional[Literal['.yaml', '.json']] = '.yaml', 
        log: Optional[bool] = False
    ):
        '''
        Initialize Quickparser specific to the keyword. Requires a
        pattern file that determines what to pull for the keyword. Consult
        documentation for how to format a pattern file.

        Args:
            keyword (str): Initializes a parser for a specific keyword
            pattern_file (str): Pulls the keyword information from this file
            ext (str, optional): Pattern file extension, default is '.yaml'.
            log (bool, optional): Flag to enable logging, default is False.
        '''
        self.logging = log
        self.keyword = keyword
        self.ext = ext.strip().lower()
        self.pattern_file = Quickparser.load(pattern_file, self.ext)

        if self.logging:
            self.initialize_logger()
            self._log(
                'info', 
                f'Initialized Quickparser for keyword "{self.keyword}"'
            )

    def initialize_logger(self):
        '''
        Initialize the logger for this instance of Quickparser.
        '''
        self.logger = logging.getLogger(f'{__name__}.{self.keyword}')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = True

        # Check for handlers in the logger hierarchy
        current_logger = self.logger
        has_handlers = False
        while current_logger:
            if current_logger.handlers:
                has_handlers = True
                break # Stop if handler found
            if current_logger is current_logger.root:
                break  # Stop if root logger found
            current_logger = current_logger.parent

        # Only add a default handler if no handlers are found in the hierarchy
        if not has_handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                datefmt='%Y-%m-%d %I:%M:%S %p'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def __str__(self):
        return str(self.keyword)

    def _log(self, level: str, message: str):
        '''
        Log a message with the specified level. Dependent on instantiation.

        Args:
            level (str): The log level (debug, info, warning, error, critical).
            message (str): The message to be logged.

        Raises:
            QuickparserError: If the provided log level is not supported.
        '''
        level = level.lower().strip()
        if self.logging:
            if level == 'debug':
                self.logger.debug(message)
            elif level == 'info':
                self.logger.info(message)
            elif level == 'warning':
                self.logger.warning(message)
            elif level == 'error':
                self.logger.error(message)
            elif level == 'critical':
                self.logger.critical(message)
            else:
                raise QuickparserError(f'Unsupported logging level: {level}')

    def __recurse_parse(
        self, 
        var_dict: dict, 
        input_text: str, 
        collapse: bool = True
    ) -> dict:
        '''
        Recursively search dictionaries and perform regex matching on values.

        Args:
            var_dict (dict): The dictionary containing regex patterns.
            input_text (str): The input text to be parsed.
            collapse (bool, optional): Determines behavior when no match is found.
                                       If True, unmatched keys are set to None.
                                       If False, they are set to 'NOT FOUND'.

        Returns:
            dict: The parsed dictionary with regex matches as values.
        '''
        parsed_dict = {}
        for key, value in var_dict.items():
            if isinstance(value, dict):
                # Recursively call nested dictionaries
                parsed_dict[key] = self.__recurse_parse(value, input_text, collapse)
            elif isinstance(value, list):
                # Attempt to match each regex pattern in the list
                for pattern in value:
                    if match := re.search(pattern, input_text, re.MULTILINE):
                        parsed_dict[key] = match.group(1).strip()
                        break
                else:
                    # No match found within the list
                    parsed_dict[key] = None if collapse else 'NOT FOUND'
            else:
                # Handle single regex pattern
                if match := re.search(value, input_text, re.MULTILINE):
                    parsed_dict[key] = match.group(1).strip()
                else:
                    # Handle no match found
                    parsed_dict[key] = None if collapse else 'NOT FOUND'

        return parsed_dict

    def parse(self, input_text: str, collapse: Optional[bool] = True) -> dict:
        '''
        Parses the instance's keyword dict against the input text.

        Args:
            input_text (str): The input text containing the log output.
            collapse (bool): Determines whether to return None or 
                'NOT FOUND' as entry.

        Returns:
            dict: The parsed dictionary containing the regex output.

        Raises:
            QuickparserError: If any step of parsing fails.
        '''
        try:
            # Loading variable dictionary
            pattern_dict = self.pattern_file
            var_dict = pattern_dict.get(self.keyword)

            # Parsing the input text using the extracted dictionary
            parsed_results = self.__recurse_parse(var_dict, input_text, collapse)

            # Returning the parsed results after collapsing empty dictionaries
            return Quickparser.collapse(parsed_results)
        except Exception as e:
            raise QuickparserError(f'Unexpected parsing error: {e}')
        
    @staticmethod
    def __recurse_compare(ref_dict, targ_dict, mismatches, matches):
        '''
        Recursive helper function for comparing dictionaries.

        Args:
            ref_dict (dict): Reference dictionary.
            targ_dict (dict): Comparison dictionary.
            mismatches (dict): Dictionary to fill with mismatches.
            matches (dict): Dictionary to fill with matches.
        '''
        for key in ref_dict:
            if key in targ_dict:
                if (
                    isinstance(ref_dict[key], dict) and 
                    isinstance(targ_dict[key], dict)
                ):
                    # Prepare new level for nested dictionaries
                    mismatches[key] = {}
                    matches[key] = {}
                    # Recursive call for nested comparison
                    Quickparser.__recurse_compare(
                        ref_dict[key], 
                        targ_dict[key], 
                        mismatches[key], 
                        matches[key]
                    )
                elif ref_dict[key] == targ_dict[key]:
                    # Values match
                    matches[key] = targ_dict[key]
                else:
                    # Values don't match
                    mismatches[key] = targ_dict[key]
            else:
                # Add to mismatch_dict if key is not found in comparison_dict
                mismatches[key] = "NOT FOUND"

        # Check for keys in comparison_dict that are not in reference_dict
        for key in targ_dict:
            if key not in ref_dict:
                mismatches[key] = targ_dict[key]
    
    @staticmethod
    def compare(reference_dict: dict, target_dict: dict) -> tuple[dict, dict]:
        '''
        Compare two dictionaries and return dictionaries containing 
        matches and mismatches.

        Args:
            reference_dict (dict): The reference dictionary.
            target_dict (dict): The dictionary to be compared against the 
                reference.

        Returns:
            tuple: A tuple containing dictionaries for matches and 
                mismatches between the two input dictionaries.
        '''

        mismatch_dict = {}
        match_dict = {}

        # Call the recursive helper method
        Quickparser.__recurse_compare(
            reference_dict, 
            target_dict, 
            mismatch_dict, 
            match_dict
        )

        # Collapse the results
        match_dict = Quickparser.collapse(match_dict)
        mismatch_dict = Quickparser.collapse(mismatch_dict)

        return match_dict, mismatch_dict

    @staticmethod
    def load(file_path: str, ext: str) -> dict:
        '''
        Load data from a file based on the specified extension.

        Args:
            file_path: The path to the file to be loaded.
            ext: The extension indicating the format ('.json', '.yaml').

        Returns:
            dict: The loaded data as a dictionary.

        Raises:
            QuickparserError: If there's an error processing the data file.
        '''
        try:
            ext = ext.lower().strip()
            with open(file_path, 'r') as file:
                if ext in {'.yaml', 'yaml', '.yml', 'yml'}:
                    return yaml.safe_load(file)
                elif ext in {'.json', 'json'}:
                    return json.load(file)
        except Exception as e:
            raise QuickparserError(f'Failed to process data: {e}')

    @staticmethod
    def dump(data: dict, file: IO, ext: str):
        '''
        Dump data to a file object based on the specified extension.

        Args:
            data (dict): The data to be dumped to the file.
            file (IO): The file object to which the data will be written.
            ext: The extension indicating the format ('.json', '.yaml').

        Raises:
            QuickparserError: If there's an error writing data to the file.
        '''
        try:
            ext = ext.lower().strip()
            if ext in {'.yaml', 'yaml', 'yml', '.yml'}:
                yaml.dump(data, file, default_flow_style=False, indent=4)
            elif ext in {'.json', 'json'}:
                json.dump(data, file, indent=4)
        except Exception as e:
            raise QuickparserError(f'Failed to write data: {e}')

    @staticmethod
    def stringify(data: dict, ext: str) -> str:
        '''
        Stringify a dictionary based on the specified extension.

        Args:
            data (dict): The dictionary to be converted to a string.
            ext: The extension indicating the format ('.json', '.yaml').

        Returns:
            str: The string representation of the dictionary.

        Raises:
            QuickparserError: If there's an error stringifying.
        '''
        ext = ext.lower().strip()
        try:
            serialized = None
            if ext in {'.yaml', 'yaml', '.yml', '.yml'}:
                serialized = yaml.dump(
                    data, 
                    default_flow_style=False, 
                    indent=4, 
                    width=500
                )
            elif ext in {'.json', 'json'}:
                serialized = json.dumps(
                    data, 
                    indent=4
                )
            return serialized.rstrip('\n')
        except Exception as e:
            raise QuickparserError(f'Failed to stringify data to {ext}: {e}')
        
    @staticmethod
    def discover(input_text: str, keywords: str) -> tuple[str, str]:
        '''
        Searches through the input text to find a keyword from the pattern file.

        Args:
            input_text (str): The text to search through for keyword names.
            pattern_file (str): The file to pull keywords from.

        Returns:
            str: The keyword found, or None if no keyword is found; '*' if '*' is
            included in the pattern file and no other keyword is found,
            indicating a wildcard to match all files where no keyword is found.
        '''

        # Search for the first occurrence of any keyword in the input text
        fallback = False
        for keyword in keywords:
            if keyword == '*': # use fallback if * is a keyword
                fallback = True
                continue
            if match := re.search(keyword, input_text):
                return match.group()
        else:
            return '*' if fallback else None
    
    @staticmethod
    def collapse(dictionary: dict) -> dict:
        '''
        Recursively collapse a dictionary's empty dictionaries as well as
        any other falsy values.

        Args:
            dictionary (dict): The dictionary to be collapsed.

        Returns:
            dict: The collapsed dictionary with falsy values removed.
        '''
        # List to keep track of keys that lead to empty dictionaries
        keys_to_delete = []

        for key, val in dictionary.items():
            # Check if the value is a dictionary itself
            if isinstance(val, dict):
                # Recursively collapse the nested dictionary
                Quickparser.collapse(val)
                # Mark for deletion if falsy
                if not val:
                    keys_to_delete.append(key)
            elif not val:  # Check for other falsy values
                keys_to_delete.append(key)

        # Remove keys marked for deletion
        for key in keys_to_delete:
            del dictionary[key]

        # Return the modified dictionary
        return dictionary
    
    @staticmethod
    def leafify(input_dict: dict) -> list:
        '''
        Searches dictionaries for leaf nodes and puts values into a single list.

        Args:
            input_dict (dict): The dictionary to search through

        Returns:
            list: A list of all leaf values
        '''
        if not input_dict:
            return []
        leaf_nodes = []
        for value in input_dict.values():
            if isinstance(value, dict):
                # Recursively search within nested dictionaries
                leaf_nodes.extend(Quickparser.leafify(value))
            elif isinstance(value, (list, tuple, set)):
                # Extend the list with each item in the iterable
                for item in value:
                    if isinstance(item, dict):
                        # Recursively search in nested dictionaries in iterable
                        leaf_nodes.extend(Quickparser.leafify(item))
                    else:
                        leaf_nodes.append(item)
            else:
                # Directly append non-dictionary and non-iterable values
                leaf_nodes.append(value)
        return leaf_nodes