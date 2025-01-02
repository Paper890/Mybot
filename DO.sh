#!/bin/bash
clear
# Minta token bot dan chat ID dari pengguna
echo -e "•••• SETUP BOT ••••"
read -p "Masukkan Token DO Anda: " DO_TOKEN

# Perbarui paket dan instal Python3-pip jika belum ada
apt-get update
apt-get install -y python3-pip

# Instal modul Python yang diperlukan
pip3 install requests
pip3 install schedule
pip3 install pyTelegramBotAPI

cd
# Buat direktori proyek
mkdir -p /root/san/bot
cd /root/san/bot

# Buat file script python
cat <<EOF > do.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import requests
import time

# Masukkan token bot telegram Anda di sini
TOKEN = '7326202667:AAHShtcwXkt51IMU8tIdAF9zZanoTvDDZ9A'
# Masukkan token API DigitalOcean Anda di sini
DO_TOKEN = '${DO_TOKEN}'

# URL endpoint untuk membuat dan mengelola droplet di DigitalOcean
DO_DROPLET_URL = 'https://api.digitalocean.com/v2/droplets'

# Default root password
ROOT_PASSWORD = '@1Vpsbysan'

# Inisialisasi objek bot
bot = telebot.TeleBot(TOKEN)

# Chat ID admin
ADMIN_CHAT_ID = 576495165

# Dictionary untuk memetakan opsi ukuran dengan kode ukuran DigitalOcean yang sesuai
size_options = {
    '1 TB / 1GB RAM': 's-1vcpu-1gb-amd',
    '2 TB / 2GB RAM': 's-1vcpu-2gb-amd',
    '3 TB / 2GB RAM': 's-2vcpu-2gb-amd',
    '4 TB / 4GB RAM': 's-2vcpu-4gb-amd',
    '5 TB / 8GB RAM': 's-4vcpu-8gb-amd',
}

# Dictionary untuk menyimpan data pengguna sementara
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    if chat_id == ADMIN_CHAT_ID:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("CREATE", callback_data="create"))
        keyboard.add(InlineKeyboardButton("DELETE", callback_data="delete"))
        keyboard.add(InlineKeyboardButton("LIST DROPLET", callback_data="list_droplet"))
        keyboard.add(InlineKeyboardButton("POWER ON", callback_data="power"))
        keyboard.add(InlineKeyboardButton("RESIZE", callback_data="resize"))
        keyboard.add(InlineKeyboardButton("CEK LIMIT DROPLET", callback_data="cek_saldo"))
        bot.send_message(chat_id, "Welcome, Admin! Choose an option:", reply_markup=keyboard)
    else:
        bot.send_message(chat_id, "You are not authorized to use this bot.")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    if call.data == "create":
        request_droplet_name(call.message)
    elif call.data == "delete":
        request_droplet_name_for_delete(call.message)
    elif call.data == "list_droplet":
        list_droplets(call.message)
    elif call.data == "power":
        request_droplet_name_for_power(call.message)
    elif call.data == "resize":
        request_droplet_name_for_resize(call.message)
    elif call.data == "cek_saldo":
        cek_saldo_trial_droplet(call.message)
    elif call.data.startswith("size_"):
        handle_size_callback(call)
    elif call.data.startswith("resize_"):
        handle_resize_callback(call)

def request_droplet_name(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, 'Enter droplet name:')
    bot.register_next_step_handler(message, create_droplet)

def create_droplet(message):
    chat_id = message.chat.id
    droplet_name = message.text
    user_data[chat_id] = {'name': droplet_name}
    
    size_keyboard = InlineKeyboardMarkup(row_width=1)
    for size_label, size_code in size_options.items():
        button = InlineKeyboardButton(text=size_label, callback_data=f"size_{size_code}")
        size_keyboard.add(button)
    
    bot.send_message(chat_id, 'Select droplet size:', reply_markup=size_keyboard)

