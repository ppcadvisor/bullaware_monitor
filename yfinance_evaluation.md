# Оценка библиотеки yfinance для проекта BullAware Monitor

## Обзор репозитория

**GitHub**: https://github.com/ranaroussi/yfinance
**Документация**: https://ranaroussi.github.io/yfinance/

### Статистика проекта
- ⭐ **18.6k звезд** - очень популярная библиотека
- 🍴 **2.8k форков** - активное сообщество
- 👥 **126 контрибьюторов** - хорошая поддержка
- 📦 **Используется в 84.1k проектах** - проверенная временем
- 🐍 **Python 100%** - чистый Python код
- 📄 **Apache 2.0 лицензия** - свободное использование

## Основные возможности

### 1. Получение данных по тикерам
```python
import yfinance as yf

# Один тикер
ticker = yf.Ticker("NVDA")
ticker.info                    # Основная информация
ticker.history(period='1mo')   # Исторические данные
ticker.calendar               # Календарь событий
ticker.analyst_price_targets  # Целевые цены аналитиков

# Множественные тикеры
tickers = yf.Tickers('NVDA TSLA AAPL')
data = yf.download(['NVDA', 'TSLA', 'AAPL'], period='1mo')
```

### 2. Типы данных
- **Исторические цены** (Open, High, Low, Close, Volume)
- **Текущие котировки** (реальное время с задержкой 15-20 мин)
- **Финансовая отчетность** (quarterly_income_stmt, balance_sheet)
- **Аналитические данные** (analyst_price_targets, recommendations)
- **Опционы** (option_chain)
- **Дивиденды и сплиты**
- **Новости и события**

### 3. Дополнительные компоненты
- **Market**: информация о рынках
- **WebSocket**: потоковые данные в реальном времени
- **Search**: поиск котировок и новостей
- **Sector/Industry**: отраслевая информация
- **Screener**: скрининг рынка

## Преимущества для нашего проекта

### ✅ Идеально подходит
1. **Бесплатный доступ** - никаких API ключей или лимитов
2. **Широкое покрытие** - все основные биржи (NYSE, NASDAQ, европейские)
3. **Простота использования** - минимум кода для получения данных
4. **Надежность** - 18.6k звезд, используется в 84k проектов
5. **Активная поддержка** - регулярные обновления (последний релиз July 2025)

### ✅ Конкретно для наших задач
```python
# Получение текущей цены для расчета позиций
def get_current_price(symbol):
    ticker = yf.Ticker(symbol)
    return ticker.history(period="1d")['Close'].iloc[-1]

# Получение волатильности для расчета stop-loss
def get_volatility(symbol, period="30d"):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)
    return hist['Close'].pct_change().std()

# Получение технических уровней
def get_support_resistance(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="60d")
    support = hist['Low'].rolling(20).min().iloc[-1]
    resistance = hist['High'].rolling(20).max().iloc[-1]
    return support, resistance

# Получение информации о компании
def get_company_info(symbol):
    ticker = yf.Ticker(symbol)
    info = ticker.info
    return {
        'name': info.get('longName'),
        'sector': info.get('sector'),
        'market_cap': info.get('marketCap'),
        'pe_ratio': info.get('trailingPE')
    }
```

## Ограничения и предупреждения

### ⚠️ Важные моменты
1. **Не аффилирован с Yahoo** - использует публичные API
2. **Только для личного использования** - согласно условиям Yahoo
3. **Задержка данных** - 15-20 минут для реального времени
4. **Зависимость от Yahoo** - если Yahoo изменит API, может сломаться

### ⚠️ Технические ограничения
- Нет гарантий стабильности API
- Возможны временные сбои
- Некоторые данные могут быть неполными для малых компаний

## Альтернативы

### Если yfinance не подойдет:
1. **Alpha Vantage** - 5 запросов/мин бесплатно
2. **Finnhub** - 60 запросов/мин бесплатно  
3. **IEX Cloud** - ограниченный бесплатный план
4. **Polygon.io** - платный, но более надежный

## Рекомендация

### 🎯 **НАСТОЯТЕЛЬНО РЕКОМЕНДУЮ** использовать yfinance

**Причины:**
1. **Идеально подходит для MVP** - быстрый старт без регистраций
2. **Покрывает все наши потребности** - цены, волатильность, техданные
3. **Проверенная библиотека** - миллионы загрузок, активное сообщество
4. **Простая интеграция** - буквально 3 строки кода для получения цены

**План интеграции:**
1. Установить: `pip install yfinance`
2. Создать модуль `price_provider.py`
3. Добавить кэширование для оптимизации
4. Реализовать fallback на другие источники при сбоях

### Пример интеграции в наш проект:
```python
# src/services/price_provider.py
import yfinance as yf
from typing import Dict, Optional
import logging

class PriceProvider:
    def __init__(self):
        self.cache = {}
        
    def get_current_price(self, symbol: str) -> Optional[float]:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logging.error(f"Error getting price for {symbol}: {e}")
        return None
        
    def get_market_data(self, symbol: str) -> Dict:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="30d")
        
        return {
            'current_price': hist['Close'].iloc[-1],
            'volatility': hist['Close'].pct_change().std(),
            'support': hist['Low'].rolling(20).min().iloc[-1],
            'resistance': hist['High'].rolling(20).max().iloc[-1],
            'volume': hist['Volume'].iloc[-1]
        }
```

## Заключение

yfinance - **отличный выбор** для нашего проекта. Библиотека надежная, простая в использовании и полностью покрывает наши потребности в получении финансовых данных. Начинаем интеграцию!

