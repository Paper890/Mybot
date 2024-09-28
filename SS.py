import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
import zipfile
import threading
from datetime import datetime
import shutil
#----BOT INISIAL---#
# Initialize bot with your bot token
API_TOKEN = '7360190308:AAFCXEy6tEzRvCgzF44XzlcX3PRNV-vPkxo'
ADMIN_CHAT_ID = '576495165'  # Replace with the actual admin ChatID
bot = telebot.TeleBot(API_TOKEN)

# Database paths
DB_PATH = 'san_store.db'
BACKUP_DIR = 'backups'

user_data = {}

# Set up SQLite database
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Create tables for storing balance, rewards, referrals, and prices
cursor.execute('''CREATE TABLE IF NOT EXISTS users
                  (chat_id INTEGER PRIMARY KEY, saldo INTEGER DEFAULT 0, reward INTEGER DEFAULT 0, referrer_id INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS prices
                  (id INTEGER PRIMARY KEY, date TEXT, harga_1 INTEGER, harga_2 INTEGER)''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS pelanggan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE,
    nama TEXT,
    nomor_rekening TEXT
)
''')
conn.commit()

# Function to create a zip backup of the database
def backup_database():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = os.path.join(BACKUP_DIR, f"backup_{timestamp}.zip")
    
    with zipfile.ZipFile(zip_filename, 'w') as backup_zip:
        backup_zip.write(DB_PATH, os.path.basename(DB_PATH))
    
    return zip_filename

# Function to send the backup to the admin
def send_backup_to_admin():
    zip_filename = backup_database()
    with open(zip_filename, 'rb') as backup_file:
        bot.send_document(ADMIN_CHAT_ID, backup_file)

# Function to restore the database from a zip file
def restore_database(zip_filename):
    with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
        zip_ref.extract(os.path.basename(DB_PATH), os.path.dirname(DB_PATH))

# Schedule autobackup every 6 hours
def schedule_backup():
    while True:
        send_backup_to_admin()
        threading.Event().wait(21600)  # 6 hours in seconds

# Start the backup scheduler in a new thread
backup_thread = threading.Thread(target=schedule_backup, daemon=True)
backup_thread.start()

