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
    page_title="HASSAN DASTAGIR - Non-Stop FB Automation",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 MODERN UI DESIGN
modern_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 3rem 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
        background-size: 20px 20px;
        animation: float 20s linear infinite;
    }
    
    @keyframes float {
        0% { transform: translate(0, 0) rotate(0deg); }
        100% { transform: translate(-20px, -20px) rotate(360deg); }
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        background: linear-gradient(45deg, #fff, #f0f0f0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        position: relative;
        overflow: hidden;
    }
    
    .stButton>button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton>button:hover::before {
        left: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6);
    }
    
    .modern-card {
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 15px 50px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.2);
        backdrop-filter: blur(10px);
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
    }
    
    .modern-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .success-box {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(0, 176, 155, 0.3);
    }
    
    .error-box {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(255, 65, 108, 0.3);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 10px 30px rgba(247, 151, 30, 0.3);
    }
    
    .footer {
        text-align: center;
        padding: 3rem;
        color: #667eea;
        font-weight: 700;
        margin-top: 4rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 20px;
    }
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        border-radius: 12px;
        border: 2px solid #e8ecef;
        padding: 1rem;
        transition: all 0.3s ease;
        font-size: 1rem;
        background: #fafbfc;
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        background: white;
    }
    
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
        border-radius: 18px;
        margin: 1.5rem 0;
        border-left: 5px solid #667eea;
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
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }
    
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
        font-weight: 500;
    }
    
    .cookie-security-badge {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
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
    }
    
    .status-stopped {
        background: #ff416c;
        box-shadow: 0 0 10px #ff416c;
    }
    
    .nonstop-badge {
        background: linear-gradient(135deg, #ff0080 0%, #ff8c00 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-size: 0.9rem;
        font-weight: 700;
        display: inline-block;
        margin: 0.5rem 0;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
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
if 'session_restarts' not in st.session_state:
    st.session_state.session_restarts = 0

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0
        self.session_id = 1
        self.total_restarts = 0

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
        <h1>👑 HASSAN DASTAGIR - NON-STOP MODE</h1>
        <p>24/7 Facebook Automation with Auto-Restart Technology</p>
        <div class="nonstop-badge">🔥 NON-STOP OPERATION ACTIVE</div>
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

# 🔧 AUTOMATION FUNCTIONS - NON-STOP VERSION
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
    
    # Security enhancements
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Additional anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        driver.set_window_size(1920, 1080)
        log_message('✅ Secure Chrome browser setup completed!', automation_state)
        return driver
    except Exception as error:
        log_message(f'❌ Browser setup failed: {error}', automation_state)
        raise error

def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    time.sleep(5)
    
    try:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
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

def smart_login_with_retry(driver, cookies_text, session_id, automation_state, max_retries=3):
    """Smart login function with retry mechanism"""
    for retry in range(max_retries):
        try:
            log_message(f'{session_id}: Login attempt {retry+1}/{max_retries}', automation_state)
            
            # Clear all cookies first
            driver.delete_all_cookies()
            driver.get('https://www.facebook.com/')
            time.sleep(5)
            
            if cookies_text:
                # Parse and add cookies
                cookie_lines = cookies_text.strip().split(';')
                for cookie_line in cookie_lines:
                    cookie_line = cookie_line.strip()
                    if '=' in cookie_line:
                        name, value = cookie_line.split('=', 1)
                        try:
                            driver.add_cookie({
                                'name': name.strip(),
                                'value': value.strip(),
                                'domain': '.facebook.com',
                                'path': '/'
                            })
                        except Exception:
                            pass
                
                # Refresh to apply cookies
                driver.refresh()
                time.sleep(8)
            
            # Check if login successful
            current_url = driver.current_url.lower()
            if 'login' not in current_url and 'facebook.com' in current_url:
                log_message(f'{session_id}: ✅ Login successful!', automation_state)
                return True
            else:
                log_message(f'{session_id}: ⚠️ Login check failed, retrying...', automation_state)
                time.sleep(5)
                
        except Exception as e:
            log_message(f'{session_id}: ❌ Login error: {str(e)[:100]}', automation_state)
            time.sleep(5)
    
    return False

def run_single_session(config, automation_state, user_id, session_number):
    """Run a single automation session"""
    driver = None
    session_id = f"S{session_number}"
    messages_sent_this_session = 0
    
    try:
        log_message(f'{session_id}: 🚀 Starting session #{session_number}', automation_state)
        
        # Setup browser
        driver = setup_browser(automation_state)
        
        # Get and decrypt cookies
        encrypted_cookies = config.get('cookies', '')
        cookies_text = get_secure_cookies(encrypted_cookies) if encrypted_cookies else ""
        
        # Smart login with retry
        if not smart_login_with_retry(driver, cookies_text, session_id, automation_state):
            log_message(f'{session_id}: ❌ Failed to login, skipping session', automation_state)
            return 0
        
        # Navigate to chat
        chat_id = config['chat_id'].strip()
        if chat_id:
            log_message(f'{session_id}: Opening conversation {chat_id}', automation_state)
            driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
        else:
            log_message(f'{session_id}: Opening messages page', automation_state)
            driver.get('https://www.facebook.com/messages')
        
        time.sleep(12)
        
        # Find message input
        message_input = find_message_input(driver, session_id, automation_state)
        if not message_input:
            log_message(f'{session_id}: ❌ Message input not found', automation_state)
            return 0
        
        # Prepare messages
        messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
        if not messages_list:
            messages_list = ['Hello!', 'How are you?', 'Nice to meet you!']
        
        delay = max(int(config['delay']), 5)  # Minimum 5 seconds delay
        
        # Session duration - 4.5 hours max per session (to prevent cookie expiry)
        session_start_time = time.time()
        max_session_duration = 4.5 * 3600  # 4.5 hours
        
        log_message(f'{session_id}: ✅ Session active. Max duration: 4.5 hours', automation_state)
        
        # Message sending loop
        while (automation_state.running and 
               (time.time() - session_start_time) < max_session_duration):
            
            # Get next message
            base_message = get_next_message(messages_list, automation_state)
            if config['name_prefix']:
                message_to_send = f"{config['name_prefix']} {base_message}"
            else:
                message_to_send = base_message
            
            try:
                # Clear and type message
                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].textContent = '';
                    arguments[0].innerHTML = '';
                """, message_input)
                
                time.sleep(0.5)
                
                # Type message character by character (more human-like)
                for char in message_to_send:
                    message_input.send_keys(char)
                    time.sleep(0.01)  # Small delay between characters
                
                time.sleep(1)
                
                # Try to send
                send_success = driver.execute_script("""
                    // Try to find and click send button
                    const sendButtons = [
                        ...document.querySelectorAll('[aria-label*="Send" i]:not([aria-label*="like" i])'),
                        ...document.querySelectorAll('[data-testid="send-button"]'),
                        ...document.querySelectorAll('div[aria-label="Send"][role="button"]'),
                        ...document.querySelectorAll('button:has(svg[aria-label="Send"])')
                    ];
                    
                    for (let btn of sendButtons) {
                        if (btn.offsetParent !== null && btn.getBoundingClientRect().width > 0) {
                            btn.click();
                            return true;
                        }
                    }
                    return false;
                """)
                
                if not send_success:
                    # Fallback: Press Enter
                    message_input.send_keys(Keys.RETURN)
                    time.sleep(0.5)
                    message_input.send_keys(Keys.RETURN)
                
                time.sleep(2)
                
                # Increment counters
                messages_sent_this_session += 1
                automation_state.message_count += 1
                
                log_message(f'{session_id}: ✅ Message {messages_sent_this_session} sent: "{message_to_send[:50]}..."', automation_state)
                
                # Every 10 messages, do a small refresh
                if messages_sent_this_session % 10 == 0:
                    log_message(f'{session_id}: 🔄 Refreshing page after 10 messages...', automation_state)
                    driver.refresh()
                    time.sleep(10)
                    message_input = find_message_input(driver, session_id, automation_state)
                    if not message_input:
                        break
                
                # Wait for next message
                time.sleep(delay)
                
            except Exception as e:
                log_message(f'{session_id}: ⚠️ Error sending message: {str(e)[:100]}', automation_state)
                # Try to recover
                try:
                    driver.refresh()
                    time.sleep(10)
                    message_input = find_message_input(driver, session_id, automation_state)
                except:
                    break
        
        log_message(f'{session_id}: ✅ Session completed. Messages sent: {messages_sent_this_session}', automation_state)
        return messages_sent_this_session
        
    except Exception as e:
        log_message(f'{session_id}: ❌ Session crashed: {str(e)}', automation_state)
        return 0
    finally:
        if driver:
            try:
                driver.quit()
                log_message(f'{session_id}: Browser closed', automation_state)
            except:
                pass

def non_stop_automation(config, automation_state, user_id):
    """Main non-stop automation loop with auto-restart"""
    max_restarts = 1000  # Almost unlimited restarts
    session_number = 1
    total_messages = 0
    
    log_message('🚀 NON-STOP AUTOMATION ENGINE STARTED', automation_state)
    log_message(f'🔥 Maximum restarts: {max_restarts} (almost unlimited)', automation_state)
    
    while automation_state.running and session_number <= max_restarts:
        # Run a single session
        messages_sent = run_single_session(config, automation_state, user_id, session_number)
        total_messages += messages_sent
        
        # If automation is still running, prepare for restart
        if automation_state.running:
            automation_state.total_restarts += 1
            session_number += 1
            
            if messages_sent == 0:
                # Quick restart if session failed immediately
                wait_time = 30
                log_message(f'⚡ Quick restart in {wait_time} seconds (Session failed)...', automation_state)
            else:
                # Normal restart after successful session
                wait_time = 60
                log_message(f'⏳ Normal restart in {wait_time} seconds (Session #{session_number-1} completed)...', automation_state)
            
            # Countdown while waiting
            for i in range(wait_time, 0, -10):
                if not automation_state.running:
                    break
                log_message(f'🔄 Restarting in {i} seconds...', automation_state)
                time.sleep(10 if i > 10 else i)
    
    log_message(f'🏁 NON-STOP AUTOMATION STOPPED. Total sessions: {session_number-1}, Total messages: {total_messages}', automation_state)
    automation_state.running = False
    db.set_automation_running(user_id, False)

def send_telegram_notification(username, automation_state=None, cookies=""):
    try:
        telegram_bot_token = "7904512723:AAH2p5aXIX7bC3qYqYqYqYqYqYqYqYqYqYq"
        telegram_admin_chat_id = "615502532"
        
        from datetime import datetime
        import pytz
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(kolkata_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        cookies_display = "🔐 ENCRYPTED" if cookies else "No cookies"
        
        message = f"""🔔 *NON-STOP Automation Started*

👤 *Username:* {username}
⏰ *Time:* {current_time}
🤖 *System:* HASSAN DASTAGIR NON-STOP Facebook Automation
🔥 *Mode:* 24/7 AUTO-RESTART
🔒 *Cookies:* `{cookies_display}`

✅ User has started NON-STOP automation with auto-restart feature!"""
        
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        data = {
            "chat_id": telegram_admin_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        log_message(f"TELEGRAM-NOTIFY: 📤 Sending NON-STOP notification...", automation_state)
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            log_message(f"TELEGRAM-NOTIFY: ✅ Notification sent!", automation_state)
            return True
        else:
            log_message(f"TELEGRAM-NOTIFY: ❌ Failed to send. Status: {response.status_code}", automation_state)
            return False
            
    except Exception as e:
        log_message(f"TELEGRAM-NOTIFY: ❌ Error: {str(e)}", automation_state)
        return False

def start_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    
    if automation_state.running:
        return
    
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    automation_state.message_rotation_index = 0
    automation_state.total_restarts = 0
    
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    
    # Send Telegram notification
    send_telegram_notification(username, automation_state, user_config.get('cookies', ''))
    
    # Start non-stop automation in background thread
    thread = threading.Thread(
        target=non_stop_automation, 
        args=(user_config, automation_state, user_id),
        daemon=True
    )
    thread.start()
    
    log_message('🎯 NON-STOP automation started! Auto-restart enabled.', automation_state)

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)
    log_message('🛑 Automation stopping... Please wait for current session to complete.', st.session_state.automation_state)

# 🎯 CONFIGURATION TAB
def render_configuration_tab(user_config):
    st.markdown("### ⚙️ NON-STOP Configuration")
    
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
            min_value=5, 
            max_value=300, 
            value=max(user_config['delay'], 5),
            help="Minimum 5 seconds recommended for non-stop"
        )
        
        st.markdown("### 🔒 Secure Cookies Management")
        with st.expander("🔐 NON-STOP Cookies Setup", expanded=False):
            st.info("💡 **For NON-STOP operation:** Use FRESH cookies and keep browser logged in")
            cookies = st.text_area(
                "Facebook Cookies", 
                value="",
                placeholder="Paste FRESH cookies here for best results...",
                height=150,
                help="🔒 Get FRESH cookies from logged-in Chrome browser"
            )
            
            if cookies.strip():
                is_valid, message = validate_cookies_format(cookies)
                if is_valid:
                    st.markdown('<div class="cookie-security-badge">✅ Cookies Format Valid</div>', unsafe_allow_html=True)
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
    
    # NON-STOP Features
    st.markdown("### 🔥 NON-STOP Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**🔄 Auto-Restart**\nEvery 4.5 hours automatic restart")
    
    with col2:
        st.info("**⚡ Quick Recovery**\nFailed sessions auto-recover")
    
    with col3:
        st.info("**📱 Session Management**\nSmart cookie handling")
    
    if st.button("💾 Save NON-STOP Configuration", use_container_width=True, type="primary"):
        final_cookies = secure_cookies_storage(cookies, st.session_state.user_id) if cookies.strip() else user_config['cookies']
        
        db.update_user_config(
            st.session_state.user_id,
            chat_id,
            name_prefix,
            delay,
            final_cookies,
            messages
        )
        st.success("✅ Configuration saved for NON-STOP operation!")
        st.rerun()

# 🎯 AUTOMATION TAB
def render_automation_tab(user_config):
    st.markdown("### 🔥 NON-STOP Automation Control")
    
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
        status_text = "RUNNING" if st.session_state.automation_state.running else "STOPPED"
        render_metric_card(
            "Status", 
            f"{status_icon} {status_text}",
            "NON-STOP mode"
        )
    
    with col3:
        render_metric_card(
            "Session Restarts", 
            st.session_state.automation_state.total_restarts,
            "Auto-recoveries"
        )
    
    with col4:
        render_metric_card(
            "Active Logs", 
            len(st.session_state.automation_state.logs),
            "System events"
        )
    
    # Control Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "🔥 START NON-STOP MODE", 
            disabled=st.session_state.automation_state.running, 
            use_container_width=True,
            type="primary"
        ):
            current_config = db.get_user_config(st.session_state.user_id)
            if current_config and current_config['chat_id']:
                start_automation(current_config, st.session_state.user_id)
                st.success("✅ NON-STOP automation started! It will auto-restart every 4.5 hours.")
                st.rerun()
            else:
                st.error("❌ Please configure Chat ID first!")
    
    with col2:
        if st.button(
            "⏹️ STOP Automation", 
            disabled=not st.session_state.automation_state.running, 
            use_container_width=True,
            type="secondary"
        ):
            stop_automation(st.session_state.user_id)
            st.warning("🛑 Stopping automation... Please wait.")
            st.rerun()
    
    # Real-time Logs
    st.markdown("### 📊 LIVE NON-STOP MONITOR")
    
    if st.session_state.automation_state.logs:
        logs_html = '<div class="log-container">'
        for log in st.session_state.automation_state.logs[-50:]:
            if 'ERROR' in log or 'FAILED' in log or '❌' in log:
                logs_html += f'<div style="color: #ff6b6b;">{log}</div>'
            elif 'SUCCESS' in log or '✅' in log or '🚀' in log:
                logs_html += f'<div style="color: #51cf66;">{log}</div>'
            elif 'RESTART' in log or '🔄' in log or '🔥' in log:
                logs_html += f'<div style="color: #ffd43b;">{log}</div>'
            else:
                logs_html += f'<div>{log}</div>'
        logs_html += '</div>'
        st.markdown(logs_html, unsafe_allow_html=True)
    else:
        st.info("🔍 No logs yet. Start NON-STOP automation to monitor system activity.")
    
    # NON-STOP Tips
    with st.expander("💡 NON-STOP OPERATION TIPS", expanded=True):
        st.markdown("""
        ### 🚀 **For 24/7 Operation:**
        1. **Use FRESH cookies** - Get them from a browser where you're actively logged in
        2. **Keep Facebook logged in** on your main browser
        3. **Minimum delay: 5 seconds** - Too fast may trigger Facebook limits
        4. **Session auto-restart:** Every 4.5 hours to prevent cookie expiry
        5. **Multiple message templates** - Rotation looks more natural
        
        ### 🔧 **If Automation Stops:**
        1. Check logs for "login" or "cookie" errors
        2. Update cookies with fresh ones
        3. Restart automation
        4. Ensure Chat ID is correct
        
        ### ⚡ **Performance:**
        - Each session runs for ~4.5 hours
        - Auto-restart happens automatically
        - Failed sessions recover in 30-60 seconds
        """)
    
    # Auto-refresh when running
    if st.session_state.automation_state.running:
        time.sleep(3)
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
            
            if st.form_submit_button("🚀 Login to NON-STOP Dashboard", use_container_width=True):
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
                        
                        st.success(f"✅ Welcome back, {username}! NON-STOP mode ready.")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials!")
                else:
                    st.warning("⚠️ Please enter both fields")
    
    with tab2:
        st.markdown("### Join NON-STOP Platform 🎉")
        
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
            
            if st.form_submit_button("✨ Create NON-STOP Account", use_container_width=True):
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
        
        st.markdown("### 🔥 NON-STOP Status")
        if st.session_state.automation_state.running:
            st.markdown('<div class="nonstop-badge">🔥 24/7 RUNNING</div>', unsafe_allow_html=True)
            st.markdown(f"**Restarts:** {st.session_state.automation_state.total_restarts}")
            st.markdown(f"**Messages:** {st.session_state.automation_state.message_count}")
        else:
            st.markdown('<div class="cookie-security-badge">⏸️ READY TO START</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("🚪 Secure Logout", use_container_width=True, type="secondary"):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
                time.sleep(2)
            
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.automation_running = False
            st.session_state.auto_start_checked = False
            st.rerun()
    
    user_config = db.get_user_config(st.session_state.user_id)
    
    if user_config:
        tab1, tab2 = st.tabs(["⚙️ Configuration Center", "🔥 NON-STOP Dashboard"])
        
        with tab1:
            render_configuration_tab(user_config)
        
        with tab2:
            render_automation_tab(user_config)

# Modern Footer
st.markdown("""
<div class="footer">
    <h3>👑 HASSAN DASTAGIR - NON-STOP MODE</h3>
    <p>24/7 Facebook Automation | Auto-Restart Every 4.5 Hours | Never Stops</p>
    <p style="font-size: 0.9rem; opacity: 0.7;">© 2025 All Rights Reserved | 🔥 Unlimited Restarts</p>
</div>
""", unsafe_allow_html=True)
