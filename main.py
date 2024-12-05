import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import threading
from datetime import datetime
import json
import os
import pandas as pd
from plyer import notification
import configparser
from binance.client import Client
from binance.exceptions import BinanceAPIException
from telegram_notifier import TelegramNotifier
import asyncio
from telegram.ext import Application, CommandHandler

class BinancePNLTracker:
    def __init__(self):
        # Config yükleme
        self.config = self.load_config()
        
        # Binance API client'ı başlat
        try:
            self.client = Client(
                self.config.get('API_KEY', ''),
                self.config.get('API_SECRET', '')
            )
            test = self.client.futures_account()
            print("API Bağlantısı başarılı!")
            print("Futures Pozisyonları:", [p for p in test['positions'] if float(p['positionAmt']) != 0])
            self.api_connected = True
        except Exception as e:
            self.api_connected = False
            print(f"API bağlantı hatası: {e}")
        
        # GUI setup
        self.root = tk.Tk()
        self.root.title("Binance PNL Takipçisi")
        self.root.geometry("1000x600")
        
        # Veri listeleri
        self.pnl_history = []
        self.time_history = []
        self.last_pnl = 0
        self.high_pnl = float('-inf')  # En düşük olası değer
        self.low_pnl = float('inf')    # En yüksek olası değer
        self.position_pnl_history = {}
        self.tracking = False
        self.active_alarms = []
        
        # İstatistik değişkenleri
        self.current_pnl_var = tk.StringVar(value="Mevcut PNL: --")
        self.high_pnl_var = tk.StringVar(value="En Yüksek: --")
        self.low_pnl_var = tk.StringVar(value="En Düşük: --")
        self.timestamp_var = tk.StringVar(value="Son Güncelleme: --")
        
        # GUI elemanlarını oluştur
        self.setup_theme()
        self.create_gui()
        self.create_futures_tab()
        self.create_alarm_tab()
        
        # Alarm kontrolü için thread
        self.alarm_thread = threading.Thread(target=self.alarm_loop, daemon=True)
        self.alarm_thread.start()
        
        # Telegram entegrasyonu
        try:
            telegram_token = self.config.get('TelegramToken', '')
            telegram_chat_id = self.config.get('TelegramChatID', '')
            
            if telegram_token and telegram_chat_id:
                self.telegram = TelegramNotifier(telegram_token, telegram_chat_id)
                self.telegram.app = self
                asyncio.run(self.telegram.send_message("🟢 PNL Tracker başlatıldı!\n\nKomutları görmek için /help yazabilirsiniz."))
                print("Telegram bağlantısı başarılı!")
            else:
                print("Telegram token veya chat ID bulunamadı!")
        except Exception as e:
            print(f"Telegram bağlantı hatası: {e}")

    def load_config(self):
        config = {}
        config_file = 'config.ini'
        
        if os.path.exists(config_file):
            parser = configparser.ConfigParser()
            parser.read(config_file)
            if 'DEFAULT' in parser:
                config['API_KEY'] = parser['DEFAULT'].get('API_KEY', '')
                config['API_SECRET'] = parser['DEFAULT'].get('API_SECRET', '')
                config['URL'] = parser['DEFAULT'].get('URL', '')
                config['CheckInterval'] = parser['DEFAULT'].get('CheckInterval', '30')
                config['AlertThreshold'] = parser['DEFAULT'].get('AlertThreshold', '5')
                config['TelegramToken'] = parser['DEFAULT'].get('TelegramToken', '')
                config['TelegramChatID'] = parser['DEFAULT'].get('TelegramChatID', '')
        return config

    def setup_theme(self):
        bg_color = '#1E2026'
        fg_color = '#EAECEF'
        accent_color = '#F0B90B'
        button_bg = '#2B2F36'
        
        style = ttk.Style()
        style.theme_use('default')
        
        self.root.configure(bg=bg_color)
        
        style.configure('TFrame', background=bg_color)
        style.configure('TLabelframe', background=bg_color, foreground=fg_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color)
        style.configure('TButton', background=button_bg, foreground=fg_color)
        style.configure('TEntry', fieldbackground=button_bg, foreground=fg_color)
        style.configure('TNotebook', background=bg_color, borderwidth=0)
        style.configure('TNotebook.Tab', background=button_bg, foreground=fg_color, padding=[10, 2])
        
        style.configure('Treeview',
                       background=button_bg,
                       foreground=fg_color,
                       fieldbackground=button_bg)
        style.configure('Treeview.Heading',
                       background=button_bg,
                       foreground=fg_color)

    def create_gui(self):
        # Notebook oluştur
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Ana sekme
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Genel PNL")
        
        # Kontrol Paneli
        control_frame = ttk.LabelFrame(self.main_tab, text="Kontrol Paneli", padding="5")
        control_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Kontrol aralığı
        interval_frame = ttk.Frame(control_frame)
        interval_frame.pack(fill=tk.X, pady=2)
        ttk.Label(interval_frame, text="Kontrol Aralığı (saniye):").pack(side=tk.LEFT)
        self.interval_var = tk.StringVar(value="3")
        ttk.Entry(interval_frame, textvariable=self.interval_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Bildirim eşiği
        threshold_frame = ttk.Frame(control_frame)
        threshold_frame.pack(fill=tk.X, pady=2)
        ttk.Label(threshold_frame, text="Bildirim Eşiği (USDT):").pack(side=tk.LEFT)
        self.threshold_var = tk.StringVar(value="5")
        ttk.Entry(threshold_frame, textvariable=self.threshold_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Kontrol butonları
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(pady=5)
        
        self.start_button = ttk.Button(button_frame, text="Başlat", command=self.start_tracking_thread)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Durdur", command=self.stop_tracking, state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Telegram test butonu ekle
        self.test_telegram_button = ttk.Button(button_frame, text="Telegram Test", command=self.test_telegram)
        self.test_telegram_button.pack(side=tk.LEFT, padx=5)
        
        # İstatistik Paneli
        stats_frame = ttk.LabelFrame(self.main_tab, text="İstatistikler", padding="5")
        stats_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # İstatistik etiketleri
        self.current_pnl_var = tk.StringVar(value="Mevcut PNL: --")
        self.high_pnl_var = tk.StringVar(value="En Yüksek: --")
        self.low_pnl_var = tk.StringVar(value="En Düşük: --")
        self.timestamp_var = tk.StringVar(value="Son Güncelleme: --")
        
        ttk.Label(stats_frame, textvariable=self.current_pnl_var).pack(pady=1)
        ttk.Label(stats_frame, textvariable=self.high_pnl_var).pack(pady=1)
        ttk.Label(stats_frame, textvariable=self.low_pnl_var).pack(pady=1)
        ttk.Label(stats_frame, textvariable=self.timestamp_var).pack(pady=1)
        
        # Grafik frame'i
        self.graph_frame = ttk.Frame(self.main_tab)
        self.graph_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Grafik oluştur
        self.create_graph()

    def create_futures_tab(self):
        """Futures sekmesini oluştur"""
        self.futures_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.futures_tab, text="Pozisyonlar")
        
        # Futures pozisyonları için tablo
        self.futures_tree = ttk.Treeview(self.futures_tab)
        
        # Tablo sütunları
        column_widths = {
            'Symbol': 100,
            'Size': 100,
            'Entry Price': 100,
            'Mark Price': 100,
            'PNL': 100,
            'ROE%': 100,
            'Leverage': 80
        }
        
        self.futures_tree['columns'] = list(column_widths.keys())
        self.futures_tree['show'] = 'headings'
        
        for col, width in column_widths.items():
            self.futures_tree.heading(col, text=col)
            self.futures_tree.column(col, width=width)
        
        self.futures_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def update_futures_data(self):
        """Futures pozisyonlarını güncelle"""
        try:
            # Tablo içeriğini temizle
            for item in self.futures_tree.get_children():
                self.futures_tree.delete(item)
            
            # Aktif pozisyonları al
            positions = [p for p in self.client.futures_position_information() if float(p['positionAmt']) != 0]
            
            for pos in positions:
                # Mark fiyatını al
                mark_price = float(self.client.futures_mark_price(symbol=pos['symbol'])['markPrice'])
                
                # ROE hesapla
                isolated_wallet = float(pos.get('isolatedWallet', 0))
                roe = float(pos['unRealizedProfit']) / isolated_wallet * 100 if isolated_wallet != 0 else 0
                
                # Pozisyon verilerini hazırla
                position_data = {
                    'symbol': pos['symbol'],
                    'pnl': float(pos['unRealizedProfit']),
                    'roe': roe,
                    'mark_price': mark_price
                }
                
                # Telegram bildirimi gönder (eğer PNL değişimi önemliyse)
                if hasattr(self, 'telegram'):
                    symbol = pos['symbol']
                    if symbol not in self.position_pnl_history:
                        self.position_pnl_history[symbol] = float(pos['unRealizedProfit'])
                    else:
                        old_pnl = self.position_pnl_history[symbol]
                        new_pnl = float(pos['unRealizedProfit'])
                        pnl_change = abs(new_pnl - old_pnl)
                        
                        # PNL değişimi belirlenen eşiği geçtiyse bildirim gönder
                        if pnl_change >= float(self.threshold_var.get()):
                            self.telegram.send_position_update(position_data)
                            self.position_pnl_history[symbol] = new_pnl
                
                # Tabloya ekle
                self.futures_tree.insert('', 'end', values=(
                    pos['symbol'],
                    f"{float(pos['positionAmt']):.3f}",
                    f"{float(pos['entryPrice']):.4f}",
                    f"{mark_price:.4f}",
                    f"{float(pos['unRealizedProfit']):.2f}",
                    f"{roe:.2f}%",
                    pos.get('leverage', 'N/A')
                ))
            
        except Exception as e:
            print(f"Futures verileri güncellenirken hata: {e}")

    def start_tracking(self):
        while self.tracking:
            try:
                account = self.client.futures_account()
                total_pnl = float(account['totalUnrealizedProfit'])
                
                # İstatistikleri güncelle
                self.update_stats(total_pnl)
                
                # Grafik verilerini güncelle
                current_time = datetime.now()
                self.time_history.append(current_time)
                self.pnl_history.append(total_pnl)
                
                # Son 50 veriyi tut
                if len(self.pnl_history) > 50:
                    self.pnl_history.pop(0)
                    self.time_history.pop(0)
                
                # Diğer güncellemeler
                self.update_futures_data()
                self.update_symbol_list()
                
                time.sleep(float(self.interval_var.get()))
                
            except Exception as e:
                print(f"Takip sırasında hata: {e}")
                time.sleep(5)

    def update_stats(self, total_pnl):
        """İstatistikleri güncelle"""
        # En yüksek ve en düşük değerleri güncelle
        self.high_pnl = max(self.high_pnl, total_pnl)
        self.low_pnl = min(self.low_pnl, total_pnl)
        
        # İstatistik etiketlerini güncelle
        self.current_pnl_var.set(f"Mevcut PNL: {total_pnl:.2f} USDT")
        self.high_pnl_var.set(f"En Yüksek: {self.high_pnl:.2f} USDT")
        self.low_pnl_var.set(f"En Düşük: {self.low_pnl:.2f} USDT")
        self.timestamp_var.set(f"Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}")
        
        # Grafik verilerini güncelle
        current_time = datetime.now()
        self.time_history.append(current_time)
        self.pnl_history.append(total_pnl)
        
        # Son 50 veriyi tut
        if len(self.pnl_history) > 50:
            self.pnl_history.pop(0)
            self.time_history.pop(0)
        
        # Grafiği güncelle
        self.update_graph()

    def create_alarm_tab(self):
        """Alarm sekmesini oluştur"""
        self.alarm_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.alarm_tab, text="Alarmlar")
        
        # Alarm kontrol frame
        control_frame = ttk.LabelFrame(self.alarm_tab, text="Alarm Ayarları", padding="10")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Symbol seçimi
        symbol_frame = ttk.Frame(control_frame)
        symbol_frame.pack(fill=tk.X, pady=5)
        ttk.Label(symbol_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        self.alarm_symbol_var = tk.StringVar()
        self.symbol_combo = ttk.Combobox(symbol_frame, textvariable=self.alarm_symbol_var)
        self.symbol_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # İlk yüklemede pozisyonları al
        positions = [p for p in self.client.futures_position_information() if float(p['positionAmt']) != 0]
        symbols = [p['symbol'] for p in positions]
        self.symbol_combo['values'] = symbols
        
        # PNL hedefi
        target_frame = ttk.Frame(control_frame)
        target_frame.pack(fill=tk.X, pady=5)
        ttk.Label(target_frame, text="Hedef PNL (USDT):").pack(side=tk.LEFT, padx=5)
        self.target_pnl_var = tk.StringVar()
        ttk.Entry(target_frame, textvariable=self.target_pnl_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Alarm tipi
        type_frame = ttk.Frame(control_frame)
        type_frame.pack(fill=tk.X, pady=5)
        ttk.Label(type_frame, text="Alarm Tipi:").pack(side=tk.LEFT, padx=5)
        self.alarm_type_var = tk.StringVar(value="Üzeri")
        ttk.Radiobutton(type_frame, text="Üzeri", value="Üzeri", variable=self.alarm_type_var).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Altı", value="Altı", variable=self.alarm_type_var).pack(side=tk.LEFT, padx=5)
        
        # Alarm ekle butonu
        ttk.Button(control_frame, text="Alarm Ekle", command=self.add_alarm).pack(pady=10)
        
        # Aktif alarmlar listesi
        self.alarms_frame = ttk.LabelFrame(self.alarm_tab, text="Aktif Alarmlar", padding="10")
        self.alarms_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Alarmlar için Treeview
        columns = ('Symbol', 'Hedef PNL', 'Tip', 'Durum')
        self.alarms_tree = ttk.Treeview(self.alarms_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.alarms_tree.heading(col, text=col)
            self.alarms_tree.column(col, width=100)
        
        self.alarms_tree.pack(fill=tk.BOTH, expand=True)
        
        # Alarm silme butonu
        ttk.Button(self.alarms_frame, text="Seçili Alarmı Sil", command=self.delete_alarm).pack(pady=5)

    def add_alarm(self):
        """Yeni alarm ekle"""
        try:
            symbol = self.alarm_symbol_var.get()
            target_pnl = float(self.target_pnl_var.get())
            alarm_type = self.alarm_type_var.get()
            
            if not symbol or not target_pnl:
                messagebox.showerror("Hata", "Lütfen tüm alanları doldurun!")
                return
            
            alarm = {
                'symbol': symbol,
                'target_pnl': target_pnl,
                'type': alarm_type,
                'active': True
            }
            
            self.active_alarms.append(alarm)
            self.alarms_tree.insert('', 'end', values=(
                symbol,
                f"{target_pnl:.2f} USDT",
                alarm_type,
                "Aktif"
            ))
            
            self.target_pnl_var.set("")
            
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir PNL değeri girin!")

    def delete_alarm(self):
        """Seçili alarmı sil"""
        selected_item = self.alarms_tree.selection()
        if selected_item:
            index = self.alarms_tree.index(selected_item)
            self.active_alarms.pop(index)
            self.alarms_tree.delete(selected_item)

    def check_alarms(self):
        """Alarmları kontrol et"""
        try:
            positions = [p for p in self.client.futures_position_information() if float(p['positionAmt']) != 0]
            
            for alarm in self.active_alarms:
                if not alarm['active']:
                    continue
                    
                for pos in positions:
                    if pos['symbol'] == alarm['symbol']:
                        current_pnl = float(pos['unRealizedProfit'])
                        
                        if (alarm['type'] == "Üzeri" and current_pnl >= alarm['target_pnl']) or \
                           (alarm['type'] == "Altı" and current_pnl <= alarm['target_pnl']):
                            # Masaüstü bildirimi
                            notification.notify(
                                title='PNL Alarmı!',
                                message=f"{alarm['symbol']} pozisyonu için {alarm['target_pnl']} USDT hedefine ulaşıldı!\nMevcut PNL: {current_pnl:.2f} USDT",
                                timeout=10
                            )
                            
                            # Telegram bildirimi
                            if hasattr(self, 'telegram'):
                                self.telegram.send_pnl_alert(
                                    symbol=alarm['symbol'],
                                    current_pnl=current_pnl,
                                    target_pnl=alarm['target_pnl'],
                                    alarm_type=alarm['type']
                                )
                            
                            alarm['active'] = False
                            
                            for item in self.alarms_tree.get_children():
                                if self.alarms_tree.item(item)['values'][0] == alarm['symbol']:
                                    values = list(self.alarms_tree.item(item)['values'])
                                    values[3] = "Tetiklendi"
                                    self.alarms_tree.item(item, values=values)
                            break
                            
        except Exception as e:
            print(f"Alarm kontrolü sırasında hata: {e}")

    def alarm_loop(self):
        """Alarm kontrolü yapan döngü"""
        while True:
            if self.tracking:
                self.check_alarms()
            time.sleep(1)

    def cleanup(self):
        """Uygulama kapatılırken temizlik yap"""
        try:
            if hasattr(self, 'tracking'):
                self.tracking = False
            if hasattr(self, 'telegram'):
                self.telegram.cleanup()
        except Exception as e:
            print(f"Cleanup hatası: {e}")

    def run(self):
        self.root.mainloop()

    def update_symbol_list(self):
        """Aktif pozisyonların symbol listesini güncelle"""
        try:
            positions = [p for p in self.client.futures_position_information() if float(p['positionAmt']) != 0]
            symbols = [p['symbol'] for p in positions]
            self.symbol_combo['values'] = symbols
            
            if self.alarm_symbol_var.get() not in symbols:
                self.alarm_symbol_var.set('')
        except Exception as e:
            print(f"Symbol listesi güncellenirken hata: {e}")

    def start_tracking_thread(self):
        """GUI'den çağrılacak metod"""
        self.tracking = True
        self.start_button['state'] = 'disabled'
        self.stop_button['state'] = 'normal'
        
        self.tracker_thread = threading.Thread(target=self.start_tracking)
        self.tracker_thread.daemon = True
        self.tracker_thread.start()

    def stop_tracking(self):
        """Takibi durdur"""
        self.tracking = False
        self.start_button['state'] = 'normal'
        self.stop_button['state'] = 'disabled'

    def create_graph(self):
        """Ana PNL grafiğini oluştur"""
        plt.style.use('dark_background')
        self.figure, self.ax = plt.subplots(figsize=(8, 4))
        self.figure.patch.set_facecolor('#1E2026')
        self.ax.set_facecolor('#1E2026')
        
        # Grafik çizgi rengi ve grid ayarları
        self.ax.grid(True, color='#2B2F36')
        self.ax.tick_params(colors='#EAECEF')
        
        for spine in self.ax.spines.values():
            spine.set_color('#2B2F36')
        
        self.canvas = FigureCanvasTkAgg(self.figure, self.graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_graph(self):
        """PNL grafiğini güncelle"""
        try:
            self.ax.clear()
            if len(self.pnl_history) > 0:
                # Grafik stilini ayarla
                self.ax.grid(True, color='#2B2F36')
                self.ax.tick_params(colors='#EAECEF')
                
                # Veriyi çiz
                self.ax.plot(self.time_history, self.pnl_history, color='#F0B90B', linewidth=2)
                
                # Başlıkları ayarla
                self.ax.set_title('PNL Değişimi', color='#EAECEF', pad=10)
                self.ax.set_xlabel('Zaman', color='#EAECEF', labelpad=10)
                self.ax.set_ylabel('PNL (USDT)', color='#EAECEF', labelpad=10)
                
                # X ekseni format
                self.ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%H:%M:%S'))
                self.ax.tick_params(axis='x', rotation=45)
                
                # Layout düzenle
                self.figure.tight_layout()
                
                # Grafiği yenile
                self.canvas.draw_idle()
                
        except Exception as e:
            print(f"Grafik güncellenirken hata: {e}")

    def test_telegram(self):
        """Telegram bağlantısını test et"""
        try:
            if hasattr(self, 'telegram'):
                success = self.telegram.send_message(" Test mesajı - PNL Tracker çalışıyor!")
                if success:
                    messagebox.showinfo("Başarılı", "Telegram test mesajı gönderildi!")
                else:
                    messagebox.showerror("Hata", "Telegram mesajı gönderilemedi!")
            else:
                messagebox.showerror("Hata", "Telegram bağlantısı bulunamadı!")
        except Exception as e:
            messagebox.showerror("Hata", f"Telegram testi sırasında hata: {e}")

    def handle_commands(self):
        """Telegram komutlarını dinle ve işle"""
        while True:
            try:
                updates = self.bot.get_updates(offset=self.last_update_id)
                for update in updates:
                    if self.last_update_id is None or update.update_id > self.last_update_id:
                        self.last_update_id = update.update_id + 1
                        
                        if update.message and update.message.text:
                            text = update.message.text
                            
                            # /pnl komutu - güncel PNL durumu
                            if text == '/pnl':
                                if hasattr(self, 'app'):
                                    try:
                                        account = self.app.client.futures_account()
                                        total_pnl = float(account['totalUnrealizedProfit'])
                                        
                                        message = f"""📊 Güncel PNL Durumu:
💰 Toplam PNL: {total_pnl:.2f} USDT
📈 En Yüksek: {self.app.high_pnl:.2f} USDT
📉 En Düşük: {self.app.low_pnl:.2f} USDT
⏰ Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}"""
                                        self.send_message(message)
                                    except Exception as e:
                                        self.send_message(f"❌ PNL bilgisi alınırken hata: {str(e)}")

                            # /positions komutu - tüm pozisyonları listele
                            elif text == '/positions':
                                if hasattr(self, 'app'):
                                    try:
                                        positions = [p for p in self.app.client.futures_position_information() if float(p['positionAmt']) != 0]
                                        
                                        if not positions:
                                            self.send_message("❌ Aktif pozisyon bulunamadı!")
                                            continue
                                        
                                        total_pnl = 0
                                        messages = []
                                        
                                        for pos in positions:
                                            symbol = pos['symbol']
                                            pnl = float(pos['unRealizedProfit'])
                                            total_pnl += pnl
                                            notional = float(pos['notional'])
                                            initial_margin = float(pos['isolatedWallet'])
                                            roi = (pnl / initial_margin * 100) if initial_margin > 0 else 0
                                            mark_price = float(self.app.client.futures_mark_price(symbol=symbol)['markPrice'])
                                            
                                            message = f"""🔍 {symbol} Pozisyon Detayları:
💰 PNL: {pnl:.2f} USDT
📊 ROI: {roi:.2f}%
💵 Pozisyon Büyüklüğü: {notional:.2f} USDT
💎 Mark Fiyat: {mark_price:.4f}
🔒 Teminat: {initial_margin:.2f} USDT
"""
                                            messages.append(message)
                                        
                                        # Toplam PNL özeti
                                        summary = f"""📈 Pozisyon Özeti:
💰 Toplam PNL: {total_pnl:.2f} USDT
📊 Pozisyon Sayısı: {len(positions)}
⏰ Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}

"""
                                        self.send_message(summary)
                                        
                                        # Her pozisyonu ayrı mesaj olarak gönder
                                        for msg in messages:
                                            self.send_message(msg)
                                            
                                    except Exception as e:
                                        self.send_message(f"❌ Pozisyon bilgileri alınırken hata: {str(e)}")

                            # Help mesajını güncelle
                            elif text == '/help':
                                help_text = """📋 Kullanılabilir komutlar:
/threshold <değer> - Bildirim eşiğini değiştirir (USDT)
/positions - Tüm aktif pozisyonları listeler
/position <symbol> - Belirli bir pozisyonun detaylarını gösterir
/pnl - Güncel PNL durumunu ve en yüksek/düşük değerleri gösterir
/status - Genel durum özeti
/help - Bu yardım mesajını gösterir"""
                                self.send_message(help_text)
                                
            except Exception as e:
                print(f"Telegram komut işleme hatası: {e}")
                time.sleep(5)
            
            time.sleep(1)

if __name__ == "__main__":
    app = BinancePNLTracker()
    try:
        app.run()
    finally:
        app.cleanup()