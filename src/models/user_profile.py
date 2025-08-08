"""
Модель профиля пользователя для управления капиталом и настройками
"""
from peewee import *
from .base import BaseModel
from datetime import datetime

class UserProfile(BaseModel):
    """Профиль пользователя с настройками капитала и риска"""
    
    user_id = IntegerField(unique=True, help_text="ID пользователя")
    
    # Капитал
    total_capital = DecimalField(max_digits=15, decimal_places=2, default=10000.00, 
                                help_text="Общий капитал пользователя")
    available_capital = DecimalField(max_digits=15, decimal_places=2, default=10000.00,
                                   help_text="Доступный для инвестиций капитал")
    invested_capital = DecimalField(max_digits=15, decimal_places=2, default=0.00,
                                  help_text="Уже инвестированный капитал")
    currency = CharField(max_length=3, default='USD', help_text="Валюта счета")
    
    # Настройки риска
    risk_tolerance = CharField(max_length=20, default='moderate',
                              help_text="Уровень риска: conservative, moderate, aggressive")
    max_risk_per_trade = DecimalField(max_digits=5, decimal_places=4, default=0.02,
                                     help_text="Максимальный риск на сделку (доля от капитала)")
    max_portfolio_risk = DecimalField(max_digits=5, decimal_places=4, default=0.10,
                                     help_text="Максимальный риск портфеля")
    
    # Предпочтения стратегий
    preferred_strategies = CharField(max_length=100, default='long_term,day_trading',
                                   help_text="Предпочитаемые стратегии через запятую")
    
    # Настройки уведомлений
    enable_notifications = BooleanField(default=True, help_text="Включить уведомления")
    notification_email = CharField(max_length=255, null=True, help_text="Email для уведомлений")
    
    # Метаданные
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'user_profiles'
    
    def save(self, *args, **kwargs):
        """Обновляем updated_at при сохранении"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    @property
    def risk_profile_settings(self):
        """Возвращает настройки риска на основе профиля"""
        risk_profiles = {
            'conservative': {
                'max_risk_per_trade': 0.01,  # 1%
                'max_portfolio_risk': 0.05,  # 5%
                'preferred_strategies': ['long_term'],
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.5
            },
            'moderate': {
                'max_risk_per_trade': 0.02,  # 2%
                'max_portfolio_risk': 0.10,  # 10%
                'preferred_strategies': ['long_term', 'day_trading'],
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 2.0
            },
            'aggressive': {
                'max_risk_per_trade': 0.05,  # 5%
                'max_portfolio_risk': 0.20,  # 20%
                'preferred_strategies': ['day_trading', 'long_term'],
                'stop_loss_multiplier': 2.0,
                'take_profit_multiplier': 2.5
            }
        }
        
        return risk_profiles.get(self.risk_tolerance, risk_profiles['moderate'])
    
    @property
    def investment_capacity(self):
        """Рассчитывает инвестиционную способность"""
        return {
            'available_amount': float(self.available_capital),
            'max_single_trade': float(self.available_capital * self.max_risk_per_trade / self.max_risk_per_trade),
            'max_risk_amount': float(self.available_capital * self.max_risk_per_trade),
            'portfolio_utilization': float(self.invested_capital / self.total_capital) if self.total_capital > 0 else 0
        }
    
    def can_invest(self, amount: float) -> bool:
        """Проверяет, может ли пользователь инвестировать указанную сумму"""
        return amount <= float(self.available_capital)
    
    def update_capital(self, invested_amount: float, operation: str = 'invest'):
        """
        Обновляет капитал после операции
        
        Args:
            invested_amount: Сумма операции
            operation: 'invest' или 'close'
        """
        if operation == 'invest':
            self.available_capital -= invested_amount
            self.invested_capital += invested_amount
        elif operation == 'close':
            self.available_capital += invested_amount
            self.invested_capital -= invested_amount
        
        self.save()
    
    @classmethod
    def get_or_create_profile(cls, user_id: int, **kwargs):
        """Получает или создает профиль пользователя"""
        try:
            return cls.get(cls.user_id == user_id)
        except cls.DoesNotExist:
            # Создаем профиль с настройками по умолчанию
            profile_data = {
                'user_id': user_id,
                'total_capital': kwargs.get('total_capital', 10000.00),
                'available_capital': kwargs.get('available_capital', 10000.00),
                'risk_tolerance': kwargs.get('risk_tolerance', 'moderate'),
                'currency': kwargs.get('currency', 'USD')
            }
            return cls.create(**profile_data)


class UserPosition(BaseModel):
    """Текущие позиции пользователя"""
    
    user_id = IntegerField(help_text="ID пользователя")
    symbol = CharField(max_length=10, help_text="Тикер инструмента")
    
    # Параметры позиции
    shares = IntegerField(help_text="Количество акций")
    entry_price = DecimalField(max_digits=10, decimal_places=2, help_text="Цена входа")
    current_price = DecimalField(max_digits=10, decimal_places=2, null=True, help_text="Текущая цена")
    
    # Риск-менеджмент
    stop_loss = DecimalField(max_digits=10, decimal_places=2, null=True, help_text="Уровень stop-loss")
    take_profit = DecimalField(max_digits=10, decimal_places=2, null=True, help_text="Уровень take-profit")
    
    # Метаданные
    strategy_type = CharField(max_length=20, help_text="Тип стратегии")
    signal_id = IntegerField(null=True, help_text="ID сигнала, по которому открыта позиция")
    status = CharField(max_length=20, default='open', help_text="Статус позиции: open, closed")
    
    # Временные метки
    opened_at = DateTimeField(default=datetime.now)
    closed_at = DateTimeField(null=True)
    updated_at = DateTimeField(default=datetime.now)
    
    class Meta:
        table_name = 'user_positions'
        indexes = (
            (('user_id', 'symbol'), False),
            (('user_id', 'status'), False),
        )
    
    def save(self, *args, **kwargs):
        """Обновляем updated_at при сохранении"""
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)
    
    @property
    def investment_amount(self):
        """Сумма инвестиций"""
        return float(self.shares * self.entry_price)
    
    @property
    def current_value(self):
        """Текущая стоимость позиции"""
        if self.current_price:
            return float(self.shares * self.current_price)
        return self.investment_amount
    
    @property
    def pnl(self):
        """Прибыль/убыток"""
        return self.current_value - self.investment_amount
    
    @property
    def pnl_percentage(self):
        """Прибыль/убыток в процентах"""
        if self.investment_amount > 0:
            return (self.pnl / self.investment_amount) * 100
        return 0
    
    @property
    def risk_amount(self):
        """Сумма риска (до stop-loss)"""
        if self.stop_loss:
            return float(self.shares * abs(self.entry_price - self.stop_loss))
        return 0
    
    def should_close_position(self):
        """Проверяет, нужно ли закрыть позицию по stop-loss/take-profit"""
        if not self.current_price:
            return False, None
        
        current = float(self.current_price)
        
        # Проверяем stop-loss
        if self.stop_loss:
            stop = float(self.stop_loss)
            if current <= stop:
                return True, 'stop_loss'
        
        # Проверяем take-profit
        if self.take_profit:
            target = float(self.take_profit)
            if current >= target:
                return True, 'take_profit'
        
        return False, None
    
    def close_position(self, close_price: float = None, reason: str = 'manual'):
        """Закрывает позицию"""
        if close_price:
            self.current_price = close_price
        
        self.status = 'closed'
        self.closed_at = datetime.now()
        self.save()
        
        # Обновляем капитал пользователя
        try:
            profile = UserProfile.get(UserProfile.user_id == self.user_id)
            profile.update_capital(self.current_value, 'close')
        except UserProfile.DoesNotExist:
            pass
    
    @classmethod
    def get_user_positions(cls, user_id: int, status: str = 'open'):
        """Получает позиции пользователя"""
        return cls.select().where(
            (cls.user_id == user_id) & (cls.status == status)
        ).order_by(cls.opened_at.desc())
    
    @classmethod
    def get_portfolio_summary(cls, user_id: int):
        """Получает сводку по портфелю пользователя"""
        positions = cls.get_user_positions(user_id, 'open')
        
        total_investment = sum(pos.investment_amount for pos in positions)
        total_current_value = sum(pos.current_value for pos in positions)
        total_pnl = total_current_value - total_investment
        
        return {
            'total_positions': len(positions),
            'total_investment': total_investment,
            'total_current_value': total_current_value,
            'total_pnl': total_pnl,
            'total_pnl_percentage': (total_pnl / total_investment * 100) if total_investment > 0 else 0,
            'positions': [
                {
                    'symbol': pos.symbol,
                    'shares': pos.shares,
                    'entry_price': float(pos.entry_price),
                    'current_price': float(pos.current_price) if pos.current_price else None,
                    'pnl': pos.pnl,
                    'pnl_percentage': pos.pnl_percentage
                }
                for pos in positions
            ]
        }

