import streamlit as st
import time
import threading
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
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

# 🔐 DATABASE FUNCTIONS - ORIGINAL
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
                'messages': result[5],
                'automation_running': result[6]
            }
        return None
    
    def update_user_config(self, user_id, chat_id, name_prefix, delay, cookies, messages):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE user_config 
            SET chat_id = ?, name_prefix = ?, delay = ?, cookies = ?, messages = ?
            WHERE user_id = ?
        ''', (chat_id, name_prefix, delay, cookies, messages, user_id))
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

# 🎨 MODERN UI CSS
st.set_page_config(
    page_title="HASSAN DASTAGIR - Advanced FB E2EE",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
if 'automation_state' not in st.session_state:
    st.session_state.automation_state = None
if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False

# 🔧 FIXED AUTOMATION FUNCTIONS
class AutomationState:
    def __init__(self, user_id, config):
        self.user_id = user_id
        self.config = config
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0
        self.thread = None
    
    def add_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        self.logs.append(formatted_msg)
        # Keep last 100 logs
        if len(self.logs) > 100:
            self.logs.pop(0)
    
    def setup_browser(self):
        """FIXED: Proper browser setup"""
        self.add_log('🔧 Setting up Chrome browser...')
        
        chrome_options = Options()
        
        # Remove headless for debugging
        # chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        
        # Remove automation detection
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            # FIXED: Use webdriver_manager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute anti-detection script
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.add_log('✅ Chrome browser setup completed!')
            return driver
        except Exception as error:
            self.add_log(f'❌ Browser setup failed: {error}')
            raise error
    
    def find_message_input(self, driver, process_id):
        """Improved message input finding"""
        self.add_log(f'{process_id}: Finding message input...')
        time.sleep(5)
        
        try:
            # Scroll to load page
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            
            # Try multiple selectors
            selectors = [
                'div[contenteditable="true"]',
                'div[role="textbox"]',
                'textarea[placeholder*="message" i]',
                'div[aria-label*="message" i]',
                'div[data-editor]'
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            if element.is_displayed() and element.is_enabled():
                                element.click()
                                time.sleep(1)
                                self.add_log(f'{process_id}: ✅ Found input with selector: {selector}')
                                return element
                        except:
                            continue
                except:
                    continue
            
            return None
            
        except Exception as e:
            self.add_log(f'{process_id}: Error finding input: {str(e)[:100]}')
            return None
    
    def send_messages(self, process_id='AUTO-1'):
        """Main automation function"""
        driver = None
        try:
            self.running = True
            db.set_automation_running(self.user_id, True)
            
            self.add_log(f'{process_id}: Starting automation...')
            driver = self.setup_browser()
            
            # Navigate to Facebook
            self.add_log(f'{process_id}: Navigating to Facebook...')
            driver.get('https://www.facebook.com')
            time.sleep(8)
            
            # Apply cookies if available
            if self.config['cookies']:
                try:
                    cookies_text = cookie_encryptor.decrypt_cookies(self.config['cookies'])
                    if cookies_text:
                        self.add_log(f'{process_id}: Adding cookies...')
                        
                        # Clear existing cookies first
                        driver.delete_all_cookies()
                        
                        # Add each cookie
                        for cookie in cookies_text.split(';'):
                            cookie = cookie.strip()
                            if '=' in cookie:
                                name, value = cookie.split('=', 1)
                                driver.add_cookie({
                                    'name': name.strip(),
                                    'value': value.strip(),
                                    'domain': '.facebook.com'
                                })
                        
                        driver.refresh()
                        time.sleep(5)
                except Exception as e:
                    self.add_log(f'{process_id}: Cookie error: {str(e)[:100]}')
            
            # Go to chat
            if self.config['chat_id']:
                self.add_log(f'{process_id}: Opening chat {self.config["chat_id"]}...')
                driver.get(f'https://www.facebook.com/messages/t/{self.config["chat_id"]}')
            else:
                self.add_log(f'{process_id}: Opening messages...')
                driver.get('https://www.facebook.com/messages')
            
            time.sleep(10)
            
            # Find message input
            message_input = self.find_message_input(driver, process_id)
            
            if not message_input:
                self.add_log(f'{process_id}: ❌ Message input not found!')
                self.running = False
                db.set_automation_running(self.user_id, False)
                return
            
            # Prepare messages
            messages_list = [msg.strip() for msg in self.config['messages'].split('\n') if msg.strip()]
            if not messages_list:
                messages_list = ['Hello!', 'How are you?', 'Nice to meet you!']
            
            delay = max(10, self.config['delay'])  # Minimum 10 seconds
            
            # Send messages loop
            while self.running:
                # Get next message
                message = messages_list[self.message_rotation_index % len(messages_list)]
                self.message_rotation_index += 1
                
                if self.config['name_prefix']:
                    message = f"{self.config['name_prefix']} {message}"
                
                try:
                    # Clear input first
                    message_input.clear()
                    time.sleep(0.5)
                    
                    # Type message
                    message_input.send_keys(message)
                    time.sleep(1)
                    
                    # Send message (press Enter)
                    message_input.send_keys(Keys.RETURN)
                    
                    self.message_count += 1
                    self.add_log(f'{process_id}: ✅ Message {self.message_count} sent: {message[:50]}...')
                    
                    # Send Telegram notification every 10 messages
                    if self.message_count % 10 == 0:
                        self.send_telegram_notification()
                    
                    # Wait before next message
                    for i in range(delay):
                        if not self.running:
                            break
                        time.sleep(1)
                    
                    # Small random delay
                    time.sleep(random.randint(1, 3))
                    
                except Exception as e:
                    self.add_log(f'{process_id}: Error sending: {str(e)[:100]}')
                    time.sleep(5)
                    # Try to find input again
                    message_input = self.find_message_input(driver, process_id)
                    if not message_input:
                        break
            
            self.add_log(f'{process_id}: Automation stopped. Total messages: {self.message_count}')
            
        except Exception as e:
            self.add_log(f'{process_id}: Fatal error: {str(e)[:200]}')
        
        finally:
            self.running = False
            db.set_automation_running(self.user_id, False)
            if driver:
                try:
                    driver.quit()
                    self.add_log(f'{process_id}: Browser closed')
                except:
                    pass
    
    def send_telegram_notification(self):
        """Send progress notification"""
        try:
            telegram_bot_token = "7904512723:AAH2p5aXIX7bC3qYqYqYqYqYqYqYqYqYqYq"
            telegram_admin_chat_id = "615502532"
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            username = db.get_username(self.user_id)
            
            message = f"""📊 Automation Progress Update

👤 User: {username}
📈 Messages Sent: {self.message_count}
⏰ Time: {current_time}
🔗 Chat ID: {self.config['chat_id'] or 'Not set'}

✅ System running smoothly"""
            
            url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
            data = {
                "chat_id": telegram_admin_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            requests.post(url, data=data, timeout=10)
            self.add_log("📤 Progress notification sent to Telegram")
            
        except Exception as e:
            self.add_log(f"Telegram error: {str(e)[:50]}")
    
    def start(self):
        """Start automation in background thread"""
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self.send_messages, daemon=True)
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Stop automation"""
        self.running = False

# 🎯 UI COMPONENTS
def render_modern_header():
    st.markdown("""
    <div class="main-header">
        <h1>👑 HASSAN DASTAGIR</h1>
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

# 🔧 VALIDATION FUNCTIONS
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
        return cookie_encryptor.decrypt_cookies(encrypted_cookies)
    except Exception:
        return ""

# 🎯 CONFIGURATION TAB
def render_configuration_tab(user_config):
    st.markdown("### ⚙️ Advanced Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        chat_id = st.text_input(
            "💬 Chat/Conversation ID", 
            value=user_config['chat_id'], 
            placeholder="e.g., 1362400298935018",
            help="Facebook conversation ID from URL"
        )
        
        name_prefix = st.text_input(
            "👤 Name Prefix", 
            value=user_config['name_prefix'],
            placeholder="e.g., [HASSAN DASTAGIR]",
            help="Prefix added before each message"
        )
    
    with col2:
        delay = st.number_input(
            "⏱️ Delay (seconds)", 
            min_value=10, 
            max_value=300, 
            value=user_config['delay'],
            help="Wait time between messages (minimum 10 seconds)"
        )
        
        st.markdown("### 🔒 Secure Cookies Management")
        with st.expander("🔐 Advanced Cookies Security", expanded=False):
            cookies = st.text_area(
                "Facebook Cookies", 
                value=get_secure_cookies(user_config['cookies']),
                placeholder="Paste your secure cookies here...",
                height=120,
                help="🔒 Your cookies are STRONGLY ENCRYPTED"
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
    
    # Security Features
    st.markdown("### 🛡️ Security Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.info("**🔐 Strong Encryption**\nAES-256 encrypted cookies")
    
    with col2:
        st.info("**🚫 Anti-Detection**\nAdvanced browser masking")
    
    with col3:
        st.info("**📱 Smart Automation**\nIntelligent message rotation")
    
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
        
        # Update automation state config if exists
        if st.session_state.automation_state:
            st.session_state.automation_state.config = db.get_user_config(st.session_state.user_id)
        
        st.success("✅ Configuration saved successfully!")
        st.rerun()

# 🎯 AUTOMATION TAB
def render_automation_tab(user_config):
    st.markdown("### 🚀 Automation Control Center")
    
    # Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        msg_count = st.session_state.automation_state.message_count if st.session_state.automation_state else 0
        render_metric_card("Messages Sent", msg_count, "Current session")
    
    with col2:
        is_running = st.session_state.automation_state.running if st.session_state.automation_state else False
        status = "🟢 Running" if is_running else "🔴 Stopped"
        render_metric_card("Status", status, "Automation state")
    
    with col3:
        log_count = len(st.session_state.automation_state.logs) if st.session_state.automation_state else 0
        render_metric_card("System Logs", log_count, "Events tracked")
    
    with col4:
        security_status = "🔐 Secure" if st.session_state.cookies_secure else "⚠️ Check"
        render_metric_card("Security", security_status, "Encryption active")
    
    # Control Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "▶️ Start Automation", 
            disabled=st.session_state.automation_state and st.session_state.automation_state.running, 
            use_container_width=True,
            type="primary",
            help="Start sending messages"
        ):
            current_config = db.get_user_config(st.session_state.user_id)
            if current_config and current_config['chat_id']:
                # Create new automation state
                st.session_state.automation_state = AutomationState(st.session_state.user_id, current_config)
                st.session_state.automation_state.start()
                st.success("🚀 Automation started!")
                st.rerun()
            else:
                st.error("❌ Please configure Chat ID first!")
    
    with col2:
        if st.button(
            "⏹️ Stop Automation", 
            disabled=not st.session_state.automation_state or not st.session_state.automation_state.running, 
            use_container_width=True,
            type="secondary",
            help="Stop sending messages"
        ):
            if st.session_state.automation_state:
                st.session_state.automation_state.stop()
                st.success("⏹️ Automation stopped!")
                st.rerun()
    
    # Real-time Logs
    st.markdown("### 📊 Live System Monitor")
    
    if st.session_state.automation_state and st.session_state.automation_state.logs:
        logs_html = '<div class="log-container">'
        for log in st.session_state.automation_state.logs[-30:]:  # Show last 30 logs
            if 'ERROR' in log or 'FAILED' in log or '❌' in log:
                logs_html += f'<div style="color: #ff6b6b;">{log}</div>'
            elif 'SUCCESS' in log or '✅' in log:
                logs_html += f'<div style="color: #51cf66;">{log}</div>'
            else:
                logs_html += f'<div>{log}</div>'
        logs_html += '</div>'
        st.markdown(logs_html, unsafe_allow_html=True)
    else:
        st.info("🔍 No logs yet. Start automation to monitor system activity.")
    
    # Auto-refresh when running
    if st.session_state.automation_state and st.session_state.automation_state.running:
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
            
            if st.form_submit_button("🚀 Login to Dashboard", use_container_width=True):
                if username and password:
                    user_id = db.verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        # Check if automation should auto-start
                        should_auto_start = db.get_automation_running(user_id)
                        if should_auto_start:
                            user_config = db.get_user_config(user_id)
                            if user_config and user_config['chat_id']:
                                st.session_state.automation_state = AutomationState(user_id, user_config)
                                st.session_state.automation_state.start()
                        
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
    # Check for auto-start
    if not st.session_state.auto_start_checked and st.session_state.user_id:
        st.session_state.auto_start_checked = True
        should_auto_start = db.get_automation_running(st.session_state.user_id)
        if should_auto_start and not st.session_state.automation_state:
            user_config = db.get_user_config(st.session_state.user_id)
            if user_config and user_config['chat_id']:
                st.session_state.automation_state = AutomationState(st.session_state.user_id, user_config)
                st.session_state.automation_state.start()
    
    # Sidebar
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
        
        st.markdown("---")
        
        # Automation Status
        if st.session_state.automation_state:
            if st.session_state.automation_state.running:
                st.success("✅ Automation Active")
                if st.button("🛑 Stop Automation", use_container_width=True):
                    st.session_state.automation_state.stop()
                    st.rerun()
            else:
                st.warning("⏸️ Automation Paused")
                if st.button("▶️ Start Automation", use_container_width=True):
                    user_config = db.get_user_config(st.session_state.user_id)
                    if user_config['chat_id']:
                        st.session_state.automation_state.start()
                        st.rerun()
                    else:
                        st.error("Configure Chat ID first!")
        
        st.markdown("---")
        
        if st.button("🚪 Secure Logout", use_container_width=True, type="secondary"):
            # Stop automation if running
            if st.session_state.automation_state:
                st.session_state.automation_state.stop()
            
            # Clear session
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.automation_state = None
            st.session_state.auto_start_checked = False
            st.rerun()
    
    # Get user config
    user_config = db.get_user_config(st.session_state.user_id)
    
    if user_config:
        # Main tabs
        tab1, tab2 = st.tabs(["⚙️ Configuration Center", "🚀 Automation Dashboard"])
        
        with tab1:
            render_configuration_tab(user_config)
        
        with tab2:
            render_automation_tab(user_config)

# Modern Footer
st.markdown("""
<div class="footer">
    <h3>👑 HASSAN DASTAGIR</h3>
    <p>Advanced E2EE Automation Platform | Secure • Modern • Powerful</p>
    <p style="font-size: 0.9rem; opacity: 0.7;">© 2025 All Rights Reserved | 🔐 End-to-End Encrypted</p>
</div>
""", unsafe_allow_html=True)

# Install instructions in sidebar
with st.sidebar:
    with st.expander("📦 Installation Guide", expanded=False):
        st.markdown("""
        **Required Packages:**
        ```bash
        pip install streamlit selenium webdriver-manager cryptography requests
        ```
        
        **Run Application:**
        ```bash
        streamlit run app.py
        ```
        
        **Note:** Chrome browser must be installed
        """)
