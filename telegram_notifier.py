from telegram.ext import Application, CommandHandler
import asyncio
from datetime import datetime
import threading
import time

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.app = None
        
        # Asenkron uygulama oluştur
        self.application = Application.builder().token(self.token).build()
        
        # Komutları kaydet
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("pnl", self.cmd_pnl))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("threshold", self.cmd_threshold))
        
        # Bot'u başlat
        self.start_bot()
        
    def start_bot(self):
        """Bot'u ayrı bir thread'de başlat"""
        def run_bot():
            while True:  # Sürekli yeniden deneme döngüsü
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    self.application.run_polling(
                        allowed_updates=["message"],
                        close_loop=False,
                        drop_pending_updates=True,
                        read_timeout=30,
                        write_timeout=30
                    )
                except Exception as e:
                    print(f"⚠️ Bot bağlantısı yenileniyor: {e}")
                    time.sleep(3)  # 3 saniye bekle ve tekrar dene

        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()
        print("✅ Telegram bot başlatıldı!")

    async def cmd_start(self, update, context):
        await update.message.reply_text(
            "🤖 PNL Tracker Bot'a Hoş Geldiniz!\n\n"
            "Komutları görmek için /help yazabilirsiniz."
        )

    async def cmd_help(self, update, context):
        await update.message.reply_text(
            "📋 Kullanılabilir komutlar:\n\n"
            "/start - Bot'u başlatır ve karşılama mesajı gönderir\n"
            "/help - Kullanılabilir komutları listeler\n"
            "/pnl - Güncel PNL durumunu gösterir\n"
            "/positions - Tüm aktif pozisyonları listeler\n"
            "/threshold <değer> - Bildirim eşiğini değiştirir (USDT)"
        )

    async def cmd_pnl(self, update, context):
        if not hasattr(self, 'app'):
            await update.message.reply_text("❌ Sistem henüz hazır değil!")
            return
            
        try:
            account = self.app.client.futures_account()
            total_pnl = float(account['totalUnrealizedProfit'])
            
            await update.message.reply_text(
                f"📊 Güncel PNL Durumu:\n"
                f"💰 Toplam PNL: {total_pnl:.2f} USDT\n"
                f"📈 En Yüksek: {self.app.high_pnl:.2f} USDT\n"
                f"📉 En Düşük: {self.app.low_pnl:.2f} USDT\n"
                f"⏰ Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Hata: {str(e)}")

    async def cmd_positions(self, update, context):
        """Positions komutu"""
        if not hasattr(self, 'app'):
            await update.message.reply_text("❌ Sistem henüz hazır değil!")
            return
            
        try:
            positions = [p for p in self.app.client.futures_position_information() if float(p['positionAmt']) != 0]
            
            if not positions:
                await update.message.reply_text("❌ Aktif pozisyon bulunamadı!")
                return
                
            # Toplam PNL hesapla
            total_pnl = sum(float(p['unRealizedProfit']) for p in positions)
            total_pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"
            
            # Özet mesajı
            summary = (
                f"📈 Pozisyon Özeti:\n"
                f"{total_pnl_emoji} Toplam PNL: {total_pnl:.2f} USDT\n"
                f"📊 Pozisyon Sayısı: {len(positions)}\n"
                f"⏰ Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}"
            )
            await update.message.reply_text(summary)
            
            # Her pozisyon için detay mesajı
            for pos in positions:
                symbol = pos['symbol']
                pnl = float(pos['unRealizedProfit'])
                position_amt = float(pos['positionAmt'])
                mark_price = float(pos['markPrice'])
                entry_price = float(pos['entryPrice'])
                
                # PNL emoji
                pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                
                # Fiyat değişimi
                price_change = ((mark_price - entry_price) / entry_price * 100)
                price_change_str = f"{price_change:+.2f}%" if position_amt > 0 else f"{-price_change:+.2f}%"
                
                # Pozisyon yönü
                side = "LONG 📈" if position_amt > 0 else "SHORT 📉"
                
                position_msg = (
                    f"🔍 {symbol} Detayları:\n"
                    f"📊 Yön: {side}\n"
                    f"{pnl_emoji} PNL: {pnl:.2f} USDT\n"
                    f"📈 Pozisyon Miktarı: {abs(position_amt):.4f}\n"
                    f"💎 Mark Fiyat: {mark_price:.4f}\n"
                    f"📊 Fiyat Değişimi: {price_change_str}"
                )
                
                await update.message.reply_text(position_msg)
                await asyncio.sleep(0.1)  # Mesajlar arası küçük gecikme
                
        except Exception as e:
            error_msg = f"❌ Hata: {str(e)}"
            print(error_msg)  # Console'a yazdır
            await update.message.reply_text(error_msg)

    async def cmd_threshold(self, update, context):
        if not context.args:
            await update.message.reply_text("❌ Lütfen bir değer girin. Örnek: /threshold 5")
            return
            
        try:
            value = float(context.args[0])
            if value <= 0:
                await update.message.reply_text("❌ Değer 0'dan büyük olmalıdır!")
                return
                
            if hasattr(self, 'app'):
                self.app.threshold_var.set(str(value))
                await update.message.reply_text(f"✅ Bildirim eşiği {value} USDT olarak ayarlandı!")
            else:
                await update.message.reply_text("❌ Sistem henüz hazır değil!")
                
        except ValueError:
            await update.message.reply_text("❌ Geçersiz değer! Örnek: /threshold 5")

    async def _send_message(self, text):
        """Asenkron mesaj gönderme"""
        try:
            await self.application.bot.send_message(
                chat_id=self.chat_id,
                text=text
            )
            return True
        except Exception as e:
            print(f"Mesaj gönderme hatası: {e}")
            return False

    def send_message(self, text):
        """Senkron mesaj gönderme metodu"""
        try:
            # Mevcut event loop'u kontrol et
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            async def _send():
                try:
                    # Rate limiting için kısa bekleme
                    await asyncio.sleep(0.1)
                    return await self.application.bot.send_message(
                        chat_id=self.chat_id,
                        text=text,
                        parse_mode='HTML',
                        disable_web_page_preview=True  # Link önizlemelerini kapat
                    )
                except Exception as e:
                    print(f"Telegram mesaj hatası: {e}")
                    # Kritik hata durumunda yeniden deneme
                    if "Bad Gateway" in str(e) or "Connection reset" in str(e):
                        await asyncio.sleep(1)
                        return await self._retry_send(text)
                    return False

            return loop.run_until_complete(_send())

        except Exception as e:
            print(f"Event loop hatası: {e}")
            return False

    async def _retry_send(self, text, max_retries=3):
        """Başarısız mesajları yeniden dene"""
        for i in range(max_retries):
            try:
                await asyncio.sleep(1 * (i + 1))  # Artan bekleme süresi
                return await self.application.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"Yeniden deneme {i+1} başarısız: {e}")
        return False

    def send_pnl_alert(self, symbol, current_pnl, target_pnl, alarm_type):
        """PNL alarm bildirimi"""
        message = (
            f"⚠️ PNL Alarmı!\n\n"
            f"{symbol} pozisyonu için {target_pnl} USDT {alarm_type.lower()} "
            f"hedefine ulaşıldı!\nMevcut PNL: {current_pnl:.2f} USDT"
        )
        self.send_message(message)

    def send_position_update(self, position_data):
        """Pozisyon güncelleme bildirimi"""
        pnl = float(position_data['pnl'])
        pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        
        message = (
            f"📈 Pozisyon Güncellemesi:\n"
            f"Symbol: {position_data['symbol']}\n"
            f"{pnl_emoji} PNL: {position_data['pnl']:.2f} USDT\n"
            f"💎 Mark Fiyat: {position_data['mark_price']:.4f}"
        )
        self.send_message(message)

    def send_general_pnl_alert(self, current_pnl, previous_pnl, threshold, alarm_type):
        """Genel PNL alarm bildirimi"""
        pnl_emoji = "🟢" if current_pnl > previous_pnl else "🔴"
        change = abs(current_pnl - previous_pnl)
        
        message = (
            f"⚠️ Genel PNL Alarmı!\n\n"
            f"{pnl_emoji} PNL {alarm_type.lower()} tespit edildi!\n"
            f"Değişim: {change:.2f} USDT\n"
            f"Önceki PNL: {previous_pnl:.2f} USDT\n"
            f"Güncel PNL: {current_pnl:.2f} USDT\n"
            f"Eşik Değeri: {threshold:.2f} USDT\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
        self.send_message(message)