# Restore database when a zip file is sent
@bot.message_handler(content_types=['document'])
def handle_zip_file(message):
    if str(message.chat.id) == ADMIN_CHAT_ID and message.document.mime_type == 'application/zip':
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        zip_filename = os.path.join(BACKUP_DIR, message.document.file_name)
        
        with open(zip_filename, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        restore_database(zip_filename)
        bot.send_message(ADMIN_CHAT_ID, "Database berhasil dipulihkan dari backup.")

# Initial prices
INITIAL_HARGA_1 = 8000
INITIAL_HARGA_2 = 14000

# Function to calculate daily price based on the current date
def get_daily_prices():
    today = datetime.now().date()
    start_of_month = today.replace(day=1)

    # Calculate the number of days since the start of the month
    days_passed = (today - start_of_month).days

    # Calculate the prices
    harga_1 = max(INITIAL_HARGA_1 - (166 * days_passed), 0)
    harga_2 = max(INITIAL_HARGA_2 - (166 * days_passed), 0)

    return harga_1, harga_2

# Start command handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    referrer_id = message.text.split()[1] if len(message.text.split()) > 1 else None
    create_or_update_user(message.chat.id, referrer_id)
    saldo, reward = get_user(message.chat.id)

    # Get the daily prices
    harga_1, harga_2 = get_daily_prices()

    markup = InlineKeyboardMarkup()
    markup.row_width = 3
    markup.add(InlineKeyboardButton("SSH", callback_data="ssh"),
               InlineKeyboardButton("VMESS", callback_data="vmess"),
               InlineKeyboardButton("TROJAN", callback_data="trojan"))
    markup.add(InlineKeyboardButton("AKRAB", callback_data="akrab_button"))      
    markup.add(InlineKeyboardButton("TOPUP", callback_data="topup"),
               InlineKeyboardButton("TEMAN", callback_data="teman"))
    markup.add(InlineKeyboardButton("CAIRKAN REWARD", callback_data="cairkan_reward"))
    markup.add(InlineKeyboardButton("REKENING REWARD", callback_data="rek_reward"))

    # Only show "LIST REWARD", "ADD BALANCE", and "ADD TEXT TO FILE" to the admin
    if str(message.chat.id) == ADMIN_CHAT_ID:
        markup.add(InlineKeyboardButton("LIST REWARD", callback_data="list_reward"),
                   InlineKeyboardButton("ADD BALANCE", callback_data="add_balance"))
        markup.add(InlineKeyboardButton("ADD TEXT TO FILE", callback_data="add_text"))

    # Send the welcome message with prices
    bot.send_message(
        message.chat.id, 
        f"🔱SELAMAT BERBELANJA DI SAN STORE🔱\n-----------------------------------------\nJenis VPN.  = Premium Share VPN\nKoneksi     = 90%\nGaransi.     = Full Akun\nMasa Aktif.  = 30-60 Hari (Dari Tanggal 1)\n\nAkrab Official (Resmi)\nGaransi ✅ \nMasa Aktif = 27-30 Hari\n\nNote: Untuk Paket Akrab Tidak Menggunakan Saldo (Bayar Langsung Pas Order)\n\n💸 Saldo: {saldo}\n💰 Reward: {reward}\n\n💲 HARGA HARI INI 💲\n 1 HP  : {harga_1}\n 1 STB : {harga_2}",
        reply_markup=markup
    )

# Function to get user info from the database
def get_user(chat_id):
    cursor.execute("SELECT saldo, reward FROM users WHERE chat_id=?", (chat_id,))
    return cursor.fetchone()

# Function to create or update a user in the database
def create_or_update_user(chat_id, referrer_id=None):
    cursor.execute("INSERT OR IGNORE INTO users (chat_id, referrer_id) VALUES (?, ?)", (chat_id, referrer_id))
    conn.commit()

# Callback query handler for InlineKeyboardButton actions
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data in ["ssh", "vmess", "trojan"]:
        handle_vpn_choice(call)
    elif call.data in ["1hp_ssh", "1stb_ssh", "1hp_vmess", "1stb_vmess", "1hp_trojan", "1stb_trojan"]:
        handle_vpn_purchase(call)
    elif call.data == "akrab_button":
        # Create the inline keyboard markup
        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        markup.add(InlineKeyboardButton("MINI", callback_data="MINI"),
                   InlineKeyboardButton("BIG", callback_data="BIG"),
                   InlineKeyboardButton("JUMBO", callback_data="JUMBO"))

        # Send the AKRAB package information message
        sent_message = bot.send_message(
            call.message.chat.id,
            "💸 PAKET AKRAB RESMI (OFFICIAL) 💸\n\n"
            "🔥 AKRAB MINI\n"
            "Area 1 = 21GB\n"
            "Area 2 = 24GB\n"
            "Area 3 = 35GB\n"
            "Area 4 = 59GB\n\n"
            "Harga  : 60.000\n\n"
            "🔥 AKRAB REWARD (Big)\n"
            "Area 1 : 33,5-36,5 GB\n"
            "Area 2 : 36,5-39,5 GB\n"
            "Area 3 : 47-50 GB\n"
            "Area 4 : 71-74 GB\n\n"
            "Harga Reseller : 70.000\n\n"
            "🔥 AKRAB XXL REWARD (Jumbo)\n"
            "Area 1 : 65,5-67,5 GB\n"
            "Area 2 : 70-72 GB\n"
            "Area 3 : 83-85 GB\n"
            "Area 4 : 123-125 GB\n\n"
            "Harga : 85.000",
            reply_markup=markup
        )    

       # Store message_id in user_data for potential future edits
        user_data[call.message.chat.id] = {'message_id': sent_message.message_id}
            
    elif call.data in ["MINI", "BIG", "JUMBO"]:
        user_data[call.message.chat.id]['quota_type'] = call.data
    
    # Menghilangkan tombol dan mengubah pesan
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=user_data[call.message.chat.id]['message_id'],
            text=f"Process Order {call.data}."
        )
        bot.send_message(call.message.chat.id, "Nomor XL/Axis Kamu :")
    
    # Menyimpan data tambahan
        bot.register_next_step_handler(call.message, ask_for_number)      
        
    elif call.data.startswith("process_") or call.data.startswith("complete_"):     
         data_parts = call.data.split('_')
         chat_id = int(data_parts[1])
         message_id = int(data_parts[2])

         if call.data.startswith("process_"):
             bot.send_message(ADMIN_CHAT_ID, f"Transaksi untuk nomor {user_data[chat_id]['number']} sedang DIPROSES.")
             bot.send_message(chat_id, "Transaksi Anda sedang diproses.")
    
         elif call.data.startswith("complete_"):
             bot.send_message(ADMIN_CHAT_ID, f"Transaksi untuk nomor {user_data[chat_id]['number']} telah SELESAI.")
             bot.send_message(chat_id, "Transaksi Anda telah selesai. Terima kasih!")
        
             # Menghapus pesan yang sudah SELESAI dari admin
             if 'admin_message_id' in user_data[chat_id]:
                 try:
                     bot.delete_message(ADMIN_CHAT_ID, user_data[chat_id]['admin_message_id'])
                 except telebot.apihelper.ApiException as e:
                     print(f"Error deleting message: {e}")
                 del user_data[chat_id]['admin_message_id']
            
    elif call.data == 'topup':
        bot.answer_callback_query(call.id, "Masukkan jumlah nominal top up:")
        bot.send_message(call.message.chat.id, "Silakan masukkan nominal yang ingin Anda top up:")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_topup)
    elif call.data == "teman":
        ref_link = f"https://t.me/sanstore_bot?start={call.message.chat.id}"
        bot.send_message(call.message.chat.id, f"Berikut Adalah link Referall Anda:\n{ref_link}\nAnda akan menerima 20% dari setiap top up yang dilakukan oleh teman yang Anda undang!.\n\nPencairan Reward Dilakukan Setiap Akhir bulan")
        
        # Show list of invited friends
        cursor.execute("SELECT chat_id FROM users WHERE referrer_id = ?", (call.message.chat.id,))
        friends = cursor.fetchall()
        if friends:
            response = "Teman yang sudah Anda undang:\n"
            for friend in friends:
                response += f"Chat ID: {friend[0]}\n"
            bot.send_message(call.message.chat.id, response)
        else:
            bot.send_message(call.message.chat.id, "Belum ada teman yang diundang.")
    elif call.data == "list_reward":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:
            cursor.execute("SELECT chat_id, reward FROM users WHERE reward > 0")
            rewards = cursor.fetchall()
            if rewards:
                response = "Daftar pengguna dengan reward:\n"
                for r in rewards:
                    response += f"Chat ID: {r[0]}, Reward: {r[1]}\n"
                bot.send_message(call.message.chat.id, response)
            else:
                bot.send_message(call.message.chat.id, "Belum ada pengguna dengan reward.")
    elif call.data == "add_balance":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:
            bot.send_message(call.message.chat.id, "Masukkan Chat ID pengguna yang ingin Anda tambahkan saldo, diikuti oleh jumlah saldo yang ingin ditambahkan, dipisahkan dengan spasi. Contoh: 123456789 50000")
            bot.register_next_step_handler(call.message, process_add_balance)
    elif call.data == "cairkan_reward":
        saldo, reward = get_user(call.message.chat.id)
        if reward > 0:
            bot.send_message(call.message.chat.id, f"Permintaan pencairan reward sebesar {reward} telah dikirim ke admin. Pastikan Kamu Telah Mengisi Rekening Reward")
            bot.send_message(ADMIN_CHAT_ID, f"Permintaan pencairan reward:\nChat ID: `{call.message.chat.id}`\nNominal: `{reward}`", parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "Reward Anda saat ini adalah 0. Tidak ada yang bisa dicairkan.")
    elif call.data == 'rek_reward':
        # Periksa apakah user sudah punya data rekening
        cursor.execute('SELECT nama, nomor_rekening FROM pelanggan WHERE chat_id = ?', (call.message.chat.id,))
        data = cursor.fetchone()
        
        if data:
            # Jika data sudah ada, tampilkan datanya dengan opsi edit
            response = f"Data Rekening Anda:\n\nNama: {data[0]}\nNo Rekening: {data[1]}\n\n"
            response += "Klik tombol di bawah jika ingin mengedit data rekening Anda."
            
            markup = InlineKeyboardMarkup()
            markup.row_width = 3
            markup.add(InlineKeyboardButton("EDIT NAMA", callback_data="edit_nama"),
                       InlineKeyboardButton("EDIT NOMOR REK", callback_data="edit_rekening"))
            
            bot.send_message(call.message.chat.id, response, reply_markup=markup)
        else:
            # Jika data belum ada, mulai proses input rekening
            msg = bot.send_message(call.message.chat.id, 'Masukkan nama pemilik rekening:')
            bot.register_next_step_handler(msg, get_nama)

    elif call.data == 'edit_nama':
        msg = bot.send_message(call.message.chat.id, 'Masukkan nama baru:')
        bot.register_next_step_handler(msg, update_nama)
    elif call.data == 'edit_rekening':
        msg = bot.send_message(call.message.chat.id, 'Masukkan nomor rekening baru:')
        bot.register_next_step_handler(msg, update_rekening)
  
    elif call.data == "add_text":
        if str(call.message.chat.id) == ADMIN_CHAT_ID:
            bot.send_message(call.message.chat.id, "Masukkan nama file (misal: ssh.txt) dan teks yang ingin Anda masukkan ke dalam file, dipisahkan oleh tanda '|'. Contoh: ssh.txt|Ini adalah teks.")
            bot.register_next_step_handler(call.message, process_add_text)

