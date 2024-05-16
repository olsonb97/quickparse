import argparse
from argparse import RawDescriptionHelpFormatter
import logging
import yaml
import json
import xml.dom.minidom
import dicttoxml
from src.utils.parsing_logic import main_parse

def convert_to_format(report_dict, mode):
    if mode == 'yaml':
        return yaml.dump(report_dict, default_flow_style=False, indent=4)
    elif mode == 'json':
        return json.dumps(report_dict, indent=4)
    elif mode == 'xml':
        xml_obj = dicttoxml.dicttoxml(report_dict, custom_root='Report', attr_type=False)
        xml_str = xml_obj.decode()
        parsed_xml = xml.dom.minidom.parseString(xml_str)
        return parsed_xml.toprettyxml()

parser_description = r'''
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

'''

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

dicttoxml.LOG.setLevel(logging.ERROR)

def main():
    parser = argparse.ArgumentParser(
        formatter_class=RawDescriptionHelpFormatter,
        description=parser_description
    )
    
    parser.add_argument(
        'pattern_file',
        help="Path to the pattern file. {.json, .yaml, .yml}"
    )
    parser.add_argument(
        'target',
        help="Path to the target directory."
    )
    parser.add_argument(
        '--reference',
        '-r',
        help="Path to the reference directory (for comparison)."
    )
    parser.add_argument(
        '--keyword',
        '-k',
        help="Keyword for parsing. Cosmetic change only. Adjusts semantics from 'Keyword' to provided argument, e.g., 'Device'.",
        default="Keyword"
    )
    parser.add_argument(
        '--serialize',
        '-s',
        choices=['yaml', 'json', 'xml'],
        help="Serialize the parsed data."
    )
    
    args = parser.parse_args()

    report_dict, report_string = main_parse(
        pattern_file=args.pattern_file,
        target_folder_path=args.target,
        reference_folder_path=args.reference,
        keyword=args.keyword
    )

    if args.serialize:
        converted_report = convert_to_format(report_dict, args.serialize)
        print(converted_report)
    else:
        print(report_string)

if __name__ == "__main__":
    main()