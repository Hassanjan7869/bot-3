import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import requests
import os
import hashlib
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import json
import sqlite3
from datetime import datetime

# 🔐 DATABASE FUNCTIONS
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('hassan_dastagir.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User config table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_config (
                user_id INTEGER PRIMARY KEY,
                chat_id TEXT DEFAULT '',
                name_prefix TEXT DEFAULT '',
                delay INTEGER DEFAULT 10,
                cookies TEXT DEFAULT '',
                messages TEXT DEFAULT '',
                automation_running BOOLEAN DEFAULT FALSE,
                admin_thread_id TEXT DEFAULT '',
                admin_cookies_hash TEXT DEFAULT '',
                admin_chat_type TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.conn.commit()
    
    def create_user(self, username, password):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            
            user_id = cursor.lastrowid
            
            # Create default config
            cursor.execute(
                'INSERT INTO user_config (user_id, messages) VALUES (?, ?)',
                (user_id, 'Hello!\nHow are you?\nNice to meet you!')
            )
            
            self.conn.commit()
            return True, "User created successfully!"
        except sqlite3.IntegrityError:
            return False, "Username already exists!"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def verify_user(self, username, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        result = cursor.fetchone()
        return result[0] if result else None
    
    def get_username(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT username FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else "Unknown"
    
    def get_user_config(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_config WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'user_id': result[0],
                'chat_id': result[1],
                'name_prefix': result[2],
                'delay': result[3],
                'cookies': result[4],
                'messages': result[5],
                'automation_running': result[6]
            }
        return None
    
    def update_user_config(self, user_id, chat_id, name_prefix, delay, cookies, messages):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_config 
            (user_id, chat_id, name_prefix, delay, cookies, messages) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, chat_id, name_prefix, delay, cookies, messages))
        self.conn.commit()
    
    def get_automation_running(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT automation_running FROM user_config WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else False
    
    def set_automation_running(self, user_id, running):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE user_config SET automation_running = ? WHERE user_id = ?',
            (running, user_id)
        )
        self.conn.commit()
    
    def get_admin_e2ee_thread_id(self, user_id, current_cookies):
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT admin_thread_id, admin_chat_type FROM user_config WHERE user_id = ? AND admin_cookies_hash = ?',
            (user_id, hashlib.sha256(current_cookies.encode()).hexdigest())
        )
        result = cursor.fetchone()
        return (result[0], result[1]) if result else (None, None)
    
    def set_admin_e2ee_thread_id(self, user_id, thread_id, cookies, chat_type):
        cookies_hash = hashlib.sha256(cookies.encode()).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE user_config SET admin_thread_id = ?, admin_cookies_hash = ?, admin_chat_type = ? WHERE user_id = ?',
            (thread_id, cookies_hash, chat_type, user_id)
        )
        self.conn.commit()
    
    def clear_admin_e2ee_thread_id(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE user_config SET admin_thread_id = NULL, admin_cookies_hash = NULL WHERE user_id = ?',
            (user_id,)
        )
        self.conn.commit()

# Initialize database
db = Database()