# Function to handle VPN choice
def handle_vpn_choice(call):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    vpn_type = call.data.upper()
    markup.add(
        InlineKeyboardButton("HP 2 BULAN", callback_data=f"1hp_{call.data}"),
        InlineKeyboardButton("STB 2 BULAN", callback_data=f"1stb_{call.data}")
    )
    bot.send_message(call.message.chat.id, "Pilih Masa Aktif Yang Diinginkan :", reply_markup=markup)

# Function to handle VPN purchase
def handle_vpn_purchase(call):
    saldo, reward = get_user(call.message.chat.id)
    harga_1, harga_2 = get_daily_prices()
    
    if "1hp" in call.data:
        amount_to_deduct = harga_1
    elif "1stb" in call.data:
        amount_to_deduct = harga_2

    if saldo >= amount_to_deduct:
        new_saldo = saldo - amount_to_deduct
        cursor.execute("UPDATE users SET saldo = ? WHERE chat_id = ?", (new_saldo, call.message.chat.id))
        conn.commit()

        vpn_type = call.data.split('_')[-1]  # ssh, vmess, or trojan
        file_path = f"/root/san/bot/{vpn_type}.txt"

        try:
            with open(file_path, 'r') as file:
                vpn_info = file.read()
                bot.send_message(call.message.chat.id, vpn_info)
                bot.send_message(call.message.chat.id, f"Pembayaran Sukses sebanyak {amount_to_deduct}. Sisa saldo: {new_saldo}")
        except FileNotFoundError:
            bot.send_message(call.message.chat.id, "File VPN tidak ditemukan.")
    else:
        bot.send_message(call.message.chat.id, "Saldo Anda tidak mencukupi untuk pembelian ini.")

