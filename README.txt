This application is meant to parse log files and compare them against a "gold" standard log.
All matches and mismatches between them are given back to the user in a report.
The report consists of a "Detailed" and a "Brief" section.
The report will have a "Verdict" determing either "PASS" or "FAIL"

The way this program determines what to look for is through regex in the format of YAML.
The YAML program files contain values to look for and this format is designed to be extensible.
The program asks for a gold folder to reference. This folder must contain logs as well as exactly one YAML file.
The program has the ability to generate a new YAML file with barebones patterns if ever needed.

This program saves a configuration file that stores a default gold folder path.
The program determines this path based on the OS and this is the only variable stored.
This is designed to tailor the program towards any specific user.
