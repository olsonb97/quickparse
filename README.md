# Quickparse

## Overview
This lightweight tool parses log files against a reference to detect deviations. It utilizes simple, one-level deep YAML configurations for regex patterns, making it efficient and easy to customize. The tool outputs a detailed report, categorizing results as "PASS" or "FAIL".

### Key Features
- **Efficient Parsing**: Employs the `QuickParser` class for swift log analysis.
- **Simplified Configuration**: Uses a straightforward YAML pattern file for defining variables and regex patterns.
- **Comprehensive Reports**: Generates reports with detailed and brief sections, including a final "Verdict".

### Quick Start
- **Setup**: Clone the repo and ensure the reference folder has log files and a YAML pattern file.
- **Run**: Execute the application, select your reference and target folder, and click "Parse".

### Requirements
- **Reference Folder**:
    - At least one log file.
    - One YAML pattern file.
        - YAML keys must occur in the text being parsed.

### YAML Patterns
- Define device variables with minimal regex patterns. (Sequences parse in hierarchical order)
- Each regex string requires exactly one group () for parsing.

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

OS keys are also compatible! The only requirement is that the key appear in the text:
```yaml
Cisco IOS XE:
    Version:
    - 'Cisco IOS XE Software, Version (.*)'
    - 'Cisco IOS XE Software Version (\S+)'
Arista EOS:
    Version: 'Arista EOS Version: (.*)'
```

### Extensibility
- **Format Flexibility**: Default pattern files are YAML for readability and ease of use, but JSON format is also supported for those who prefer it.
- **Modular Parsing**: The QuickParser class is designed to function independently, allowing it to be imported and utilized in other Python projects.
- **Expandable Patterns**: New regex patterns can be easily added to the YAML or JSON files, making the tool adaptable.

## License
Licensed under GNU General Public License version 3 (GPLv3), ensuring free use and modification.
