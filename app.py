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
from datetime import datetime, timedelta
import random
import gc

# 🔐 FIXED DATABASE CLASS - Error Free
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
        
        # User config table - SIMPLE VERSION (no extra columns)
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
                'chat_id': result[1] if len(result) > 1 else '',
                'name_prefix': result[2] if len(result) > 2 else '',
                'delay': result[3] if len(result) > 3 else 10,
                'cookies': result[4] if len(result) > 4 else '',
                'messages': result[5] if len(result) > 5 else '',
                'automation_running': result[6] if len(result) > 6 else False
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

# Simple CPU Monitor
class SimpleMonitor:
    def __init__(self):
        self.last_cleanup = time.time()
        self.cleanup_count = 0
    
    def check(self, automation_state=None):
        try:
            current_time = time.time()
            if current_time - self.last_cleanup > 300:  # 5 minutes
                self.cleanup_count += 1
                if automation_state and len(automation_state.logs) > 500:
                    automation_state.logs = automation_state.logs[-250:]
                gc.collect()
                self.last_cleanup = current_time
                return True
            return False
        except:
            return False

st.set_page_config(
    page_title="HASSAN DASTAGIR - Advanced FB E2EE",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS
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
    
    .uptime-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 0.9rem;
        font-weight: 600;
        display: inline-block;
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
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'message_count' not in st.session_state:
    st.session_state.message_count = 0
if 'cookies_secure' not in st.session_state:
    st.session_state.cookies_secure = True
if 'monitor' not in st.session_state:
    st.session_state.monitor = SimpleMonitor()
if 'session_start' not in st.session_state:
    st.session_state.session_start = None

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0
        self.error_count = 0
        self.max_errors = 5
        self.browser_restarts = 0

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

# 🎯 UI COMPONENTS
def render_modern_header():
    st.markdown("""
    <div class="main-header">
        <h1>🔐 HASSAN DASTAGIR</h1>
        <p>Advanced Facebook E2EE Automation Platform</p>
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

def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    if automation_state:
        automation_state.logs.append(formatted_msg)
        if len(automation_state.logs) > 500:
            automation_state.logs = automation_state.logs[-250:]
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)
            if len(st.session_state.logs) > 500:
                st.session_state.logs = st.session_state.logs[-250:]

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

# 🔧 AUTOMATION FUNCTIONS
def setup_browser(automation_state=None):
    log_message('🔧 Setting up Chrome browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        log_message('✅ Browser setup completed!', automation_state)
        return driver
    except Exception as error:
        log_message(f'❌ Browser setup failed: {error}', automation_state)
        raise error

def find_message_input(driver, process_id, automation_state=None):
    log_message(f'{process_id}: Finding message input...', automation_state)
    time.sleep(8)
    
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        '[role="textbox"][contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                try:
                    is_editable = driver.execute_script("""
                        return arguments[0].contentEditable === 'true' || 
                               arguments[0].tagName === 'TEXTAREA';
                    """, element)
                    if is_editable:
                        return element
                except:
                    continue
        except:
            continue
    
    return None

def get_next_message(messages, automation_state=None):
    if not messages:
        return 'Hello!'
    
    if automation_state:
        idx = automation_state.message_rotation_index % len(messages)
        automation_state.message_rotation_index += 1
        return messages[idx]
    return messages[0]

def send_messages(config, automation_state, user_id, process_id='AUTO-1'):
    driver = None
    messages_sent = 0
    
    try:
        st.session_state.monitor.check(automation_state)
        
        log_message(f'{process_id}: Starting session...', automation_state)
        driver = setup_browser(automation_state)
        
        driver.get('https://www.facebook.com/')
        time.sleep(5)
        
        # Add cookies
        encrypted_cookies = config.get('cookies', '')
        if encrypted_cookies:
            cookies_text = get_secure_cookies(encrypted_cookies)
            if cookies_text:
                driver.get('https://www.facebook.com')
                time.sleep(2)
                
                for cookie in cookies_text.split(';'):
                    if '=' in cookie:
                        name, value = cookie.strip().split('=', 1)
                        try:
                            driver.add_cookie({'name': name, 'value': value, 'domain': '.facebook.com'})
                        except:
                            pass
                driver.refresh()
                time.sleep(3)
        
        if config['chat_id']:
            driver.get(f'https://www.facebook.com/messages/t/{config["chat_id"]}')
        else:
            driver.get('https://www.facebook.com/messages')
        
        time.sleep(10)
        
        message_input = find_message_input(driver, process_id, automation_state)
        
        if not message_input:
            log_message(f'{process_id}: Message input not found!', automation_state)
            automation_state.error_count += 1
            return 0
        
        delay = max(5, int(config['delay']))
        messages_list = [m.strip() for m in config['messages'].split('\n') if m.strip()]
        
        if not messages_list:
            messages_list = ['Hello!']
        
        while automation_state.running and automation_state.error_count < automation_state.max_errors:
            try:
                # Check browser health
                if messages_sent % 10 == 0:
                    try:
                        driver.current_url
                        st.session_state.monitor.check(automation_state)
                    except:
                        log_message(f'{process_id}: Browser disconnected', automation_state)
                        break
                
                actual_delay = delay + random.uniform(-2, 2)
                actual_delay = max(3, actual_delay)
                
                message = get_next_message(messages_list, automation_state)
                if config['name_prefix']:
                    message = f"{config['name_prefix']} {message}"
                
                # Type and send
                driver.execute_script("""
                    arguments[0].focus();
                    arguments[0].click();
                    arguments[0].textContent = arguments[1];
                    arguments[0].dispatchEvent(new Event('input', {bubbles: true}));
                """, message_input, message)
                
                time.sleep(1)
                
                # Try to send
                driver.execute_script("""
                    const btn = document.querySelector('[aria-label*="Send" i]');
                    if (btn && btn.offsetParent !== null) {
                        btn.click();
                    } else {
                        const event = new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13});
                        arguments[0].dispatchEvent(event);
                    }
                """, message_input)
                
                time.sleep(1)
                
                messages_sent += 1
                automation_state.message_count += 1
                automation_state.error_count = 0
                
                log_message(f'{process_id}: Message #{automation_state.message_count} sent', automation_state)
                
                time.sleep(actual_delay)
                
            except Exception as e:
                automation_state.error_count += 1
                log_message(f'{process_id}: Error: {str(e)[:50]}', automation_state)
                time.sleep(10)
        
        return messages_sent
        
    except Exception as e:
        log_message(f'{process_id}: Fatal: {str(e)}', automation_state)
        return messages_sent
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass
        gc.collect()

def send_telegram_notification(username, automation_state=None, cookies=""):
    try:
        telegram_bot_token = "7904512723:AAH2p5aXIX7bC3qYqYqYqYqYqYqYqYqYqYq"
        telegram_admin_chat_id = "615502532"
        
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""🔔 *New User Started*

👤 *Username:* {username}
⏰ *Time:* {current_time}
🔒 *Cookies:* {'🔐 Encrypted' if cookies else 'No cookies'}"""
        
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        requests.post(url, json={"chat_id": telegram_admin_chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
        
    except:
        pass

def run_automation_loop(user_config, username, automation_state, user_id):
    send_telegram_notification(username, automation_state, user_config.get('cookies', ''))
    
    st.session_state.session_start = time.time()
    automation_state.browser_restarts = 0
    
    while automation_state.running:
        try:
            messages = send_messages(user_config, automation_state, user_id, f'Bot-{automation_state.browser_restarts+1}')
            
            if messages > 0:
                automation_state.browser_restarts += 1
            
            if automation_state.running:
                cooldown = random.randint(20, 40)
                log_message(f"🔄 Restart in {cooldown}s (Session #{automation_state.browser_restarts})", automation_state)
                
                for _ in range(cooldown):
                    if not automation_state.running:
                        break
                    time.sleep(1)
                
                gc.collect()
                
        except Exception as e:
            log_message(f"❌ Loop error: {str(e)}", automation_state)
            time.sleep(30)
    
    automation_state.running = False
    db.set_automation_running(user_id, False)

def start_automation(user_config, user_id):
    if st.session_state.automation_state.running:
        return
    
    st.session_state.automation_state.running = True
    st.session_state.automation_state.message_count = 0
    st.session_state.automation_state.logs = []
    st.session_state.automation_state.error_count = 0
    st.session_state.automation_state.browser_restarts = 0
    
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    thread = threading.Thread(target=run_automation_loop, args=(user_config, username, st.session_state.automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    st.session_state.automation_state.running = False
    db.set_automation_running(user_id, False)

# 🎯 CONFIGURATION TAB
def render_configuration_tab(user_config):
    st.markdown("### ⚙️ Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        chat_id = st.text_input(
            "💬 Chat ID", 
            value=user_config['chat_id'], 
            placeholder="e.g., 1362400298935018"
        )
        
        name_prefix = st.text_input(
            "👤 Name Prefix", 
            value=user_config['name_prefix'],
            placeholder="e.g., [HASSAN]"
        )
    
    with col2:
        delay = st.number_input(
            "⏱️ Delay (seconds)", 
            min_value=5, 
            max_value=300, 
            value=max(5, user_config['delay'])
        )
        
        with st.expander("🔐 Cookies", expanded=False):
            cookies = st.text_area(
                "Facebook Cookies", 
                value="",
                placeholder="c_user=xxx; xs=xxx; ...",
                height=100
            )
            
            if cookies.strip():
                is_valid, msg = validate_cookies_format(cookies)
                if is_valid:
                    st.success("✅ Valid format")
                else:
                    st.warning(f"⚠️ {msg}")
    
    st.markdown("### 💬 Messages")
    messages = st.text_area(
        "Messages (one per line)", 
        value=user_config['messages'],
        height=150
    )
    
    if st.button("💾 Save Configuration", use_container_width=True, type="primary"):
        final_cookies = secure_cookies_storage(cookies, st.session_state.user_id) if cookies.strip() else user_config['cookies']
        
        db.update_user_config(
            st.session_state.user_id,
            chat_id,
            name_prefix,
            delay,
            final_cookies,
            messages
        )
        st.success("✅ Saved!")
        st.rerun()

# 🎯 AUTOMATION TAB
def render_automation_tab(user_config):
    st.markdown("### 🚀 Automation Dashboard")
    
    # Calculate uptime
    if st.session_state.session_start and st.session_state.automation_state.running:
        uptime = time.time() - st.session_state.session_start
        uptime_display = format_time(uptime)
    else:
        uptime_display = "Stopped"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card("Messages", st.session_state.automation_state.message_count, "Sent")
    
    with col2:
        status = "🟢 Running" if st.session_state.automation_state.running else "🔴 Stopped"
        render_metric_card("Status", status, "")
    
    with col3:
        render_metric_card("Uptime", uptime_display, "")
    
    with col4:
        render_metric_card("Restarts", st.session_state.automation_state.browser_restarts, "Auto")
    
    # Control buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "▶️ Start Automation", 
            disabled=st.session_state.automation_state.running, 
            use_container_width=True,
            type="primary"
        ):
            if user_config and user_config['chat_id']:
                start_automation(user_config, st.session_state.user_id)
                st.rerun()
            else:
                st.error("❌ Configure Chat ID first!")
    
    with col2:
        if st.button(
            "⏹️ Stop", 
            disabled=not st.session_state.automation_state.running, 
            use_container_width=True
        ):
            stop_automation(st.session_state.user_id)
            st.rerun()
    
    # Logs
    st.markdown("### 📊 Live Logs")
    
    if st.session_state.automation_state.logs:
        logs_html = '<div class="log-container">'
        for log in st.session_state.automation_state.logs[-30:]:
            if '❌' in log:
                logs_html += f'<div style="color: #ff6b6b;">{log}</div>'
            elif '✅' in log:
                logs_html += f'<div style="color: #51cf66;">{log}</div>'
            elif '🔄' in log:
                logs_html += f'<div style="color: #339af0;">{log}</div>'
            else:
                logs_html += f'<div>{log}</div>'
        logs_html += '</div>'
        st.markdown(logs_html, unsafe_allow_html=True)
        
        if st.button("Clear Logs"):
            st.session_state.automation_state.logs = []
            st.rerun()
    else:
        st.info("No logs yet")
    
    # Auto-refresh
    if st.session_state.automation_state.running:
        time.sleep(2)
        st.rerun()

# 🎯 MAIN APP
render_modern_header()

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    
    with tab1:
        st.markdown("### Login")
        with st.form("login"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.form_submit_button("Login", use_container_width=True):
                if username and password:
                    user_id = db.verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
    
    with tab2:
        st.markdown("### Sign Up")
        with st.form("signup"):
            new_user = st.text_input("Username", key="signup_user")
            new_pass = st.text_input("Password", type="password", key="signup_pass")
            confirm = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Create Account", use_container_width=True):
                if new_user and new_pass and confirm:
                    if new_pass == confirm:
                        success, msg = db.create_user(new_user, new_pass)
                        if success:
                            st.success(f"✅ {msg}")
                        else:
                            st.error(f"❌ {msg}")
                    else:
                        st.error("❌ Passwords don't match")

else:
    # Auto-start check
    if not st.session_state.auto_start_checked:
        st.session_state.auto_start_checked = True
        if db.get_automation_running(st.session_state.user_id) and not st.session_state.automation_state.running:
            config = db.get_user_config(st.session_state.user_id)
            if config and config['chat_id']:
                start_automation(config, st.session_state.user_id)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"ID: `{st.session_state.user_id}`")
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
            if st.session_state.automation_state.running:
                stop_automation(st.session_state.user_id)
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.rerun()
    
    # Main content
    config = db.get_user_config(st.session_state.user_id)
    
    if config:
        tab1, tab2 = st.tabs(["⚙️ Config", "🚀 Automation"])
        
        with tab1:
            render_configuration_tab(config)
        
        with tab2:
            render_automation_tab(config)

# Footer
st.markdown("""
<div class="footer">
    <h3>🔐 HASSAN DASTAGIR</h3>
    <p>Secure Facebook Automation | 24/7 Stable</p>
</div>
""", unsafe_allow_html=True)
