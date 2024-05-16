# Quickparse

## Overview
Quickparse is a parsing tool that provides graphical interfaces for analyzing device logs and text files. This tool allows users to customize parsing rules through JSON/YAML templates to handle various file formats and log structures efficiently. Quickparse leverages multi-threading as well as multi-processing for advanced Python speeds.

### Key Features
- **Dual Mode Parsing**: Enables parsing a single target folder or comparative analysis against a reference folder.
- **In-app Template Editor**: Facilitates the direct editing of JSON/YAML templates within the application.
- **Comprehensive Reporting**: Generates detailed reports that classify results based on parsing accuracy and identify discrepancies in comparative analyses.
- **Quickparser Module**: Importable package designed to be usable with or without the GUI elements.

## GUI Usage Instructions
Run main.pyw from the repository.

### Single-Target Parsing
1. **Prepare Your Logs**: Place all log files you wish to parse in a single folder. Ensure they are in `.txt` or `.log` format.
2. **Create a Pattern File**: Define the patterns for parsing using a JSON or YAML file. This file should specify the log entry components to be extracted, such as version, mac address, or any other relevant data. There is an example template in /resources for reference.
3. **Load Resources**: Through the GUI, load your pattern file and target folder.
4. **Begin Parsing**: Initiate the parsing process via the GUI. Quickparse will process the logs based on your pattern definitions and generate a report summarizing the results.'
5. **Save Results**": The options to save the parsed information as txt, log, yaml, json, and xml are available.

### Comparison Mode
1. **Prepare Reference and Target Logs**: Organize your reference logs (the standard for comparison) and the target logs (to be analyzed) into two separate folders.
2. **Create a Pattern File**: Similar to single-target parsing, create a JSON or YAML pattern file that defines the parsing rules.
3. **Set Parsing Mode**: In the GUI, select the comparison mode option.
4. **Load Resources**: Through the GUI, load your pattern file, target folder, and reference folder.
5. **Begin Parsing**: Start the parsing process. Quickparse will first analyze the reference logs to establish a baseline, then parse the target logs and compare the findings, highlighting any deviations or matches.
6. **Review the Report**: Analyze the generated report to see detailed comparisons, matches, and deviations between the target logs and the reference logs.
7. **Save Results**": The options to save the parsed information as txt, log, yaml, json, and xml are available.

## CLI Usage Instructions
1. Run the command "pip install ." from the directory to install `quickparse` as a working command.
2. Use command `quickparse /path/to/pattern_file /path/to/target_directory` to parse a pattern_file against a directory.
3. For comparison mode, add the option `-r /path/to/reference_directory` or `--reference /path/to/reference_directory`
4. For serializing output, add the option `-s {xml/yaml/json}` or `--serialize {xml/yaml/json}`

## Pattern Files

### Template Editor
- **Access the Template Editor**: From the main interface, navigate to the template editor section.
- **Create a Template**: The option to load an example template and begin editing with a starting point is available.
- **Modify Existing Templates**: Open an existing template file and make changes as needed. The editor supports both JSON and YAML formats.
- **Save Templates**: After editing, save the template file directly within the application for immediate use in parsing tasks.

### Pattern File Configuration
- Patterns are defined to efficiently match and parse specific entries in device logs.
- Device names:
  - These must occur within the log. Subsequent parsing relies on a device name match.
  - Use "*" as a catch-all to avoid device matching.
- Variables:
  - Variable names are arbitrary. Their regex pattern must contain one "()" value to pull.
  - Regex strings may be put into lists and they will parse hierarchically until found.

### Example patterns:

#### YAML Pattern Example
```yaml
'*':
    Generic Version: 'Version (.*)'
Cisco IOS XE:
    Version:
    - 'Cisco IOS XE Software, Version (.*)'
    - 'Cisco IOS XE Software Version (\S+)'
    MAC Address: 'MAC Address\s+:\s+(\S+)'
Arista EOS:
    Version: 'Arista EOS Version: (.*)'
```
#### JSON Pattern Example
```json
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
    },
    "Arista EOS": {
        "Version": "Arista EOS Version: (.*)"
    }
}
```

## Extensibility
- **Pattern Files**: Quickparse pattern files support a rigid structure, but allow for the choice of YAML or JSON.
- **Modular Parsing**: The core parsing functionality, encapsulated in the `QuickParser` class, can be extended or integrated into other projects, allowing for broad application across various log parsing scenarios.

## License
This software is released under the GNU General Public License version 3 (GPLv3), permitting free use, modification, and distribution under the same license.
