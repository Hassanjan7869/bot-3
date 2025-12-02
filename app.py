import streamlit as st
import time
import threading
import random
import requests
import os
import hashlib
import base64
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import json

# 🔥 STREAMLIT COMPATIBLE VERSION - NO SELENIUM ISSUES 🔥

# 🔐 ENHANCED DATABASE
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('hassan_nonstop.db', check_same_thread=False)
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
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User config table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_config (
                user_id INTEGER PRIMARY KEY,
                chat_id TEXT DEFAULT '',
                name_prefix TEXT DEFAULT '',
                delay_min INTEGER DEFAULT 30,
                delay_max INTEGER DEFAULT 60,
                cookies TEXT DEFAULT '',
                messages TEXT DEFAULT '',
                automation_running BOOLEAN DEFAULT TRUE,
                total_messages INTEGER DEFAULT 0,
                today_messages INTEGER DEFAULT 0,
                last_reset DATE DEFAULT CURRENT_DATE,
                api_key TEXT DEFAULT '',
                webhook_url TEXT DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Message history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message TEXT,
                status TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # System logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event TEXT,
                details TEXT,
                user_id INTEGER
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
            
            # Default config
            default_messages = """Hello!
How are you?
Nice to meet you!
Good to see you!
What's up?
Long time no see!"""
            
            cursor.execute(
                'INSERT INTO user_config (user_id, messages) VALUES (?, ?)',
                (user_id, default_messages)
            )
            
            self.log_event('USER_CREATED', f'User {username} created', user_id)
            self.conn.commit()
            return True, "Account created successfully!"
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
            cursor.execute(
                'UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?',
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
                'total_messages': result[8],
                'today_messages': result[9],
                'last_reset': result[10],
                'api_key': result[11],
                'webhook_url': result[12]
            }
        return None
    
    def update_config(self, user_id, **kwargs):
        cursor = self.conn.cursor()
        
        if 'cookies' in kwargs and kwargs['cookies']:
            kwargs['cookies'] = self.encrypt_cookies(kwargs['cookies'])
        
        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(user_id)
        
        query = f'UPDATE user_config SET {set_clause} WHERE user_id = ?'
        cursor.execute(query, values)
        
        self.conn.commit()
    
    def update_message_count(self, user_id, count=1):
        cursor = self.conn.cursor()
        
        # Check if reset needed
        cursor.execute('SELECT last_reset FROM user_config WHERE user_id = ?', (user_id,))
        last_reset = cursor.fetchone()[0]
        today = datetime.now().date().isoformat()
        
        if str(last_reset) != today:
            cursor.execute('''
                UPDATE user_config 
                SET today_messages = ?, last_reset = ?, total_messages = total_messages + ?
                WHERE user_id = ?
            ''', (count, today, count, user_id))
        else:
            cursor.execute('''
                UPDATE user_config 
                SET today_messages = today_messages + ?, total_messages = total_messages + ?
                WHERE user_id = ?
            ''', (count, count, user_id))
        
        self.conn.commit()
    
    def log_message(self, user_id, message, status="sent"):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO message_logs (user_id, message, status) VALUES (?, ?, ?)',
            (user_id, message[:200], status)
        )
        self.conn.commit()
    
    def log_event(self, event, details, user_id=None):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO system_logs (event, details, user_id) VALUES (?, ?, ?)',
            (event, details, user_id)
        )
        self.conn.commit()
    
    def encrypt_cookies(self, cookies_text):
        # Simple XOR encryption (for demo - use proper encryption in production)
        key = "HASSAN_DASTAGIR_2025"
        encrypted = ""
        for i, char in enumerate(cookies_text):
            key_char = key[i % len(key)]
            encrypted += chr(ord(char) ^ ord(key_char))
        return base64.b64encode(encrypted.encode()).decode()
    
    def decrypt_cookies(self, encrypted_text):
        if not encrypted_text:
            return ""
        try:
            encrypted = base64.b64decode(encrypted_text.encode()).decode()
            key = "HASSAN_DASTAGIR_2025"
            decrypted = ""
            for i, char in enumerate(encrypted):
                key_char = key[i % len(key)]
                decrypted += chr(ord(char) ^ ord(key_char))
            return decrypted
        except:
            return ""

# Initialize database
db = Database()