def handle_size_callback(call: CallbackQuery):
    chat_id = call.message.chat.id
    size_code = call.data.split('_')[1]
    droplet_name = user_data.get(chat_id, {}).get('name')
    
    if not droplet_name:
        bot.send_message(chat_id, 'Error occurred. Please start again.')
        return

    region = 'sgp1'
    image = 'ubuntu-20-04-x64'
    
    data = {
        'name': droplet_name,
        'region': region,
        'size': size_code,
        'image': image,
        'user_data': f'''#!/bin/bash
                        useradd -m -s /bin/bash root
                        echo "root:{ROOT_PASSWORD}" | chpasswd
                        '''
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DO_TOKEN}'
    }
    
    response = requests.post(DO_DROPLET_URL, json=data, headers=headers)
    
    if response.status_code == 202:
        bot.send_message(chat_id, 'Droplet created successfully! Waiting 60 seconds to fetch information...')
        time.sleep(60)
        droplet_info = get_droplet_info(response.json()['droplet']['id'])
        if droplet_info:
            respon = "DROPLET INFORMATION\n"
            respon += f"Name: {droplet_info['name']}\n"
            respon += f"ID: {droplet_info['id']}\n"
            respon += f"Public IP: {droplet_info['ip_address']}"
            bot.send_message(chat_id, respon)
        else:
            bot.send_message(chat_id, 'Failed to retrieve droplet information.')
    else:
        bot.send_message(chat_id, 'Failed to create droplet. Please try again.')

def get_droplet_info(droplet_id):
    droplet_info_url = f"{DO_DROPLET_URL}/{droplet_id}"
    headers = {
        'Authorization': f'Bearer {DO_TOKEN}'
    }
    response = requests.get(droplet_info_url, headers=headers)
    if response.status_code == 200:
        droplet_info = response.json()['droplet']
        return {
            'id': droplet_info['id'],
            'name': droplet_info['name'],
            'ip_address': droplet_info['networks']['v4'][0]['ip_address']
        }
    else:
        return None

def request_droplet_name_for_delete(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, 'Enter droplet name to delete:')
    bot.register_next_step_handler(message, delete_droplet_by_name)

def delete_droplet_by_name(message):
    chat_id = message.chat.id
    droplet_name = message.text
    droplet_id = get_droplet_id_by_name(droplet_name)
    
    if droplet_id:
        if delete_droplet(droplet_id):
            bot.send_message(chat_id, f"Droplet '{droplet_name}' has been deleted.")
        else:
            bot.send_message(chat_id, f"Failed to delete droplet '{droplet_name}'.")
    else:
        bot.send_message(chat_id, f"Droplet '{droplet_name}' not found.")

def get_droplet_id_by_name(droplet_name):
    headers = {
        'Authorization': f'Bearer {DO_TOKEN}'
    }
    response = requests.get(DO_DROPLET_URL, headers=headers)
    if response.status_code == 200:
        droplets = response.json().get('droplets', [])
        for droplet in droplets:
            if droplet['name'] == droplet_name:
                return droplet['id']
    return None

def delete_droplet(droplet_id):
    url = f'https://api.digitalocean.com/v2/droplets/{droplet_id}'
    headers = {'Authorization': f'Bearer {DO_TOKEN}'}
    response = requests.delete(url, headers=headers)
    return response.status_code == 204

def list_droplets(message):
    chat_id = message.chat.id
    headers = {
        'Authorization': f'Bearer {DO_TOKEN}'
    }
    response = requests.get(DO_DROPLET_URL, headers=headers)
    
    if response.status_code == 200:
        droplets = response.json().get('droplets', [])
        if droplets:
            respon = "DROPLET LIST:\n\n"
            for droplet in droplets:
                name = droplet['name']
                droplet_id = droplet['id']
                ip_address = next((net['ip_address'] for net in droplet['networks']['v4'] if net['type'] == 'public'), 'No public IP')
                respon += f"Name: {name}\nID: {droplet_id}\nPublic IP: {ip_address}\n\n"
            bot.send_message(chat_id, respon)
        else:
            bot.send_message(chat_id, "No droplets found.")
    else:
        bot.send_message(chat_id, "Error retrieving droplet list.")