# Fungsi untuk memproses nominal top up dari pengguna
def process_topup(message):
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
        bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"Permintaan Top Up\nChat ID: `{chat_id}`\nNominal: Rp `{nominal:,}`", parse_mode="Markdown")

        # Beri tahu pengguna bahwa permintaan mereka sedang diproses
        bot.send_message(chat_id, "Permintaan top up Anda telah dikirim dan sedang diproses.")

    else:
        bot.send_message(chat_id, "Silakan kirimkan foto bukti transfer")
        bot.register_next_step_handler_by_chat_id(chat_id, process_transfer_proof)
        
# Process adding balance by admin
def process_add_balance(message):
    try:
        chat_id, amount = map(int, message.text.split())
        cursor.execute("SELECT saldo FROM users WHERE chat_id = ?", (chat_id,))
        saldo = cursor.fetchone()

        if saldo:
            new_saldo = saldo[0] + amount
            cursor.execute("UPDATE users SET saldo = ? WHERE chat_id = ?", (new_saldo, chat_id))
            conn.commit()
            bot.send_message(chat_id, f"Saldo Anda telah ditambahkan sebesar {amount}. Saldo saat ini: {new_saldo}")

            # Handle referral reward if the user was referred
            cursor.execute("SELECT referrer_id FROM users WHERE chat_id = ?", (chat_id,))
            referrer_id = cursor.fetchone()[0]
            if referrer_id:
                reward_amount = int(amount * 0.1) 
                cursor.execute("UPDATE users SET reward = reward + ? WHERE chat_id = ?", (reward_amount, referrer_id))
                conn.commit()
                bot.send_message(referrer_id, f"Anda menerima reward sebesar {reward_amount} dari top up teman Anda. Reward saat ini: {reward_amount}")

            bot.send_message(ADMIN_CHAT_ID, f"Saldo pengguna dengan Chat ID {chat_id} telah ditambahkan sebesar {amount}.")
        else:
            bot.send_message(ADMIN_CHAT_ID, "Chat ID tidak ditemukan. Silakan coba lagi.")
    except (ValueError, IndexError):
        bot.send_message(ADMIN_CHAT_ID, "Format tidak valid. Silakan masukkan Chat ID dan jumlah saldo yang benar, dipisahkan dengan spasi.")
        
