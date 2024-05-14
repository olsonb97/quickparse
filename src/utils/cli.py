import argparse
from argparse import RawDescriptionHelpFormatter
import logging
from src.utils.parsing_logic import main_parse

logging_handler = logging.StreamHandler()
logging_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s.%(msecs)03d - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
)
logging.getLogger().addHandler(logging_handler)
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger()
logger.addHandler(logging_handler)

def main():
    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description=r'''
Quickparse

Overview:
Quickparse is a parsing tool for analyzing device logs and text files. It provides customizable parsing rules through JSON/YAML templates.

Key Features:
- Dual Mode Parsing: Parse a single target folder or compare against a reference folder.
- Comprehensive Reporting: Generate detailed reports with parsing accuracy and discrepancies in comparative analyses.
- Quickparser Module: Importable package for use with or without GUI elements.

Usage Instructions:
- Single-Target Parsing:
    1. Prepare Logs.
    2. Create a Pattern File.
    3. Load Resources.
    4. Begin Parsing.
    5. Save Results.

- Comparison Mode:
    1. Prepare Reference and Target Logs.
    2. Create a Pattern File.
    3. Set Parsing Mode.
    4. Load Resources.
    5. Begin Parsing.
    6. Review and Save Results.

Pattern Files:
- Patterns define efficient parsing of specific entries in device logs.
- Supports YAML or JSON formats.

YAML Pattern Example:

    '*':
        Generic Version: 'Version (.*)'
    Cisco IOS XE:
        Version:
        - 'Cisco IOS XE Software, Version (.*)'
        - 'Cisco IOS XE Software Version (\S+)'
        MAC Address: 'MAC Address\s+:\s+(\S+)'

JSON Pattern Example:

    {
        "*": {
            "Generic Version": "Version (.*)"
        },
        "Cisco IOS XE": {
            "Version": [
                "Cisco IOS XE Software, Version (.*)",
                "Cisco IOS XE Software Version (\\S+)"
            ],
            "MAC Address": "MAC Address\\s+:\\s+(\\S+)"
        }
    }

Extensibility:
- Pattern Files: Support YAML or JSON with a rigid structure.
- Modular Parsing: Core parsing functionality can be extended or integrated into other projects.

License:
This software is released under the GNU General Public License version 3 (GPLv3), permitting free use, modification, and distribution.

''')
    parser.add_argument(
        'pattern_file',
        help="Path to the pattern file. [.json, .yaml, .yml]"
    )
    parser.add_argument(
        'target_directory_path',
        help="Path to the target directory."
    )
    parser.add_argument(
        '--reference_directory_path',
        '-r',
        help="Path to the reference directory (for comparison)."
    )
    parser.add_argument(
        '--keyword',
        '-k',
        help="Keyword for parsing. Cosmetic change only. Adjusts semantics from 'Keyword' to provided argument.",
        default="Keyword"
    )
    
    args = parser.parse_args()

    main_parse(
        pattern_file=args.pattern_file,
        target_folder_path=args.target_directory_path,
        reference_folder_path=args.reference_directory_path,
        keyword=args.keyword
    )

if __name__ == "__main__":
    main()