def request_droplet_name_for_power(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, 'Enter droplet name to power on/off:')
    bot.register_next_step_handler(message, power_droplet)

def power_droplet(message):
    chat_id = message.chat.id
    droplet_name = message.text
    droplet_id = get_droplet_id_by_name(droplet_name)
    
    if droplet_id:
        current_status = get_droplet_status(droplet_id)
        if current_status == "active":
            action = "power_off"
        else:
            action = "power_on"

        if power_action_droplet(droplet_id, action):
            bot.send_message(chat_id, f"Droplet '{droplet_name}' has been powered {'on' if action == 'power_on' else 'off'}.")
        else:
            bot.send_message(chat_id, f"Failed to perform power action on droplet '{droplet_name}'.")
    else:
        bot.send_message(chat_id, f"Droplet '{droplet_name}' not found.")

def get_droplet_status(droplet_id):
    droplet_info = get_droplet_info(droplet_id)
    if droplet_info:
        return droplet_info.get('status')
    return None

def power_action_droplet(droplet_id, action):
    url = f'{DO_DROPLET_URL}/{droplet_id}/actions'
    headers = {
        'Authorization': f'Bearer {DO_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {'type': action}
    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 201

def request_droplet_name_for_resize(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, 'Enter droplet name to resize:')
    bot.register_next_step_handler(message, resize_droplet)

def resize_droplet(message):
    chat_id = message.chat.id
    droplet_name = message.text
    user_data[chat_id] = {'name': droplet_name}
    droplet_id = get_droplet_id_by_name(droplet_name)
    
    if droplet_id:
        size_keyboard = InlineKeyboardMarkup(row_width=1)
        for size_label, size_code in size_options.items():
            button = InlineKeyboardButton(text=size_label, callback_data=f"resize_{size_code}")
            size_keyboard.add(button)
        
        bot.send_message(chat_id, 'Select new droplet size:', reply_markup=size_keyboard)
    else:
        bot.send_message(chat_id, f"Droplet '{droplet_name}' not found.")

def handle_resize_callback(call: CallbackQuery):
    chat_id = call.message.chat.id
    size_code = call.data.split('_')[1]
    droplet_name = user_data.get(chat_id, {}).get('name')
    droplet_id = get_droplet_id_by_name(droplet_name)
    
    if droplet_id:
        if resize_droplet_action(droplet_id, size_code):
            bot.send_message(chat_id, f"Droplet '{droplet_name}' has been resized to {size_code}.")
        else:
            bot.send_message(chat_id, f"Failed to resize droplet '{droplet_name}'.")
    else:
        bot.send_message(chat_id, 'Error occurred. Please start again.')

def resize_droplet_action(droplet_id, size_code):
    url = f'{DO_DROPLET_URL}/{droplet_id}/actions'
    headers = {
        'Authorization': f'Bearer {DO_TOKEN}',
        'Content-Type': 'application/json'
    }
    data = {
        'type': 'resize',
        'size': size_code
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code == 201
        
# Start polling for Telegram bot
bot.polling()  
EOF

# Buat file service systemd
cat << 'EOF' > /etc/systemd/system/do.service
[Unit]
Description=Do Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/san/bot
ExecStart=/usr/bin/python3 do.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd dan mulai service
systemctl daemon-reload
systemctl enable do
systemctl start do

echo "Berhasil Install DO" 

#!/bin/bash
mkdir -p /root/san/bot
cd /root/san/bot

cat << 'EOF' > dns.py
import telebot
from telebot import types
import requests
import json

# Konfigurasi bot Telegram
bot_token = '7336371877:AAGxgO7pWRCvZrd3hiXWgMfAkGLfPxcntwg'
bot = telebot.TeleBot(bot_token)

# Konfigurasi Cloudflare
cloudflare_api_token = 'mHxjeQgvZhqWGL2T8mTs866h4Kqi1xncAiJDWvSc'
zone_id = 'f7400aabacca20ee7f6227f716396fab'
base_url = f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records'

# Fungsi untuk menambahkan DNS record
def add_dns_record(type="A", name="", content="", ttl=1, proxied=False):
    headers = {
        'Authorization': f'Bearer {cloudflare_api_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'type': type,
        'name': name,
        'content': content,
        'ttl': ttl,
        'proxied': proxied
    }
    response = requests.post(base_url, headers=headers, data=json.dumps(data))
    return response.json()

# Fungsi untuk mengedit DNS record
def edit_dns_record(record_id, type="A", name="", content="", ttl=1, proxied=False):
    headers = {
        'Authorization': f'Bearer {cloudflare_api_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'type': type,
        'name': name,
        'content': content,
        'ttl': ttl,
        'proxied': proxied
    }
    url = f'{base_url}/{record_id}'
    response = requests.put(url, headers=headers, data=json.dumps(data))
    return response.json()

# Fungsi untuk mendapatkan ID DNS record berdasarkan nama
def get_dns_record_id(name):
    headers = {
        'Authorization': f'Bearer {cloudflare_api_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(base_url, headers=headers)
    records = response.json().get('result', [])
    for record in records:
        if record['name'] == name:
            return record['id']
    return None

# Command handler untuk /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = types.InlineKeyboardMarkup()
    btn_add = types.InlineKeyboardButton("ADD DNS", callback_data="add_dns")
    btn_edit = types.InlineKeyboardButton("EDIT DNS", callback_data="edit_dns")
    markup.add(btn_add, btn_edit)
    bot.send_message(message.chat.id, "Pilih tindakan:", reply_markup=markup)

# Callback handler untuk tombol InlineKeyboardButton
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "add_dns":
        bot.send_message(call.message.chat.id, "Masukkan nama domain:")
        bot.register_next_step_handler(call.message, get_dns_name_to_add)
    elif call.data == "edit_dns":
        bot.send_message(call.message.chat.id, "Masukkan nama domain yang ingin diubah:")
        bot.register_next_step_handler(call.message, get_edit_dns_name)

# Fungsi untuk menambah DNS record
def get_dns_name_to_add(message):
    dns_name = message.text
    bot.reply_to(message, "Masukkan konten (misalnya alamat IP):")
    bot.register_next_step_handler(message, get_dns_content_to_add, dns_name)

def get_dns_content_to_add(message, dns_name):
    dns_content = message.text
    result = add_dns_record(name=dns_name, content=dns_content)
    if result.get('success'):
        bot.reply_to(
            message, 
            f"Registrasi DNS Record\nDNS : `{dns_name}.easyvpn.biz.id`\nIP : `{dns_content}`", 
            parse_mode="MarkdownV2"
        )
    else:
        bot.reply_to(message, f"Terjadi kesalahan: {result.get('errors')}")

# Fungsi untuk mengedit DNS record
def get_edit_dns_name(message):
    dns_name = message.text
    record_id = get_dns_record_id(dns_name)
    if record_id:
        bot.reply_to(message, "Masukkan konten baru (misalnya alamat IP):")
        bot.register_next_step_handler(message, get_new_dns_content, record_id, dns_name)
    else:
        bot.reply_to(message, "DNS record tidak ditemukan.")

def get_new_dns_content(message, record_id, dns_name):
    dns_content = message.text
    result = edit_dns_record(record_id, name=dns_name, content=dns_content)
    if result.get('success'):
        bot.reply_to(message, "Sukses✓")
    else:
        bot.reply_to(message, f"Terjadi kesalahan: {result.get('errors')}")

# Menjalankan bot
bot.polling()

EOF

cat << 'EOF' > /etc/systemd/system/dns.service
[Unit]
Description=Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/san/bot
ExecStart=/usr/bin/python3 dns.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload 
sudo systemctl start dns
sudo systemctl enable dns

echo "Berhasil Install DNS"
echo "Sukses✓"
cd
rm DO.sh
