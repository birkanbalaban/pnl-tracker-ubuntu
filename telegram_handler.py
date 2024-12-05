class TelegramHandler:
    def __init__(self, token, chat_id):
        self.bot = telegram.Bot(token=token)
        self.chat_id = chat_id
        # Bağlantı havuzu ayarlarını güncelle
        self.session = ClientSession(
            connector=TCPConnector(
                limit=None,  # Bağlantı limiti kaldır
                ttl_dns_cache=300
            )
        )
        self.message_queue = asyncio.Queue()
        
    async def send_message(self, message):
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Mesaj gönderme hatası: {str(e)}")
            # Başarısız mesajı kuyruğa geri ekle
            await self.message_queue.put(message)
            await asyncio.sleep(1)  # Yeniden denemeden önce bekle

    async def process_message_queue(self):
        while True:
            try:
                message = await self.message_queue.get()
                await self.send_message(message)
                await asyncio.sleep(0.1)  # Rate limiting için küçük gecikme
            except Exception as e:
                print(f"Kuyruk işleme hatası: {str(e)}")
                await asyncio.sleep(1) 