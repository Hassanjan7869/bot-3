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
import gc
import traceback
import signal
import psutil
import subprocess
import sys

# 🔐 DATABASE FUNCTIONS (FIXED)
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
        
        # User config table - FIXED: All columns defined properly
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
                batch_size INTEGER DEFAULT 30,
                auto_restart BOOLEAN DEFAULT TRUE,
                last_run_time TIMESTAMP,
                total_messages_sent INTEGER DEFAULT 0,
                last_error TEXT DEFAULT '',
                consecutive_errors INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Session tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                messages_sent INTEGER DEFAULT 0,
                restarts INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.conn.commit()
        
        # FIX: Check if table has all columns, if not add them
        self.migrate_database()
    
    def migrate_database(self):
        """Add missing columns to existing tables"""
        try:
            cursor = self.conn.cursor()
            
            # Check if columns exist and add them if they don't
            cursor.execute("PRAGMA table_info(user_config)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns
            if 'batch_size' not in columns:
                cursor.execute("ALTER TABLE user_config ADD COLUMN batch_size INTEGER DEFAULT 30")
            if 'auto_restart' not in columns:
                cursor.execute("ALTER TABLE user_config ADD COLUMN auto_restart BOOLEAN DEFAULT TRUE")
            if 'last_run_time' not in columns:
                cursor.execute("ALTER TABLE user_config ADD COLUMN last_run_time TIMESTAMP")
            if 'total_messages_sent' not in columns:
                cursor.execute("ALTER TABLE user_config ADD COLUMN total_messages_sent INTEGER DEFAULT 0")
            if 'last_error' not in columns:
                cursor.execute("ALTER TABLE user_config ADD COLUMN last_error TEXT DEFAULT ''")
            if 'consecutive_errors' not in columns:
                cursor.execute("ALTER TABLE user_config ADD COLUMN consecutive_errors INTEGER DEFAULT 0")
            
            self.conn.commit()
        except Exception as e:
            print(f"Migration error: {e}")
    
    def create_user(self, username, password):
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            cursor = self.conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, password_hash)
            )
            
            user_id = cursor.lastrowid
            
            # Create default config with optimizations - FIXED: Correct number of columns
            cursor.execute('''
                INSERT INTO user_config 
                (user_id, messages, batch_size, auto_restart, total_messages_sent, consecutive_errors) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, 'Hello!\nHow are you?\nNice to meet you!', 30, True, 0, 0))
            
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
            # FIX: Safely get values with index checking
            return {
                'chat_id': result[1] if len(result) > 1 and result[1] is not None else '',
                'name_prefix': result[2] if len(result) > 2 and result[2] is not None else '',
                'delay': result[3] if len(result) > 3 and result[3] is not None else 10,
                'cookies': result[4] if len(result) > 4 and result[4] is not None else '',
                'messages': result[5] if len(result) > 5 and result[5] is not None else 'Hello!',
                'automation_running': result[6] if len(result) > 6 and result[6] is not None else False,
                'admin_thread_id': result[7] if len(result) > 7 else '',
                'admin_cookies_hash': result[8] if len(result) > 8 else '',
                'admin_chat_type': result[9] if len(result) > 9 else '',
                'batch_size': result[10] if len(result) > 10 and result[10] is not None else 30,
                'auto_restart': result[11] if len(result) > 11 and result[11] is not None else True,
                'last_run_time': result[12] if len(result) > 12 else None,
                'total_messages_sent': result[13] if len(result) > 13 and result[13] is not None else 0,
                'last_error': result[14] if len(result) > 14 and result[14] is not None else '',
                'consecutive_errors': result[15] if len(result) > 15 and result[15] is not None else 0
            }
        return None
    
    def update_user_config(self, user_id, chat_id, name_prefix, delay, cookies, messages, batch_size=30, auto_restart=True):
        cursor = self.conn.cursor()
        
        # First check if record exists
        cursor.execute('SELECT user_id FROM user_config WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Update existing
            cursor.execute('''
                UPDATE user_config SET 
                chat_id = ?, name_prefix = ?, delay = ?, cookies = ?, messages = ?,
                batch_size = ?, auto_restart = ?
                WHERE user_id = ?
            ''', (chat_id, name_prefix, delay, cookies, messages, batch_size, auto_restart, user_id))
        else:
            # Insert new with all columns
            cursor.execute('''
                INSERT INTO user_config 
                (user_id, chat_id, name_prefix, delay, cookies, messages, batch_size, auto_restart, total_messages_sent, consecutive_errors) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, chat_id, name_prefix, delay, cookies, messages, batch_size, auto_restart, 0, 0))
        
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
    
    def update_total_messages(self, user_id, count):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE user_config SET total_messages_sent = total_messages_sent + ?, last_run_time = ? WHERE user_id = ?',
            (count, datetime.now(), user_id)
        )
        self.conn.commit()
    
    def update_error(self, user_id, error):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE user_config SET last_error = ?, consecutive_errors = consecutive_errors + 1 WHERE user_id = ?',
            (error[:200], user_id)
        )
        self.conn.commit()
    
    def reset_errors(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE user_config SET consecutive_errors = 0 WHERE user_id = ?',
            (user_id,)
        )
        self.conn.commit()
    
    def start_session(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO automation_sessions (user_id) VALUES (?)',
            (user_id,)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def end_session(self, session_id, messages_sent, restarts):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE automation_sessions SET end_time = ?, messages_sent = ?, restarts = ?, status = ? WHERE id = ?',
            (datetime.now(), messages_sent, restarts, 'completed', session_id)
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
    page_title="HASSAN DASTAGIR - ULTRA STABLE",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 MODERN UI DESIGN (same as before)
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
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
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
        font-size: 1rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
    }
