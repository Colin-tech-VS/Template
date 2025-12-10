with open('.env', 'r') as f:
    lines = f.readlines()
    
for i, line in enumerate(lines, 1):
    if 'TEMPLATE_MASTER_API_KEY=' in line:
        key_part = line.split('=', 1)[1].strip()
        print(f"Line {i}: {repr(line)}")
        print(f"Value part: {repr(key_part)}")
        print(f"Expected: {repr('template-master-key-2025')}")
        print(f"Match: {key_part == 'template-master-key-2025'}")
        print(f"Length: {len(key_part)}")
