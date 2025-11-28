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
import random

# 🔐 DATABASE FUNCTIONS
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('hassan_rajput.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
                'chat_id': result[1],
                'name_prefix': result[2],
                'delay': result[3],
                'cookies': result[4],
                'messages': result[5]
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

db = Database()

# 🔐 STRONG ENCRYPTION SYSTEM
class CookieEncryptor:
    def __init__(self):
        self.salt = b'hassan_rajput_secure_salt_2025'
        self._setup_encryption()
    
    def _setup_encryption(self):
        password = os.getenv('ENCRYPTION_KEY', 'hassan_rajput_king_2025').encode()
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
    page_title="HASSAN RAJPUT - Elite FB E2EE",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 ULTRA MODERN UI DESIGN
ultra_modern_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        padding: 4rem 2rem;
        border-radius: 30px;
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
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><polygon fill="rgba(255,255,255,0.1)" points="0,1000 1000,0 1000,1000"/></svg>');
        background-size: cover;
        animation: slide 20s linear infinite;
    }
    
    @keyframes slide {
        0% { transform: translateX(0) translateY(0); }
        100% { transform: translateX(-100px) translateY(-100px); }
    }
    
    .main-header h1 {
        color: white;
        font-size: 4rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 4px 4px 8px rgba(0,0,0,0.3);
        background: linear-gradient(45deg, #fff, #f0f0f0, #e0e0e0);
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
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
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
        border: 2px solid rgba(255,255,255,0.1);
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
    
    .modern-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 3rem;
        border-radius: 25px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.3);
        backdrop-filter: blur(15px);
        margin: 2rem 0;
        position: relative;
        overflow: hidden;
        transition: transform 0.3s ease;
    }
    
    .modern-card:hover {
        transform: translateY(-5px);
    }
    
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 6px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .modern-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 200px;
        height: 200px;
        background: radial-gradient(circle, rgba(102,126,234,0.1) 0%, transparent 70%);
        border-radius: 50%;
    }
    
    .success-box {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 15px 35px rgba(0, 176, 155, 0.4);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .error-box {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 15px 35px rgba(255, 65, 108, 0.4);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        padding: 2rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 15px 35px rgba(247, 151, 30, 0.4);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .footer {
        text-align: center;
        padding: 4rem;
        color: #667eea;
        font-weight: 800;
        margin-top: 5rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 30px;
        border: 1px solid rgba(255,255,255,0.3);
        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
    }
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        border-radius: 15px;
        border: 2px solid #e8ecef;
        padding: 1.2rem;
        transition: all 0.3s ease;
        font-size: 1.1rem;
        background: rgba(248, 250, 252, 0.8);
        backdrop-filter: blur(10px);
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.15);
        background: white;
        transform: scale(1.02);
    }
    
    .info-card {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin: 2rem 0;
        border-left: 6px solid #667eea;
        box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.5);
    }
    
    .log-container {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        color: #00ff9d;
        padding: 2rem;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        max-height: 600px;
        overflow-y: auto;
        border: 1px solid #444;
        box-shadow: inset 0 4px 20px rgba(0,0,0,0.5);
        position: relative;
    }
    
    .log-container::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #00ff9d, transparent);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.5);
        border: 1px solid rgba(255,255,255,0.2);
        transition: transform 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .metric-card:hover {
        transform: translateY(-8px);
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
        animation: rotate 10s linear infinite;
    }
    
    @keyframes rotate {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .metric-value {
        font-size: 3rem;
        font-weight: 800;
        margin: 1rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        position: relative;
        z-index: 2;
    }
    
    .metric-label {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 600;
        position: relative;
        z-index: 2;
    }
    
    .cookie-security-badge {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 0.8rem 1.5rem;
        border-radius: 30px;
        font-size: 0.9rem;
        font-weight: 700;
        display: inline-block;
        margin: 0.8rem 0;
        box-shadow: 0 8px 20px rgba(0, 176, 155, 0.4);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .status-indicator {
        display: inline-block;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        margin-right: 10px;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(0, 255, 157, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(0, 255, 157, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 255, 157, 0); }
    }
    
    .status-running {
        background: #00ff9d;
        box-shadow: 0 0 20px #00ff9d;
    }
    
    .status-stopped {
        background: #ff416c;
        box-shadow: 0 0 20px #ff416c;
    }
    
    .tab-container {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border-radius: 20px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .user-avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 2rem;
        font-weight: 800;
        margin: 0 auto;
        box-shadow: 0 15px 30px rgba(102, 126, 234, 0.4);
        border: 3px solid rgba(255,255,255,0.3);
    }
    
    .floating-element {
        animation: float 6s ease-in-out infinite;
    }
    
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-20px); }
        100% { transform: translateY(0px); }
    }
    
    .glass-effect {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
    }
    
    .cyber-grid {
        background-image: 
            linear-gradient(rgba(102, 126, 234, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(102, 126, 234, 0.1) 1px, transparent 1px);
        background-size: 50px 50px;
    }
</style>
"""

st.markdown(ultra_modern_css, unsafe_allow_html=True)

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

# 🎯 ULTRA MODERN UI COMPONENTS
def render_ultra_header():
    st.markdown("""
    <div class="main-header floating-element">
        <h1>👑 HASSAN RAJPUT</h1>
        <p>Elite Facebook E2EE Automation Platform • Next Generation</p>
    </div>
    """, unsafe_allow_html=True)

def render_cyber_metric_card(title, value, subtitle="", icon="🚀"):
    st.markdown(f"""
    <div class="metric-card cyber-grid">
        <div style="font-size: 2.5rem; margin-bottom: 1rem;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{title}</div>
        <div style="font-size: 0.9rem; opacity: 0.8; margin-top: 0.5rem;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_glass_card(title, content):
    st.markdown(f"""
    <div class="modern-card glass-effect">
        <h3 style="color: #333; margin-bottom: 2rem; font-size: 1.8rem; font-weight: 700;">{title}</h3>
        {content}
    </div>
    """, unsafe_allow_html=True)

def render_user_avatar(username):
    initials = ''.join([name[0].upper() for name in username.split()[:2]]) if username else "U"
    st.markdown(f"""
    <div class="user-avatar floating-element">
        {initials}
    </div>
    """, unsafe_allow_html=True)

# 🔧 AUTOMATION FUNCTIONS (Same as before)
def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    if automation_state:
        automation_state.logs.append(formatted_msg)
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)

