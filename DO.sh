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

# URL endpoint untuk membuat droplet di DigitalOcean
DO_DROPLET_URL = 'https://api.digitalocean.com/v2/droplets'

# Default root password
ROOT_PASSWORD = '@1Vpsbysan'

# Inisialisasi objek bot
bot = telebot.TeleBot(TOKEN)

# Admin ChatID
ADMIN_CHAT_ID = 576495165

# Dictionary untuk memetakan opsi ukuran dengan kode ukuran DigitalOcean yang sesuai
size_options = {
    '1 TB / 1GB RAM': 's-1vcpu-1gb-amd',
    '2 TB / 2GB RAM': 's-1vcpu-2gb-amd',
    '3 TB / 2GB RAM': 's-2vcpu-2gb-amd',
    '4 TB / 4GB RAM': 's-2vcpu-4gb-amd',
    '5 TB / 8GB RAM': 's-4vcpu-8gb-amd',
    # Tambahkan lebih banyak opsi ukuran jika diperlukan
}

# Dictionary untuk menyimpan nama droplet yang diinput oleh pengguna
user_data = {}

@bot.message_handler(commands=['create'])
def request_droplet_name(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_CHAT_ID:
        bot.send_message(chat_id, 'Anda tidak memiliki izin untuk menggunakan perintah ini.')
        return
    bot.send_message(chat_id, 'Masukkan nama droplet:')
    bot.register_next_step_handler(message, create_droplet)

def create_droplet(message):
    chat_id = message.chat.id
    droplet_name = message.text
    user_data[chat_id] = {'name': droplet_name}  # Simpan nama droplet di user_data
    # Membuat InlineKeyboard untuk memilih ukuran droplet
    size_keyboard = InlineKeyboardMarkup(row_width=1)
    for size_label, size_code in size_options.items():
        button = InlineKeyboardButton(text=size_label, callback_data=f"size_{size_code}")
        size_keyboard.add(button)
    
    bot.send_message(chat_id, 'Pilih ukuran droplet:', reply_markup=size_keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('size_'))
def handle_size_callback(call: CallbackQuery):
    chat_id = call.message.chat.id
    if chat_id != ADMIN_CHAT_ID:
        bot.send_message(chat_id, 'Anda tidak memiliki izin untuk menggunakan perintah ini.')
        return
    size_code = call.data.split('_')[1]  # Mendapatkan kode ukuran dari data callback
    droplet_name = user_data.get(chat_id, {}).get('name')  # Mendapatkan nama droplet dari user_data

    if not droplet_name:
        bot.send_message(chat_id, 'Terjadi kesalahan. Silakan mulai lagi.')
        return

    if size_code not in size_options.values():
        bot.send_message(chat_id, 'Ukuran droplet tidak valid. Silakan coba lagi.')
        return

    # Parameter lain untuk membuat droplet
    region = 'sgp1'  
    image = 'debian-10-x64'  
    
    # Membuat payload untuk request API DigitalOcean
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
    
    # Header untuk autentikasi dengan token API DigitalOcean
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DO_TOKEN}'
    }
    
    # Mengirim request untuk membuat droplet
    response = requests.post(DO_DROPLET_URL, json=data, headers=headers)
    
    if response.status_code == 202:
        bot.send_message(chat_id, 'Droplet berhasil dibuat! Menunggu 60 detik sebelum mengambil informasi...')
        time.sleep(60)
        droplet_info = get_droplet_info(response.json()['droplet']['id'])
        respon = "INFORMASI DROPLET\n"
        respon += f"NAMA: {droplet_info['name']}\n"
        respon += f"ID: {droplet_info['id']}\n"
        respon += f"IP: {droplet_info['ip_address']}"
        bot.send_message(chat_id, respon)
    else:
        bot.send_message(chat_id, 'Gagal membuat droplet. Silakan coba lagi.')

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

# Fungsi untuk menghapus droplet berdasarkan ID
def delete_droplet(droplet_id):
    url = f'https://api.digitalocean.com/v2/droplets/{droplet_id}'
    headers = {'Authorization': f'Bearer {DO_TOKEN}'}
    response = requests.delete(url, headers=headers)
    return response.status_code == 204

# Handler untuk menerima perintah /delete
@bot.message_handler(commands=['delete'])
def handle_delete_droplet(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_CHAT_ID:
        bot.send_message(chat_id, 'Anda tidak memiliki izin untuk menggunakan perintah ini.')
        return
    try:
        # Memecah pesan untuk mendapatkan ID droplet
        droplet_id = message.text.split()[1]
        # Menghapus droplet dan memberikan balasan
        if delete_droplet(droplet_id):
            bot.reply_to(message, f"Droplet dengan ID {droplet_id} berhasil dihapus.")
        else:
            bot.reply_to(message, f"Droplet dengan ID {droplet_id} tidak ditemukan atau gagal dihapus.")
    except IndexError:
        bot.reply_to(message, "Format perintah salah. Gunakan /delete_droplet <DROPLET_ID>.")

# Start bot polling
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

echo "Autobackup Berhasil Di install" 

cd
rm DO.sh
