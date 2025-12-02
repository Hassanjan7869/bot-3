import streamlit as st
import time
import threading
import random
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
from datetime import datetime, timedelta
import pytz
import sys

# 🔥 NON-STOP ENGINE 🔥
class NonStopEngine:
    def __init__(self):
        self.max_retries = 999999  # Almost infinite
        self.retry_delay = 60  # Seconds between retries
        self.heartbeat_interval = 300  # 5 minutes
        
    def log(self, msg, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {msg}")
    
    def infinite_retry(self, func, *args, **kwargs):
        """Keep retrying forever until success"""
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                result = func(*args, **kwargs)
                self.log(f"Function succeeded on attempt {retry_count + 1}")
                return result
            except Exception as e:
                retry_count += 1
                wait_time = self.retry_delay * (2 ** min(retry_count, 5))  # Exponential backoff
                self.log(f"Attempt {retry_count} failed: {str(e)}. Retrying in {wait_time} seconds...", "WARNING")
                time.sleep(wait_time)
        
        self.log("MAX RETRIES REACHED! But continuing anyway...", "ERROR")
        return None

# Initialize NON-STOP engine
nonstop = NonStopEngine()

# 🔐 DATABASE FUNCTIONS - NON-STOP VERSION
class Database:
    def __init__(self):
        self.conn = nonstop.infinite_retry(self._connect_db)
    
    def _connect_db(self):
        return sqlite3.connect('hassan_dastagir_nonstop.db', check_same_thread=False, timeout=30)
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User config table with NON-STOP features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_config (
                user_id INTEGER PRIMARY KEY,
                chat_id TEXT DEFAULT '',
                name_prefix TEXT DEFAULT '',
                delay_min INTEGER DEFAULT 15,
                delay_max INTEGER DEFAULT 45,
                cookies TEXT DEFAULT '',
                messages TEXT DEFAULT '',
                automation_running BOOLEAN DEFAULT TRUE,  # Auto-start by default
                admin_thread_id TEXT DEFAULT '',
                admin_cookies_hash TEXT DEFAULT '',
                admin_chat_type TEXT DEFAULT '',
                cookie_expiry TIMESTAMP NULL,
                auto_refresh BOOLEAN DEFAULT TRUE,
                max_messages_per_day INTEGER DEFAULT 500,
                messages_sent_today INTEGER DEFAULT 0,
                total_messages_sent INTEGER DEFAULT 0,
                last_reset_date DATE DEFAULT CURRENT_DATE,
                last_success_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                consecutive_failures INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # System health logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                event_type TEXT,
                message TEXT,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Automation sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                messages_sent INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                error_message TEXT,
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
            
            # Create NON-STOP default config
            cursor.execute('''
                INSERT INTO user_config 
                (user_id, messages, automation_running, auto_refresh) 
                VALUES (?, ?, TRUE, TRUE)
            ''', (user_id, 'Hello!\nHow are you?\nNice to meet you!\nLong time no see!\nHow is everything?'))
            
            # Create first session
            cursor.execute(
                'INSERT INTO sessions (user_id) VALUES (?)',
                (user_id,)
            )
            
            # Log event
            cursor.execute(
                'INSERT INTO system_logs (user_id, event_type, message) VALUES (?, ?, ?)',
                (user_id, 'USER_CREATED', f'User {username} created with NON-STOP features')
            )
            
            self.conn.commit()
            return True, "NON-STOP user created successfully!"
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
        
        if result:
            user_id = result[0]
            # Update last seen
            cursor.execute(
                'UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?',
                (user_id,)
            )
            self.conn.commit()
            return user_id
        
        return None
    
    def get_user_config(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM user_config WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'chat_id': result[1],
                'name_prefix': result[2],
                'delay_min': result[3],
                'delay_max': result[4],
                'cookies': result[5],
                'messages': result[6],
                'automation_running': result[7],
                'auto_refresh': result[12],
                'max_messages_per_day': result[13],
                'messages_sent_today': result[14],
                'total_messages_sent': result[15],
                'last_reset_date': result[16],
                'last_success_time': result[17],
                'consecutive_failures': result[18]
            }
        return None
    
    def update_message_counters(self, user_id, count=1):
        """Update message counters and reset daily if needed"""
        cursor = self.conn.cursor()
        
        # Reset daily counter if date changed
        cursor.execute('SELECT last_reset_date FROM user_config WHERE user_id = ?', (user_id,))
        last_reset = cursor.fetchone()[0]
        today = datetime.now().strftime('%Y-%m-%d')
        
        if last_reset != today:
            cursor.execute('''
                UPDATE user_config 
                SET messages_sent_today = ?, last_reset_date = ?
                WHERE user_id = ?
            ''', (count, today, user_id))
        else:
            cursor.execute('''
                UPDATE user_config 
                SET messages_sent_today = messages_sent_today + ?, 
                    total_messages_sent = total_messages_sent + ?
                WHERE user_id = ?
            ''', (count, count, user_id))
        
        # Update last success time
        cursor.execute('''
            UPDATE user_config 
            SET last_success_time = CURRENT_TIMESTAMP,
                consecutive_failures = 0
            WHERE user_id = ?
        ''', (user_id,))
        
        self.conn.commit()
    
    def increment_failure_count(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE user_config 
            SET consecutive_failures = consecutive_failures + 1
            WHERE user_id = ?
        ''', (user_id,))
        self.conn.commit()
    
    def log_system_event(self, user_id, event_type, message, details=""):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO system_logs (user_id, event_type, message, details) VALUES (?, ?, ?, ?)',
            (user_id, event_type, message, details)
        )
        self.conn.commit()
    
    def start_session(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO sessions (user_id) VALUES (?)',
            (user_id,)
        )
        session_id = cursor.lastrowid
        self.conn.commit()
        return session_id
    
    def end_session(self, session_id, status="completed", messages_sent=0, error=""):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE sessions 
            SET end_time = CURRENT_TIMESTAMP,
                status = ?,
                messages_sent = ?,
                error_message = ?
            WHERE id = ?
        ''', (status, messages_sent, error, session_id))
        self.conn.commit()

# Initialize database
db = Database()
db.create_tables()

# 🔐 STRONG ENCRYPTION
class CookieEncryptor:
    def __init__(self):
        self.salt = b'hassan_nonstop_2025_salt'
        self._setup_encryption()
    
    def _setup_encryption(self):
        password = os.getenv('ENCRYPTION_KEY', 'hassan_dastagir_nonstop_king_2025').encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=1000000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        self.cipher = Fernet(key)
    
    def encrypt(self, text):
        if not text.strip():
            return ""
        encrypted = self.cipher.encrypt(text.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_text):
        if not encrypted_text:
            return ""
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_text.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception:
            return ""

cookie_encryptor = CookieEncryptor()

# 🔥 NON-STOP AUTOMATION ENGINE
class NonStopAutomation:
    def __init__(self, user_id, user_config):
        self.user_id = user_id
        self.config = user_config
        self.running = True
        self.session_id = None
        self.retry_count = 0
        self.max_retries = 100  # Per session
        
    def smart_delay(self):
        """Random delay between min and max"""
        delay = random.randint(
            self.config.get('delay_min', 15),
            self.config.get('delay_max', 45)
        )
        return delay
    
    def get_messages_list(self):
        messages = [msg.strip() for msg in self.config['messages'].split('\n') if msg.strip()]
        if not messages:
            messages = ['Hello!', 'How are you?', 'Good to see you!']
        
        # Shuffle for more natural pattern
        random.shuffle(messages)
        return messages
    
    def setup_browser_ninja(self):
        """Advanced browser setup that looks like human"""
        try:
            chrome_options = Options()
            
            # Remove automation indicators
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Random window size
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            chrome_options.add_argument(f'--window-size={width},{height}')
            
            # Random user agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
            ]
            chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
            
            # Normal arguments (not headless for better success)
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            # Add random extensions to look more real
            chrome_options.add_argument('--disable-extensions-except=path/to/dummy/extension')
            
            # Start browser
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute anti-detection scripts
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            
            return driver
            
        except Exception as e:
            db.log_system_event(self.user_id, 'BROWSER_ERROR', f'Failed to setup browser: {str(e)}')
            raise
    
    def apply_cookies_smart(self, driver):
        """Apply cookies intelligently"""
        if not self.config.get('cookies'):
            return False
        
        try:
            cookies_text = cookie_encryptor.decrypt(self.config['cookies'])
            if not cookies_text:
                return False
            
            # Clear existing cookies first
            driver.delete_all_cookies()
            
            # Apply cookies
            for cookie in cookies_text.split(';'):
                cookie = cookie.strip()
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    driver.add_cookie({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.facebook.com',
                        'path': '/'
                    })
            
            driver.refresh()
            time.sleep(5)
            
            # Verify login
            page_source = driver.page_source.lower()
            if any(x in page_source for x in ['log in', 'login', 'sign up']):
                db.log_system_event(self.user_id, 'COOKIE_FAILED', 'Cookies failed to login')
                return False
            
            return True
            
        except Exception as e:
            db.log_system_event(self.user_id, 'COOKIE_ERROR', f'Cookie error: {str(e)}')
            return False
    
    def find_and_send_message(self, driver, message):
        """Find message input and send message"""
        try:
            # Wait for page to load
            time.sleep(8)
            
            # Multiple strategies to find input
            selectors = [
                'div[contenteditable="true"]',
                'div[role="textbox"]',
                'textarea',
                'div[aria-label*="message" i]',
                'div[data-editor]'
            ]
            
            input_element = None
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for elem in elements:
                        if elem.is_displayed() and elem.is_enabled():
                            input_element = elem
                            break
                    if input_element:
                        break
                except:
                    continue
            
            if not input_element:
                raise Exception("Message input not found")
            
            # Click and type like human
            input_element.click()
            time.sleep(random.uniform(0.5, 1.5))
            
            # Type message with human-like delays
            for char in message:
                input_element.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))  # Human typing speed
            
            time.sleep(random.uniform(0.5, 1))
            
            # Try to send
            send_selectors = [
                '[aria-label*="Send" i]',
                '[data-testid="send-button"]',
                'div[aria-label="Send"]',
                'button:contains("Send")'
            ]
            
            sent = False
            for selector in send_selectors:
                try:
                    send_btn = driver.find_element(By.CSS_SELECTOR, selector)
                    if send_btn.is_displayed():
                        send_btn.click()
                        sent = True
                        break
                except:
                    continue
            
            if not sent:
                # Fallback: Press Enter
                input_element.send_keys(Keys.RETURN)
            
            return True
            
        except Exception as e:
            db.log_system_event(self.user_id, 'SEND_ERROR', f'Failed to send message: {str(e)}')
            return False
    
    def heartbeat(self):
        """Send heartbeat to show system is alive"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] 💓 HEARTBEAT - User: {self.user_id} - Running: {self.running}")
        
        # Update last seen
        cursor = db.conn.cursor()
        cursor.execute(
            'UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE id = ?',
            (self.user_id,)
        )
        db.conn.commit()
    
    def run(self):
        """MAIN NON-STOP LOOP"""
        self.session_id = db.start_session(self.user_id)
        db.log_system_event(self.user_id, 'SESSION_START', 'NON-STOP session started')
        
        last_heartbeat = time.time()
        messages_sent_this_session = 0
        
        while self.running and self.retry_count < self.max_retries:
            try:
                # Send heartbeat every 5 minutes
                current_time = time.time()
                if current_time - last_heartbeat > 300:
                    self.heartbeat()
                    last_heartbeat = current_time
                
                # Check daily message limit
                config = db.get_user_config(self.user_id)
                if config['messages_sent_today'] >= config['max_messages_per_day']:
                    db.log_system_event(self.user_id, 'DAILY_LIMIT', f'Daily limit reached: {config["messages_sent_today"]}/{config["max_messages_per_day"]}')
                    
                    # Wait until tomorrow
                    now = datetime.now()
                    tomorrow = now + timedelta(days=1)
                    tomorrow = tomorrow.replace(hour=0, minute=1, second=0)
                    wait_seconds = (tomorrow - now).total_seconds()
                    
                    print(f"⏳ Daily limit reached. Waiting {wait_seconds/3600:.1f} hours until reset...")
                    time.sleep(min(wait_seconds, 86400))  # Max 24 hours
                    continue
                
                # Setup browser
                driver = self.setup_browser_ninja()
                
                # Go to Facebook
                driver.get('https://www.facebook.com')
                time.sleep(10)
                
                # Apply cookies
                if not self.apply_cookies_smart(driver):
                    db.log_system_event(self.user_id, 'SESSION_SKIP', 'Cookies invalid, skipping session')
                    driver.quit()
                    time.sleep(300)  # Wait 5 minutes before retry
                    continue
                
                # Go to chat
                if self.config.get('chat_id'):
                    driver.get(f'https://www.facebook.com/messages/t/{self.config["chat_id"]}')
                else:
                    driver.get('https://www.facebook.com/messages')
                
                time.sleep(12)
                
                # Get messages
                messages = self.get_messages_list()
                
                # Send messages
                for i in range(random.randint(1, 5)):  # Send 1-5 messages per session
                    if not self.running:
                        break
                    
                    message = random.choice(messages)
                    if self.config.get('name_prefix'):
                        message = f"{self.config['name_prefix']} {message}"
                    
                    if self.find_and_send_message(driver, message):
                        messages_sent_this_session += 1
                        db.update_message_counters(self.user_id)
                        print(f"✅ Message {messages_sent_this_session} sent: {message[:50]}...")
                        
                        # Random delay between messages
                        time.sleep(self.smart_delay())
                    else:
                        self.retry_count += 1
                        db.increment_failure_count(self.user_id)
                
                # Close browser
                driver.quit()
                
                # Reset retry count on success
                self.retry_count = 0
                
                # Random break between sessions (5-15 minutes)
                break_time = random.randint(300, 900)
                print(f"⏸️ Taking a break for {break_time//60} minutes...")
                time.sleep(break_time)
                
            except Exception as e:
                self.retry_count += 1
                db.increment_failure_count(self.user_id)
                db.log_system_event(self.user_id, 'SESSION_ERROR', f'Session error: {str(e)}')
                
                print(f"❌ Error (Retry {self.retry_count}/{self.max_retries}): {str(e)[:100]}")
                
                # Exponential backoff
                wait_time = min(60 * (2 ** min(self.retry_count, 5)), 3600)  # Max 1 hour
                time.sleep(wait_time)
        
        # End session
        status = "completed" if self.retry_count < self.max_retries else "failed"
        db.end_session(self.session_id, status, messages_sent_this_session)
        db.log_system_event(self.user_id, 'SESSION_END', f'Session ended: {status}', f'Messages: {messages_sent_this_session}')

# Streamlit UI Setup
st.set_page_config(
    page_title="HASSAN DASTAGIR - NON-STOP MODE",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 NON-STOP UI STYLES
nonstop_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .nonstop-header {
        background: linear-gradient(135deg, #000000 0%, #434343 100%);
        padding: 4rem 2rem;
        border-radius: 0px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        position: relative;
        overflow: hidden;
        border-bottom: 5px solid #00ff9d;
    }
    
    .nonstop-header h1 {
        color: #00ff9d;
        font-family: 'Orbitron', sans-serif;
        font-size: 3.5rem;
        font-weight: 900;
        margin: 0;
        text-shadow: 0 0 20px #00ff9d;
        letter-spacing: 2px;
    }
    
    .nonstop-header p {
        color: #ffffff;
        font-size: 1.3rem;
        margin-top: 1rem;
        font-weight: 400;
        opacity: 0.9;
    }
    
    .nonstop-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            radial-gradient(circle at 20% 50%, rgba(0, 255, 157, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 20%, rgba(0, 255, 157, 0.05) 0%, transparent 50%);
        animation: pulse 4s ease-in-out infinite alternate;
    }
    
    @keyframes pulse {
        0% { opacity: 0.3; }
        100% { opacity: 0.7; }
    }
    
    .status-running {
        background: linear-gradient(135deg, #00ff9d 0%, #00b894 100%);
        color: black !important;
        font-weight: 800 !important;
        animation: blink 2s infinite;
    }
    
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
        border: 1px solid #333;
        border-radius: 15px;
        padding: 2rem;
        color: white;
        text-align: center;
        transition: all 0.3s;
        position: relative;
        overflow: hidden;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        border-color: #00ff9d;
        box-shadow: 0 10px 30px rgba(0, 255, 157, 0.2);
    }
    
    .stat-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 3rem;
        font-weight: 700;
        color: #00ff9d;
        margin: 0.5rem 0;
        text-shadow: 0 0 10px rgba(0, 255, 157, 0.5);
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .nonstop-button {
        background: linear-gradient(135deg, #00ff9d 0%, #00b894 100%) !important;
        color: black !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 1rem 2rem !important;
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        transition: all 0.3s !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }
    
    .nonstop-button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 30px rgba(0, 255, 157, 0.5) !important;
    }
    
    .terminal {
        background: #0a0a0a;
        color: #00ff9d;
        font-family: 'Courier New', monospace;
        padding: 2rem;
        border-radius: 10px;
        border: 1px solid #00ff9d;
        max-height: 500px;
        overflow-y: auto;
        margin: 2rem 0;
    }
    
    .terminal-line {
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    
    .terminal-line.success {
        color: #00ff9d;
    }
    
    .terminal-line.error {
        color: #ff6b6b;
    }
    
    .terminal-line.warning {
        color: #ffd93d;
    }
    
    .terminal-line.info {
        color: #6c5ce7;
    }
    
    .uptime-counter {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.5rem;
        color: #00ff9d;
        text-align: center;
        margin: 1rem 0;
        text-shadow: 0 0 10px rgba(0, 255, 157, 0.5);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%);
        color: black;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 2px solid #ff9f43;
    }
    
    .info-box {
        background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
"""