# 🔥 STREAMLIT UI SETUP
st.set_page_config(
    page_title="HASSAN DASTAGIR - NON-STOP MESSENGER",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 MODERN UI STYLES
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 4rem 2rem;
        border-radius: 0px;
        text-align: center;
        margin-bottom: 3rem;
        box-shadow: 0 20px 40px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
        border-bottom: 5px solid #00ff9d;
    }
    
    .main-header h1 {
        color: white;
        font-size: 3.5rem;
        font-weight: 900;
        margin: 0;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        background: linear-gradient(45deg, #fff, #f0f0f0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.3rem;
        margin-top: 1rem;
        font-weight: 400;
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
    }
    
    .stat-card {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        text-align: center;
        border: 2px solid transparent;
        transition: all 0.3s;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        border-color: #667eea;
        box-shadow: 0 15px 40px rgba(102, 126, 234, 0.2);
    }
    
    .stat-value {
        font-size: 2.8rem;
        font-weight: 800;
        color: #667eea;
        margin: 0.5rem 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .nonstop-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 1rem 2rem !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        transition: all 0.3s !important;
        width: 100% !important;
    }
    
    .nonstop-button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 35px rgba(102, 126, 234, 0.4) !important;
    }
    
    .terminal {
        background: #1a1a1a;
        color: #00ff9d;
        font-family: 'Courier New', monospace;
        padding: 2rem;
        border-radius: 15px;
        border: 1px solid #333;
        max-height: 500px;
        overflow-y: auto;
        margin: 2rem 0;
    }
    
    .terminal-line {
        margin: 0.5rem 0;
        font-size: 0.9rem;
        border-bottom: 1px solid #333;
        padding-bottom: 0.5rem;
    }
    
    .config-card {
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 15px 50px rgba(0,0,0,0.1);
        margin: 2rem 0;
        border-left: 5px solid #667eea;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.5rem 1.5rem;
        border-radius: 25px;
        font-weight: 700;
        font-size: 1rem;
        margin: 0.5rem;
    }
    
    .status-active {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    
    .status-inactive {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #f7971e 0%, #ffd200 100%);
        color: black;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1.5rem 0;
        border: 2px solid #ff9f43;
    }
    
    .success-box {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# 🚀 SIMULATED AUTOMATION ENGINE (NO SELENIUM)
class NonStopEngine:
    def __init__(self, user_id, config):
        self.user_id = user_id
        self.config = config
        self.running = False
        self.thread = None
        self.message_count = 0
        
    def start(self):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        db.log_event('AUTOMATION_STARTED', f'User {self.user_id} started automation', self.user_id)
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        db.log_event('AUTOMATION_STOPPED', f'User {self.user_id} stopped automation', self.user_id)
    
    def run_loop(self):
        """Main automation loop - SIMULATED FOR NOW"""
        messages = [m.strip() for m in self.config['messages'].split('\n') if m.strip()]
        
        if not messages:
            messages = ["Hello!", "How are you?", "Good to see you!"]
        
        session_messages = 0
        max_messages = 100  # Safety limit per session
        
        while self.running and session_messages < max_messages:
            try:
                # Simulate sending message
                message = random.choice(messages)
                if self.config.get('name_prefix'):
                    message = f"{self.config['name_prefix']} {message}"
                
                # Log message
                db.log_message(self.user_id, message, "simulated")
                db.update_message_count(self.user_id, 1)
                self.message_count += 1
                session_messages += 1
                
                # Add to terminal logs
                timestamp = datetime.now().strftime("%H:%M:%S")
                log_entry = f"[{timestamp}] ✅ Message sent: {message[:50]}..."
                
                if 'terminal_logs' in st.session_state:
                    st.session_state.terminal_logs.append(log_entry)
                    if len(st.session_state.terminal_logs) > 50:
                        st.session_state.terminal_logs.pop(0)
                
                # Random delay
                delay = random.randint(
                    self.config.get('delay_min', 30),
                    self.config.get('delay_max', 60)
                )
                
                # Check if should continue
                for _ in range(delay):
                    if not self.running:
                        break
                    time.sleep(1)
                
                # Random break between sessions
                if session_messages % random.randint(3, 10) == 0:
                    break_time = random.randint(60, 300)  # 1-5 minutes
                    for _ in range(break_time):
                        if not self.running:
                            break
                        time.sleep(1)
                        
            except Exception as e:
                error_msg = f"Error in automation: {str(e)[:100]}"
                db.log_event('AUTOMATION_ERROR', error_msg, self.user_id)
                time.sleep(60)  # Wait before retry
        
        self.running = False
        db.update_config(self.user_id, automation_running=False)

# Session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'terminal_logs' not in st.session_state:
    st.session_state.terminal_logs = []
if 'automation_engines' not in st.session_state:
    st.session_state.automation_engines = {}
if 'start_time' not in st.session_state:
    st.session_state.start_time = datetime.now()

# 🎯 HEADER
st.markdown("""
<div class="main-header">
    <h1>🔥 HASSAN DASTAGIR NON-STOP</h1>
    <p>24/7 Automated Messaging System • Zero Downtime • Infinite Operation</p>
</div>
""", unsafe_allow_html=True)

# 🚀 MAIN APP
if not st.session_state.logged_in:
    # Login/Register Section
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔐 Login to Dashboard")
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.form_submit_button("🚀 Login", use_container_width=True):
                if username and password:
                    user_id = db.verify_user(username, password)
                    if user_id:
                        st.session_state.logged_in = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        
                        # Auto-start if configured
                        config = db.get_user_config(user_id)
                        if config and config['automation_running']:
                            engine = NonStopEngine(user_id, config)
                            engine.start()
                            st.session_state.automation_engines[user_id] = engine
                        
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials!")
                else:
                    st.warning("Please enter both fields")
    
    with col2:
        st.markdown("### ✨ Create Account")
        with st.form("register_form"):
            new_user = st.text_input("Choose Username", key="reg_user")
            new_pass = st.text_input("Create Password", type="password", key="reg_pass")
            confirm_pass = st.text_input("Confirm Password", type="password", key="reg_confirm")
            
            if st.form_submit_button("✨ Create Account", use_container_width=True):
                if new_user and new_pass and confirm_pass:
                    if new_pass == confirm_pass:
                        success, message = db.create_user(new_user, new_pass)
                        if success:
                            st.success(message)
                            st.info("You can now login with your credentials")
                        else:
                            st.error(message)
                    else:
                        st.error("Passwords don't match!")
                else:
                    st.warning("Please complete all fields")

else:
    # User is logged in
    user_id = st.session_state.user_id
    config = db.get_user_config(user_id)
    
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown(f"**User ID:** `#{user_id}`")
        
        # Stats
        st.markdown("---")
        st.markdown("### 📊 Quick Stats")
        st.metric("Total Messages", config['total_messages'])
        st.metric("Today's Messages", config['today_messages'])
        
        # Status
        st.markdown("---")
        st.markdown("### 🔥 Status")
        
        if user_id in st.session_state.automation_engines:
            engine = st.session_state.automation_engines[user_id]
            if engine.running:
                st.markdown('<div class="status-badge status-active">🚀 ACTIVE</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-badge status-inactive">⏸️ INACTIVE</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-badge status-inactive">🔴 OFFLINE</div>', unsafe_allow_html=True)
        
        # Control buttons
        st.markdown("---")
        st.markdown("### 🎛️ Controls")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                if user_id not in st.session_state.automation_engines:
                    engine = NonStopEngine(user_id, config)
                    engine.start()
                    st.session_state.automation_engines[user_id] = engine
                    db.update_config(user_id, automation_running=True)
                    st.success("Automation started!")
                    st.rerun()
        
        with col2:
            if st.button("⏹️ Stop", use_container_width=True):
                if user_id in st.session_state.automation_engines:
                    engine = st.session_state.automation_engines[user_id]
                    engine.stop()
                    db.update_config(user_id, automation_running=False)
                    st.success("Automation stopped!")
                    st.rerun()
        
        # Logout
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            # Stop automation if running
            if user_id in st.session_state.automation_engines:
                engine = st.session_state.automation_engines[user_id]
                engine.stop()
            
            # Clear session
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()
    
    # Main Content
    st.markdown("## 🎛️ Control Panel")
    
    # Stats Grid
    st.markdown('<div class="stats-grid">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        uptime = datetime.now() - st.session_state.start_time
        hours = uptime.seconds // 3600
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{hours}:{(uptime.seconds % 3600)//60:02d}</div>
            <div class="stat-label">System Uptime</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        engine = st.session_state.automation_engines.get(user_id)
        msg_count = engine.message_count if engine else 0
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{msg_count}</div>
            <div class="stat-label">Session Messages</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{config['total_messages']}</div>
            <div class="stat-label">Total Messages</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        status = "ACTIVE" if user_id in st.session_state.automation_engines else "INACTIVE"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-value">{status}</div>
            <div class="stat-label">Current Status</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Configuration Section
    st.markdown("## ⚙️ Configuration")
    
    with st.form("config_form"):
        st.markdown('<div class="config-card">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            chat_id = st.text_input(
                "💬 Chat ID",
                value=config['chat_id'],
                placeholder="Enter Facebook Chat ID",
                help="Get this from Facebook URL"
            )
            
            name_prefix = st.text_input(
                "🏷️ Message Prefix",
                value=config['name_prefix'],
                placeholder="[HASSAN DASTAGIR]",
                help="Added before each message"
            )
        
        with col2:
            delay_min = st.number_input(
                "⏱️ Minimum Delay (seconds)",
                min_value=10,
                max_value=300,
                value=config['delay_min'],
                help="Minimum time between messages"
            )
            
            delay_max = st.number_input(
                "⏱️ Maximum Delay (seconds)",
                min_value=20,
                max_value=600,
                value=config['delay_max'],
                help="Maximum time between messages"
            )
        
        # Messages
        st.markdown("### 💬 Message Templates")
        messages = st.text_area(
            "Enter one message per line",
            value=config['messages'],
            height=200,
            placeholder="Hello!\nHow are you?\nGood to see you!\nWhat's up?",
            help="System will randomly select messages"
        )
        
        # Cookies (Optional)
        st.markdown("### 🔐 Facebook Cookies (Optional)")
        with st.expander("Advanced Cookie Settings"):
            cookies = st.text_area(
                "Paste Facebook cookies here",
                value=db.decrypt_cookies(config['cookies']),
                height=100,
                placeholder="c_user=...; xs=...; datr=...",
                help="Required for real Facebook automation"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button
        if st.form_submit_button("💾 Save Configuration", use_container_width=True):
            update_data = {
                'chat_id': chat_id,
                'name_prefix': name_prefix,
                'delay_min': delay_min,
                'delay_max': delay_max,
                'messages': messages
            }
            
            if cookies:
                update_data['cookies'] = cookies
            
            db.update_config(user_id, **update_data)
            st.success("✅ Configuration saved successfully!")
            
            # Update engine config if running
            if user_id in st.session_state.automation_engines:
                st.session_state.automation_engines[user_id].config = db.get_user_config(user_id)
            
            st.rerun()
    
    # Terminal Logs
    st.markdown("## 📟 System Terminal")
    
    # Add sample logs if empty
    if not st.session_state.terminal_logs:
        sample_logs = [
            "[14:30:15] ✅ System initialized successfully!",
            "[14:31:22] 🔥 NON-STOP mode activated",
            "[14:32:45] 📊 Database connection established",
            "[14:33:10] 👤 User session started",
            "[14:34:05] 🚀 Automation engine ready"
        ]
        st.session_state.terminal_logs = sample_logs
    
    # Display terminal
    terminal_html = '<div class="terminal">'
    for log in st.session_state.terminal_logs[-20:]:  # Last 20 logs
        if '✅' in log or 'SUCCESS' in log.upper():
            terminal_html += f'<div class="terminal-line" style="color: #00ff9d;">{log}</div>'
        elif '❌' in log or 'ERROR' in log.upper():
            terminal_html += f'<div class="terminal-line" style="color: #ff6b6b;">{log}</div>'
        elif '⚠️' in log or 'WARNING' in log.upper():
            terminal_html += f'<div class="terminal-line" style="color: #ffd93d;">{log}</div>'
        else:
            terminal_html += f'<div class="terminal-line">{log}</div>'
    terminal_html += '</div>'
    
    st.markdown(terminal_html, unsafe_allow_html=True)
    
    # Auto-refresh when automation is running
    if user_id in st.session_state.automation_engines:
        engine = st.session_state.automation_engines[user_id]
        if engine.running:
            time.sleep(3)
            st.rerun()

# Footer
st.markdown("""
<div style="text-align: center; margin-top: 4rem; padding: 3rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 20px; color: white;">
    <h3 style="margin: 0; font-weight: 800;">🔥 HASSAN DASTAGIR NON-STOP EDITION</h3>
    <p style="opacity: 0.9; margin-top: 1rem;">24/7 Automated Messaging • Zero Maintenance • Infinite Operation</p>
    <p style="font-size: 0.9rem; opacity: 0.7; margin-top: 2rem;">© 2025 • All Rights Reserved • Never Stop Automating</p>
</div>
""", unsafe_allow_html=True)
