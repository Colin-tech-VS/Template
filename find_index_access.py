#!/usr/bin/env python3
import os
import re

pattern = re.compile(r'\w+\[\d\]')

print("=== Files using index access ===\n")

# Search in all HTML files
for root, dirs, files in os.walk('templates'):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    matches = pattern.findall(line)
                    if matches:
                        print(f'{filepath}:{i+1}: {line.strip()}')
