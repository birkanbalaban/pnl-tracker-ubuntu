class FuturesPositionTracker:
    def __init__(self, client):
        self.client = client
        
    def get_futures_positions(self):
        try:
            positions = self.client.futures_position_information()
            # Sadece aktif pozisyonları filtrele
            active_positions = [p for p in positions if float(p['positionAmt']) != 0]
            return active_positions
        except Exception as e:
            print(f"Futures pozisyon hatası: {e}")
            return []
            
    def get_position_details(self, symbol):
        try:
            # Pozisyon detaylarını al
            position = self.client.futures_position_information(symbol=symbol)[0]
            # Mark fiyatını al
            mark_price = float(self.client.futures_mark_price(symbol=symbol)['markPrice'])
            
            return {
                'symbol': position['symbol'],
                'size': float(position['positionAmt']),
                'entry_price': float(position['entryPrice']),
                'mark_price': mark_price,
                'unrealized_pnl': float(position['unRealizedProfit']),
                'roe': float(position['unRealizedProfit']) / float(position['isolatedWallet']) * 100 if float(position['isolatedWallet']) != 0 else 0,
                'leverage': int(position['leverage'])
            }
        except Exception as e:
            print(f"Pozisyon detay hatası: {e}")
            return None 