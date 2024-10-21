import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import subprocess
import json
import datetime
from datetime import datetime, timedelta
from uuid import uuid4
import base64
import telebot
import sqlite3
import os
import zipfile
import threading
import time


API_TOKEN = '7360190308:AAFCXEy6tEzRvCgzF44XzlcX3PRNV-vPkxo'
bot = telebot.TeleBot(API_TOKEN)

admin_id = 576495165  
user_data = {}
DB_PATH = 'user_data.db'
BACKUP_DIR = 'backups/'

#================== DATABASE AREA ===========
# Database setup
def init_db():
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        balance INTEGER DEFAULT 0,
                        reseller_status TEXT DEFAULT 'non reseller')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
                        code_name TEXT PRIMARY KEY,
                        balance INTEGER NOT NULL,
                        remaining_uses INTEGER NOT NULL,
                        total_uses INTEGER NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS redeemed_codes (
                        user_id INTEGER NOT NULL,
                        code_name TEXT NOT NULL,
                        PRIMARY KEY (user_id, code_name))''')
    # Check if the reseller_status column exists, if not, add it
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'reseller_status' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN reseller_status TEXT DEFAULT 'non reseller'")
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, balance, reseller_status) VALUES (?, 0, "non reseller")', (user_id,))
    cursor.execute('SELECT balance, reseller_status FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return {'balance': result[0], 'reseller_status': result[1]}


def update_balance(user_id, amount):
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, balance, reseller_status) VALUES (?, 0, "non reseller")', (user_id,))
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    
    # Fetch the updated balance and current reseller status
    cursor.execute('SELECT balance, reseller_status FROM users WHERE user_id = ?', (user_id,))
    balance, reseller_status = cursor.fetchone()
    
    # Update reseller status based on new balance and top-up rules
    if reseller_status == 'reseller' and balance == 0:
        # If balance reaches 0, downgrade to non reseller
        cursor.execute('UPDATE users SET reseller_status = "non reseller" WHERE user_id = ?', (user_id,))
    elif reseller_status != 'reseller' and amount >= 30000:
        # If top-up is 30,000 or more, upgrade to reseller
        cursor.execute('UPDATE users SET reseller_status = "reseller" WHERE user_id = ?', (user_id,))
    elif reseller_status == 'reseller' and amount < 10000 and balance > 0:
        # If top-up is below 30,000 but balance is still above 0, retain reseller status
        pass
    elif amount < 30000:
        # If top-up is below 30,000 and user is not a reseller, keep status as non reseller
        cursor.execute('UPDATE users SET reseller_status = "non reseller" WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()


# Initialize the database
init_db()

#============================================

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    user_data = get_user_data(message.chat.id)
    reseller_status = user_data['reseller_status']
    vpn_price = 5000 if reseller_status == 'reseller' else 10000
    
    markup = InlineKeyboardMarkup()

    menu_vpn = InlineKeyboardButton("🛡️Menu VPN", callback_data="menu_vpn")
    menu_topup = InlineKeyboardButton("💰Top Up", callback_data="topup")
    menu_ceksaldo = InlineKeyboardButton("💳Cek Saldo", callback_data="cek_saldo")

    markup.add(menu_vpn)
    markup.add(menu_topup, menu_ceksaldo)

    # Cek apakah user adalah admin
    if message.chat.id == admin_id:
        broadcast = InlineKeyboardButton("Broadcast", callback_data="broadcast")
        markup.add(broadcast)

    bot.send_message(
        message.chat.id,
        "*»»——— SAN STORE BOT ———««*\n\n"
        "🔹 *VPN Premium & Kuota Murah* 🔹\n"
        "🔒 *Kecepatan & Keamanan Terbaik*\n\n"
        f"👤 *Owner: @Sanmaxx*\n"
        f"💲 *Status: {reseller_status.capitalize()}*\n"
        f"💵 *Harga VPN: {vpn_price}*\n\n"
        "*»»——— Thanks for coming ———««*",
        parse_mode='Markdown',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data in ["menu_vpn", "cek_saldo"])
def callback_query_handler(call):
    user_data = get_user_data(call.message.chat.id)
    
    if call.data == "menu_vpn":
        menu_vpn(call.message)
    elif call.data == "cek_saldo":
        balance = user_data['balance']
        bot.send_message(call.message.chat.id, f"Saldo Anda saat ini adalah: {balance}")
    
       
@bot.callback_query_handler(func=lambda call: call.data == "kembali") 
def kembali_handler(call): 
    markup = InlineKeyboardMarkup()

    menu_vpn = InlineKeyboardButton("🛡️Menu VPN", callback_data="menu_vpn")
    menu_topup = InlineKeyboardButton("💰Top Up", callback_data="topup")
    menu_ceksaldo = InlineKeyboardButton("💳Cek Saldo", callback_data="cek_saldo")

    markup.add(menu_vpn)
    markup.add(menu_topup, menu_ceksaldo)

    # Cek apakah user adalah admin
    if call.message.chat.id == admin_id:
        broadcast = InlineKeyboardButton("Broadcast", callback_data="broadcast")
        markup.add(broadcast)

    bot.edit_message_text(
    chat_id=call.message.chat.id,
    message_id=call.message.message_id,
    text="*»»——— SAN STORE BOT ———««*\n\n"
         "🔹 *VPN Premium & Kuota Murah* 🔹\n"
         "🔒 *Kecepatan & Keamanan Terbaik*\n\n"
         "👤 *Owner: @Sanmaxx*\n\n"
         "*»»——— Thanks for coming ———««*",
    parse_mode='Markdown',
    reply_markup=markup
    )
    
#======================== BAGIAN FUNGSI UNTUK SEMUA BUTTON MENU ====================
#----------------- PART SSH --------------
def menu_vpn(message):
    markup = InlineKeyboardMarkup()

    menu_ssh = InlineKeyboardButton("SSH/OVPN", callback_data="menu_ssh")
    menu_vmess = InlineKeyboardButton("VMESS/XRAY", callback_data="menu_vmess")
    menu_trojan = InlineKeyboardButton("TROJAN/XRAY", callback_data="menu_trojan")
    kembali = InlineKeyboardButton("KEMBALI", callback_data="kembali")
    

    markup.add(menu_ssh, menu_vmess, menu_trojan)
    markup.add(kembali)

    bot.edit_message_text(
    chat_id=message.chat.id,
    message_id=message.message_id,
    text="*»»——— SAN STORE BOT ———««*\n\n"
         "🔹*VPN Premium Rules*🔹\n"
         "❌ *Dilarang Multi Login Melebihi ketentuan* \n\n"
         "Banned Otomatis Tanpa pemberitahuan dan tidak menerima Refund atau Garansi dalam bentuk apapun\n"
         "*»»——— Thanks for coming ———««*",
    parse_mode='Markdown',
    reply_markup=markup
    )
    
#------------------------
@bot.callback_query_handler(func=lambda call: call.data == "menu_ssh") 
def menu_ssh_handler(call):
    sub_menu_ssh(call.message)
                
def sub_menu_ssh(message):
    markup = InlineKeyboardMarkup()
    
    ssh_create_button = InlineKeyboardButton("NEW SSH", callback_data="create_ssh")
    ssh_renew_button = InlineKeyboardButton("RENEW SSH", callback_data="renew_ssh")
    kembali = InlineKeyboardButton("KEMBALI", callback_data="kembali")
    markup.add(ssh_create_button, ssh_renew_button)
    markup.add(kembali)
    
    
    bot.edit_message_text(
    chat_id=message.chat.id,
    message_id=message.message_id,
    text="*»»——— SAN STORE BOT ———««*\n\n"
         "🔹 *SSH PREMIUM* 🔹\n\n"
         "Region : SG\n"
         "ISP : DigitalOcean\n"
         "Support : HP & STB\n"
         "*»»——— Thanks for coming ———««*",
    parse_mode='Markdown',
    reply_markup=markup
    )
    
@bot.callback_query_handler(func=lambda call: call.data in ["create_ssh", "renew_ssh"])
def handle_callback(call):
    user_data = get_user_data(call.message.chat.id)
    reseller_status = user_data['reseller_status']
    vpn_price = 5000 if reseller_status == 'reseller' else 10000
    
    if call.data == "create_ssh":
        user_balance = user_data['balance']
        if user_balance >= vpn_price:
            update_balance(call.message.chat.id, -vpn_price)
            create_ssh(call.message)
        else:
            bot.send_message(call.message.chat.id, "Saldo tidak cukup.")
    elif call.data == "renew_ssh":
        user_balance = user_data['balance']
        if user_balance >= vpn_price:
            update_balance(call.message.chat.id, -vpn_price)
            renew_ssh(call.message)
        else:
            bot.send_message(call.message.chat.id, "Saldo tidak cukup.")
        

def create_ssh(message):
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Input Username:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, get_username_ssh)

def renew_ssh(message):
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Input Username:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, get_renew_ssh)

def get_username_ssh(message):
    username = message.text.strip()

    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    
    # Validasi username: tidak boleh mengandung spasi dan panjang maksimal 8 karakter
    if ' ' in username or len(username) > 8:
        bot.send_message(message.chat.id, 'Username tidak boleh mengandung spasi dan maksimal 8 karakter. Masukkan username lain:')
        bot.register_next_step_handler(message, get_username_ssh)
    elif username.lower() == 'root' or username in get_existing_users():
        bot.send_message(message.chat.id, 'Username tidak valid atau sudah ada. Silakan masukkan username lain:')
        bot.register_next_step_handler(message, get_username_ssh)
    else:
        bot.send_message(message.chat.id, '*🔐Input Password:*', parse_mode='Markdown')
        bot.register_next_step_handler(message, get_password, username)

def get_password(message, username):
    password = message.text.strip()
    
    # Set default expiry to 30 days
    expired_days = 30
    
    # Call the create account function directly with 30 days expiry
    create_account_action(username, password, expired_days, message)

def create_account_action(username, password, expired_days, message):
    exp_date = (datetime.now() + timedelta(days=expired_days)).strftime('%Y-%m-%d')

    # Membuat akun SSH
    subprocess.run(['useradd', '-e', exp_date, '-s', '/bin/false', '-M', username])
    subprocess.run(['sh', '-c', f'echo "{username}:{password}" | chpasswd'])

    # Mendapatkan informasi IP dan domain
    domain = subprocess.getoutput("cat /etc/xray/domain")
    IP = subprocess.getoutput("curl -sS ifconfig.me")

    # Mendapatkan tanggal expired
    exp = subprocess.getoutput(f"chage -l {username} | grep 'Account expires' | awk -F': ' '{{print $2}}'")

    def progress_bar(progress, total, length=20):
        filled_length = int(length * progress // total)
        bar = '█' * filled_length + '-' * (length - filled_length)
        return f"[{bar}] {int((progress / total) * 100)}%"

    # Total iterasi untuk animasi loading
    total_steps = 10

    # Mengirim pesan awal untuk progress bar
    loading_message = bot.send_message(message.chat.id, "Loading [--------------------] 0%")

    # Mengedit pesan animasi loading secara bertahap
    for step in range(1, total_steps + 1):
        bar_message = progress_bar(step, total_steps)
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=f"Loading {bar_message}")
        time.sleep(0.3)  # Jeda waktu antar update

    
    # Mengirim informasi akun kepada pengguna
    result_message = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"• SSH ACCOUNT INFORMATION •\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  Username   : `{username}`\n"
        f"  Password   : `{password}`\n"
        f"  Expired On : {exp}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  IP         : {IP}\n"
        f"  Host       : `{domain}`\n"
        f"  OpenSSH    : 22\n"
        f"  Dropbear   : 443\n"
        f"  SSH-WS     : 80, 8880\n"
        f"  SSH-SSL-WS : 443\n"
        f"  SSH-UDP    : 56-65545\n"
        f"  SSL/TLS    :443\n"
        f"  UDPGW      : 7100-7300\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  GET /HTTP/1.1[crlf]Host: [host] [crlf]Upgrade: websocket[crlf][crlf]\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=result_message, parse_mode='Markdown')

# Tambahkan dictionary untuk melacak percobaan
user_attempts = {}

def get_renew_ssh(message):
    username = message.text.strip()
    user_id = message.chat.id

    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    
    # Periksa apakah pengguna sudah ada di dalam sesi percobaan
    if user_id not in user_attempts:
        user_attempts[user_id] = 1  # Inisialisasi dengan 1 percobaan
    else:
        user_attempts[user_id] += 1  # Tambah percobaan jika sudah ada
    
    # Jika username salah 3 kali, akhiri sesi
    if user_attempts[user_id] > 3:
        bot.send_message(message.chat.id, 'Anda telah salah memasukkan username sebanyak 3 kali. Silakan mulai dari awal.')
        user_attempts.pop(user_id, None)  # Hapus percobaan untuk user ini
        return
    
    # Jika username valid, reset percobaan dan lanjutkan proses perpanjangan
    if username not in get_existing_users():
        bot.send_message(message.chat.id, 'Username Ssh Tidak Ditemukan')
        bot.register_next_step_handler(message, get_renew_ssh)
    else:
        user_attempts.pop(user_id, None)  # Reset percobaan jika berhasil
        renew_account_action(username, message)

def renew_account_action(username, message):
    expired_days = 30
    
    # Mendapatkan tanggal expired saat ini
    current_exp = subprocess.getoutput(f"chage -l {username} | grep 'Account expires' | awk -F': ' '{{print $2}}'")
    current_exp_date = datetime.strptime(current_exp.strip(), '%b %d, %Y')
    new_exp_date = current_exp_date + timedelta(days=expired_days)
    new_exp_str = new_exp_date.strftime('%Y-%m-%d')

    # Memperbarui tanggal expired akun
    subprocess.run(['chage', '-E', new_exp_str, username])

    def progress_bar(progress, total, length=20):
        filled_length = int(length * progress // total)
        bar = '█' * filled_length + '-' * (length - filled_length)
        return f"[{bar}] {int((progress / total) * 100)}%"

    # Total iterasi untuk animasi loading
    total_steps = 10

    # Mengirim pesan awal untuk progress bar
    loading_message = bot.send_message(message.chat.id, "Loading [--------------------] 0%")

    # Mengedit pesan animasi loading secara bertahap
    for step in range(1, total_steps + 1):
        bar_message = progress_bar(step, total_steps)
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=f"Loading {bar_message}")
        time.sleep(0.3)  # Jeda waktu antar update

    
    # Mengirim informasi perpanjangan kepada pengguna
    result_message = (
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "       • Successfully Renew •\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Username : {username}\n"
        f"Masa Aktif : {new_exp_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=result_message, parse_mode='Markdown')

def get_existing_users():
    try:
        users = subprocess.getoutput("cut -d: -f1 /etc/passwd").split()
        return users
    except Exception as e:
        print(f"Error fetching existing users: {e}")
        return []

#--------------------- PART VMESS -------------------
@bot.callback_query_handler(func=lambda call: call.data == "menu_vmess") 
def menu_vmess_handler(call):
    sub_menu_vmess(call.message)

def sub_menu_vmess(message):
    markup = InlineKeyboardMarkup()
    
    create_button = InlineKeyboardButton("NEW VMESS", callback_data="create_vmess")
    renew_button = InlineKeyboardButton("RENEW VMESS", callback_data="renew_vmess")
    kembali = InlineKeyboardButton("KEMBALI", callback_data="kembali")
    markup.add(create_button, renew_button)
    markup.add(kembali)
    
    bot.edit_message_text(
    chat_id=message.chat.id,
    message_id=message.message_id,
    text="*»»——— SAN STORE BOT ———««*\n\n"
         "🔹 *VMESS PREMIUM* 🔹\n\n"
         "Region : SG\n"
         "ISP : DigitalOcean\n"
         "Support : HP & STB\n"
         "*»»——— Thanks for Order ———««*",
    parse_mode='Markdown',
    reply_markup=markup
    )
#======================================#
@bot.callback_query_handler(func=lambda call: call.data in ["create_vmess", "renew_vmess"])
def handle_callback(call):
    user_data = get_user_data(call.message.chat.id)
    reseller_status = user_data['reseller_status']
    vpn_price = 5000 if reseller_status == 'reseller' else 10000
    
    if call.data == "create_vmess":
        user_balance = user_data['balance']
        if user_balance >= vpn_price:
            update_balance(call.message.chat.id, -vpn_price)
            create_vmess(call.message)
        else:
            bot.send_message(call.message.chat.id, "Saldo tidak cukup.")
    elif call.data == "renew_vmess":
        user_balance = user_data['balance']
        if user_balance >= vpn_price:
            update_balance(call.message.chat.id, -vpn_price)
            renew_vmess(call.message)
        else:
            bot.send_message(call.message.chat.id, "Saldo tidak cukup.")
       

def create_vmess(message):
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Input Username:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, get_username_vmess)

def get_username_vmess(message):
    username = message.text
    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    if is_username_exists(username):
        bot.send_message(message.chat.id, 'Nama sudah ada, Silahkan Masukkan Username Yang lain:')
        bot.register_next_step_handler(message, get_username_vmess)
    else:
        # Automatically set expired to 30 days
        expired_days = 30
        exp_date = (datetime.now() + timedelta(days=expired_days)).strftime('%Y-%m-%d')
        domain = subprocess.getoutput("cat /etc/xray/domain")
        uuid = str(uuid4())

        # Update config.json
        config_path = '/etc/xray/config.json'
        with open(config_path, 'r+') as file:
            config_data = file.read()

            # Insert new user details
            new_user_entry = f'\n### {username} {exp_date}\n}},{{"id": "{uuid}","alterId": 0,"email": "{username}"'

            # Find the position to insert for #vmess
            vmess_pos = config_data.find('#vmess')
            if (vmess_pos != -1):
                insert_pos = config_data.find('\n', vmess_pos)
                config_data = config_data[:insert_pos] + new_user_entry + config_data[insert_pos:]

            # Find the position to insert for #vmessgrpc
            vmessgrpc_pos = config_data.find('#vmessgrpc')
            if (vmessgrpc_pos != -1):
                insert_pos = config_data.find('\n', vmessgrpc_pos)
                config_data = config_data[:insert_pos] + new_user_entry + config_data[insert_pos:]

            # Write back the updated config
            file.seek(0)
            file.write(config_data)
            file.truncate()

        # VMESS links
        asu = {
            "v": "2",
            "ps": username,
            "add": domain,
            "port": "443",
            "id": uuid,
            "aid": "0",
            "net": "ws",
            "path": "/vmess",
            "type": "none",
            "host": domain,
            "tls": "tls"
        }
        ask = {
            "v": "2",
            "ps": username,
            "add": domain,
            "port": "80",
            "id": uuid,
            "aid": "0",
            "net": "ws",
            "path": "/vmess",
            "type": "none",
            "host": domain,
            "tls": "none"
        }
        grpc = {
            "v": "2",
            "ps": username,
            "add": domain,
            "port": "443",
            "id": uuid,
            "aid": "0",
            "net": "grpc",
            "path": "vmess-grpc",
            "type": "none",
            "host": domain,
            "tls": "tls"
        }

        vmesslink1 = f"vmess://{base64.urlsafe_b64encode(json.dumps(asu).encode()).decode()}"
        vmesslink2 = f"vmess://{base64.urlsafe_b64encode(json.dumps(ask).encode()).decode()}"
        vmesslink3 = f"vmess://{base64.urlsafe_b64encode(json.dumps(grpc).encode()).decode()}"

        # Restart services
        subprocess.run(['systemctl', 'restart', 'xray'])
        subprocess.run(['service', 'cron', 'restart'])

        def progress_bar(progress, total, length=20):
            filled_length = int(length * progress // total)
            bar = '█' * filled_length + '-' * (length - filled_length)
            return f"[{bar}] {int((progress / total) * 100)}%"

        # Total iterasi untuk animasi loading
        total_steps = 10

        # Mengirim pesan awal untuk progress bar
        loading_message = bot.send_message(message.chat.id, "Loading [--------------------] 0%")

    # Mengedit pesan animasi loading secara bertahap
        for step in range(1, total_steps + 1):
            bar_message = progress_bar(step, total_steps)
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=f"Loading {bar_message}")
            time.sleep(0.5)  # Jeda waktu antar update

        
        # Send result
        result_message = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  • CREATE VMESS USER •\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Remarks       : {username}\n"
            f"Expired On    : {exp_date}\n"
            f"Domain        : {domain}\n"
            f"Port TLS      : 443\n"
            f"Port none TLS : 80\n"
            f"Port  GRPC    : 443\n"
            f"id            : {uuid}\n"
            f"alterId       : 0\n"
            f"Security      : auto\n"
            f"Network       : ws\n"
            f"Path          : /vmess\n"
            f"Path WSS      : wss://bug.com/vmess\n"
            f"ServiceName   : vmess-grpc\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Link TLS : \n`{vmesslink1}`\n"
            f"\n"
            f"Link none TLS : \n`{vmesslink2}`\n"
            f"\n"
            f"Link GRPC : \n`{vmesslink3}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )

        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=result_message, parse_mode='Markdown')
        
# Check if username exists
def is_username_exists(username):
    config_path = '/etc/xray/config.json'
    try:
        with open(config_path, 'r') as file:
            config_data = file.read()
        return f'### {username} ' in config_data
    except FileNotFoundError:
        return False


def renew_vmess(message):
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Input Username:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, get_renew_username)

def get_renew_username(message):
    username = message.text
    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    if is_username_exists(username):
        # Automatically set additional expiration to 30 days
        additional_days = 30
        renew_callback_vmess(username, additional_days, message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Username tidak ditemukan. Silahkan masukkan username yang benar:')
        bot.register_next_step_handler(message, get_renew_username)

def renew_callback_vmess(username, additional_days, chat_id):
    try:
        config_path = '/etc/xray/config.json'
        with open(config_path, 'r+') as file:
            config_data = file.read()

            # Find and update expiration date in #vmess
            user_pos = config_data.find(f'### {username} ')
            if user_pos == -1:
                bot.send_message(chat_id, 'Username tidak ditemukan.')
                return
            
            # Get current expiration date
            start_pos = user_pos + len(f'### {username} ')
            end_pos = config_data.find('\n', start_pos)
            current_exp_date = config_data[start_pos:end_pos].strip()
            current_exp_date = datetime.strptime(current_exp_date, '%Y-%m-%d')
            
            # Calculate new expiration date
            new_exp_date = (current_exp_date + timedelta(days=additional_days)).strftime('%Y-%m-%d')
            
            # Update expiration date in config
            config_data = config_data[:start_pos] + new_exp_date + config_data[end_pos:]

            # Find and update expiration date in #vmessgrpc
            user_pos_grpc = config_data.find(f'### {username} ', end_pos)
            if user_pos_grpc != -1:
                start_pos_grpc = user_pos_grpc + len(f'### {username} ')
                end_pos_grpc = config_data.find('\n', start_pos_grpc)
                config_data = config_data[:start_pos_grpc] + new_exp_date + config_data[end_pos_grpc:]

            # Write back updated config
            file.seek(0)
            file.write(config_data)
            file.truncate()

        # Restart services
        subprocess.run(['systemctl', 'restart', 'xray'])
        subprocess.run(['service', 'cron', 'restart'])

        def progress_bar(progress, total, length=20):
            filled_length = int(length * progress // total)
            bar = '█' * filled_length + '-' * (length - filled_length)
            return f"[{bar}] {int((progress / total) * 100)}%"

        # Total iterasi untuk animasi loading
        total_steps = 10

        # Mengirim pesan awal untuk progress bar
        loading_message = bot.send_message(chat_id, "Loading [--------------------] 0%")

        # Mengedit pesan animasi loading secara bertahap
        for step in range(1, total_steps + 1):
            bar_message = progress_bar(step, total_steps)
            bot.edit_message_text(chat_id=chat_id, message_id=loading_message.message_id, text=f"Loading {bar_message}")
            time.sleep(0.3)  # Jeda waktu antar update
        
        # Send confirmation message
        bot.edit_message_text(chat_id=chat_id, message_id=loading_message.message_id, 
                      text=(
                          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                          f"  • RENEW VMESS USER •\n"
                          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                          f"Remarks       : {username}\n"
                          f"Expired On    : {new_exp_date}\n"
                          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                      ), 
                      parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')
        
#------------------------ TROJAN PAGE --------------------
@bot.callback_query_handler(func=lambda call: call.data == "menu_trojan") 
def menu_trojan_handler(call):
    sub_menu_trojan(call.message)
    
def sub_menu_trojan(message):
    markup = InlineKeyboardMarkup()
    
    create_button = InlineKeyboardButton("NEW TROJAN ", callback_data="create_trojan")
    renew_button = InlineKeyboardButton("RENEW TROJAN", callback_data="renew_trojan")
    kembali = InlineKeyboardButton("KEMBALI", callback_data="kembali")
    markup.add(create_button, renew_button)
    markup.add(kembali)
    
    bot.edit_message_text(
    chat_id=message.chat.id,
    message_id=message.message_id,
    text="*»»——— SAN STORE BOT ———««*\n\n"
         "🔹 *TROJAN PREMIUM* 🔹\n\n"
         "Region : SG\n"
         "ISP : DigitalOcean\n"
         "Support : HP & STB\n"
         "*»»——— Thanks for coming ———««*",
    parse_mode='Markdown',
    reply_markup=markup
    )
#======================================#
@bot.callback_query_handler(func=lambda call: call.data in ["create_trojan", "renew_trojan"])
def handle_callback(call):
    user_data = get_user_data(call.message.chat.id)
    reseller_status = user_data['reseller_status']
    vpn_price = 5000 if reseller_status == 'reseller' else 10000
    
    if call.data == "create_trojan":
        user_balance = user_data['balance']
        if user_balance >= vpn_price:
            update_balance(call.message.chat.id, -vpn_price)
            create_trojan(call.message)
        else:
            bot.send_message(call.message.chat.id, "Saldo tidak cukup.")
        
    elif call.data == "renew_trojan":
        user_balance = user_data['balance']
        if user_balance >= vpn_price:
            update_balance(call.message.chat.id, -vpn_price)
            renew_trojan(call.message)
        else:
            bot.send_message(call.message.chat.id, "Saldo tidak cukup.")
        
def create_trojan(message):    
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Input Username:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, get_username_trojan)

def get_username_trojan(message):
    username = message.text
    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    if is_username_exists(username):
        bot.send_message(message.chat.id, 'Nama sudah ada, Pilih Nama lain:')
        bot.register_next_step_handler(message, get_username_trojan)
    else:
        # Automatically set expiration to 30 days
        expired_days = 30
        exp_date = (datetime.now() + timedelta(days=expired_days)).strftime('%Y-%m-%d')
        domain = subprocess.getoutput("cat /etc/xray/domain")
        uuid = str(uuid4())

        # Update config.json
        config_path = '/etc/xray/config.json'
        with open(config_path, 'r+') as file:
            config_data = file.read()

            # Insert new user details for trojanws and trojangrpc
            new_user_entry = f'\n#! {username} {exp_date}\n}},{{"password": "{uuid}","email": "{username}"'

            # Find the position to insert for #trojanws
            trojanws_pos = config_data.find('#trojanws')
            if trojanws_pos != -1:
                insert_pos = config_data.find('\n', trojanws_pos)
                config_data = config_data[:insert_pos] + new_user_entry + config_data[insert_pos:]

            # Find the position to insert for #trojangrpc
            trojangrpc_pos = config_data.find('#trojangrpc')
            if trojangrpc_pos != -1:
                insert_pos = config_data.find('\n', trojangrpc_pos)
                config_data = config_data[:insert_pos] + new_user_entry + config_data[insert_pos:]

            # Write back the updated config
            file.seek(0)
            file.write(config_data)
            file.truncate()

        # Trojan links
        tr = '443'  # Assuming the port is 443 for simplicity
        trojanlink1 = f"trojan://{uuid}@{domain}:{tr}?mode=gun&security=tls&type=grpc&serviceName=trojan-grpc&sni={domain}#{username}"
        trojanlink2 = f"trojan://{uuid}@bug.com:{tr}?path=%2Ftrojan-ws&security=tls&host={domain}&type=ws&sni={domain}#{username}"

        # Restart services
        subprocess.run(['systemctl', 'restart', 'xray'])
        subprocess.run(['service', 'cron', 'restart'])

        def progress_bar(progress, total, length=20):
            filled_length = int(length * progress // total)
            bar = '█' * filled_length + '-' * (length - filled_length)
            return f"[{bar}] {int((progress / total) * 100)}%"

        # Total iterasi untuk animasi loading
        total_steps = 10

        # Mengirim pesan awal untuk progress bar
        loading_message = bot.send_message(message.chat.id, "Loading [--------------------] 0%")

        # Mengedit pesan animasi loading secara bertahap
        for step in range(1, total_steps + 1):
            bar_message = progress_bar(step, total_steps)
            bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=f"Loading {bar_message}")
            time.sleep(0.3)  # Jeda waktu antar update

        # Send result
        result_message = (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  • CREATE TROJAN USER •\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Remarks     : {username}\n"
            f"Expired On  : {exp_date}\n"
            f"Host/IP     : {domain}\n"
            f"Port        : {tr}\n"
            f"Key         : {uuid}\n"
            f"Path        : /trojan-ws\n"
            f"Path WSS    : wss://bug.com/trojan-ws\n"
            f"ServiceName : trojan-grpc\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Link WS : \n`{trojanlink2}`\n"
            f"\n"
            f"Link GRPC : \n`{trojanlink1}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        
        bot.edit_message_text(chat_id=message.chat.id, message_id=loading_message.message_id, text=result_message, parse_mode='Markdown')

def is_username_exists_trojan(username):
    config_path = '/etc/xray/config.json'
    try:
        with open(config_path, 'r') as file:
            config_data = file.read()
        # Cek apakah nama pengguna muncul dalam konfigurasi dengan format yang tepat
        return f'#! {username} ' in config_data
    except FileNotFoundError:
        return False


def renew_trojan(message):
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Input Username:*", parse_mode='Markdown')
    bot.register_next_step_handler(message, get_username_for_renew)

def get_username_for_renew(message):
    username = message.text
    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    if is_username_exists_trojan(username):
        # Automatically set additional expiration to 30 days
        additional_days = 30
        renew_callback_trojan(username, additional_days, message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Username tidak ditemukan, silakan coba lagi.')
        bot.register_next_step_handler(message, get_username_for_renew)

def renew_callback_trojan(username, additional_days, chat_id):
    try:
        # Update expiration date in config.json
        config_path = '/etc/xray/config.json'
        with open(config_path, 'r+') as file:
            config_data = file.read()

            # Find user entry and update expiration date
            user_entry_start = config_data.find(f'#! {username} ')
            if user_entry_start != -1:
                # Find current expiration date
                current_exp_date_str = config_data[user_entry_start + len(f'#! {username} '):].split('\n', 1)[0].strip()
                try:
                    current_exp_date = datetime.strptime(current_exp_date_str, '%Y-%m-%d')
                except ValueError:
                    bot.send_message(chat_id, 'Tanggal kedaluwarsa tidak valid dalam konfigurasi.')
                    return

                new_exp_date = (current_exp_date + timedelta(days=additional_days)).strftime('%Y-%m-%d')

                # Replace old expiration date with new one
                config_data = config_data[:user_entry_start + len(f'#! {username} ')] + new_exp_date + config_data[user_entry_start + len(f'#! {username} ') + len(current_exp_date_str):]

                # Write back the updated config
                file.seek(0)
                file.write(config_data)
                file.truncate()
                
                # Update expiration date in #trojangrpc
                trojangrpc_pos = config_data.find(f'#trojangrpc')
                if trojangrpc_pos != -1:
                    user_entry_start = config_data.find(f'#! {username} ', trojangrpc_pos)
                    if user_entry_start != -1:
                        current_exp_date_str = config_data[user_entry_start + len(f'#! {username} '):].split('\n', 1)[0].strip()
                        new_exp_date = (datetime.strptime(current_exp_date_str, '%Y-%m-%d') + timedelta(days=additional_days)).strftime('%Y-%m-%d')
                        config_data = config_data[:user_entry_start + len(f'#! {username} ')] + new_exp_date + config_data[user_entry_start + len(f'#! {username} ') + len(current_exp_date_str):]
                        file.seek(0)
                        file.write(config_data)
                        file.truncate()

                # Restart services
                subprocess.run(['systemctl', 'restart', 'xray'])
                subprocess.run(['service', 'cron', 'restart'])

                def progress_bar(progress, total, length=20):
                    filled_length = int(length * progress // total)
                    bar = '█' * filled_length + '-' * (length - filled_length)
                    return f"[{bar}] {int((progress / total) * 100)}%"

               # Total iterasi untuk animasi loading
                total_steps = 10

                # Mengirim pesan awal untuk progress bar
                loading_message = bot.send_message(chat_id, "Loading [--------------------] 0%")

               # Mengedit pesan animasi loading secara bertahap
                for step in range(1, total_steps + 1):
                    bar_message = progress_bar(step, total_steps)
                    bot.edit_message_text(chat_id=chat_id, message_id=loading_message.message_id, text=f"Loading {bar_message}")
                    time.sleep(0.3)  # Jeda waktu antar update
        
                bot.edit_message_text(chat_id=chat_id, message_id=loading_message.message_id, 
                      text=(
                          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                          f"  • RENEW TROJAN USER •\n"
                          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                          f"Remarks       : {username}\n"
                          f"Expired On    : {new_exp_date}\n"
                          f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                      ), 
                      parse_mode='Markdown')

            else:
                bot.send_message(chat_id, f'Pengguna {username} tidak ditemukan dalam konfigurasi.')
    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')

#======================== FUNGSI BALANCE =================
@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    if message.chat.id != admin_id:
        bot.send_message(message.chat.id, "Anda tidak memiliki izin untuk menambahkan saldo.")
        return

    try:
        _, user_id, amount = message.text.split()
        user_id = int(user_id)
        amount = int(amount)
        update_balance(user_id, amount)
        user_data = get_user_data(user_id)
        bot.send_message(message.chat.id, f"Saldo berhasil ditambahkan. User {user_id} sekarang memiliki saldo: {user_data['balance']} dan status: {user_data['reseller_status']}")
    except ValueError:
        bot.send_message(message.chat.id, "Format salah. Gunakan /addbalance <user_id> <amount>.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Terjadi kesalahan: {str(e)}")
        
def get_vpn_price(user_id):
    user_data = get_user_data(user_id)
    reseller_status = user_data['reseller_status']
    return 5000 if reseller_status == 'reseller' else 10000
   
#======================= FITUR HANDLE TOP UP ================
@bot.callback_query_handler(func=lambda call: call.data == "topup") 
def menu_topup_handler(call):
    topup_handler(call.message)

def topup_handler(message):
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text="*Masukkan Nominal Top*", parse_mode='Markdown')
    bot.register_next_step_handler_by_chat_id(message.chat.id, process_topup)
        
def process_topup(message):
    if username == '/start':
        bot.send_message(message.chat.id, "Proses pembuatan username dihentikan. Ketikkan /start untuk memulai lagi.")
        return  # Stop processing and return
    try:
        nominal = int(message.text)  # Pastikan pengguna memasukkan angka
        chat_id = message.chat.id

        # Simpan nominal ke user_data sementara
        user_data[chat_id] = {'nominal': nominal}

        # Meminta pengguna untuk mengirimkan foto bukti transfer
        bot.send_message(chat_id, f"Anda ingin top up sebesar Rp{nominal:,}\n Silahkan Lakukan Pembayaran Ke DANA/GOPAY : 082292615651\nAtau Melalui Qris : https://tinyurl.com/SanQris\n\nKirim Bukti Screenshot Transfer Disini Jika selesai")
        bot.register_next_step_handler_by_chat_id(chat_id, process_transfer_proof)
    except ValueError:
        bot.send_message(message.chat.id, "Nominal tidak valid. Silakan masukkan angka yang benar.")
        bot.register_next_step_handler_by_chat_id(message.chat.id, process_topup)

# Fungsi untuk memproses foto bukti transfer
def process_transfer_proof(message):
    chat_id = message.chat.id

    if message.photo:  # Jika pengguna mengirimkan foto
        # Ambil file ID foto bukti transfer
        photo_id = message.photo[-1].file_id

        # Simpan file ID foto di user_data
        user_data[chat_id]['photo'] = photo_id

        # Ambil informasi dari user_data
        nominal = user_data[chat_id]['nominal']

        # Kirim notifikasi ke admin
        bot.send_photo(admin_id, photo_id, caption=f"Permintaan Top Up\nChat ID: `{chat_id}`\nNominal: Rp `{nominal:,}`", parse_mode="Markdown")

        # Beri tahu pengguna bahwa permintaan mereka sedang diproses
        bot.send_message(chat_id, "Permintaan top up Anda telah dikirim dan sedang diproses.")

    else:
        bot.send_message(chat_id, "Silakan kirimkan foto bukti transfer")
        bot.register_next_step_handler_by_chat_id(chat_id, process_transfer_proof)
        

#======================= BROADCAST ===================>
@bot.callback_query_handler(func=lambda call: call.data == "broadcast") 
def menu_trojan_handler(call):
    broadcast_handler(call.message)

def broadcast_handler(message):
    msg = bot.send_message(message.chat.id, "𝙄𝙨𝙞 𝘽𝙧𝙤𝙖𝙙𝙘𝙖𝙨𝙩📢")
    bot.register_next_step_handler(msg, send_broadcast_message)

def send_broadcast_message(message):
    broadcast_text = message.text

    # Connect to the database
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()

    # Get all users' chat IDs from the database
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    if not users:
        bot.send_message(message.chat.id, "No users found to send the broadcast.")
        connection.close()
        return

    # Send the broadcast message to each user
    sent_count = 0
    for user in users:
        try:
            bot.send_message(user[0], f"📢 INFORMASI 📢\n\n{broadcast_text}")
            sent_count += 1
        except Exception as e:
            print(f"Failed to send message to {user[0]}: {e}")

    bot.send_message(message.chat.id, f"Pesan telah berhasil dikirim ke {sent_count} pengguna.")
    connection.commit()
    connection.close()

#================== BACKUP & RESTORE ===============
def backup_database():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w') as backup_zip:
            backup_zip.write(DB_PATH, os.path.basename(DB_PATH))
        return zip_filename
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return None

# Function to send the backup to the admin
def send_backup_to_admin():
    zip_filename = backup_database()
    if zip_filename:
        try:
            with open(zip_filename, 'rb') as backup_file:
                bot.send_document(admin_id, backup_file)
        except Exception as e:
            print(f"Failed to send backup to admin: {e}")

# Function to restore the database from a zip file
def restore_database(zip_filename):
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            zip_ref.extract(os.path.basename(DB_PATH), os.path.dirname(DB_PATH))
        print("Database restored successfully.")
    except Exception as e:
        print(f"Failed to restore the database: {e}")

# Schedule autobackup every 6 hours
def schedule_backup():
    while True:
        send_backup_to_admin()
        threading.Event().wait(21600)  # 6 hours in seconds

# Start the backup scheduler in a new thread
backup_thread = threading.Thread(target=schedule_backup, daemon=True)
backup_thread.start()

@bot.message_handler(content_types=['document'])
def handle_zip_file(message):
    if str(message.chat.id) == "576495165" and message.document.mime_type == 'application/zip':
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        zip_filename = os.path.join(BACKUP_DIR, message.document.file_name)
        
        with open(zip_filename, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        restore_database(zip_filename)
        bot.send_message(576495165, "Database berhasil dipulihkan dari backup.")
    else:
        bot.send_message(message.chat.id, "You don't have permission to restore the database.")

#=================== REDEM CODE ===================
# Function to create a new redeem code
def create_redeem_code(code_name, balance, total_uses):
    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT OR REPLACE INTO redeem_codes (code_name, balance, remaining_uses, total_uses)
                      VALUES (?, ?, ?, ?)''', (code_name, balance, total_uses, total_uses))
    conn.commit()
    conn.close()