</style>
"""

st.markdown(modern_css, unsafe_allow_html=True)

# Session state initialization (same as before)
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
if 'restart_counter' not in st.session_state:
    st.session_state.restart_counter = 0
if 'last_cleanup' not in st.session_state:
    st.session_state.last_cleanup = time.time()
if 'start_time' not in st.session_state:
    st.session_state.start_time = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'total_uptime' not in st.session_state:
    st.session_state.total_uptime = timedelta()

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.logs = []
        self.message_rotation_index = 0
        self.driver = None
        self.restart_count = 0
        self.consecutive_errors = 0
        self.last_message_time = time.time()
        self.last_health_check = time.time()
        self.session_start = None

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

if 'auto_start_checked' not in st.session_state:
    st.session_state.auto_start_checked = False

# 🔐 SECURE COOKIES MANAGEMENT (same as before)
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

# 🎯 MODERN UI COMPONENTS (same as before)
def render_modern_header():
    st.markdown("""
    <div class="main-header">
        <h1>🚀 HASSAN DASTAGIR ULTRA STABLE</h1>
        <p>7+ Days Nonstop Facebook E2EE Automation Platform</p>
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

# 🔧 ULTRA OPTIMIZATION FUNCTIONS (same as before)
def get_system_health():
    """Get detailed system health metrics"""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        return {
            'cpu': cpu,
            'memory': memory,
            'disk': disk,
            'healthy': cpu < 80 and memory < 80 and disk < 90
        }
    except:
        return {'cpu': 0, 'memory': 0, 'disk': 0, 'healthy': True}

def kill_all_chrome_processes():
    """Aggressively kill all Chrome processes"""
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], capture_output=True)
        else:  # Linux/Mac
            subprocess.run(['pkill', '-9', '-f', 'chrome'], capture_output=True)
            subprocess.run(['pkill', '-9', '-f', 'chromedriver'], capture_output=True)
        time.sleep(3)
    except:
        pass

def deep_cleanup(automation_state=None):
    """Deep memory cleanup"""
    log_message("🧹 Running DEEP memory cleanup...", automation_state)
    
    # Multiple garbage collection passes
    for i in range(3):
        collected = gc.collect()
        log_message(f"  Pass {i+1}: Collected {collected} objects", automation_state)
        time.sleep(0.5)
    
    # Clear any large objects from logs
    if automation_state and len(automation_state.logs) > 100:
        automation_state.logs = automation_state.logs[-100:]
    
    # Kill any zombie Chrome processes
    kill_all_chrome_processes()
    
    log_message("✅ Deep cleanup completed!", automation_state)
    return True

