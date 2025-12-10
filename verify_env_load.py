import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('TEMPLATE_MASTER_API_KEY')
print(f"TEMPLATE_MASTER_API_KEY loaded: {repr(api_key)}")
print(f"Match with expected value: {api_key == 'template-master-key-2025'}")
