# Источники данных для улучшенной системы BullAware Monitor

## 1. Текущие котировки акций

### Бесплатные API источники:
- **Yahoo Finance API** (через yfinance Python библиотеку)
  - Бесплатный, без лимитов
  - Реальные цены с задержкой 15-20 минут
  - Поддерживает все основные биржи (NYSE, NASDAQ, европейские)

- **Alpha Vantage API** 
  - 5 запросов в минуту бесплатно
  - Реальные данные
  - Хорошее покрытие международных рынков

- **Finnhub API**
  - 60 запросов в минуту бесплатно
  - Реальные данные

### Пример получения цены:
```python
import yfinance as yf

def get_current_price(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d")
    return data['Close'].iloc[-1]

# Пример: get_current_price("NVDA") -> 875.50
```

## 2. Капитал пользователя

### Источник: Настройки пользователя в системе
- **Ввод пользователем** через веб-интерфейс
- **Хранение в БД** (таблица user_profiles)
- **Обновление** пользователем по мере необходимости

### Структура данных:
```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    total_capital DECIMAL(15,2),
    available_capital DECIMAL(15,2),
    invested_capital DECIMAL(15,2),
    currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 3. Риск-толерантность

### Источник: Профиль пользователя + анкетирование
- **Анкета при регистрации** (стандартные вопросы о риске)
- **Настройки пользователя** (можно изменить в любое время)
- **Автоматический расчет** на основе поведения

### Уровни риска:
```python
RISK_PROFILES = {
    'conservative': {
        'max_risk_per_trade': 0.01,  # 1% на сделку
        'max_portfolio_risk': 0.05,  # 5% портфеля
        'preferred_strategies': ['long_term']
    },
    'moderate': {
        'max_risk_per_trade': 0.02,  # 2% на сделку
        'max_portfolio_risk': 0.10,  # 10% портфеля
        'preferred_strategies': ['long_term', 'day_trading']
    },
    'aggressive': {
        'max_risk_per_trade': 0.05,  # 5% на сделку
        'max_portfolio_risk': 0.20,  # 20% портфеля
        'preferred_strategies': ['day_trading', 'long_term']
    }
}
```

## 4. Stop-Loss и Take-Profit уровни

### Источники расчета:

#### A) На основе волатильности инструмента
```python
def calculate_stop_loss_levels(symbol, entry_price, strategy_type):
    # Получаем историческую волатильность
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="30d")
    volatility = hist['Close'].pct_change().std() * 100
    
    if strategy_type == 'day_trading':
        # Для дейтрейдинга: более узкие уровни
        stop_loss_pct = min(volatility * 1.5, 3.0)  # Максимум 3%
        take_profit_pct = stop_loss_pct * 2  # Соотношение 1:2
    else:
        # Для долгосрочных: более широкие уровни
        stop_loss_pct = min(volatility * 2.0, 8.0)  # Максимум 8%
        take_profit_pct = stop_loss_pct * 1.5  # Соотношение 1:1.5
    
    return {
        'stop_loss': entry_price * (1 - stop_loss_pct/100),
        'take_profit': entry_price * (1 + take_profit_pct/100)
    }
```

#### B) На основе технического анализа
```python
def calculate_technical_levels(symbol):
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="60d")
    
    # Поддержка и сопротивление
    support = hist['Low'].rolling(20).min().iloc[-1]
    resistance = hist['High'].rolling(20).max().iloc[-1]
    
    return {
        'support_level': support,
        'resistance_level': resistance
    }
```

#### C) На основе консенсуса трейдеров
```python
def get_trader_exit_levels(symbol, supporting_traders):
    # Анализируем, на каких уровнях топ-трейдеры 
    # обычно закрывают позиции по этому инструменту
    # (из исторических данных BullAware)
    pass
```

## 5. Размер позиции

### Формула расчета:
```python
def calculate_position_size(
    available_capital: float,
    risk_per_trade: float,
    entry_price: float,
    stop_loss_price: float,
    confidence: float
):
    # Базовый риск на сделку
    risk_amount = available_capital * risk_per_trade
    
    # Корректировка на уверенность в сигнале
    confidence_multiplier = 0.5 + (confidence * 0.5)  # От 0.5 до 1.0
    adjusted_risk = risk_amount * confidence_multiplier
    
    # Расчет размера позиции
    price_risk_per_share = abs(entry_price - stop_loss_price)
    max_shares = int(adjusted_risk / price_risk_per_share)
    
    # Максимальная сумма инвестиций
    max_investment = max_shares * entry_price
    
    return {
        'shares': max_shares,
        'investment_amount': max_investment,
        'risk_amount': adjusted_risk
    }
```

## 6. Текущие позиции пользователя

### Источник: База данных системы
```sql
CREATE TABLE user_positions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    symbol VARCHAR(10),
    shares INTEGER,
    entry_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    take_profit DECIMAL(10,2),
    strategy_type VARCHAR(20),
    signal_id INTEGER,
    opened_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'open'
);
```

### Обновление цен:
- **Автоматическое обновление** каждые 15-30 минут
- **Расчет P&L** в реальном времени
- **Уведомления** при достижении stop-loss/take-profit

## 7. Пример полного потока данных

### Шаг 1: Генерация сигнала
1. BullAware API → данные трейдеров
2. Алгоритм консенсуса → сигнал BUY NVDA
3. Yahoo Finance API → текущая цена NVDA = $875.50

### Шаг 2: Расчет рекомендации
1. Профиль пользователя → капитал $10,000, риск moderate
2. Волатильность NVDA → stop-loss на уровне $831.73 (-5%)
3. Размер позиции → 1 акция, инвестиция $875.50, риск $43.77

### Шаг 3: Представление пользователю
```json
{
    "signal": {
        "instrument": "NVDA",
        "action": "BUY",
        "confidence": 85,
        "current_price": 875.50,
        "recommendation": {
            "shares_to_buy": 1,
            "investment_amount": 875.50,
            "percentage_of_portfolio": 8.8,
            "stop_loss": 831.73,
            "take_profit": 963.05,
            "max_risk": 43.77,
            "risk_reward_ratio": "1:2"
        }
    }
}
```

## Реализация

Хотите, чтобы я начал реализацию с:
1. **Интеграции Yahoo Finance API** для получения цен?
2. **Создания модуля управления капиталом**?
3. **Добавления профиля пользователя в БД**?

Все эти данные будут получаться из открытых источников и настроек пользователя - никаких платных API или сложных интеграций не требуется!

