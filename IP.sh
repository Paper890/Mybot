#!/bin/bash
clear
# Minta token bot dan chat ID dari pengguna
echo -e "•••• SETUP BOT ••••"
read -p "Masukkan Token Github Anda: " GIT_TOKEN

cd
# Buat direktori proyek
mkdir -p /root/san/bot
cd /root/san/bot

# Buat file script python
cat <<EOF > ip.py
import datetime
import random
import re
import requests
import base64
import telebot

bot_token = '6933923564:AAHC1esXFo0eLFFaRxNv7woM0yEu5-pM6wY'
bot = telebot.TeleBot(bot_token)

github_username = 'Paper890'
github_repository = 'izin'
file_name = 'IP'
github_token = '${GIT_TOKEN}'

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, '🤖Bot Registrasi Autoscript By San🤖 \n📝Masukkan /newsc untuk Registrasi')

def add_text(message):
    bot.reply_to(message, "Masukkan Masa Aktif dan IP. Contoh : 10 192.168.1.1")

@bot.message_handler(func=lambda message: True)
def echo(message):
    if message.text.startswith('/newsc'):
        add_text(message)
    elif not message.text.startswith('/start'):
        text = message.text
        ip = text.split()[-1]
        days = int(text.split()[0])
        user = generate_user()
        expiry_date = calculate_expiry(days)
        was_updated, new_expiry_date = update_or_add_entry(github_username, github_repository, file_name, f"# {user} {expiry_date} {ip} ON", ip, days, github_token)
        
        if was_updated:
            bot.reply_to(message, f"IP {ip} telah diperpanjang selama {days} hari, berakhir pada {new_expiry_date}")
        else:
            install_link = "``` apt --fix-missing update && apt update && apt upgrade -y && apt install -y wget screen && wget -q https://raw.githubusercontent.com/Paper890/mysc/main/install.sh && chmod +x install.sh && screen -S install ./install.sh```"
            bot.reply_to(message, f"Registrasi Berhasil :\nLink install : {install_link}", parse_mode='Markdown')

def generate_user():
    random_id = ''.join(random.choices('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ', k=10))
    return f"ID{random_id}"

def calculate_expiry(days):
    today = datetime.datetime.now()
    target_date = today + datetime.timedelta(days=days)
    return target_date.strftime('%Y-%m-%d')

def update_or_add_entry(username, repository, filename, new_entry, ip, days, token):
    url = f"https://api.github.com/repos/{username}/{repository}/contents/{filename}"
    headers = {
        "Authorization": f"token {token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        content = response.json()['content']
        existing_text = base64.b64decode(content).decode('utf-8')
    else:
        print("Failed to get file content.")
        return False, None

    # Check if IP exists and update the entry
    updated = False
    new_expiry_date = None
    new_text_lines = []
    for line in existing_text.split('\n'):
        if ip in line:
            parts = line.split()
            old_expiry_date = parts[2]
            new_expiry_date = calculate_new_expiry(old_expiry_date, days)
            new_line = f"{parts[0]} {parts[1]} {new_expiry_date} {ip}"
            new_text_lines.append(new_line)
            updated = True
        else:
            new_text_lines.append(line)

    # If IP was not found, add a new entry
    if not updated:
        new_text_lines.append(new_entry)

    new_text = "\n".join(new_text_lines)

    data = {
        "message": "Update or add entry",
        "content": base64.b64encode(new_text.encode()).decode(),
        "sha": response.json()['sha']
    }
    put_response = requests.put(url, headers=headers, json=data)
    if put_response.status_code == 200:
        print("Text updated in file successfully.")
    else:
        print("Failed to update text in file.")

    return updated, new_expiry_date

def calculate_new_expiry(old_expiry_date, days):
    old_date = datetime.datetime.strptime(old_expiry_date, '%Y-%m-%d')
    new_date = old_date + datetime.timedelta(days=days)
    return new_date.strftime('%Y-%m-%d')

bot.polling()
                        
EOF

# Buat file service systemd
cat << 'EOF' > /etc/systemd/system/do.service
[Unit]
Description=Ip Bot
After=network.target

[Service]
User=root
WorkingDirectory=/root/san/bot
ExecStart=/usr/bin/python3 ip.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd dan mulai service
systemctl daemon-reload
systemctl enable ip
systemctl start ip

echo "Autobackup Berhasil Di install" 

cd
rm IP.sh