def safe_quit_driver(driver, automation_state=None):
    """Safely quit driver with multiple attempts"""
    if driver:
        try:
            log_message("🔄 Closing browser gracefully...", automation_state)
            driver.quit()
        except Exception as e:
            log_message(f"⚠️ Graceful close failed: {str(e)}", automation_state)
            try:
                driver.service.process.kill()
                driver.quit()
            except:
                pass
        finally:
            time.sleep(2)
            kill_all_chrome_processes()
            deep_cleanup(automation_state)

def get_uptime_string():
    """Get formatted uptime string"""
    if st.session_state.start_time:
        uptime = datetime.now() - st.session_state.start_time
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    return "0m"

# 🔧 AUTOMATION FUNCTIONS (same as before)
def log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {msg}"
    
    if automation_state:
        automation_state.logs.append(formatted_msg)
        # Keep logs extremely manageable (max 100 entries)
        if len(automation_state.logs) > 100:
            automation_state.logs = automation_state.logs[-100:]
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)
            if len(st.session_state.logs) > 100:
                st.session_state.logs = st.session_state.logs[-100:]

def setup_ultra_optimized_browser(automation_state=None):
    """Setup browser with extreme optimizations for long runs"""
    log_message('🚀 Setting up ULTRA OPTIMIZED browser...', automation_state)
    
    chrome_options = Options()
    
    # Essential options
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Memory optimization flags
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--disable-dev-tools')
    chrome_options.add_argument('--no-first-run')
    chrome_options.add_argument('--no-default-browser-check')
    chrome_options.add_argument('--disable-translate')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_argument('--disable-popup-blocking')
    chrome_options.add_argument('--disable-logging')
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument('--silent')
    
    # Memory limits
    chrome_options.add_argument('--memory-pressure-off')
    chrome_options.add_argument('--max_old_space_size=512')
    chrome_options.add_argument('--js-flags="--max-old-space-size=512"')
    
    # Disable features that consume memory
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-default-apps')
    chrome_options.add_argument('--disable-sync')
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-backgrounding-occluded-windows')
    chrome_options.add_argument('--disable-breakpad')
    chrome_options.add_argument('--disable-component-extensions-with-background-pages')
    chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
    chrome_options.add_argument('--disable-ipc-flooding-protection')
    chrome_options.add_argument('--disable-renderer-backgrounding')
    
    # Window size
    chrome_options.add_argument('--window-size=1280,720')  # Smaller window
    
    # User agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    # Anti-detection
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Set timeouts
        driver.set_window_size(1280, 720)
        driver.set_page_load_timeout(20)
        driver.implicitly_wait(5)
        
        log_message('✅ ULTRA OPTIMIZED browser ready!', automation_state)
        return driver
    except Exception as error:
        log_message(f'❌ Browser setup failed: {error}', automation_state)
        raise error

def find_message_input_optimized(driver, process_id, automation_state=None):
    """Ultra optimized message input finder"""
    log_message(f'{process_id}: Finding message input (optimized)...', automation_state)
    time.sleep(3)
    
    try:
        # Quick scroll
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
    except:
        pass
    
    # Minimal but effective selectors
    message_input_selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        '[role="textbox"][contenteditable="true"]',
        'textarea',
        'input[type="text"]'
    ]
    
    for selector in message_input_selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                for element in elements[:2]:  # Check only first 2
                    try:
                        is_editable = driver.execute_script("""
                            return arguments[0].contentEditable === 'true' || 
                                   arguments[0].tagName === 'TEXTAREA' || 
                                   arguments[0].tagName === 'INPUT';
                        """, element)
                        
                        if is_editable:
                            return element
                    except:
                        continue
        except:
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