# Process adding text to file by admin
def process_add_text(message):
    try:
        file_name, text = message.text.split('|', 1)
        directory = "/root/san/bot/"

        # Ensure the directory exists
        if not os.path.exists(directory):
            os.makedirs(directory)

        file_path = os.path.join(directory, file_name.strip())

        # Write the text to the file
        with open(file_path, 'a') as file:
            file.write(text.strip() + "\n")

        bot.send_message(ADMIN_CHAT_ID, f"Teks telah berhasil ditambahkan ke file {file_name}.")
    except ValueError:
        bot.send_message(ADMIN_CHAT_ID, "Format tidak valid. Pastikan Anda memasukkan nama file dan teks, dipisahkan oleh tanda '|'.")
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"Terjadi kesalahan: {e}")
        
  # Function to process reward withdrawal by admin
@bot.message_handler(commands=['acc'])
def acc_cairkan_reward(message):
    try:
        parts = message.text.split()
        chat_id = int(parts[1])

        # Reset the reward to 0 after admin approval
        cursor.execute("UPDATE users SET reward = 0 WHERE chat_id = ?", (chat_id,))
        conn.commit()

        bot.send_message(message.chat.id, f"Permintaan pencairan reward untuk Chat ID {chat_id} telah disetujui.")
        bot.send_message(chat_id, "Permintaan Pencairan Reward Telah Dikirim Ke Rekening mu")
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "Format tidak valid. Pastikan Anda memasukkan Chat ID yang benar.")
        
# Fungsi untuk meminta nomor yang akan diisi
def ask_for_number(message):
    user_data[message.chat.id]['number'] = message.text
    bot.send_message(message.chat.id, "Silahkan Lakukan Pembayaran Ke DANA/GOPAY : 082292615651\nAtau Melalui Qris : https://tinyurl.com/SanQris\n\nKirim Bukti Screenshot Transfer Jika selesai Dan Pesananmu Akan Diteruskan Ke Admin")

# Callback handler untuk admin yang memproses transaksi
@bot.callback_query_handler(func=lambda call: call.data.startswith("process_") or call.data.startswith("complete_"))
def handle_admin_action(call):
    data_parts = call.data.split('_')
    chat_id = int(data_parts[1])
    message_id = int(data_parts[2])

    if call.data.startswith("process_"):
        bot.send_message(ADMIN_CHAT_ID, f"Transaksi untuk nomor {user_data[chat_id]['number']} sedang DIPROSES.")
        bot.send_message(chat_id, "Transaksi Anda sedang diproses.")
    
    elif call.data.startswith("complete_"):
        bot.send_message(ADMIN_CHAT_ID, f"Transaksi untuk nomor {user_data[chat_id]['number']} telah SELESAI.")
        bot.send_message(chat_id, "Transaksi Anda telah selesai. Terima kasih!")
        
        # Menghapus pesan yang sudah SELESAI dari admin
        if 'admin_message_id' in user_data[chat_id]:
            try:
                bot.delete_message(ADMIN_CHAT_ID, user_data[chat_id]['admin_message_id'])
            except telebot.apihelper.ApiException as e:
                print(f"Error deleting message: {e}")
            del user_data[chat_id]['admin_message_id']
            
 # Handler untuk menerima bukti pembayaran