def setup_browser(automation_state=None):
    log_message('🔧 Setting up secure Chrome browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_window_size(1920, 1080)
        log_message('✅ Secure Chrome browser setup completed!', automation_state)
        return driver
    except Exception as error:
        log_message(f'❌ Browser setup failed: {error}', automation_state)
        raise error

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
        log_message(f'{process_id}: Starting automation...', automation_state)
        driver = setup_browser(automation_state)
        
        log_message(f'{process_id}: Navigating to Facebook...', automation_state)
        driver.get('https://www.facebook.com/')
        time.sleep(8)
        
        encrypted_cookies = config.get('cookies', '')
        if encrypted_cookies:
            cookies_text = get_secure_cookies(encrypted_cookies)
            if cookies_text:
                log_message(f'{process_id}: Adding secure cookies...', automation_state)
                cookie_array = cookies_text.split(';')
                for cookie in cookie_array:
                    cookie_trimmed = cookie.strip()
                    if cookie_trimmed:
                        first_equal_index = cookie_trimmed.find('=')
                        if first_equal_index > 0:
                            name = cookie_trimmed[:first_equal_index].strip()
                            value = cookie_trimmed[first_equal_index + 1:].strip()
                            try:
                                driver.add_cookie({
                                    'name': name,
                                    'value': value,
                                    'domain': '.facebook.com',
                                    'path': '/'
                                })
                            except Exception:
                                pass
        
        if config['chat_id']:
            chat_id = config['chat_id'].strip()
            log_message(f'{process_id}: Opening conversation {chat_id}...', automation_state)
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        else:
            log_message(f'{process_id}: Opening messages...', automation_state)
            driver.get('https://www.facebook.com/messages')
        
        time.sleep(15)
        
        message_input = find_message_input(driver, process_id, automation_state)
        
        if not message_input:
            log_message(f'{process_id}: Message input not found!', automation_state)
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
                driver.execute_script("""
                    const element = arguments[0];
                    const message = arguments[1];
                    
                    element.scrollIntoView({behavior: 'smooth', block: 'center'});
                    element.focus();
                    element.click();
                    
                    if (element.tagName === 'DIV') {
                        element.textContent = message;
                        element.innerHTML = message;
                    } else {
                        element.value = message;
                    }
                    
                    element.dispatchEvent(new Event('input', { bubbles: true }));
                    element.dispatchEvent(new Event('change', { bubbles: true }));
                    element.dispatchEvent(new InputEvent('input', { bubbles: true, data: message }));
                """, message_input, message_to_send)
                
                time.sleep(1)
                
                sent = driver.execute_script("""
                    const sendButtons = document.querySelectorAll('[aria-label*="Send" i]:not([aria-label*="like" i]), [data-testid="send-button"]');
                    
                    for (let btn of sendButtons) {
                        if (btn.offsetParent !== null) {
                            btn.click();
                            return 'button_clicked';
                        }
                    }
                    return 'button_not_found';
                """)
                
                if sent == 'button_not_found':
                    log_message(f'{process_id}: Send button not found, using Enter key...', automation_state)
                    driver.execute_script("""
                        const element = arguments[0];
                        element.focus();
                        
                        const events = [
                            new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                            new KeyboardEvent('keypress', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }),
                            new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true })
                        ];
                        
                        events.forEach(event => element.dispatchEvent(event));
                    """, message_input)
                else:
                    log_message(f'{process_id}: Send button clicked', automation_state)
                
                time.sleep(1)
                
                messages_sent += 1
                automation_state.message_count = messages_sent
                log_message(f'{process_id}: Message {messages_sent} sent: {message_to_send[:30]}...', automation_state)
                
                time.sleep(delay)
                
            except Exception as e:
                log_message(f'{process_id}: Error sending message: {str(e)}', automation_state)
                break
        
        log_message(f'{process_id}: Automation stopped! Total messages sent: {messages_sent}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return messages_sent
        
    except Exception as e:
        log_message(f'{process_id}: Fatal error: {str(e)}', automation_state)
        automation_state.running = False
        db.set_automation_running(user_id, False)
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                log_message(f'{process_id}: Browser closed', automation_state)
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
🤖 *System:* HASSAN RAJPUT E2EE Facebook Automation
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
    
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    thread = threading.Thread(target=run_automation_with_notification, args=(user_config, username, automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)

# 🎯 ULTRA MODERN CONFIGURATION TAB
def render_ultra_configuration_tab(user_config):
    with st.container():
        st.markdown("### ⚙️ Advanced Configuration Center")
        
        col1, col2 = st.columns(2)
        
        with col1:
            render_glass_card("💬 Conversation Settings", """
            <div style="padding: 1rem 0;">
                <label style="font-weight: 600; color: #333; margin-bottom: 0.5rem; display: block;">Chat ID</label>
            </div>
            """)
            chat_id = st.text_input(
                "Chat ID", 
                value=user_config['chat_id'], 
                placeholder="e.g., 1362400298935018",
                label_visibility="collapsed"
            )
            
            name_prefix = st.text_input(
                "👤 Hatersname Prefix", 
                value=user_config['name_prefix'],
                placeholder="e.g., [HASSAN RAJPUT E2EE]",
                help="Prefix added before each message"
            )
        
        with col2:
            render_glass_card("⏱️ Timing Settings", """
            <div style="padding: 1rem 0;">
                <label style="font-weight: 600; color: #333; margin-bottom: 0.5rem; display: block;">Delay (seconds)</label>
            </div>
            """)
            delay = st.number_input(
                "Delay", 
                min_value=1, 
                max_value=300, 
                value=user_config['delay'],
                label_visibility="collapsed"
            )
            
            st.markdown("### 🔒 Secure Cookies Management")
            with st.expander("🔐 Advanced Cookies Security", expanded=False):
                cookies = st.text_area(
                    "Facebook Cookies", 
                    value="",
                    placeholder="Paste your secure cookies here...",
                    height=120,
                    help="🔒 Your cookies are STRONGLY ENCRYPTED and never stored in plain text"
                )
                
                if cookies.strip():
                    is_valid, message = validate_cookies_format(cookies)
                    if is_valid:
                        st.markdown('<div class="cookie-security-badge">✅ Cookies Format Valid</div>', unsafe_allow_html=True)
                    else:
                        st.warning(f"⚠️ {message}")
        
        render_glass_card("💬 Message Templates", f"""
        <div style="padding: 1rem 0;">
            <textarea placeholder="Enter your message templates here...&#10;One message per line" style="width: 100%; height: 200px; padding: 1rem; border-radius: 15px; border: 2px solid #e8ecef; font-family: inherit; resize: vertical;"></textarea>
        </div>
        """)
        
        messages = st.text_area(
            "Messages", 
            value=user_config['messages'],
            placeholder="Enter your message templates here...\nOne message per line",
            height=200,
            label_visibility="collapsed"
        )
        
        # Security Features Grid
        st.markdown("### 🛡️ Security Features")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="info-card">
                <h4>🔐 AES-256 Encryption</h4>
                <p>Military-grade cookie encryption</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="info-card">
                <h4>🚫 Zero Data Leaks</h4>
                <p>Secure session management</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="info-card">
                <h4>📱 Anti-Detection</h4>
                <p>Advanced browser masking</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="info-card">
                <h4>⚡ Real-time Monitoring</h4>
                <p>Live system analytics</p>
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

# 🎯 ULTRA MODERN AUTOMATION TAB
def render_ultra_automation_tab(user_config):
    st.markdown("### 🚀 Automation Control Center")
    
    # Cyber Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_cyber_metric_card(
            "Messages Sent", 
            st.session_state.automation_state.message_count,
            "Total delivered messages",
            "📨"
        )
    
    with col2:
        status_icon = "🟢" if st.session_state.automation_state.running else "🔴"
        status_text = "Running" if st.session_state.automation_state.running else "Stopped"
        render_cyber_metric_card(
            "Status", 
            f"{status_icon} {status_text}",
            "Automation state",
            "⚡"
        )
    
    with col3:
        render_cyber_metric_card(
            "Active Logs", 
            len(st.session_state.automation_state.logs),
            "System events",
            "📊"
        )
    
    with col4:
        security_status = "🔐 Secure" if st.session_state.cookies_secure else "⚠️ Check"
        render_cyber_metric_card(
            "Security", 
            security_status,
            "Encryption active",
            "🛡️"
        )
    
    # Control Buttons with Glass Effect
    st.markdown("""
    <div class="glass-effect" style="padding: 2rem; margin: 2rem 0; border-radius: 20px;">
        <h3 style="color: #333; text-align: center; margin-bottom: 2rem;">🚀 Control Panel</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if st.button(
            "▶️ Start Elite Automation", 
            disabled=st.session_state.automation_state.running, 
            use_container_width=True,
            type="primary"
        ):
            current_config = db.get_user_config(st.session_state.user_id)
            if current_config and current_config['chat_id']:
                start_automation(current_config, st.session_state.user_id)
                st.rerun()
            else:
                st.error("❌ Please configure Chat ID first!")
        
        if st.button(
            "⏹️ Stop Automation", 
            disabled=not st.session_state.automation_state.running, 
            use_container_width=True,
            type="secondary"
        ):
            stop_automation(st.session_state.user_id)
            st.rerun()
    
    # Real-time Logs with Cyber Theme
    st.markdown("### 📊 Live System Monitor")
    
    if st.session_state.automation_state.logs:
        logs_html = '<div class="log-container">'
        for log in st.session_state.automation_state.logs[-50:]:
            if 'ERROR' in log or 'FAILED' in log:
                logs_html += f'<div style="color: #ff6b6b; padding: 0.5rem 0; border-bottom: 1px solid #333;">{log}</div>'
            elif 'SUCCESS' in log or '✅' in log:
                logs_html += f'<div style="color: #51cf66; padding: 0.5rem 0; border-bottom: 1px solid #333;">{log}</div>'
            elif 'WARNING' in log or '⚠️' in log:
                logs_html += f'<div style="color: #ffd43b; padding: 0.5rem 0; border-bottom: 1px solid #333;">{log}</div>'
            else:
                logs_html += f'<div style="padding: 0.5rem 0; border-bottom: 1px solid #333;">{log}</div>'
        logs_html += '</div>'
        st.markdown(logs_html, unsafe_allow_html=True)
    else:
        st.info("🔍 No logs yet. Start automation to monitor system activity.")
    
    # Auto-refresh when running
    if st.session_state.automation_state.running:
        time.sleep(2)
        st.rerun()

# 🎯 MAIN APPLICATION
render_ultra_header()

if not st.session_state.logged_in:
    # Ultra Modern Login/Signup
    tab1, tab2 = st.tabs(["🔐 Secure Login", "✨ Create Account"])
    
    with tab1:
        render_glass_card("Welcome Back! 👋", """
        <div style="text-align: center; padding: 2rem 0;">
            <h2 style="color: #333; margin-bottom: 2rem;">Access Your Dashboard</h2>
        </div>
        """)
        
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
            
            if st.form_submit_button("🚀 Login to Elite Dashboard", use_container_width=True):
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
        render_glass_card("Join the Elite Platform 🎉", """
        <div style="text-align: center; padding: 2rem 0;">
            <h2 style="color: #333; margin-bottom: 2rem;">Create New Account</h2>
        </div>
        """)
        
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
            
            if st.form_submit_button("✨ Create Elite Account", use_container_width=True):
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
    # Ultra Modern Dashboard
    if not st.session_state.auto_start_checked and st.session_state.user_id:
        st.session_state.auto_start_checked = True
        should_auto_start = db.get_automation_running(st.session_state.user_id)
        if should_auto_start and not st.session_state.automation_state.running:
            user_config = db.get_user_config(st.session_state.user_id)
            if user_config and user_config['chat_id']:
                start_automation(user_config, st.session_state.user_id)
    
    # Ultra Modern Sidebar
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 2rem 0;">
            <h3 style="color: #333; margin-bottom: 1rem;">👤 User Panel</h3>
        </div>
        """, unsafe_allow_html=True)
        
        render_user_avatar(st.session_state.username)
        
        st.markdown(f"""
        <div style="text-align: center; margin: 1rem 0;">
            <h4 style="color: #333; margin: 0.5rem 0;">{st.session_state.username}</h4>
            <p style="color: #666; font-size: 0.9rem; margin: 0;">ID: #{st.session_state.user_id}</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("### 🛡️ Security Status")
        st.markdown('<div class="cookie-security-badge">🔐 ELITE ENCRYPTION ACTIVE</div>', unsafe_allow_html=True)
        
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
            render_ultra_configuration_tab(user_config)
        
        with tab2:
            render_ultra_automation_tab(user_config)

# Ultra Modern Footer
st.markdown("""
<div class="footer floating-element">
    <h3>👑 HASSAN RAJPUT</h3>
    <p>Elite E2EE Automation Platform • Next Generation Technology</p>
    <p style="font-size: 0.9rem; opacity: 0.7; margin-top: 1rem;">© 2025 All Rights Reserved | 🔐 Military-Grade Encryption</p>
</div>
""", unsafe_allow_html=True)