# Command to add a new redeem code (for admin or authorized users)
@bot.message_handler(commands=['addcode'])
def add_code(message):
    # Example format: /addcode code_name balance total_uses
    if len(message.text.split()) != 4:
        bot.reply_to(message, "Usage: /addcode <code_name> <balance> <total_uses>")
        return

    _, code_name, balance, total_uses = message.text.split()
    balance = int(balance)
    total_uses = int(total_uses)

    # Create the redeem code
    create_redeem_code(code_name, balance, total_uses)
    bot.reply_to(message, f"Redeem code '{code_name}' created with {balance} balance and {total_uses} total uses.")

# Handler for all text messages (redeem code processing)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    code_name = message.text.strip()

    conn = sqlite3.connect('user_data.db')
    cursor = conn.cursor()

    # Check if the user has already used this redeem code
    cursor.execute('SELECT 1 FROM redeemed_codes WHERE user_id = ? AND code_name = ?', (user_id, code_name))
    if cursor.fetchone():
        bot.reply_to(message, "You have already used this redeem code.")
        conn.close()
        return

    # Check if the code exists and has remaining uses
    cursor.execute('SELECT balance, remaining_uses FROM redeem_codes WHERE code_name = ?', (code_name,))
    result = cursor.fetchone()

    if result:
        balance, remaining_uses = result
        if remaining_uses > 0:
            # Update user's balance
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (balance, user_id))
            # If user does not exist, insert new record
            if cursor.rowcount == 0:
                cursor.execute('INSERT INTO users (user_id, balance) VALUES (?, ?)', (user_id, balance))
            
            # Update remaining uses of the redeem code
            cursor.execute('UPDATE redeem_codes SET remaining_uses = remaining_uses - 1 WHERE code_name = ?', (code_name,))
            # Record that the user has redeemed this code
            cursor.execute('INSERT INTO redeemed_codes (user_id, code_name) VALUES (?, ?)', (user_id, code_name))
            bot.reply_to(message, f"Successfully redeemed {balance} balance! Remaining uses for this code: {remaining_uses - 1}")
        else:
            bot.reply_to(message, "This redeem code has been fully used.")
    else:
        bot.reply_to(message, "Invalid redeem code.")

    conn.commit()
    conn.close()

