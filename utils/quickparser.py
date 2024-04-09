import re
import yaml
import json
import logging
from typing import IO, Optional, Literal
from .errors import QuickparserError

class Quickparser:
    ext = '.yaml'

    def __init__(self, device: str, pattern_file: str, ext: Literal['.yaml', '.json'] = ext, log: Optional[bool] = False):
        """
        Initialize Quickparser specific to the device.

        Args:
            device (str): The device to parse. Use discover to find it.
            pattern_file (str): The pattern file to be used.
            ext (str, optional): Pattern file extension, default is '.yaml'.
        """
        self.logging = log
        self.device = device
        self.logger = logging.getLogger(f'{__name__}.{self.device}')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = True  # Ensure log messages propagate up

        # Manually walk up the logger hierarchy to check for handlers
        current_logger = self.logger
        has_handlers = False
        while current_logger:
            if current_logger.handlers:
                has_handlers = True
                break
            if current_logger is current_logger.root:
                break  # Stop if we have reached the root logger
            current_logger = current_logger.parent

        # Only add a default handler if no handlers are found in the hierarchy
        if not has_handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.ext = ext.strip().lower()
        
        self.pattern_file = Quickparser.load(pattern_file, self.ext)
        self.log('info', f"Initialized Quickparser for device '{self.device}'")


    def log(self, level: str, message: str):
        """
        Log a message with the specified level. Dependent on instantiation.

        Args:
            level (str): The log level (debug, info, warning, error, critical).
            message (str): The message to be logged.

        Raises:
            ValueError: If the provided log level is not supported.
        """
        if self.logging:
            if level.lower() == 'debug':
                self.logger.debug(message)
            elif level.lower() == 'info':
                self.logger.info(message)
            elif level.lower() == 'warning':
                self.logger.warning(message)
            elif level.lower() == 'error':
                self.logger.error(message)
            elif level.lower() == 'critical':
                self.logger.critical(message)
            else:
                raise ValueError(f"Unsupported logging level: {level}")

    def _parse(self, var_dict: dict, input_text: str, collapse: bool = True) -> dict:
        """
        Iteratively search dictionaries and perform regex matching on values.

        Args:
            var_dict (dict): The dictionary containing regex patterns.
            input_text (str): The input text to be parsed.

        Returns:
            dict: The parsed dictionary with regex matches as values.
        """
        stack = [(var_dict, {})]
        result = {}

        while stack:
            current_data, current_parsed_dict = stack.pop()
            for key, value in current_data.items():
                if isinstance(value, dict):
                    # Initialize nested dict if not already present
                    if key not in current_parsed_dict:
                        current_parsed_dict[key] = {}
                    stack.append((value, current_parsed_dict[key]))
                else:
                    match = None
                    if isinstance(value, list):
                        for item in value:
                            match = re.search(item, input_text, re.MULTILINE)
                            if match:
                                break
                    else:
                        match = re.search(value, input_text, re.MULTILINE)
                    
                    if match:
                        current_parsed_dict[key] = match.group().strip()  # Use entire match if specific group isn't specified
                    else:
                        if collapse:
                            current_parsed_dict[key] = None
                        else:
                            current_parsed_dict[key] = "NOT FOUND"

        result.update(current_parsed_dict)
        return result

    def parse(self, input_text: str, collapse: Optional[bool] = True) -> dict:
        """
        Parses the platform's file against the input_text

        Args:
            input_text (str): The input text containing the log output.
            collapse (bool): Determines whether to return {} or "NOT FOUND" as entry.

        Returns:
            dict: The parsed dictionary containing the regex output.

        Raises:
            QuickparserError: Parsing failed. Check pattern file, regex, or input text.
        """
        try:
            # Logging the start of the parsing process

            # Loading variable dictionary
            pattern_dict = self.pattern_file
            var_dict = pattern_dict.get(self.device)

            # Parsing the input text using the extracted dictionary
            parsed_results = self._parse(var_dict, input_text, collapse)

            # Returning the parsed results after collapsing empty dictionaries
            return Quickparser.collapse(parsed_results)
        except Exception as e:
            raise QuickparserError(f"Unexpected parsing error: {e}")

    @staticmethod
    def load(file_path: str, ext: str) -> dict:
        """
        Load data from a file based on the specified extension.

        Args:
            file_path: The path to the file to be loaded.
            ext: The extension indicating the format (".json", ".yaml").

        Returns:
            dict: The loaded data as a dictionary.

        Raises:
            QuickparserError: If there's an error processing the data file.
        """
        try:
            ext = ext.lower().strip()
            with open(file_path, 'r') as file:
                if ext in ['.yaml', 'yaml']:
                    return yaml.safe_load(file)
                elif ext in ['.json', 'json']:
                    return json.load(file)
        except Exception as e:
            raise QuickparserError(f"Failed to process data: {e}")

    @staticmethod
    def dump(data: dict, file: IO, ext: str):
        """
        Dump data to a file object based on the specified extension.

        Args:
            data (dict): The data to be dumped to the file.
            file (IO): The file object to which the data will be written.
            ext: The extension indicating the format (".json", ".yaml").

        Raises:
            QuickparserError: If there's an error writing data to the file.
        """
        try:
            ext = ext.lower().strip()
            if ext in ['.yaml', 'yaml']:
                yaml.dump(data, file, default_flow_style=False, indent=4)
            elif ext in ['.json', 'json']:
                json.dump(data, file, indent=4)
        except Exception as e:
            raise QuickparserError(f"Failed to write data: {e}")

    @staticmethod
    def serialize(data: dict, ext: str) -> str:
        """
        Convert a dictionary to a string representation based on the specified extension.

        Args:
            data (dict): The dictionary to be converted to a string.
            ext: The extension indicating the format (".json", ".yaml").

        Returns:
            str: The string representation of the dictionary.

        Raises:
            QuickparserError: If there's an error converting the dictionary to a string.
        """
        ext = ext.lower().strip()
        try:
            if ext in ['.yaml', 'yaml']:
                return yaml.dump(data, default_flow_style=False, indent=4, width=500)
            elif ext in ['.json', 'json']:
                return json.dumps(data, indent=4)
        except Exception as e:
            raise QuickparserError(f"Failed to convert data to {ext} string: {e}")
        
    @staticmethod
    def discover(input_text: str, pattern: str) -> tuple[str, str]:
        """
        Searches through the input text to find a device from the pattern file.

        Args:
            input_text (str): The text to search through for device names.
            pattern_file (str): The file to pull devices from.

        Returns:
            str: The device found

        Raises:
            QuickparserError: If pattern file is Falsy
            QuickparserError: If no device is found, error.
        """

        # Search for the first occurrence of any device in the input text
        if match := pattern.search(input_text):
            return match.group()
        else:
            return None
    
    @staticmethod
    def collapse(dictionary: dict) -> dict:
        """
        Collapse dictionaries with no values by removing their keys.

        This method recursively checks each value in the given dictionary. If a value is an empty dictionary,
        or becomes empty after recursively collapsing its own nested dictionaries, its key is removed from the parent dictionary.

        Args:
            dictionary (dict): The dictionary to be collapsed.

        Returns:
            dict: The collapsed dictionary with empty dictionaries removed.
        """
        # List to keep track of keys that lead to empty dictionaries
        keys_to_delete = []

        # Iterate over key-value pairs in the dictionary
        for key, val in dictionary.items():
            # Check if the value is a dictionary itself
            if isinstance(val, dict):
                # Recursively collapse the nested dictionary
                Quickparser.collapse(val)
                # If the nested dictionary is empty after collapsing, mark its key for deletion
                if not val:
                    keys_to_delete.append(key)
            elif not val:  # Check for other Falsey values
                keys_to_delete.append(key)

        # Remove keys that were marked for deletion, i.e., those that had empty dictionaries as values
        for key in keys_to_delete:
            del dictionary[key]

        # Return the modified dictionary with empty nested dictionaries removed
        return dictionary
    
    @staticmethod
    def leafify(input_dict: dict) -> list:
        """
        Searches dictionaries for leaf nodes and puts values into a single list.

        Args:
            input_dict (dict): The dictionary to search through

        Returns:
            list: A list of all leaf values
        """
        leaf_nodes = []
        for value in input_dict.values():
            if isinstance(value, dict):
                # Recursively search within nested dictionaries
                leaf_nodes.extend(Quickparser.leafify(value))
            elif isinstance(value, (list, tuple, set)):
                # Extend the list with each item in the iterable
                for item in value:
                    if isinstance(item, dict):
                        # Recursively search within nested dictionaries inside the iterable
                        leaf_nodes.extend(Quickparser.leafify(item))
                    else:
                        leaf_nodes.append(item)
            else:
                # Directly append non-dictionary and non-iterable values
                leaf_nodes.append(value)
        return leaf_nodes
    
    @staticmethod
    def compare(reference_dict: dict, comparison_dict: dict) -> tuple[dict, dict]:
        """
        Compare two dictionaries and return a dictionary containing matches and mismatches.

        Args:
            reference_dict (dict): The reference dictionary.
            comparison_dict (dict): The dictionary to be compared with the reference.

        Returns:
            dict: A dictionary containing matches and mismatches between the two input dictionaries.
        """
        mismatch_dict = {}
        match_dict = {}

        stack = [(reference_dict, comparison_dict, mismatch_dict, match_dict)]

        while stack:
            current_ref_dict, current_comp_dict, current_mismatch_dict, current_match_dict = stack.pop()

            for key in current_ref_dict:
                if key in current_comp_dict:
                    if isinstance(current_ref_dict[key], dict) and isinstance(current_comp_dict[key], dict):
                        # Prepare new level for nested dictionaries
                        new_mismatch = {}
                        new_match = {}
                        current_mismatch_dict[key] = new_mismatch
                        current_match_dict[key] = new_match
                        # Add to stack for further comparison
                        stack.append((current_ref_dict[key], current_comp_dict[key], new_mismatch, new_match, key))
                    elif current_ref_dict[key] == current_comp_dict[key]:
                        # Add to match_dict if values match
                        current_match_dict[key] = current_comp_dict[key]
                    else:
                        # Add to mismatch_dict if values don't match
                        current_mismatch_dict[key] = current_comp_dict[key]
                else:
                    # Add to mismatch_dict if key is not found in comparison_dict
                    current_mismatch_dict[key] = "NOT FOUND"

            # Check for keys in comparison_dict that are not in reference_dict
            for key in current_comp_dict:
                if key not in current_ref_dict:
                    current_mismatch_dict[key] = current_comp_dict[key]

        match_dict = Quickparser.collapse(match_dict)
        mismatch_dict = Quickparser.collapse(mismatch_dict)

        return match_dict, mismatch_dict