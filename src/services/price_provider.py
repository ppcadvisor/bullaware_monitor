"""
Модуль для получения финансовых данных через Yahoo Finance API
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class PriceProvider:
    """Провайдер финансовых данных через Yahoo Finance"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 минут кэш
        
    def _is_cache_valid(self, symbol: str) -> bool:
        """Проверяет валидность кэша для символа"""
        if symbol not in self.cache:
            return False
        
        cache_time = self.cache[symbol].get('timestamp', 0)
        return (time.time() - cache_time) < self.cache_timeout
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Получает текущую цену инструмента
        
        Args:
            symbol: Тикер инструмента (например, 'NVDA', 'TSLA')
            
        Returns:
            Текущая цена или None при ошибке
        """
        try:
            # Проверяем кэш
            if self._is_cache_valid(symbol):
                return self.cache[symbol]['current_price']
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            
            if data.empty:
                logger.warning(f"No data found for symbol {symbol}")
                return None
                
            current_price = float(data['Close'].iloc[-1])
            
            # Обновляем кэш
            if symbol not in self.cache:
                self.cache[symbol] = {}
            self.cache[symbol]['current_price'] = current_price
            self.cache[symbol]['timestamp'] = time.time()
            
            return current_price
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_volatility(self, symbol: str, period: str = "30d") -> Optional[float]:
        """
        Рассчитывает волатильность инструмента
        
        Args:
            symbol: Тикер инструмента
            period: Период для расчета (30d, 60d, 90d)
            
        Returns:
            Волатильность (стандартное отклонение дневных изменений)
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None
                
            # Рассчитываем дневные изменения в процентах
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std()
            
            return float(volatility)
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return None
    
    def get_support_resistance(self, symbol: str, period: str = "60d") -> Tuple[Optional[float], Optional[float]]:
        """
        Рассчитывает уровни поддержки и сопротивления
        
        Args:
            symbol: Тикер инструмента
            period: Период для анализа
            
        Returns:
            Кортеж (поддержка, сопротивление)
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)
            
            if hist.empty:
                return None, None
            
            # Поддержка - минимум за последние 20 дней
            support = hist['Low'].rolling(window=20).min().iloc[-1]
            
            # Сопротивление - максимум за последние 20 дней
            resistance = hist['High'].rolling(window=20).max().iloc[-1]
            
            return float(support), float(resistance)
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance for {symbol}: {e}")
            return None, None
    
    def get_company_info(self, symbol: str) -> Dict:
        """
        Получает информацию о компании
        
        Args:
            symbol: Тикер инструмента
            
        Returns:
            Словарь с информацией о компании
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'name': info.get('longName', symbol),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'currency': info.get('currency', 'USD')
            }
            
        except Exception as e:
            logger.error(f"Error getting company info for {symbol}: {e}")
            return {
                'name': symbol,
                'sector': 'Unknown',
                'industry': 'Unknown',
                'market_cap': None,
                'pe_ratio': None,
                'dividend_yield': None,
                'beta': None,
                'currency': 'USD'
            }
    
    def get_market_data(self, symbol: str) -> Dict:
        """
        Получает комплексные рыночные данные для инструмента
        
        Args:
            symbol: Тикер инструмента
            
        Returns:
            Словарь с рыночными данными
        """
        try:
            current_price = self.get_current_price(symbol)
            volatility = self.get_volatility(symbol)
            support, resistance = self.get_support_resistance(symbol)
            company_info = self.get_company_info(symbol)
            
            # Получаем дополнительные данные
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            
            volume = None
            price_change_pct = None
            
            if not hist.empty:
                volume = int(hist['Volume'].iloc[-1])
                if len(hist) >= 2:
                    prev_close = hist['Close'].iloc[-2]
                    price_change_pct = ((current_price - prev_close) / prev_close) * 100
            
            return {
                'symbol': symbol,
                'current_price': current_price,
                'volatility': volatility,
                'support_level': support,
                'resistance_level': resistance,
                'volume': volume,
                'price_change_pct': price_change_pct,
                'company_info': company_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return {
                'symbol': symbol,
                'current_price': None,
                'volatility': None,
                'support_level': None,
                'resistance_level': None,
                'volume': None,
                'price_change_pct': None,
                'company_info': {'name': symbol},
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Получает цены для множества инструментов одновременно
        
        Args:
            symbols: Список тикеров
            
        Returns:
            Словарь {символ: цена}
        """
        try:
            # Используем yf.download для эффективного получения множественных данных
            data = yf.download(symbols, period="1d", interval="1d", group_by='ticker')
            
            prices = {}
            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        # Для одного символа структура данных отличается
                        price = data['Close'].iloc[-1]
                    else:
                        # Для множественных символов
                        price = data[symbol]['Close'].iloc[-1]
                    
                    prices[symbol] = float(price)
                except (KeyError, IndexError, TypeError):
                    # Fallback на индивидуальный запрос
                    prices[symbol] = self.get_current_price(symbol)
            
            return prices
            
        except Exception as e:
            logger.error(f"Error getting multiple prices: {e}")
            # Fallback на индивидуальные запросы
            prices = {}
            for symbol in symbols:
                prices[symbol] = self.get_current_price(symbol)
            return prices
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Проверяет, существует ли тикер
        
        Args:
            symbol: Тикер для проверки
            
        Returns:
            True если тикер существует
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Проверяем, что получили валидную информацию
            return 'symbol' in info or 'shortName' in info or 'longName' in info
            
        except Exception:
            return False


# Глобальный экземпляр провайдера
price_provider = PriceProvider()

