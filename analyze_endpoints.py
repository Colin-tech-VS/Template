#!/usr/bin/env python3
import re

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Chercher les routes avec POST
for i, line in enumerate(lines):
    if '@app.route' in line and 'POST' in line:
        # Afficher la route et les 2 lignes suivantes pour voir le nom de la fonction
        print(f"Line {i+1}: {line.strip()}")
        if i+1 < len(lines):
            print(f"Line {i+2}: {lines[i+1].strip()}")
        print()

print("\n\n=== Routes GET pour export ===\n")

for i, line in enumerate(lines):
    if '@app.route' in line and '/api/export' in line and 'GET' in line:
        print(f"Line {i+1}: {line.strip()}")
        if i+1 < len(lines):
            print(f"Line {i+2}: {lines[i+1].strip()}")
        print()
