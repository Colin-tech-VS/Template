import shutil

env_path = '.env'
backup_path = '.env.backup'

shutil.copy(env_path, backup_path)
print(f"Backup created: {backup_path}")

with open(env_path, 'rb') as f:
    raw_bytes = f.read()

print(f"Original file size: {len(raw_bytes)} bytes")

cleaned = raw_bytes.replace(b'\x00', b'').decode('utf-8', errors='ignore')

with open(env_path, 'w', encoding='utf-8') as f:
    f.write(cleaned)

print("File cleaned and saved")

with open(env_path, 'r') as f:
    lines = f.readlines()
    template_lines = [l.strip() for l in lines if 'TEMPLATE' in l]
    print(f"TEMPLATE_MASTER_API_KEY lines after cleanup: {len(template_lines)}")
    for line in template_lines:
        print(f"  {repr(line)}")
