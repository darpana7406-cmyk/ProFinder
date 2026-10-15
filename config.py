import os
from dotenv import load_dotenv

load_dotenv()

# ============================================
# SECURITY
# ============================================
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')

# ============================================
# DATABASE
# ============================================
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB = os.getenv('MYSQL_DB', 'profinder_db')
MYSQL_CHARSET = os.getenv('MYSQL_CHARSET', 'utf8mb4')

# ============================================
# EMAIL (optional)
# ============================================
MAIL_ENABLED = os.getenv('MAIL_ENABLED', 'False').lower() == 'true'
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', '587'))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', '')