#================== COMMAND DELETE ACCOUNT ===========

@bot.message_handler(commands=['admin'])
def start_command(message):
    # Check if the user is the admin
    if message.chat.id == ADMIN_CHAT_ID:
        # Create an inline keyboard
        markup = InlineKeyboardMarkup()

        ssh = InlineKeyboardButton("DELETE SSH", callback_data="delete_ssh")
        vmess = InlineKeyboardButton("DELETE VMESS", callback_data="delete_vmess")
        trojan = InlineKeyboardButton("DELETE TROJAN", callback_data="delete_trojan")

        markup.add(ssh)
        markup.add(vmess, trojan)
        
        bot.send_message(message.chat.id, "Halo Tuan....", reply_markup=markup)
    else:
        # If the user is not the admin, deny access
        bot.send_message(message.chat.id, "Access denied. You are not authorized to use this bot.")

# Callback handler for specific inline button data
@bot.callback_query_handler(func=lambda call: call.data in ["delete_ssh", "delete_vmess", "delete_trojan"])
def handle_callback(call):
    # Check if the user is the admin
    if call.message.chat.id != ADMIN_CHAT_ID:
        bot.answer_callback_query(call.id, "Access denied.")
        return

    # Handle the button actions
    if call.data == "delete_ssh":
        delete_ssh_account(call.message)
    elif call.data == "delete_vmess":
        delete_vmess(call.message)
    elif call.data == "delete_trojan":
        delete_trojan(call.message)
    

