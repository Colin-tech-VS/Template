import os

env_path = r'.env'

with open(env_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

template_lines = [line.strip() for line in lines if 'TEMPLATE_MASTER_API_KEY' in line]

print("=== Checking TEMPLATE_MASTER_API_KEY ===")
print(f"Total lines found: {len(template_lines)}")
print()

for i, line in enumerate(template_lines, 1):
    print(f"Line {i}: {repr(line)}")

if len(template_lines) == 0:
    print("ERROR: TEMPLATE_MASTER_API_KEY not found in .env")
elif len(template_lines) == 1:
    line = template_lines[0]
    if line == "TEMPLATE_MASTER_API_KEY=template-master-key-2025":
        print("\n[OK] Configuration is CORRECT")
    else:
        print(f"\n[FAIL] Configuration is WRONG")
        print(f"  Expected: TEMPLATE_MASTER_API_KEY=template-master-key-2025")
        print(f"  Got:      {line}")
else:
    print(f"\n[WARNING] Multiple TEMPLATE_MASTER_API_KEY lines found ({len(template_lines)})")
    print("This may cause issues. The file should have only one.")