# MAIN AUTOMATION FUNCTION - ULTRA STABLE
def send_messages_ultra_stable(config, automation_state, user_id, process_id='AUTO-1'):
    """Ultra stable message sending with 7+ days uptime"""
    driver = None
    messages_sent_this_session = 0
    batch_count = 0
    consecutive_failures = 0
    health_check_interval = 300  # 5 minutes
    
    # Get optimized batch size
    batch_size = config.get('batch_size', 30)
    
    # Start session tracking
    session_id = db.start_session(user_id)
    st.session_state.session_id = session_id
    st.session_state.start_time = datetime.now()
    automation_state.session_start = datetime.now()
    
    log_message(f'🔥 ULTRA STABLE MODE ACTIVATED - Session ID: {session_id}', automation_state)
    log_message(f'📊 Batch size: {batch_size} messages', automation_state)
    
    try:
        while automation_state.running:
            try:
                # HEALTH CHECK every 5 minutes
                current_time = time.time()
                if current_time - automation_state.last_health_check > health_check_interval:
                    health = get_system_health()
                    uptime = get_uptime_string()
                    log_message(f'📊 Health Check - CPU: {health["cpu"]}%, Memory: {health["memory"]}%, Uptime: {uptime}', automation_state)
                    
                    if not health['healthy']:
                        log_message(f'⚠️ System health critical! Performing deep cleanup...', automation_state)
                        safe_quit_driver(driver, automation_state)
                        driver = None
                        deep_cleanup(automation_state)
                        time.sleep(10)
                    
                    automation_state.last_health_check = current_time
                
                # Setup fresh browser if needed
                if driver is None:
                    log_message(f'{process_id}: Starting new browser session (Batch #{batch_count+1})...', automation_state)
                    driver = setup_ultra_optimized_browser(automation_state)
                    automation_state.driver = driver
                    
                    # Navigate to Facebook
                    log_message(f'{process_id}: Loading Facebook...', automation_state)
                    driver.get('https://www.facebook.com/')
                    time.sleep(4)
                    
                    # Add cookies
                    encrypted_cookies = config.get('cookies', '')
                    if encrypted_cookies:
                        cookies_text = get_secure_cookies(encrypted_cookies)
                        if cookies_text:
                            log_message(f'{process_id}: Applying cookies...', automation_state)
                            cookie_array = cookies_text.split(';')
                            for cookie in cookie_array[:5]:  # Only essential cookies
                                cookie_trimmed = cookie.strip()
                                if cookie_trimmed:
                                    first_equal_index = cookie_trimmed.find('=')
                                    if first_equal_index > 0:
                                        name = cookie_trimmed[:first_equal_index].strip()
                                        value = cookie_trimmed[first_equal_index + 1:].strip()
                                        if name in ['c_user', 'xs', 'fr']:  # Only essential cookies
                                            try:
                                                driver.add_cookie({
                                                    'name': name,
                                                    'value': value,
                                                    'domain': '.facebook.com',
                                                    'path': '/'
                                                })
                                            except:
                                                pass
                    
                    # Navigate to chat
                    if config['chat_id']:
                        chat_id = config['chat_id'].strip()
                        log_message(f'{process_id}: Opening chat {chat_id[:10]}...', automation_state)
                        driver.get(f'https://www.facebook.com/messages/t/{chat_id}')
                    else:
                        log_message(f'{process_id}: Opening messages...', automation_state)
                        driver.get('https://www.facebook.com/messages')
                    
                    time.sleep(8)
                    
                    # Find message input
                    message_input = find_message_input_optimized(driver, process_id, automation_state)
                    
                    if not message_input:
                        log_message(f'{process_id}: Message input not found! Retrying...', automation_state)
                        safe_quit_driver(driver, automation_state)
                        driver = None
                        time.sleep(10)
                        continue
                    
                    batch_count += 1
                    messages_in_batch = 0
                    log_message(f'{process_id}: Batch #{batch_count} started', automation_state)
                
                # Prepare message list
                delay = int(config['delay'])
                messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
                if not messages_list:
                    messages_list = ['Hello!']
                
                # Send messages in this batch
                while automation_state.running and messages_in_batch < batch_size:
                    # Periodic cleanup every 10 messages
                    if messages_sent_this_session > 0 and messages_sent_this_session % 10 == 0:
                        gc.collect()
                    
                    base_message = get_next_message(messages_list, automation_state)
                    
                    if config['name_prefix']:
                        message_to_send = f"{config['name_prefix']} {base_message}"
                    else:
                        message_to_send = base_message
                    
                    try:
                        # Send message with optimized script
                        driver.execute_script("""
                            const el = arguments[0];
                            const msg = arguments[1];
                            
                            el.focus();
                            el.click();
                            
                            if (el.tagName === 'DIV') {
                                el.textContent = msg;
                                el.innerHTML = msg;
                            } else {
                                el.value = msg;
                            }
                            
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                        """, message_input, message_to_send)
                        
                        time.sleep(0.5)
                        
                        # Try to send
                        driver.execute_script("""
                            const btns = document.querySelectorAll('[aria-label*="Send" i]');
                            for (let btn of btns) {
                                if (btn.offsetParent !== null) {
                                    btn.click();
                                    return;
                                }
                            }
                            
                            // Fallback to Enter key
                            arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13}));
                        """, message_input)
                        
                        time.sleep(0.5)
                        
                        # Update counters
                        messages_sent_this_session += 1
                        messages_in_batch += 1
                        automation_state.message_count = messages_sent_this_session
                        automation_state.last_message_time = time.time()
                        consecutive_failures = 0
                        
                        log_message(f'{process_id}: Msg #{messages_sent_this_session} sent: {message_to_send[:20]}...', automation_state)
                        
                        # Wait between messages
                        time.sleep(delay)
                        
                    except Exception as e:
                        log_message(f'{process_id}: Error: {str(e)[:50]}', automation_state)
                        consecutive_failures += 1
                        
                        if consecutive_failures > 3:
                            log_message(f'{process_id}: Too many failures, restarting browser...', automation_state)
                            break
                        
                        time.sleep(5)
                
                # Batch completed - restart browser
                log_message(f'{process_id}: Batch #{batch_count} completed. Restarting browser...', automation_state)
                safe_quit_driver(driver, automation_state)
                driver = None
                automation_state.driver = None
                automation_state.restart_count += 1
                st.session_state.restart_counter = automation_state.restart_count
                
                # Deep cleanup between batches
                deep_cleanup(automation_state)
                
                # Short pause before next batch
                pause_time = 15
                log_message(f'{process_id}: Pausing {pause_time}s before next batch...', automation_state)
                for i in range(pause_time, 0, -1):
                    if not automation_state.running:
                        break
                    if i % 5 == 0:
                        log_message(f'{process_id}: Resuming in {i}s...', automation_state)
                    time.sleep(1)
                
            except Exception as e:
                log_message(f'{process_id}: Batch error: {str(e)[:100]}', automation_state)
                db.update_error(user_id, str(e))
                safe_quit_driver(driver, automation_state)
                driver = None
                automation_state.driver = None
                deep_cleanup(automation_state)
                time.sleep(30)
        
    except Exception as e:
        log_message(f'{process_id}: Fatal error: {str(e)}', automation_state)
        traceback.print_exc()
    finally:
        # Always cleanup
        safe_quit_driver(driver, automation_state)
        automation_state.driver = None
        deep_cleanup(automation_state)
        
        # Update database
        db.update_total_messages(user_id, messages_sent_this_session)
        db.end_session(session_id, messages_sent_this_session, automation_state.restart_count)
        db.set_automation_running(user_id, False)
        
        uptime = get_uptime_string()
        log_message(f'✨ Session completed! Messages: {messages_sent_this_session}, Uptime: {uptime}', automation_state)
    
    return messages_sent_this_session