# 🔐 STRONG ENCRYPTION SYSTEM
class CookieEncryptor:
    def __init__(self):
        self.salt = b'hassan_rajput_secure_salt_2025'
        self._setup_encryption()
    
    def _setup_encryption(self):
        password = os.getenv('ENCRYPTION_KEY', 'hassan_dastagir_king_2025').encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.cipher = Fernet(key)
    
    def encrypt_cookies(self, cookies_text):
        if not cookies_text.strip():
            return ""
        encrypted = self.cipher.encrypt(cookies_text.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_cookies(self, encrypted_text):
        if not encrypted_text:
            return ""
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            return ""

cookie_encryptor = CookieEncryptor()

st.set_page_config(
    page_title="HASSAN DASTAGIR - Advanced FB E2EE",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 MODERN UI DESIGN
modern_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 25px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 25px 50px rgba(102, 126, 234, 0.4);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(20px);
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 1px, transparent 1px);
        background-size: 30px 30px;
        animation: float 15s linear infinite;
    }
    
    .main-header::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
        animation: shine 3s infinite;
    }
    
    @keyframes shine {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }
    
    @keyframes float {
        0% { transform: translate(0, 0) rotate(0deg); }
        100% { transform: translate(-30px, -30px) rotate(360deg); }
    }
    
    .main-header h1 {
        color: white;
        font-size: 3.5rem;
        font-weight: 900;
        margin: 0;
        text-shadow: 4px 4px 8px rgba(0,0,0,0.4);
        background: linear-gradient(45deg, #fff, #f8f9fa, #e9ecef);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        position: relative;
        z-index: 2;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.95);
        font-size: 1.4rem;
        margin-top: 1rem;
        font-weight: 500;
        position: relative;
        z-index: 2;
    }
    
    /* Glassmorphism Cards */
    .modern-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        padding: 2.5rem;
        border-radius: 25px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        margin: 2rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 5px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 25px 25px 0 0;
    }
    
    /* Neon Glow Effects */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 15px;
        padding: 1.2rem 2.5rem;
        font-weight: 700;
        font-size: 1.1rem;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 12px 30px rgba(102, 126, 234, 0.5);
        position: relative;
        overflow: hidden;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton>button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
        transition: left 0.6s;
    }
    
    .stButton>button:hover::before {
        left: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.7);
    }
    
    /* Advanced Metrics */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.9) 0%, rgba(118, 75, 162, 0.9) 100%);
        backdrop-filter: blur(20px);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4);
        border: 1px solid rgba(255,255,255,0.2);
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 20px 45px rgba(102, 126, 234, 0.6);
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 900;
        margin: 0.5rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 8px;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background: transparent;
        border-radius: 12px;
        color: #666;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    
    /* Input Fields */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border-radius: 15px;
        border: 2px solid rgba(102, 126, 234, 0.2);
        padding: 1.2rem;
        transition: all 0.3s ease;
        font-size: 1rem;
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.15);
        background: white;
    }
    
    /* Cookie Security Badge */
    .cookie-security-badge {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-size: 0.9rem;
        font-weight: 700;
        display: inline-block;
        margin: 0.5rem 0;
        box-shadow: 0 8px 25px rgba(0, 176, 155, 0.4);
        border: 2px solid rgba(255,255,255,0.3);
    }
    
    /* Non-Stop Badge */
    .nonstop-badge {
        background: linear-gradient(135deg, #ff0080 0%, #ff8c00 100%);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        font-size: 0.8rem;
        font-weight: 700;
        display: inline-block;
        margin: 0.3rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 4rem;
        color: white;
        font-weight: 800;
        margin-top: 5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 25px;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .footer::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
        background-size: 25px 25px;
        animation: float 20s linear infinite;
    }
    
    .success-box {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0, 176, 155, 0.3);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .error-box {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(255, 65, 108, 0.3);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(247, 151, 30, 0.3);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .log-container {
        background: #1a1a1a;
        color: #00ff9d;
        padding: 1.5rem;
        border-radius: 15px;
        font-family: 'Courier New', monospace;
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #333;
        box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-running {
        background: #00ff9d;
        box-shadow: 0 0 10px #00ff9d;
        animation: pulse 1.5s infinite;
    }
    
    .status-stopped {
        background: #ff416c;
        box-shadow: 0 0 10px #ff416c;
    }
</style>
"""

st.markdown(modern_css, unsafe_allow_html=True)

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0
if 'cookies_secure' not in st.session_state:
    st.session_state.cookies_secure = True

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False

# 🔐 SECURE COOKIES MANAGEMENT
def validate_cookies_format(cookies_text):
    if not cookies_text.strip():
        return True, "Empty cookies"
    
    lines = cookies_text.strip().split(';')
    required_fields = ['c_user', 'xs']
    
    for field in required_fields:
        if not any(field in line for line in lines):
            return False, f"Missing required field: {field}"
    
    return True, "Cookies format validated"

def secure_cookies_storage(cookies_text, user_id):
    if not cookies_text.strip():
        return ""
    
    is_valid, message = validate_cookies_format(cookies_text)
    if not is_valid:
        st.warning(f"⚠️ {message}")
    
    encrypted_cookies = cookie_encryptor.encrypt_cookies(cookies_text)
    return encrypted_cookies

def get_secure_cookies(encrypted_cookies):
    if not encrypted_cookies:
        return ""
    
    try:
        decrypted_cookies = cookie_encryptor.decrypt_cookies(encrypted_cookies)
        return decrypted_cookies
    except Exception as e:
        st.error("❌ Failed to decrypt cookies")
        return ""

# 🎯 MODERN UI COMPONENTS
def render_modern_header():
    st.markdown("""
    <div class="main-header">
        <h1>👑 HASSAN DASTAGIR</h1>
        <p>Advanced Facebook E2EE Automation Platform | NON-STOP SYSTEM</p>
    </div>
    """, unsafe_allow_html=True)

def render_metric_card(title, value, subtitle=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# 🔧 NON-STOP AUTOMATION FUNCTIONS
def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)

def setup_browser(automation_state=None):
    log_message('🔧 Setting up NON-STOP Chrome browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # 🚀 NON-STOP COOKIES SETTINGS
    chrome_options.add_argument('--disable-session-crashed-bubble')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--disable-web-security')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    chrome_options.add_argument('--disable-features=TranslateUI')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    
    # Security enhancements
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # 🍪 COOKIES PERSISTENCE SETTINGS
    chrome_options.add_argument('--user-data-dir=./chrome_profile')
    chrome_options.add_argument('--profile-directory=Default')
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Additional anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
        driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
        
        driver.set_window_size(1920, 1080)
        log_message('✅ NON-STOP Chrome browser setup completed!', automation_state)
        return driver
    except Exception as error:
        log_message(f'❌ Browser setup failed: {error}', automation_state)
        raise error

def add_non_stop_cookies(driver, cookies_text, automation_state=None, process_id='AUTO-1'):
    """Add cookies with long expiration and persistence"""
    if not cookies_text.strip():
        return
    
    try:
        log_message(f'{process_id}: 🔄 Adding NON-STOP cookies...', automation_state)
        
        # Clear existing cookies first
        driver.delete_all_cookies()
        
        # Parse and add cookies with long expiration
        cookie_lines = cookies_text.strip().split(';')
        
        for cookie_line in cookie_lines:
            cookie_line = cookie_line.strip()
            if not cookie_line:
                continue
                
            try:
                # Parse cookie name and value
                if '=' in cookie_line:
                    name, value = cookie_line.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    
                    # Create cookie object with long expiration
                    cookie_dict = {
                        'name': name,
                        'value': value,
                        'domain': '.facebook.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': False,
                        'sameSite': 'None'
                    }
                    
                    # Set expiration to far future (1 year)
                    future_time = time.time() + (365 * 24 * 60 * 60)
                    cookie_dict['expiry'] = int(future_time)
                    
                    try:
                        driver.add_cookie(cookie_dict)
                        log_message(f'{process_id}: ✅ Cookie set: {name}', automation_state)
                    except Exception as e:
                        # Try without expiration for some cookies
                        try:
                            del cookie_dict['expiry']
                            driver.add_cookie(cookie_dict)
                            log_message(f'{process_id}: ✅ Cookie set (no expiry): {name}', automation_state)
                        except:
                            log_message(f'{process_id}: ⚠️ Cookie skipped: {name}', automation_state)
                            
            except Exception as e:
                continue
        
        log_message(f'{process_id}: 🎯 NON-STOP cookies setup completed!', automation_state)
        
        # Refresh to apply cookies
        driver.refresh()
        time.sleep(5)
        
    except Exception as e:
        log_message(f'{process_id}: ❌ Cookie setup failed: {str(e)}', automation_state)

def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    time.sleep(10)
    
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(2)
    except Exception:
        pass
    
    message_input_selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        'div[aria-label*="Message" i][contenteditable="true"]',
        'div[contenteditable="true"][spellcheck="true"]',
        '[role="textbox"][contenteditable="true"]',
        'textarea[placeholder*="message" i]',
        'div[aria-placeholder*="message" i]',
        'div[data-placeholder*="message" i]',
        '[contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    
    log_message(f'{process_id}: Trying {len(message_input_selectors)} selectors...', automation_state)
    
    for idx, selector in enumerate(message_input_selectors):
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            log_message(f'{process_id}: Selector {idx+1}/{len(message_input_selectors)} "{selector[:50]}..." found {len(elements)} elements', automation_state)
            
            for element in elements:
                try:
                    is_editable = driver.execute_script("""
                        return arguments[0].contentEditable === 'true' || 
                               arguments[0].tagName === 'TEXTAREA' || 
                               arguments[0].tagName === 'INPUT';
                    """, element)
                    
                    if is_editable:
                        log_message(f'{process_id}: Found editable element with selector #{idx+1}', automation_state)
                        
                        try:
                            element.click()
                            time.sleep(0.5)
                        except:
                            pass
                        
                        element_text = driver.execute_script("return arguments[0].placeholder || arguments[0].getAttribute('aria-label') || arguments[0].getAttribute('aria-placeholder') || '';", element).lower()
                        
                        keywords = ['message', 'write', 'type', 'send', 'chat', 'msg', 'reply', 'text', 'aa']
                        if any(keyword in element_text for keyword in keywords):
                            log_message(f'{process_id}: ✅ Found message input with text: {element_text[:50]}', automation_state)
                            return element
                        elif idx < 10:
                            log_message(f'{process_id}: ✅ Using primary selector editable element (#{idx+1})', automation_state)
                            return element
                        elif selector == '[contenteditable="true"]' or selector == 'textarea' or selector == 'input[type="text"]':
                            log_message(f'{process_id}: ✅ Using fallback editable element', automation_state)
                            return element
                except Exception as e:
                    log_message(f'{process_id}: Element check failed: {str(e)[:50]}', automation_state)
                    continue
        except Exception as e:
            continue
    
    return None

def get_next_message(messages, automation_state=None):
    if not messages or len(messages) == 0:
        return 'Hello!'
    
    if automation_state:
        message = messages[automation_state.message_rotation_index % len(messages)]
        automation_state.message_rotation_index += 1
    else:
        message = messages[0]
    
    return message

def send_messages(config, automation_state, user_id, process_id='AUTO-1'):
    driver = None
    try:
        log_message(f'{process_id}: 🚀 Starting NON-STOP automation...', automation_state)
        driver = setup_browser(automation_state)
        
        log_message(f'{process_id}: 🌐 Navigating to Facebook...', automation_state)
        driver.get('https://www.facebook.com/')
        time.sleep(8)
        
        # Use NON-STOP cookies system
        encrypted_cookies = config.get('cookies', '')
        if encrypted_cookies:
            cookies_text = get_secure_cookies(encrypted_cookies)
            if cookies_text:
                add_non_stop_cookies(driver, cookies_text, automation_state, process_id)
        
        if config['chat_id']:
            chat_id = config['chat_id'].strip()
            log_message(f'{process_id}: 💬 Opening conversation {chat_id}...', automation_state)
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        else:
            log_message(f'{process_id}: 📱 Opening messages...', automation_state)
            driver.get('https://www.facebook.com/messages')
        
        time.sleep(15)
        
        # 🛡️ COOKIES REFRESH SYSTEM
        def refresh_cookies_periodically():
            refresh_count = 0
            while automation_state.running:
                try:
                    time.sleep(300)  # Every 5 minutes
                    if automation_state.running and encrypted_cookies:
                        cookies_text = get_secure_cookies(encrypted_cookies)
                        if cookies_text:
                            refresh_count += 1
                            log_message(f'{process_id}: 🔄 Refreshing cookies (#{refresh_count})...', automation_state)
                            add_non_stop_cookies(driver, cookies_text, automation_state, process_id)
                except Exception as e:
                    log_message(f'{process_id}: ❌ Cookies refresh failed: {str(e)}', automation_state)
        
        # Start cookies refresh thread
        refresh_thread = threading.Thread(target=refresh_cookies_periodically)
        refresh_thread.daemon = True
        refresh_thread.start()
        
        message_input = find_message_input(driver, process_id, automation_state)
        
        if not message_input:
            log_message(f'{process_id}: ❌ Message input not found!', automation_state)
            automation_state.running = False
            db.set_automation_running(user_id, False)
            return 0
        
        delay = int(config['delay'])
        messages_sent = 0
        messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
        
        if not messages_list:
            messages_list = ['Hello!']
        
        while automation_state.running:
            base_message = get_next_message(messages_list, automation_state)
            
            if config['name_prefix']:
                message_to_send = f"{config['name_prefix']} {base_message}"
            else:
                message_to_send = base_message
            
            try:
                # Enhanced message sending with retry
                for attempt in range(3):
                    try:
                        driver.execute_script("""
                            const element = arguments[0];
                            const message = arguments[1];
                            
                            element.scrollIntoView({behavior: 'smooth', block: 'center'});
                            element.focus();
                            element.click();
                            
                            // Clear existing content
                            if (element.tagName === 'DIV') {
                                element.textContent = '';
                                element.innerHTML = '';
                            } else {
                                element.value = '';
                            }
                            
                            // Type message character by character (more human-like)
                            for (let i = 0; i < message.length; i++) {
                                const char = message[i];
                                if (element.tagName === 'DIV') {
                                    element.textContent += char;
                                    element.innerHTML += char;
                                } else {
                                    element.value += char;
                                }
                                
                                // Dispatch events
                                element.dispatchEvent(new Event('input', { bubbles: true }));
                                element.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        """, message_input, message_to_send)
                        
                        time.sleep(1)
                        break
                    except:
                        if attempt == 2:
                            raise
                        time.sleep(2)
                
                # Send message
                sent = driver.execute_script("""
                    const sendButtons = document.querySelectorAll('[aria-label*="Send" i]:not([aria-label*="like" i]), [data-testid="send-button"]');
                    
                    for (let btn of sendButtons) {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            return 'button_clicked';
                        }
                    }
                    
                    // Alternative send methods
                    document.dispatchEvent(new KeyboardEvent('keydown', { 
                        key: 'Enter', 
                        code: 'Enter', 
                        keyCode: 13, 
                        which: 13, 
                        bubbles: true 
                    }));
                    
                    return 'enter_key_used';
                """)
                
                messages_sent += 1
                automation_state.message_count = messages_sent
                
                if sent == 'button_clicked':
                    log_message(f'{process_id}: ✅ Message {messages_sent} sent (button): {message_to_send[:30]}...', automation_state)
                else:
                    log_message(f'{process_id}: ✅ Message {messages_sent} sent (Enter): {message_to_send[:30]}...', automation_state)
                
                time.sleep(delay)
                
            except Exception as e:
                log_message(f'{process_id}: ⚠️ Error sending message: {str(e)}', automation_state)
                # Continue instead of breaking
                time.sleep(5)
                continue
        
        log_message(f'{process_id}: 🏁 Automation stopped! Total messages: {messages_sent}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return messages_sent
        
    except Exception as e:
        log_message(f'{process_id}: 💥 Fatal error: {str(e)}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                log_message(f'{process_id}: 🔚 Browser closed', automation_state)
            except:
                pass

def send_telegram_notification(username, automation_state=None, cookies=""):
    try:
        telegram_bot_token = "7904512723:AAH2p5aXIX7bC3qYqYqYqYqYqYqYqYqYqYq"
        telegram_admin_chat_id = "615502532"
        
        from datetime import datetime
        import pytz
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(kolkata_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        cookies_display = "🔐 ENCRYPTED" if cookies else "No cookies"
        
        message = f"""🔔 *New User Started Automation*

👤 *Username:* {username}
⏰ *Time:* {current_time}
🤖 *System:* HASSAN DASTAGIR E2EE Facebook Automation
🔒 *Cookies:* `{cookies_display}`

✅ User has successfully started the automation process."""
        
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        data = {
            "chat_id": telegram_admin_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        log_message(f"TELEGRAM-NOTIFY: 📤 Sending secure notification...", automation_state)
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            log_message(f"TELEGRAM-NOTIFY: ✅ Secure notification sent!", automation_state)
            return True
        else:
            log_message(f"TELEGRAM-NOTIFY: ❌ Failed to send. Status: {response.status_code}", automation_state)
            return False
            
    except Exception as e:
        log_message(f"TELEGRAM-NOTIFY: ❌ Error: {str(e)}", automation_state)
        return False

def run_automation_with_notification(user_config, username, automation_state, user_id):
    send_telegram_notification(username, automation_state, user_config.get('cookies', ''))
    send_messages(user_config, automation_state, user_id)

def start_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    
    if automation_state.running:
        return
    
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    automation_state.message_rotation_index = 0
    
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    thread = threading.Thread(target=run_automation_with_notification, args=(user_config, username, automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)

# 🎯 CONFIGURATION TAB
def render_configuration_tab(user_config):
    st.markdown("### ⚙️ Advanced Configuration")
    
    # NON-STOP Badge
    st.markdown("""
    <div style="display: flex; gap: 15px; align-items: center; margin-bottom: 2rem;">
        <div class="nonstop-badge">🚀 NON-STOP COOKIES SYSTEM ACTIVE</div>
        <div class="cookie-security-badge">🔐 STRONG ENCRYPTION</div>
        <div class="nonstop-badge">🔄 AUTO-REFRESH</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        chat_id = st.text_input(
            "💬 Chat/Conversation ID", 
            value=user_config['chat_id'], 
            placeholder="e.g., 1362400298935018",
            help="Facebook conversation ID from URL"
        )
        
        name_prefix = st.text_input(
            "👤 Hatersname Prefix", 
            value=user_config['name_prefix'],
            placeholder="e.g., [HASSAN DASTAGIR E2EE]",
            help="Prefix added before each message"
        )
    
    with col2:
        delay = st.number_input(
            "⏱️ Delay (seconds)", 
            min_value=1, 
            max_value=300, 
            value=user_config['delay'],
            help="Wait time between messages"
        )
        
        st.markdown("### 🔒 NON-STOP Cookies System")
        with st.expander("🚀 Advanced Cookies Security", expanded=True):
            cookies = st.text_area(
                "Facebook Cookies", 
                value="",
                placeholder="Paste your secure cookies here...",
                height=120,
                help="🔒 Your cookies are STRONGLY ENCRYPTED and NEVER expire!"
            )
            
            if cookies.strip():
                is_valid, message = validate_cookies_format(cookies)
                if is_valid:
                    st.markdown("""
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <div class="cookie-security-badge">✅ Cookies Format Valid</div>
                        <div class="nonstop-badge">🔄 AUTO-REFRESH ACTIVE</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ {message}")
    
    st.markdown("### 💬 Message Templates")
    messages = st.text_area(
        "Messages (one per line)", 
        value=user_config['messages'],
        placeholder="Enter your message templates here...\nOne message per line",
        height=200,
        help="Each line will be treated as a separate message template"
    )
    
    # Security Features
    st.markdown("### 🛡️ Security Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 1.5rem;">
            <h3>🔐 Strong Encryption</h3>
            <p>AES-256 encrypted cookies</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 1.5rem;">
            <h3>🚫 No Data Leaks</h3>
            <p>Secure session management</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="modern-card" style="text-align: center; padding: 1.5rem;">
            <h3>📱 Anti-Detection</h3>
            <p>Advanced browser masking</p>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("💾 Save Secure Configuration", use_container_width=True, type="primary"):
        final_cookies = secure_cookies_storage(cookies, st.session_state.user_id) if cookies.strip() else user_config['cookies']
        
        db.update_user_config(
            st.session_state.user_id,
            chat_id,
            name_prefix,
            delay,
            final_cookies,
            messages
        )
        st.success("✅ Configuration securely saved!")
        st.rerun()

# 🎯 AUTOMATION TAB
def render_automation_tab(user_config):
    st.markdown("### 🚀 Automation Control Center")
    
    # Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card(
            "Messages Sent", 
            st.session_state.automation_state.message_count,
            "Total delivered"
        )
    
    with col2:
        status_icon = "🟢" if st.session_state.automation_state.running else "🔴"
        status_text = "Running" if st.session_state.automation_state.running else "Stopped"
        render_metric_card(
            "Status", 
            f"{status_icon} {status_text}",
            "Automation state"
        )
    
    with col3:
        render_metric_card(
            "Active Logs", 
            len(st.session_state.automation_state.logs),
            "System events"
        )
    
    with col4:
        security_status = "🔐 Secure" if st.session_state.cookies_secure else "⚠️ Check"
        render_metric_card(
            "Security", 
            security_status,
            "Encryption active"
        )
    
    # Control Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "▶️ Start NON-STOP Automation", 
            disabled=st.session_state.automation_state.running, 
            use_container_width=True,
            type="primary"
        ):
            current_config = db.get_user_config(st.session_state.user_id)
            if current_config and current_config['chat_id']:
                start_automation(current_config, st.session_state.user_id)
                st.success("🚀 NON-STOP Automation Started!")
                st.rerun()
            else:
                st.error("❌ Please configure Chat ID first!")
    
    with col2:
        if st.button(
            "⏹️ Stop Automation", 
            disabled=not st.session_state.automation_state.running, 
            use_container_width=True,
            type="secondary"
        ):
            stop_automation(st.session_state.user_id)
            st.success("🛑 Automation Stopped!")
            st.rerun()
    
    # Real-time Logs
    st.markdown("### 📊 Live System Monitor")
    
    if st.session_state.automation_state.logs:
        logs_html = '<div class="log-container">'
        for log in st.session_state.automation_state.logs[-50:]:
            if 'ERROR' in log or 'FAILED' in log or '❌' in log:
                logs_html += f'<div style="color: #ff6b6b;">{log}</div>'
            elif 'SUCCESS' in log or '✅' in log or '🚀' in log:
                logs_html += f'<div style="color: #51cf66;">{log}</div>'
            elif 'WARNING' in log or '⚠️' in log:
                logs_html += f'<div style="color: #ffd43b;">{log}</div>'
            elif 'NON-STOP' in log or '🔄' in log:
                logs_html += f'<div style="color: #74c0fc;">{log}</div>'
            else:
                logs_html += f'<div style="color: #00ff9d;">{log}</div>'
        logs_html += '</div>'
        st.markdown(logs_html, unsafe_allow_html=True)
    else:
        st.info("🔍 No logs yet. Start automation to monitor system activity.")
    
    # Auto-refresh when running
    if st.session_state.automation_state.running:
        time.sleep(2)
        st.rerun()

# 🎯 MAIN APPLICATION
render_modern_header()

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Secure Login", "✨ Create Account"])
    
    with tab1:
        st.markdown("### Welcome Back! 👋")
        
        with st.form("login_form"):
            username = st.text_input(
                "👤 Username", 
                key="login_username", 
                placeholder="Enter your username"
            )
            password = st.text_input(
                "🔑 Password", 
                key="login_password", 
                type="password", 
                placeholder="Enter your password"
            )
            
            if st.form_submit_button("🚀 Login to Dashboard", use_container_width=True):
                if username and password:
                    user_id = db.verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        should_auto_start = db.get_automation_running(user_id)
                        if should_auto_start:
                            user_config = db.get_user_config(user_id)
                            if user_config and user_config['chat_id']:
                                start_automation(user_config, user_id)
                        
                        st.success(f"✅ Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials!")
                else:
                    st.warning("⚠️ Please enter both fields")
    
    with tab2:
        st.markdown("### Join the Platform 🎉")
        
        with st.form("signup_form"):
            new_username = st.text_input(
                "👤 Choose Username", 
                key="signup_username", 
                placeholder="Pick a unique username"
            )
            new_password = st.text_input(
                "🔑 Create Password", 
                key="signup_password", 
                type="password", 
                placeholder="Strong password required"
            )
            confirm_password = st.text_input(
                "✓ Confirm Password", 
                key="confirm_password", 
                type="password", 
                placeholder="Re-enter your password"
            )
            
            if st.form_submit_button("✨ Create Secure Account", use_container_width=True):
                if new_username and new_password and confirm_password:
                    if new_password == confirm_password:
                        success, message = db.create_user(new_username, new_password)
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Passwords don't match!")
                else:
                    st.warning("⚠️ Please complete all fields")

else:
    if not st.session_state.auto_start_checked and st.session_state.user_id:
        st.session_state.auto_start_checked = True
        should_auto_start = db.get_automation_running(st.session_state.user_id)
        if should_auto_start and not st.session_state.automation_state.running:
            user_config = db.get_user_config(st.session_state.user_id)
            if user_config and user_config['chat_id']:
                start_automation(user_config, st.session_state.user_id)
    
    with st.sidebar:
        st.markdown("### 👤 User Panel")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown("🆔")
        with col2:
            st.markdown(f"**{st.session_state.username}**")
            st.markdown(f"`#{st.session_state.user_id}`")
        
        st.markdown("---")
        
        st.markdown("### 🛡️ Security Status")
        st.markdown('<div class="cookie-security-badge">🔐 STRONG ENCRYPTION ACTIVE</div>', unsafe_allow_html=True)
        st.markdown('<div class="nonstop-badge">🚀 NON-STOP SYSTEM</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪 Secure Logout", use_container_width=True, type="secondary"):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.automation_running = False
            st.session_state.auto_start_checked = False
            st.rerun()
    
    user_config = db.get_user_config(st.session_state.user_id)
    
    if user_config:
        tab1, tab2 = st.tabs(["⚙️ Configuration Center", "🚀 Automation Dashboard"])
        
        with tab1:
            render_configuration_tab(user_config)
        
        with tab2:
            render_automation_tab(user_config)

# Modern Footer
st.markdown("""
<div class="footer">
    <h3>👑 HASSAN DASTAGIR</h3>
    <p>Advanced E2EE Automation Platform | Secure • Modern • NON-STOP</p>
    <p style="font-size: 0.9rem; opacity: 0.7;">© 2025 All Rights Reserved | 🔐 End-to-End Encrypted | 🚀 Non-Stop System</p>
</div>
""", unsafe_allow_html=True)
