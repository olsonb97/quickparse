# Project Title

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
- **Reference Folder**: Must contain a unique reference file for each device model and a single YAML pattern file for regex patterns.

### YAML Patterns
Define device variables with minimal regex patterns:

```yaml
C9200L:
  Version: 'Cisco IOS XE Software, Version (.*)'
  MAC Address: 'MAC Address\s+:\s+(\S+)'
C9300:
  Version: 'Cisco IOS XE Software, Version (.*)'
  MAC Address: 'MAC Address\s+:\s+(\S+)'
...

## License
- Licensed under GNU General Public License version 3 (GPLv3), ensuring free use and modification.