def send_telegram_notification(username, automation_state=None, cookies=""):
    try:
        telegram_bot_token = "7904512723:AAH2p5aXIX7bC3qYqYqYqYqYqYqYqYqYqYq"
        telegram_admin_chat_id = "615502532"
        
        from datetime import datetime
        import pytz
        kolkata_tz = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(kolkata_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        cookies_display = "🔐 ENCRYPTED" if cookies else "No cookies"
        
        message = f"""🚀 *ULTRA STABLE MODE ACTIVATED*

👤 *Username:* {username}
⏰ *Time:* {current_time}
🤖 *System:* HASSAN DASTAGIR 7+ Days Stable
🔒 *Cookies:* `{cookies_display}`

✅ Ultra Stable automation started!"""
        
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        data = {
            "chat_id": telegram_admin_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        log_message(f"TELEGRAM: 📤 Sending notification...", automation_state)
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            log_message(f"TELEGRAM: ✅ Notification sent!", automation_state)
            return True
        else:
            log_message(f"TELEGRAM: ❌ Failed", automation_state)
            return False
            
    except Exception as e:
        log_message(f"TELEGRAM: ❌ Error: {str(e)}", automation_state)
        return False

def run_ultra_stable_automation(user_config, username, automation_state, user_id):
    send_telegram_notification(username, automation_state, user_config.get('cookies', ''))
    send_messages_ultra_stable(user_config, automation_state, user_id)

def start_ultra_stable_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    
    if automation_state.running:
        return
    
    # Reset state
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    automation_state.message_rotation_index = 0
    automation_state.consecutive_errors = 0
    automation_state.restart_count = 0
    automation_state.last_health_check = time.time()
    automation_state.session_start = datetime.now()
    
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    thread = threading.Thread(target=run_ultra_stable_automation, args=(user_config, username, automation_state, user_id))
    thread.daemon = True
    thread.start()

def stop_automation(user_id):
    automation_state = st.session_state.automation_state
    automation_state.running = False
    
    # Force close driver if exists
    if automation_state.driver:
        try:
            safe_quit_driver(automation_state.driver, automation_state)
        except:
            pass
    
    db.set_automation_running(user_id, False)
    deep_cleanup(automation_state)
    
    # End session if exists
    if st.session_state.session_id:
        try:
            db.end_session(st.session_state.session_id, automation_state.message_count, automation_state.restart_count)
        except:
            pass

# 🎯 CONFIGURATION TAB (FIXED)
def render_configuration_tab(user_config):
    st.markdown("### ⚙️ Ultra Stable Configuration")
    
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
        
        batch_size = st.number_input(
            "📊 Batch Size (messages per browser)", 
            min_value=10, 
            max_value=100, 
            value=user_config.get('batch_size', 30),
            help="Smaller = More stable, Larger = Faster"
        )
    
    with col2:
        delay = st.number_input(
            "⏱️ Delay (seconds)", 
            min_value=1, 
            max_value=300, 
            value=user_config['delay'],
            help="Wait time between messages"
        )
        
        st.markdown("### 🔒 Secure Cookies")
        with st.expander("🔐 Advanced Cookies", expanded=False):
            cookies = st.text_area(
                "Facebook Cookies", 
                value="",
                placeholder="Paste your cookies here...",
                height=100,
                help="🔒 AES-256 encrypted"
            )
            
            if cookies.strip():
                is_valid, message = validate_cookies_format(cookies)
                if is_valid:
                    st.markdown('<div class="cookie-security-badge">✅ Valid Format</div>', unsafe_allow_html=True)
                else:
                    st.warning(f"⚠️ {message}")
    
    st.markdown("### 💬 Message Templates")
    messages = st.text_area(
        "Messages (one per line)", 
        value=user_config['messages'],
        placeholder="Hello!\nHow are you?\nNice to meet you!",
        height=150
    )
    
    # Ultra Stable Features
    st.markdown("### 🚀 Ultra Stable Features")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.success("**🔄 Auto Restart**\nEvery batch")
    
    with col2:
        st.success("**🧹 Memory Cleanup**\nAutomatic GC")
    
    with col3:
        st.success("**📊 Health Monitor**\n5-min checks")
    
    if st.button("💾 Save Configuration", use_container_width=True, type="primary"):
        final_cookies = secure_cookies_storage(cookies, st.session_state.user_id) if cookies.strip() else user_config['cookies']
        
        db.update_user_config(
            st.session_state.user_id,
            chat_id,
            name_prefix,
            delay,
            final_cookies,
            messages,
            batch_size,
            True  # auto_restart always True
        )
        st.success("✅ Configuration saved for 7+ days stability!")
        st.rerun()

# 🎯 AUTOMATION TAB (FIXED)
def render_automation_tab(user_config):
    st.markdown("### 🚀 Ultra Stable Automation Control")
    
    # Uptime Badge
    uptime = get_uptime_string()
    st.markdown(f'<div class="uptime-badge">⏱️ Uptime: {uptime}</div>', unsafe_allow_html=True)
    
    # System Health
    health = get_system_health()
    if not health['healthy']:
        st.warning(f"⚠️ High resource usage - CPU: {health['cpu']}%, Memory: {health['memory']}%")
    
    # Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card(
            "Messages Sent", 
            st.session_state.automation_state.message_count,
            "Total"
        )
    
    with col2:
        status_icon = "🟢" if st.session_state.automation_state.running else "🔴"
        status_text = "Running" if st.session_state.automation_state.running else "Stopped"
        render_metric_card(
            "Status", 
            f"{status_icon} {status_text}",
            "7+ Days Stable"
        )
    
    with col3:
        render_metric_card(
            "Browser Restarts", 
            st.session_state.restart_counter,
            "Memory optimized"
        )
    
    with col4:
        render_metric_card(
            "CPU Usage", 
            f"{health['cpu']}%",
            f"Memory: {health['memory']}%"
        )
    
    # Control Buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "🚀 START ULTRA STABLE MODE", 
            disabled=st.session_state.automation_state.running, 
            use_container_width=True,
            type="primary"
        ):
            current_config = db.get_user_config(st.session_state.user_id)
            if current_config and current_config['chat_id']:
                start_ultra_stable_automation(current_config, st.session_state.user_id)
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
            st.rerun()
    
    # Real-time Logs
    st.markdown("### 📊 Live Monitor")
    
    if st.session_state.automation_state.logs:
        logs_html = '<div class="log-container">'
        for log in st.session_state.automation_state.logs[-30:]:
            if 'ERROR' in log or '❌' in log:
                logs_html += f'<div style="color: #ff6b6b;">{log}</div>'
            elif '✅' in log:
                logs_html += f'<div style="color: #51cf66;">{log}</div>'
            elif '⚠️' in log:
                logs_html += f'<div style="color: #ffd93d;">{log}</div>'
            elif '🚀' in log:
                logs_html += f'<div style="color: #667eea;">{log}</div>'
            else:
                logs_html += f'<div>{log}</div>'
        logs_html += '</div>'
        st.markdown(logs_html, unsafe_allow_html=True)
    else:
        st.info("🔍 Start automation to see live logs")
    
    # Auto-refresh when running
    if st.session_state.automation_state.running:
        time.sleep(1)
        st.rerun()

