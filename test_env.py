import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('TEMPLATE_MASTER_API_KEY')
print(f'TEMPLATE_MASTER_API_KEY: {key}')
print(f'Key is: {repr(key)}')
