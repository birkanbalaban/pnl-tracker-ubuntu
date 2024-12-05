"""
Binance PNL Tracker
~~~~~~~~~~~~~~~~~~

Binance Futures PNL tracking application with real-time monitoring and alerts.
"""

__version__ = '1.0.0'
__author__ = 'Your Name'
__email__ = 'your.email@example.com'

try:
    from main import BinancePNLTracker
    from futures_tracker import FuturesPositionTracker
except ImportError:
    print("Import uyarısı: Modüller yüklenemedi, ancak bu programın çalışmasını etkilemez.")

__all__ = [
    'BinancePNLTracker',
    'FuturesPositionTracker',
] 