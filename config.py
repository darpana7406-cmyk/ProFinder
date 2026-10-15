SECRET_KEY = 'profinder-secret-key-2025'

MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'Darpana@07'
MYSQL_DB = 'profinder_db'
MYSQL_CHARSET = 'utf8mb4'

# ============================================
# EMAIL CONFIG (Optional — for real email sending)
# ============================================
# To enable real emails:
#   1. Gmail account
#   2. Enable 2-Step Verification
#   3. Generate App Password
#   4. Fill fields below + set MAIL_ENABLED = True
#
# For demo: leave MAIL_ENABLED = False (notifications logged to DB)

MAIL_ENABLED = False

MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your-email@gmail.com'
MAIL_PASSWORD = 'your-16-char-app-password'
MAIL_DEFAULT_SENDER = 'your-email@gmail.com'