@bot.message_handler(content_types=['photo'])
def handle_payment(message):
    if message.chat.id in user_data and 'number' in user_data[message.chat.id]:
        photo_id = message.photo[-1].file_id
        user_data[message.chat.id]['payment_proof'] = photo_id
        
        # Notifikasi ke admin
        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        markup.add(InlineKeyboardButton("DIPROSES", callback_data=f"process_{message.chat.id}_{message.message_id}"),
                   InlineKeyboardButton("SELESAI", callback_data=f"complete_{message.chat.id}_{message.message_id}"))

        sent_message = bot.send_photo(ADMIN_CHAT_ID, photo_id, caption=f"Transaksi baru:\nKuota: {user_data[message.chat.id]['quota_type']}\nNomor: {user_data[message.chat.id]['number']}", reply_markup=markup)
        # Menyimpan ID pesan untuk pengeditan di kemudian hari
        user_data[message.chat.id]['admin_message_id'] = sent_message.message_id

        bot.send_message(message.chat.id, "Terima kasih! Pembayaran Anda telah diterima dan akan segera diproses.")
    else:
        bot.send_message(message.chat.id, "Anda belum memasukkan nomor yang akan diisi. Silakan mulai lagi dengan /start.")
            

# Fungsi untuk mendapatkan nama dari pengguna
def get_nama(message):
    nama = message.text
    msg = bot.send_message(message.chat.id, 'Masukkan nomor rekening. Nomor DANA/GOPAY:')
    bot.register_next_step_handler(msg, get_nomor_rekening, nama)

# Fungsi untuk mendapatkan nomor rekening dan menyimpan ke database
def get_nomor_rekening(message, nama):
    nomor_rekening = message.text

    # Simpan atau update data ke SQLite
    cursor.execute('INSERT OR REPLACE INTO pelanggan (chat_id, nama, nomor_rekening) VALUES (?, ?, ?)', 
                   (message.chat.id, nama, nomor_rekening))
    conn.commit()
    
    bot.send_message(message.chat.id, 'Data rekening Anda telah disimpan!')

# Fungsi untuk menampilkan data rekening kepada admin secara perorangan
@bot.message_handler(commands=['lihat_data'])
def lihat_data_rekening(message):
    if str(message.chat.id) == ADMIN_CHAT_ID:
        try:
            # Mengambil ChatID dari perintah /lihat_data {ChatID}
            command_parts = message.text.split()
            if len(command_parts) != 2:
                bot.send_message(message.chat.id, 'Gunakan format: /lihat_data {ChatID}')
                return
            
            target_chat_id = command_parts[1]
            
            # Ambil data rekening dari database berdasarkan ChatID yang diberikan
            cursor.execute('SELECT nama, nomor_rekening FROM pelanggan WHERE chat_id = ?', (target_chat_id,))
            data = cursor.fetchone()
            
            if data:
                response = f"Data Rekening Pelanggan (ChatID: {target_chat_id}):\n\nNama: {data[0]}\nNo Rekening: {data[1]}"
                bot.send_message(message.chat.id, response)
            else:
                bot.send_message(message.chat.id, f"Tidak ada data rekening untuk ChatID: {target_chat_id}")
        
        except Exception as e:
            bot.send_message(message.chat.id, f"Terjadi kesalahan: {str(e)}")
    else:
        bot.send_message(message.chat.id, 'Anda tidak memiliki izin untuk melihat data ini.')

# Fungsi untuk mengupdate nama pelanggan
def update_nama(message):
    nama_baru = message.text
    
    # Update nama di database
    cursor.execute('UPDATE pelanggan SET nama = ? WHERE chat_id = ?', (nama_baru, message.chat.id))
    conn.commit()
    
    bot.send_message(message.chat.id, 'Nama rekening Anda telah diperbarui!')

# Fungsi untuk mengupdate nomor rekening pelanggan
def update_rekening(message):
    nomor_rekening_baru = message.text
    
    # Update nomor rekening di database
    cursor.execute('UPDATE pelanggan SET nomor_rekening = ? WHERE chat_id = ?', (nomor_rekening_baru, message.chat.id))
    conn.commit()
    
    bot.send_message(message.chat.id, 'Nomor rekening Anda telah diperbarui!')

# Start polling
bot.polling()
