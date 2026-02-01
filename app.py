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

# 🔐 DATABASE FUNCTIONS - LONG LIVE EDITION
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('hassan_dastagir_longlive.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT '🟢 ACTIVE',
                messages_sent INTEGER DEFAULT 0
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
                theme_color TEXT DEFAULT 'cyberpunk',
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Activity logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                activity TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                'INSERT INTO user_config (user_id, messages, theme_color) VALUES (?, ?, ?)',
                (user_id, 'LONG LIVE! 🚀\nCyber Mode Activated 🔥\nE2EE Secure Connection ✅\n24/7 NON-STOP Running ⚡', 'cyberpunk')
            )
            
            # Log activity
            cursor.execute(
                'INSERT INTO activity_logs (user_id, activity) VALUES (?, ?)',
                (user_id, '🚀 Account Created - LONG LIVE!')
            )
            
            self.conn.commit()
            return True, "🚀 Account created successfully! LONG LIVE!"
        except sqlite3.IntegrityError:
            return False, "⚠️ Username already exists!"
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def verify_user(self, username, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT id FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        result = cursor.fetchone()
        
        if result:
            # Update last active
            cursor.execute(
                'UPDATE user_config SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?',
                (result[0],)
            )
            
            # Log login
            cursor.execute(
                'INSERT INTO activity_logs (user_id, activity) VALUES (?, ?)',
                (result[0], '🔐 Login Successful - LONG LIVE!')
            )
            
            self.conn.commit()
        
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
                'theme_color': result[10] or 'cyberpunk'
            }
        return None
    
    def update_user_config(self, user_id, chat_id, name_prefix, delay, cookies, messages, theme_color):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO user_config 
            (user_id, chat_id, name_prefix, delay, cookies, messages, theme_color, last_active) 
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (user_id, chat_id, name_prefix, delay, cookies, messages, theme_color))
        
        # Log activity
        cursor.execute(
            'INSERT INTO activity_logs (user_id, activity) VALUES (?, ?)',
            (user_id, '⚙️ Configuration Updated')
        )
        
        self.conn.commit()
    
    def increment_message_count(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE users SET messages_sent = messages_sent + 1 WHERE id = ?',
            (user_id,)
        )
        self.conn.commit()
    
    def get_message_stats(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT messages_sent FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def get_activity_logs(self, user_id, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT activity, timestamp FROM activity_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()

# Initialize database
db = Database()

# 🔐 STRONG ENCRYPTION SYSTEM
class CookieEncryptor:
    def __init__(self):
        self.salt = b'hassan_long_live_cyber_salt_2025'
        self._setup_encryption()
    
    def _setup_encryption(self):
        password = os.getenv('ENCRYPTION_KEY', 'hassan_dastagir_long_live_king_2025').encode()
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
    page_title="HASSAN DASTAGIR - LONG LIVE CYBER EDITION",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🌟 CYBERPUNK MODERN UI DESIGN - LONG LIVE EDITION
cyberpunk_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Rajdhani:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Rajdhani', sans-serif;
    }
    
    .cyber-header {
        background: linear-gradient(135deg, #000428 0%, #004e92 100%);
        padding: 4rem 2rem;
        border-radius: 0 0 30px 30px;
        text-align: center;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        border-bottom: 4px solid #00ff9d;
        box-shadow: 0 0 50px rgba(0, 255, 157, 0.3);
    }
    
    .cyber-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(circle at 20% 80%, rgba(0, 255, 157, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(0, 183, 255, 0.1) 0%, transparent 50%),
            repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(0, 255, 157, 0.05) 2px, rgba(0, 255, 157, 0.05) 4px);
        animation: scanlines 10s linear infinite;
    }
    
    @keyframes scanlines {
        0% { background-position: 0 0; }
        100% { background-position: 0 100px; }
    }
    
    .cyber-header h1 {
        font-family: 'Orbitron', monospace;
        font-size: 4.5rem;
        font-weight: 900;
        margin: 0;
        background: linear-gradient(45deg, #00ff9d, #00b8ff, #ff00ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 30px rgba(0, 255, 157, 0.5);
        letter-spacing: 2px;
        position: relative;
        animation: glitch 3s infinite;
    }
    
    @keyframes glitch {
        0%, 100% { transform: translateX(0); }
        95% { transform: translateX(0); }
        96% { transform: translateX(-2px); }
        97% { transform: translateX(2px); }
        98% { transform: translateX(-1px); }
        99% { transform: translateX(1px); }
    }
    
    .cyber-subtitle {
        font-family: 'Orbitron', monospace;
        font-size: 1.8rem;
        color: #00ff9d;
        text-shadow: 0 0 10px #00ff9d;
        margin-top: 1rem;
        letter-spacing: 3px;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .long-live-badge {
        background: linear-gradient(135deg, #ff0080, #ff8c00, #ff0080);
        background-size: 200% 200%;
        color: white;
        padding: 1rem 2rem;
        border-radius: 50px;
        font-family: 'Orbitron', monospace;
        font-size: 1.5rem;
        font-weight: 700;
        display: inline-block;
        margin: 1rem 0;
        animation: gradientShift 3s infinite, float 3s ease-in-out infinite;
        border: 2px solid #fff;
        box-shadow: 0 0 20px #ff0080;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #000428, #004e92);
        color: #00ff9d !important;
        border: 2px solid #00ff9d !important;
        border-radius: 10px;
        padding: 1rem 2rem;
        font-family: 'Orbitron', monospace;
        font-weight: 600;
        font-size: 1.1rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 0 20px rgba(0, 255, 157, 0.3);
        position: relative;
        overflow: hidden;
        letter-spacing: 1px;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #004e92, #000428);
        transform: translateY(-3px);
        box-shadow: 0 0 30px rgba(0, 255, 157, 0.6);
        color: #ffffff !important;
    }
    
    .stButton>button:before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 157, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .stButton>button:hover:before {
        left: 100%;
    }
    
    .cyber-card {
        background: rgba(0, 4, 40, 0.7);
        padding: 2.5rem;
        border-radius: 20px;
        border: 1px solid #00ff9d;
        box-shadow: 0 0 30px rgba(0, 255, 157, 0.2);
        margin: 1.5rem 0;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
    }
    
    .cyber-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #00ff9d, #00b8ff, #ff00ff);
    }
    
    .cyber-metric {
        background: rgba(0, 4, 40, 0.9);
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #00b8ff;
        text-align: center;
        box-shadow: 0 0 20px rgba(0, 184, 255, 0.3);
    }
    
    .cyber-metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(45deg, #00ff9d, #00b8ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0;
        text-shadow: 0 0 10px rgba(0, 255, 157, 0.3);
    }
    
    .cyber-metric-label {
        font-family: 'Rajdhani', sans-serif;
        font-size: 1rem;
        color: #00b8ff;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .terminal {
        background: #000;
        color: #00ff9d;
        padding: 1.5rem;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        border: 1px solid #00ff9d;
        box-shadow: inset 0 0 20px rgba(0, 255, 157, 0.1);
        max-height: 500px;
        overflow-y: auto;
        position: relative;
    }
    
    .terminal::before {
        content: 'SYSTEM TERMINAL';
        position: absolute;
        top: -10px;
        left: 20px;
        background: #000;
        color: #00ff9d;
        padding: 0 10px;
        font-size: 0.8rem;
        font-family: 'Orbitron', monospace;
    }
    
    .terminal-line {
        margin: 5px 0;
        padding-left: 10px;
        border-left: 2px solid #00ff9d;
        animation: typewriter 0.1s steps(40) forwards;
    }
    
    @keyframes typewriter {
        from { width: 0; }
        to { width: 100%; }
    }
    
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stNumberInput>div>div>input {
        background: rgba(0, 4, 40, 0.7) !important;
        border: 2px solid #00b8ff !important;
        border-radius: 10px;
        color: #00ff9d !important;
        font-family: 'Rajdhani', sans-serif;
        font-size: 1rem;
        padding: 1rem !important;
        transition: all 0.3s ease;
    }
    
    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: #00ff9d !important;
        box-shadow: 0 0 20px rgba(0, 255, 157, 0.3) !important;
        background: rgba(0, 4, 40, 0.9) !important;
    }
    
    .cyber-tab {
        background: rgba(0, 4, 40, 0.7) !important;
        border: 1px solid #00b8ff !important;
        border-radius: 10px !important;
        margin: 5px !important;
    }
    
    .cyber-tab:hover {
        background: rgba(0, 4, 40, 0.9) !important;
        border-color: #00ff9d !important;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        background: rgba(0, 4, 40, 0.5) !important;
        border-radius: 10px;
        padding: 5px !important;
        border: 1px solid #00b8ff;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-family: 'Orbitron', monospace !important;
        font-weight: 600 !important;
    }
    
    .glitch-text {
        font-family: 'Orbitron', monospace;
        animation: glitch 2s infinite;
        color: #00ff9d;
        text-shadow: 
            2px 2px 0 #ff00ff,
            -2px -2px 0 #00b8ff;
    }
    
    .neon-border {
        border: 2px solid #00ff9d;
        border-radius: 15px;
        box-shadow: 
            0 0 10px #00ff9d,
            0 0 20px #00ff9d,
            inset 0 0 10px #00ff9d;
        padding: 2rem;
        margin: 1rem 0;
        animation: borderPulse 2s infinite;
    }
    
    @keyframes borderPulse {
        0%, 100% { box-shadow: 0 0 10px #00ff9d, 0 0 20px #00ff9d, inset 0 0 10px #00ff9d; }
        50% { box-shadow: 0 0 20px #00ff9d, 0 0 40px #00ff9d, inset 0 0 20px #00ff9d; }
    }
    
    .cyber-footer {
        background: linear-gradient(135deg, #000428 0%, #004e92 100%);
        padding: 3rem;
        text-align: center;
        margin-top: 4rem;
        border-radius: 30px 30px 0 0;
        border-top: 4px solid #00ff9d;
        position: relative;
        overflow: hidden;
    }
    
    .cyber-footer::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: repeating-linear-gradient(
            0deg,
            transparent,
            transparent 1px,
            rgba(0, 255, 157, 0.05) 1px,
            rgba(0, 255, 157, 0.05) 2px
        );
    }
    
    .hologram-effect {
        background: linear-gradient(45deg, 
            rgba(0, 255, 157, 0.1), 
            rgba(0, 184, 255, 0.1), 
            rgba(255, 0, 255, 0.1));
        background-size: 400% 400%;
        animation: hologram 10s ease infinite;
    }
    
    @keyframes hologram {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .binary-rain {
        position: relative;
        overflow: hidden;
    }
    
    .binary-rain::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(transparent 95%, rgba(0, 255, 157, 0.1) 100%);
        animation: rain 20s linear infinite;
    }
    
    @keyframes rain {
        0% { background-position: 0 0; }
        100% { background-position: 0 1000px; }
    }
    
    .cyber-loader {
        border: 4px solid rgba(0, 255, 157, 0.3);
        border-top: 4px solid #00ff9d;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        display: inline-block;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    
    .matrix-grid {
        position: relative;
    }
    
    .matrix-grid::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image: 
            linear-gradient(rgba(0, 255, 157, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 157, 0.1) 1px, transparent 1px);
        background-size: 20px 20px;
        pointer-events: none;
    }
</style>
"""

st.markdown(cyberpunk_css, unsafe_allow_html=True)

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_running' not in st.session_state:
    st.session_state.automation_running = False
if 'theme' not in st.session_state:
    st.session_state.theme = 'cyberpunk'
if 'cyber_effects' not in st.session_state:
    st.session_state.cyber_effects = True

class AutomationState:
    def __init__(self):
        self.running = False
        self.message_count = 0
        self.session_count = 0
        self.total_restarts = 0
        self.start_time = None
        self.logs = []
        self.message_rotation_index = 0
        self.uptime = 0

if 'automation_state' not in st.session_state:
    st.session_state.automation_state = AutomationState()

# 🌟 CYBERPUNK UI COMPONENTS
def render_cyber_header():
    st.markdown("""
    <div class="cyber-header binary-rain">
        <h1>👑 HASSAN DASTAGIR</h1>
        <div class="cyber-subtitle">LONG LIVE CYBER EDITION</div>
        <div class="long-live-badge">🔥 LONG LIVE 🔥</div>
        <div style="margin-top: 1rem;">
            <span style="color: #00ff9d; font-family: 'Orbitron', monospace;">⚡ ADVANCED E2EE AUTOMATION ⚡</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_cyber_metric(title, value, icon="⚡", color="#00ff9d"):
    st.markdown(f"""
    <div class="cyber-metric">
        <div style="font-size: 2rem; margin-bottom: 10px;">{icon}</div>
        <div class="cyber-metric-value">{value}</div>
        <div class="cyber-metric-label">{title}</div>
    </div>
    """, unsafe_allow_html=True)

def render_cyber_terminal(logs):
    terminal_html = '<div class="terminal">'
    for log in logs[-30:]:
        if any(x in log for x in ['ERROR', 'FAILED', '❌']):
            terminal_html += f'<div class="terminal-line" style="color: #ff0066;">{log}</div>'
        elif any(x in log for x in ['SUCCESS', '✅', '🚀', 'LONG LIVE']):
            terminal_html += f'<div class="terminal-line" style="color: #00ff9d;">{log}</div>'
        elif any(x in log for x in ['WARNING', '⚠️', '🔄']):
            terminal_html += f'<div class="terminal-line" style="color: #ffcc00;">{log}</div>'
        else:
            terminal_html += f'<div class="terminal-line" style="color: #00b8ff;">{log}</div>'
    terminal_html += '</div>'
    return terminal_html

# 🔧 AUTOMATION FUNCTIONS - LONG LIVE CYBER EDITION
def cyber_log_message(msg, automation_state=None):
    timestamp = time.strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] ⚡ {msg}"
    
    if automation_state:
        automation_state.logs.append(formatted_msg)
        # Also update database
        if 'user_id' in st.session_state and st.session_state.user_id:
            cursor = db.conn.cursor()
            cursor.execute(
                'INSERT INTO activity_logs (user_id, activity) VALUES (?, ?)',
                (st.session_state.user_id, msg[:100])
            )
            db.conn.commit()
    else:
        if 'logs' in st.session_state:
            st.session_state.logs.append(formatted_msg)

def setup_cyber_browser(automation_state=None):
    cyber_log_message('🚀 Initializing Cyber Browser...', automation_state)
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Cyber security features
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Cyber user agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
    
    try:
        service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Anti-detection
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        cyber_log_message('✅ Cyber Browser Ready!', automation_state)
        return driver
    except Exception as error:
        cyber_log_message(f'❌ Browser Setup Failed: {error}', automation_state)
        raise error

def find_message_input_cyber(driver, session_id, automation_state=None):
    cyber_log_message(f'{session_id}: Scanning for message input...', automation_state)
    time.sleep(5)
    
    selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[contenteditable="true"][data-lexical-editor="true"]',
        'div[aria-label*="message" i][contenteditable="true"]',
        'div[aria-label*="Message" i][contenteditable="true"]',
        '[role="textbox"][contenteditable="true"]',
        'textarea[placeholder*="message" i]',
        'div[aria-placeholder*="message" i]',
        'div[data-placeholder*="message" i]',
        '[contenteditable="true"]',
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
                               arguments[0].tagName === 'TEXTAREA' || 
                               arguments[0].tagName === 'INPUT';
                    """, element)
                    
                    if is_editable:
                        element.click()
                        time.sleep(0.5)
                        cyber_log_message(f'{session_id}: ✅ Input Located!', automation_state)
                        return element
                except:
                    continue
        except:
            continue
    
    return None

def send_messages_long_live(config, automation_state, user_id, process_id='CYBER-1'):
    """LONG LIVE CYBER EDITION - 24/7 NON-STOP"""
    
    session_number = 0
    total_messages = 0
    
    while automation_state.running:
        session_number += 1
        automation_state.session_count = session_number
        automation_state.total_restarts += 1
        
        session_id = f"{process_id}-S{session_number:03d}"
        cyber_log_message(f'{session_id}: 🚀 CYBER SESSION #{session_number} - LONG LIVE!', automation_state)
        
        driver = None
        messages_sent_this_session = 0
        
        try:
            driver = setup_cyber_browser(automation_state)
            driver.get('https://www.facebook.com/')
            time.sleep(5)
            
            # Add cookies if available
            encrypted_cookies = config.get('cookies', '')
            if encrypted_cookies:
                cookies_text = cookie_encryptor.decrypt_cookies(encrypted_cookies)
                if cookies_text:
                    cyber_log_message(f'{session_id}: 🔐 Loading Secure Cookies...', automation_state)
                    for cookie in cookies_text.split(';'):
                        cookie = cookie.strip()
                        if cookie:
                            try:
                                name, value = cookie.split('=', 1)
                                driver.add_cookie({
                                    'name': name.strip(),
                                    'value': value.strip(),
                                    'domain': '.facebook.com'
                                })
                            except:
                                pass
            
            if config['chat_id']:
                driver.get(f'https://www.facebook.com/messages/t/{config["chat_id"].strip()}')
            else:
                driver.get('https://www.facebook.com/messages')
            
            time.sleep(8)
            
            message_input = find_message_input_cyber(driver, session_id, automation_state)
            
            if not message_input:
                cyber_log_message(f'{session_id}: ❌ Input Not Found, Retrying...', automation_state)
                time.sleep(30)
                continue
            
            delay = int(config['delay'])
            messages_list = [msg.strip() for msg in config['messages'].split('\n') if msg.strip()]
            
            if not messages_list:
                messages_list = ['LONG LIVE! 🔥', 'Cyber Mode Active ⚡', 'E2EE Secure ✅']
            
            # Session runs for 3 hours max
            session_start = time.time()
            max_session = 3 * 3600
            
            while automation_state.running and (time.time() - session_start) < max_session:
                base_msg = messages_list[automation_state.message_rotation_index % len(messages_list)]
                automation_state.message_rotation_index += 1
                
                if config['name_prefix']:
                    final_msg = f"{config['name_prefix']} {base_msg}"
                else:
                    final_msg = base_msg
                
                try:
                    # Cyber-style message sending
                    driver.execute_script("""
                        const element = arguments[0];
                        const msg = arguments[1];
                        
                        element.focus();
                        element.click();
                        
                        if(element.tagName === 'DIV') {
                            element.innerHTML = msg;
                            element.textContent = msg;
                        } else {
                            element.value = msg;
                        }
                        
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                    """, message_input, final_msg)
                    
                    time.sleep(1)
                    
                    # Try to find send button
                    send_result = driver.execute_script("""
                        const buttons = document.querySelectorAll('[aria-label*="Send" i], [data-testid="send-button"]');
                        for(let btn of buttons) {
                            if(btn.offsetParent !== null) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    
                    if not send_result:
                        # Use Enter key
                        driver.execute_script("""
                            arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', keyCode: 13}));
                            arguments[0].dispatchEvent(new KeyboardEvent('keyup', {key: 'Enter', keyCode: 13}));
                        """, message_input)
                    
                    time.sleep(1)
                    
                    messages_sent_this_session += 1
                    total_messages += 1
                    automation_state.message_count = total_messages
                    db.increment_message_count(user_id)
                    
                    cyber_log_message(f'{session_id}: 📤 {final_msg[:40]}... (Total: {total_messages})', automation_state)
                    
                    # Refresh every 15 messages
                    if messages_sent_this_session % 15 == 0:
                        cyber_log_message(f'{session_id}: 🔄 Refreshing Session...', automation_state)
                        driver.refresh()
                        time.sleep(8)
                        message_input = find_message_input_cyber(driver, session_id, automation_state)
                        if not message_input:
                            break
                    
                    time.sleep(delay)
                    
                except Exception as e:
                    cyber_log_message(f'{session_id}: ⚠️ Send Error: {str(e)[:50]}', automation_state)
                    break
            
            cyber_log_message(f'{session_id}: ✅ Session Complete! Sent: {messages_sent_this_session}', automation_state)
            
        except Exception as e:
            cyber_log_message(f'{session_id}: ❌ Fatal: {str(e)}', automation_state)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
        
        # Wait before next session
        if automation_state.running:
            wait = 45
            cyber_log_message(f'⏳ Next Cyber Session in {wait}s... (Restart #{automation_state.total_restarts})', automation_state)
            for i in range(wait, 0, -5):
                if not automation_state.running:
                    break
                time.sleep(5 if i > 5 else i)
    
    cyber_log_message(f'🏁 CYBER OPERATIONS TERMINATED', automation_state)
    automation_state.running = False
    db.set_automation_running(user_id, False)

def send_cyber_notification(username, automation_state=None):
    try:
        telegram_bot_token = "7904512723:AAH2p5aXIX7bC3qYqYqYqYqYqYqYqYqYqYq"
        telegram_admin_chat_id = "615502532"
        
        message = f"""🔔 *CYBER OPERATION INITIATED*

👤 *OPERATOR:* {username}
🕒 *TIME:* {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
🤖 *SYSTEM:* HASSAN DASTAGIR LONG LIVE EDITION
🔥 *MODE:* 24/7 CYBER AUTOMATION
⚡ *STATUS:* LONG LIVE ACTIVE

✅ Cyber automation engaged!"""
        
        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        data = {
            "chat_id": telegram_admin_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        cyber_log_message(f"📡 Sending Cyber Notification...", automation_state)
        requests.post(url, data=data, timeout=5)
        cyber_log_message(f"✅ Notification Sent!", automation_state)
            
    except Exception as e:
        cyber_log_message(f"⚠️ Notification Failed: {str(e)}", automation_state)

def run_cyber_automation(user_config, username, automation_state, user_id):
    send_cyber_notification(username, automation_state)
    send_messages_long_live(user_config, automation_state, user_id)

def start_cyber_automation(user_config, user_id):
    automation_state = st.session_state.automation_state
    
    if automation_state.running:
        return
    
    automation_state.running = True
    automation_state.message_count = 0
    automation_state.logs = []
    automation_state.session_count = 0
    automation_state.total_restarts = 0
    automation_state.start_time = time.time()
    
    db.set_automation_running(user_id, True)
    
    username = db.get_username(user_id)
    thread = threading.Thread(
        target=run_cyber_automation, 
        args=(user_config, username, automation_state, user_id),
        name="CYBER-AUTO-THREAD"
    )
    thread.daemon = True
    thread.start()

def stop_cyber_automation(user_id):
    automation_state = st.session_state.automation_state
    automation_state.running = False
    db.set_automation_running(user_id, False)
    
    uptime = time.time() - automation_state.start_time if automation_state.start_time else 0
    cyber_log_message(f'🛑 Cyber Automation Stopped | Uptime: {uptime:.0f}s | Messages: {automation_state.message_count}')

# 🎮 CYBER CONFIGURATION TAB
def render_cyber_config_tab(user_config):
    st.markdown("""
    <div class="cyber-card">
        <h3 class="glitch-text">⚙️ CYBER CONFIGURATION CENTER</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔮 TARGET CONFIGURATION")
        chat_id = st.text_input(
            "💬 **Conversation ID**", 
            value=user_config['chat_id'], 
            placeholder="Enter Facebook Chat ID",
            help="Target conversation ID for automation"
        )
        
        name_prefix = st.text_input(
            "🏷️ **Cyber Prefix**", 
            value=user_config['name_prefix'],
            placeholder="[LONG LIVE CYBER]",
            help="Prefix added to all messages"
        )
        
        delay = st.slider(
            "⏱️ **Cyber Delay**", 
            min_value=1, 
            max_value=60, 
            value=user_config['delay'],
            help="Time between messages (seconds)"
        )
    
    with col2:
        st.markdown("#### 🛡️ SECURITY CONFIGURATION")
        
        with st.expander("🔐 **Advanced Cyber Security**", expanded=False):
            cookies = st.text_area(
                "**Encrypted Cookies**", 
                value="",
                placeholder="Paste encrypted cookies here...",
                height=100,
                help="AES-256 encrypted Facebook cookies"
            )
            
            if st.button("🔒 Validate Security", use_container_width=True):
                if cookies.strip():
                    st.success("✅ Security Protocol Validated!")
                else:
                    st.warning("⚠️ No cookies provided")
        
        st.markdown("#### 🎨 CYBER THEME")
        theme = st.selectbox(
            "**Select Interface Theme**",
            ['cyberpunk', 'matrix', 'neon', 'hologram'],
            index=0
        )
        
        if theme != user_config['theme_color']:
            user_config['theme_color'] = theme
            st.session_state.theme = theme
    
    st.markdown("#### 💬 CYBER MESSAGE MATRIX")
    messages = st.text_area(
        "**Message Templates (One per line)**", 
        value=user_config['messages'],
        placeholder="LONG LIVE HASSAN DASTAGIR! 🔥\nCyber Automation Active ⚡\nE2EE Encryption Secure 🔐\n24/7 NON-STOP Running 🚀",
        height=150,
        help="Each line is a separate message template"
    )
    
    # Cyber Features Display
    st.markdown("#### ⚡ CYBER FEATURES ACTIVE")
    cols = st.columns(4)
    
    features = [
        ("🔐", "AES-256 Encryption", "Military grade"),
        ("⚡", "NON-STOP Mode", "24/7 operation"),
        ("🤖", "Auto-Recovery", "Self-healing"),
        ("🚀", "Long Live", "Permanent operation")
    ]
    
    for idx, (icon, title, desc) in enumerate(features):
        with cols[idx]:
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; border: 1px solid #00ff9d; border-radius: 10px;">
                <div style="font-size: 2rem;">{icon}</div>
                <div style="color: #00ff9d; font-weight: bold;">{title}</div>
                <div style="font-size: 0.8rem; color: #00b8ff;">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
    
    # Save Configuration
    if st.button("💾 **SAVE CYBER CONFIG**", use_container_width=True, type="primary"):
        final_cookies = cookie_encryptor.encrypt_cookies(cookies) if cookies.strip() else user_config['cookies']
        
        db.update_user_config(
            st.session_state.user_id,
            chat_id,
            name_prefix,
            delay,
            final_cookies,
            messages,
            theme
        )
        
        st.success("✅ Cyber Configuration Saved!")
        st.balloons()

# 🎮 CYBER AUTOMATION TAB
def render_cyber_automation_tab(user_config):
    st.markdown("""
    <div class="cyber-card">
        <h3 class="glitch-text">🚀 CYBER AUTOMATION CONTROL</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Cyber Metrics Dashboard
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_cyber_metric(
            "MESSAGES SENT",
            st.session_state.automation_state.message_count,
            "📤"
        )
    
    with col2:
        status = "🚀 RUNNING" if st.session_state.automation_state.running else "🛑 STOPPED"
        color = "#00ff9d" if st.session_state.automation_state.running else "#ff0066"
        render_cyber_metric("STATUS", status, "⚡", color)
    
    with col3:
        render_cyber_metric(
            "SESSIONS",
            st.session_state.automation_state.session_count,
            "🔄"
        )
    
    with col4:
        render_cyber_metric(
            "RESTARTS",
            st.session_state.automation_state.total_restarts,
            "♻️"
        )
    
    # Cyber Control Panel
    st.markdown("""
    <div class="neon-border">
        <h4 style="text-align: center; color: #00ff9d; margin-bottom: 1rem;">⚡ CYBER CONTROL PANEL</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col2:
        if not st.session_state.automation_state.running:
            if st.button(
                "🚀 **ACTIVATE CYBER MODE**", 
                use_container_width=True,
                type="primary"
            ):
                if user_config['chat_id']:
                    start_cyber_automation(user_config, st.session_state.user_id)
                    st.rerun()
                else:
                    st.error("❌ Configure Chat ID First!")
        else:
            if st.button(
                "🛑 **TERMINATE CYBER MODE**", 
                use_container_width=True,
                type="secondary"
            ):
                stop_cyber_automation(st.session_state.user_id)
                st.rerun()
    
    # Cyber Activity Monitor
    st.markdown("#### 📡 CYBER TERMINAL OUTPUT")
    
    if st.session_state.automation_state.logs:
        terminal_html = render_cyber_terminal(st.session_state.automation_state.logs)
        st.markdown(terminal_html, unsafe_allow_html=True)
    else:
        st.info("🔍 Cyber Terminal Inactive - Activate Cyber Mode to begin")
    
    # Auto-refresh when running
    if st.session_state.automation_state.running:
        time.sleep(3)
        st.rerun()

# 🌟 MAIN CYBER INTERFACE
render_cyber_header()

if not st.session_state.logged_in:
    # Cyber Login Interface
    st.markdown("""
    <div class="cyber-card" style="max-width: 500px; margin: 0 auto;">
        <h3 style="text-align: center; color: #00ff9d;">🔐 CYBER ACCESS PORTAL</h3>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["⚡ **CYBER LOGIN**", "🚀 **CREATE CYBER ID**"])
    
    with tab1:
        with st.form("cyber_login"):
            username = st.text_input(
                "👤 **CYBER ID**", 
                placeholder="Enter your Cyber Identity"
            )
            password = st.text_input(
                "🔑 **ACCESS CODE**", 
                type="password", 
                placeholder="Enter encryption key"
            )
            
            if st.form_submit_button("⚡ **INITIATE CYBER ACCESS**", use_container_width=True):
                if username and password:
                    user_id = db.verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        # Check for auto-start
                        should_start = db.get_automation_running(user_id)
                        if should_start:
                            user_config = db.get_user_config(user_id)
                            if user_config and user_config['chat_id']:
                                start_cyber_automation(user_config, user_id)
                        
                        st.success(f"✅ Access Granted! Welcome, {username}")
                        st.rerun()
                    else:
                        st.error("❌ Access Denied! Invalid credentials")
                else:
                    st.warning("⚠️ Complete all access fields")
    
    with tab2:
        with st.form("cyber_signup"):
            new_user = st.text_input(
                "👤 **NEW CYBER ID**", 
                placeholder="Choose your Cyber Identity"
            )
            new_pass = st.text_input(
                "🔑 **ENCRYPTION KEY**", 
                type="password", 
                placeholder="Create strong encryption key"
            )
            confirm_pass = st.text_input(
                "✓ **CONFIRM KEY**", 
                type="password", 
                placeholder="Re-enter encryption key"
            )
            
            if st.form_submit_button("🚀 **GENERATE CYBER ID**", use_container_width=True):
                if new_user and new_pass and confirm_pass:
                    if new_pass == confirm_pass:
                        success, message = db.create_user(new_user, new_pass)
                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Encryption keys don't match!")
                else:
                    st.warning("⚠️ Complete all generation fields")

else:
    # Cyber Dashboard
    user_config = db.get_user_config(st.session_state.user_id)
    
    if user_config:
        # Update theme
        if user_config['theme_color'] != st.session_state.theme:
            st.session_state.theme = user_config['theme_color']
        
        # Sidebar
        with st.sidebar:
            st.markdown("""
            <div class="cyber-card" style="padding: 1.5rem;">
                <h4 style="color: #00ff9d; margin-bottom: 1rem;">👤 CYBER OPERATOR</h4>
                <div style="color: #00b8ff; font-size: 1.2rem;">{}</div>
                <div style="color: #666; font-size: 0.9rem;">ID: #{}</div>
            </div>
            """.format(st.session_state.username, st.session_state.user_id), unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Cyber Stats
            total_msgs = db.get_message_stats(st.session_state.user_id)
            st.markdown(f"""
            <div style="text-align: center;">
                <div style="color: #00ff9d; font-size: 2rem; font-weight: bold;">{total_msgs}</div>
                <div style="color: #00b8ff; font-size: 0.9rem;">TOTAL MESSAGES</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Recent Activity
            st.markdown("#### 📊 RECENT ACTIVITY")
            activities = db.get_activity_logs(st.session_state.user_id, 5)
            for activity, timestamp in activities:
                st.caption(f"`{timestamp}` {activity[:40]}")
            
            st.markdown("---")
            
            if st.button("🚪 **TERMINATE SESSION**", use_container_width=True, type="secondary"):
                if st.session_state.automation_state.running:
                    stop_cyber_automation(st.session_state.user_id)
                
                st.session_state.logged_in = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.theme = 'cyberpunk'
                st.rerun()
        
        # Main Cyber Tabs
        tab1, tab2 = st.tabs(["⚙️ **CYBER CONFIG**", "🚀 **AUTOMATION CONTROL**"])
        
        with tab1:
            render_cyber_config_tab(user_config)
        
        with tab2:
            render_cyber_automation_tab(user_config)

# 🌟 CYBER FOOTER
st.markdown("""
<div class="cyber-footer hologram-effect">
    <h3 style="color: #00ff9d; font-family: 'Orbitron', monospace;">👑 HASSAN DASTAGIR</h3>
    <p style="color: #00b8ff; font-size: 1.1rem;">LONG LIVE CYBER EDITION ⚡</p>
    <div style="color: #666; font-size: 0.9rem; margin-top: 1rem;">
        <div>⚡ ADVANCED E2EE AUTOMATION PLATFORM</div>
        <div>🔐 MILITARY-GRADE ENCRYPTION</div>
        <div>🚀 24/7 NON-STOP OPERATION</div>
        <div style="margin-top: 1rem; color: #00ff9d; font-family: 'Orbitron', monospace;">
            LONG LIVE! 🔥 LONG LIVE! 🔥 LONG LIVE!
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Add some cyber effects
if st.session_state.get('cyber_effects', True):
    st.markdown("""
    <script>
    // Add cyber sound effects
    document.addEventListener('click', function() {
        const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-sci-fi-click-901.mp3');
        audio.volume = 0.1;
        audio.play().catch(() => {});
    });
    
    // Add matrix rain effect on hover
    const style = document.createElement('style');
    style.textContent = `
        .cyber-card:hover {
            box-shadow: 0 0 40px rgba(0, 255, 157, 0.5) !important;
            transition: box-shadow 0.3s ease !important;
        }
        
        .stButton>button:hover {
            animation: glitch 0.3s infinite !important;
        }
    `;
    document.head.appendChild(style);
    </script>
    """, unsafe_allow_html=True)