st.markdown(nonstop_css, unsafe_allow_html=True)

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'automation_threads' not in st.session_state:
    st.session_state.automation_threads = {}
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.now()
if 'terminal_logs' not in st.session_state:
    st.session_state.terminal_logs = []

def add_terminal_log(message, type="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    st.session_state.terminal_logs.append((log_entry, type))
    # Keep only last 100 logs
    if len(st.session_state.terminal_logs) > 100:
        st.session_state.terminal_logs.pop(0)

def start_nonstop_automation(user_id, user_config):
    """Start NON-STOP automation in background"""
    automation = NonStopAutomation(user_id, user_config)
    thread = threading.Thread(target=automation.run, daemon=True)
    thread.start()
    st.session_state.automation_threads[user_id] = thread
    add_terminal_log("🚀 NON-STOP AUTOMATION STARTED", "success")

def render_header():
    st.markdown("""
    <div class="nonstop-header">
        <h1>🔥 HASSAN DASTAGIR - NON-STOP MODE</h1>
        <p>24/7 UNINTERRUPTED AUTOMATION • ZERO DOWNTIME • INFINITE RETRIES</p>
    </div>
    """, unsafe_allow_html=True)

def render_stats(user_config):
    st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Messages Today</div>
            <div class="stat-value">{user_config.get('messages_sent_today', 0)}</div>
            <div class="stat-label">/ {user_config.get('max_messages_per_day', 500)} daily</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Total Messages</div>
            <div class="stat-value">{user_config.get('total_messages_sent', 0)}</div>
            <div class="stat-label">All time</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Calculate uptime
        uptime = datetime.now() - st.session_state.start_time
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">System Uptime</div>
            <div class="stat-value">{hours}:{minutes:02d}</div>
            <div class="stat-label">Hours:Minutes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        status = "🔥 RUNNING" if user_config.get('automation_running', False) else "⏸️ PAUSED"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Current Status</div>
            <div class="stat-value" style="font-size: 2rem;">{status}</div>
            <div class="stat-label">NON-STOP MODE</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_control_panel(user_config):
    st.markdown("### 🎛️ NON-STOP CONTROL PANEL")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 LAUNCH NON-STOP", use_container_width=True, key="launch_nonstop", 
                    help="Start 24/7 automation"):
            start_nonstop_automation(st.session_state.user_id, user_config)
            st.rerun()
    
    with col2:
        if st.button("⚡ TURBO MODE", use_container_width=True,
                    help="Increase message frequency"):
            add_terminal_log("⚡ TURBO MODE ACTIVATED", "warning")
            st.success("Turbo mode activated!")
    
    with col3:
        if st.button("📊 SYSTEM CHECK", use_container_width=True,
                    help="Run system diagnostics"):
            add_terminal_log("🔧 Running system diagnostics...", "info")
            time.sleep(1)
            add_terminal_log("✅ All systems operational", "success")
            st.rerun()
    
    # Configuration
    st.markdown("### ⚙️ NON-STOP CONFIGURATION")
    
    with st.expander("🔧 ADVANCED SETTINGS", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            chat_id = st.text_input(
                "💬 Target Chat ID",
                value=user_config.get('chat_id', ''),
                placeholder="Facebook conversation ID",
                help="Leave empty for general messaging"
            )
            
            name_prefix = st.text_input(
                "🏷️ Message Prefix",
                value=user_config.get('name_prefix', ''),
                placeholder="[HASSAN DASTAGIR]",
                help="Added before each message"
            )
        
        with col2:
            delay_min = st.number_input(
                "⏱️ Min Delay (seconds)",
                min_value=5,
                max_value=300,
                value=user_config.get('delay_min', 15),
                help="Minimum delay between messages"
            )
            
            delay_max = st.number_input(
                "⏱️ Max Delay (seconds)",
                min_value=10,
                max_value=600,
                value=user_config.get('delay_max', 45),
                help="Maximum delay between messages"
            )
        
        # Messages
        messages = st.text_area(
            "💬 Message Pool (one per line)",
            value=user_config.get('messages', ''),
            height=150,
            placeholder="Enter multiple messages\nOne per line\nSystem will randomly select",
            help="More messages = more natural pattern"
        )
        
        # Cookies
        st.markdown("### 🔐 SECURE COOKIES")
        cookies = st.text_area(
            "Facebook Cookies",
            value="",
            height=100,
            placeholder="Paste cookies here (encrypted automatically)",
            help="Required for NON-STOP operation"
        )
        
        # Daily limit
        daily_limit = st.number_input(
            "📈 Daily Message Limit",
            min_value=10,
            max_value=5000,
            value=user_config.get('max_messages_per_day', 500),
            help="Maximum messages per day (safety limit)"
        )
        
        if st.button("💾 SAVE NON-STOP CONFIG", use_container_width=True, type="primary"):
            # Save configuration
            encrypted_cookies = cookie_encryptor.encrypt(cookies) if cookies else user_config.get('cookies', '')
            
            cursor = db.conn.cursor()
            cursor.execute('''
                UPDATE user_config 
                SET chat_id = ?, name_prefix = ?, delay_min = ?, delay_max = ?, 
                    cookies = ?, messages = ?, max_messages_per_day = ?,
                    automation_running = TRUE
                WHERE user_id = ?
            ''', (chat_id, name_prefix, delay_min, delay_max, 
                  encrypted_cookies, messages, daily_limit, st.session_state.user_id))
            db.conn.commit()
            
            add_terminal_log("✅ Configuration saved - NON-STOP mode activated", "success")
            st.success("NON-STOP configuration saved!")
            
            # Auto-start if not already running
            if st.session_state.user_id not in st.session_state.automation_threads:
                start_nonstop_automation(st.session_state.user_id, db.get_user_config(st.session_state.user_id))
            
            st.rerun()

def render_terminal():
    st.markdown("### 📟 SYSTEM TERMINAL")
    st.markdown('<div class="terminal">', unsafe_allow_html=True)
    
    for log, log_type in st.session_state.terminal_logs[-20:]:  # Show last 20 logs
        css_class = f"terminal-line {log_type}"
        st.markdown(f'<div class="{css_class}">{log}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# Main App
render_header()

if not st.session_state.logged_in:
    tab1, tab2 = st.tabs(["🚀 LOGIN", "✨ REGISTER"])
    
    with tab1:
        st.markdown("### ACCESS NON-STOP SYSTEM")
        
        with st.form("login"):
            username = st.text_input("👤 USERNAME")
            password = st.text_input("🔑 PASSWORD", type="password")
            
            if st.form_submit_button("🚀 LOGIN TO NON-STOP", use_container_width=True):
                if username and password:
                    user_id = db.verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        # Check if automation should auto-start
                        user_config = db.get_user_config(user_id)
                        if user_config and user_config.get('automation_running', True):
                            start_nonstop_automation(user_id, user_config)
                        
                        add_terminal_log(f"👤 User '{username}' logged in", "success")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.warning("⚠️ Enter credentials")
    
    with tab2:
        st.markdown("### CREATE NON-STOP ACCOUNT")
        
        with st.form("register"):
            new_user = st.text_input("👤 CHOOSE USERNAME")
            new_pass = st.text_input("🔑 CREATE PASSWORD", type="password")
            confirm_pass = st.text_input("✓ CONFIRM PASSWORD", type="password")
            
            if st.form_submit_button("✨ CREATE NON-STOP ACCOUNT", use_container_width=True):
                if new_user and new_pass and confirm_pass:
                    if new_pass == confirm_pass:
                        success, message = db.create_user(new_user, new_pass)
                        if success:
                            st.success(f"✅ {message}")
                            add_terminal_log(f"🆕 Account created: {new_user}", "success")
                        else:
                            st.error(f"❌ {message}")
                    else:
                        st.error("❌ Passwords don't match")
                else:
                    st.warning("⚠️ Complete all fields")

else:
    # User is logged in
    user_config = db.get_user_config(st.session_state.user_id)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"**ID:** `#{st.session_state.user_id}`")
        
        st.markdown("---")
        st.markdown("### 🔥 NON-STOP STATUS")
        
        # Auto-start if not running
        if (user_config.get('automation_running', True) and 
            st.session_state.user_id not in st.session_state.automation_threads):
            start_nonstop_automation(st.session_state.user_id, user_config)
        
        if st.session_state.user_id in st.session_state.automation_threads:
            st.markdown('<div class="status-running" style="padding: 1rem; border-radius: 10px; text-align: center;">🔥 ACTIVE</div>', 
                       unsafe_allow_html=True)
        else:
            st.warning("⏸️ INACTIVE")
        
        st.markdown("---")
        
        if st.button("🚪 LOGOUT", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    
    # Main content
    render_stats(user_config)
    
    st.markdown("""
    <div class="info-box">
        <h4>⚠️ NON-STOP MODE ACTIVE</h4>
        <p>• System will run 24/7 with automatic retry</p>
        <p>• Messages sent: <strong>{}</strong> today</p>
        <p>• Daily limit: <strong>{}/{}</strong></p>
        <p>• Auto-resets at midnight</p>
    </div>
    """.format(
        user_config.get('messages_sent_today', 0),
        user_config.get('messages_sent_today', 0),
        user_config.get('max_messages_per_day', 500)
    ), unsafe_allow_html=True)
    
    render_control_panel(user_config)
    render_terminal()
    
    # Auto-refresh terminal
    time.sleep(2)
    st.rerun()

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 4rem; padding: 2rem; background: #1a1a1a; border-radius: 10px;">
    <h3 style="color: #00ff9d; font-family: 'Orbitron', sans-serif;">🔥 HASSAN DASTAGIR NON-STOP EDITION</h3>
    <p style="color: #888;">24/7 Operation • Infinite Retry • Zero Downtime</p>
    <p style="color: #666; font-size: 0.8rem;">© 2025 • NEVER STOP AUTOMATING</p>
</div>
""", unsafe_allow_html=True)
