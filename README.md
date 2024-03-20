# Quickparse

## Overview
This lightweight tool parses log files against a reference to detect deviations. It utilizes simple, one-level deep YAML configurations for regex patterns, making it efficient and easy to customize. The tool outputs a detailed report, categorizing results as "PASS" or "FAIL".

### Key Features
- **Efficient Parsing**: Employs the `QuickParser` class for swift log analysis.
- **Simplified Configuration**: Uses a straightforward YAML pattern file for defining variables and regex patterns.
- **Comprehensive Reports**: Generates reports with detailed and brief sections, including a final "Verdict".

### Quick Start
- **Setup**: Clone the repo and ensure the reference folder has log files and a YAML pattern file.
- **Run**: Execute the application and follow prompts for paths to reference and target folders.

### Requirements
- **Reference Folder**:
    - One YAML pattern file.
    - At least one log file.
    - Device names in logs must match YAML keys.

### YAML Patterns
Define device variables with minimal regex patterns (Sequences parse in hierarchical order):

```yaml
C9200L:
    Version:
    - 'Cisco IOS XE Software, Version (.*)'
    - 'Cisco IOS XE Software Version (\S+)'
    MAC Address: 'MAC Address\s+:\s+(\S+)'
C9300:
    Version: 'Cisco IOS XE Software, Version (.*)'
    MAC Address: 'MAC Address\s+:\s+(\S+)'
```

### Extensibility
- **Format Flexibility**: Default pattern files are YAML for readability and ease of use, but JSON format is also supported for those who prefer it.
- **Modular Parsing**: The QuickParser class is designed to function independently, allowing it to be imported and utilized in other Python projects.
- **Expandable Patterns**: New regex patterns can be easily added to the YAML or JSON files, making the tool adaptable.

## License
Licensed under GNU General Public License version 3 (GPLv3), ensuring free use and modification.