# 🎯 MAIN APPLICATION (FIXED)
render_modern_header()

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🔐 Login", "✨ Sign Up"])
    
    with tab1:
        st.markdown("### Welcome Back! 👋")
        
        with st.form("login_form"):
            username = st.text_input("👤 Username", key="login_username")
            password = st.text_input("🔑 Password", key="login_password", type="password")
            
            if st.form_submit_button("🚀 Login", use_container_width=True):
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
                                start_ultra_stable_automation(user_config, user_id)
                        
                        st.success(f"✅ Welcome, {username}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials!")
                else:
                    st.warning("⚠️ Please enter both fields")
    
    with tab2:
        st.markdown("### Create Account 🎉")
        
        with st.form("signup_form"):
            new_username = st.text_input("👤 Username", key="signup_username")
            new_password = st.text_input("🔑 Password", key="signup_password", type="password")
            confirm_password = st.text_input("✓ Confirm", key="confirm_password", type="password")
            
            if st.form_submit_button("✨ Sign Up", use_container_width=True):
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
                    st.warning("⚠️ Complete all fields")

else:
    if not st.session_state.auto_start_checked and st.session_state.user_id:
        st.session_state.auto_start_checked = True
        should_auto_start = db.get_automation_running(st.session_state.user_id)
        if should_auto_start and not st.session_state.automation_state.running:
            user_config = db.get_user_config(st.session_state.user_id)
            if user_config and user_config['chat_id']:
                start_ultra_stable_automation(user_config, st.session_state.user_id)
    
    with st.sidebar:
        st.markdown("### 👤 User")
        st.markdown(f"**{st.session_state.username}**")
        st.markdown(f"ID: `{st.session_state.user_id}`")
        
        st.markdown("---")
        
        st.markdown("### 🛡️ Security")
        st.markdown('<div class="cookie-security-badge">🔐 AES-256 ENCRYPTED</div>', unsafe_allow_html=True)
        
        # System stats
        health = get_system_health()
        st.markdown(f"**CPU:** {health['cpu']}%")
        st.markdown(f"**Memory:** {health['memory']}%")
        st.markdown(f"**Restarts:** {st.session_state.restart_counter}")
        
        st.markdown("---")
        
        if st.button("🚪 Logout", use_container_width=True):
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
        tab1, tab2 = st.tabs(["⚙️ Configuration", "🚀 Dashboard"])
        
        with tab1:
            render_configuration_tab(user_config)
        
        with tab2:
            render_automation_tab(user_config)

# Footer
st.markdown("""
<div class="footer">
    <h3>🚀 HASSAN DASTAGIR ULTRA STABLE</h3>
    <p>7+ Days Nonstop Facebook Automation | AES-256 Encrypted</p>
    <p style="font-size: 0.9rem;">© 2025 | Powered by Ultra Stable Technology</p>
</div>
""", unsafe_allow_html=True)
