import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'waf.db')

class Config:
    SECRET_KEY = 'cloudwaf-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WAF_MODE = 'protection'

    CC_RATE_LIMIT = 60
    CC_WINDOW = 60
    CC_BLOCK_DURATION = 300

    SCAN_404_THRESHOLD = 20
    SCAN_WINDOW = 60
    SCAN_BLOCK_DURATION = 600

    ADMIN_USERNAME = 'admin'
    ADMIN_PASSWORD = 'admin123'

    DEFAULT_BACKEND = 'http://httpbin.org'