#=============== DELETE SSH ======================
def delete_ssh_account(message):
    bot.send_message(message.chat.id, 'Input the SSH username to delete:')
    bot.register_next_step_handler(message, handle_delete_username)

def handle_delete_username(message):
    username = message.text
    if is_user_exists(username):
        try:
            # Delete the user account
            subprocess.run(['userdel', '-r', username], check=True)
            bot.send_message(message.chat.id, f'User {username} has been deleted successfully.')
        except Exception as e:
            bot.send_message(message.chat.id, f'Error deleting user {username}: {str(e)}')
    else:
        bot.send_message(message.chat.id, 'User does not exist. Please provide a valid username.')

def is_user_exists(username):
    try:
        # Check if the user exists in the system
        result = subprocess.run(['id', username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception:
        return False

#====================== FUNGSI DELETE VMESS =============

def delete_vmess(message):
    bot.send_message(message.chat.id, 'Input Username to Delete:')
    bot.register_next_step_handler(message, get_delete_username_vmess)

def get_delete_username_vmess(message):
    username = message.text
    if is_username_exists(username):
        delete_vmess_account(username, message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Username tidak ditemukan. Silahkan masukkan username yang benar:')
        bot.register_next_step_handler(message, get_delete_username_vmess)

def delete_vmess_account(username, chat_id):
    try:
        config_path = '/etc/xray/config.json'
        with open(config_path, 'r+') as file:
            config_data = file.read()

            # Find and remove user entry in #vmess
            user_pos = config_data.find(f'### {username} ')
            if user_pos == -1:
                bot.send_message(chat_id, 'Username tidak ditemukan.')
                return

            # Find the end of the user entry
            end_pos = config_data.find('\n', user_pos) + 1

            # Remove the user entry from the config
            config_data = config_data[:user_pos] + config_data[end_pos:]

            # Find and remove user entry in #vmessgrpc if it exists
            user_pos_grpc = config_data.find(f'### {username} ')
            if user_pos_grpc != -1:
                end_pos_grpc = config_data.find('\n', user_pos_grpc) + 1
                config_data = config_data[:user_pos_grpc] + config_data[end_pos_grpc:]

            # Write back the updated config
            file.seek(0)
            file.write(config_data)
            file.truncate()

        # Restart services
        subprocess.run(['systemctl', 'restart', 'xray'])
        subprocess.run(['service', 'cron', 'restart'])

        # Send confirmation message
        bot.send_message(chat_id, f'User {username} telah dihapus dari config.')

    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')
        
        
#=========================== DELETE TROJAN =====================

def delete_trojan(message):
    bot.send_message(message.chat.id, 'Input Username to Delete:')
    bot.register_next_step_handler(message, get_delete_username_trojan)

def get_delete_username_trojan(message):
    username = message.text
    if is_username_exists_trojan(username):
        delete_trojan_account(username, message.chat.id)
    else:
        bot.send_message(message.chat.id, 'Username tidak ditemukan. Silahkan masukkan username yang benar:')
        bot.register_next_step_handler(message, get_delete_username_trojan)

def delete_trojan_account(username, chat_id):
    try:
        config_path = '/etc/xray/config.json'
        with open(config_path, 'r+') as file:
            config_data = file.read()

            user_pos = config_data.find(f'#! {username} ')
            if user_pos == -1:
                bot.send_message(chat_id, 'Username tidak ditemukan.')
                return

            # Find the end of the user entry
            end_pos = config_data.find('\n', user_pos) + 1

            # Remove the user entry from the config
            config_data = config_data[:user_pos] + config_data[end_pos:]

            # Find and remove user entry in grpc if it exists
            user_pos_grpc = config_data.find(f'#! {username} ')
            if user_pos_grpc != -1:
                end_pos_grpc = config_data.find('\n', user_pos_grpc) + 1
                config_data = config_data[:user_pos_grpc] + config_data[end_pos_grpc:]

            # Write back the updated config
            file.seek(0)
            file.write(config_data)
            file.truncate()

        # Restart services
        subprocess.run(['systemctl', 'restart', 'xray'])
        subprocess.run(['service', 'cron', 'restart'])

        # Send confirmation message
        bot.send_message(chat_id, f'User {username} telah dihapus dari config.')

    except Exception as e:
        bot.send_message(chat_id, f'Error: {str(e)}')
               
        
bot.polling()



        
