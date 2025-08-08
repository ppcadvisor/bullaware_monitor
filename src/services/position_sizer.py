"""
Модуль для расчета размеров позиций и управления капиталом
"""
import math
from typing import Dict, Optional, Tuple
from decimal import Decimal
import logging

from ..models.user_profile import UserProfile
from .price_provider import price_provider

logger = logging.getLogger(__name__)

class PositionSizer:
    """Калькулятор размеров позиций и управления капиталом"""
    
    def __init__(self):
        self.price_provider = price_provider
    
    def calculate_stop_loss_levels(self, 
                                 symbol: str, 
                                 entry_price: float, 
                                 strategy_type: str,
                                 risk_tolerance: str = 'moderate') -> Dict:
        """
        Рассчитывает уровни stop-loss и take-profit
        
        Args:
            symbol: Тикер инструмента
            entry_price: Цена входа
            strategy_type: Тип стратегии ('day_trading' или 'long_term')
            risk_tolerance: Уровень риска пользователя
            
        Returns:
            Словарь с уровнями stop-loss и take-profit
        """
        try:
            # Получаем волатильность инструмента
            volatility = self.price_provider.get_volatility(symbol, period="30d")
            if not volatility:
                volatility = 0.02  # Дефолтная волатильность 2%
            
            # Получаем технические уровни
            support, resistance = self.price_provider.get_support_resistance(symbol)
            
            # Настройки риска по профилю
            risk_multipliers = {
                'conservative': {'stop': 1.0, 'profit': 1.5},
                'moderate': {'stop': 1.5, 'profit': 2.0},
                'aggressive': {'stop': 2.0, 'profit': 2.5}
            }
            
            multiplier = risk_multipliers.get(risk_tolerance, risk_multipliers['moderate'])
            
            # Базовые проценты для stop-loss
            if strategy_type == 'day_trading':
                # Для дейтрейдинга: более узкие уровни
                base_stop_pct = min(volatility * multiplier['stop'], 0.03)  # Максимум 3%
                base_profit_pct = base_stop_pct * multiplier['profit']
            else:
                # Для долгосрочных: более широкие уровни
                base_stop_pct = min(volatility * multiplier['stop'], 0.08)  # Максимум 8%
                base_profit_pct = base_stop_pct * multiplier['profit']
            
            # Рассчитываем уровни
            stop_loss_price = entry_price * (1 - base_stop_pct)
            take_profit_price = entry_price * (1 + base_profit_pct)
            
            # Корректируем на основе технических уровней
            if support and stop_loss_price < support:
                stop_loss_price = support * 0.99  # Чуть ниже поддержки
            
            if resistance and take_profit_price > resistance:
                take_profit_price = resistance * 0.99  # Чуть ниже сопротивления
            
            return {
                'stop_loss': round(stop_loss_price, 2),
                'take_profit': round(take_profit_price, 2),
                'stop_loss_pct': round(((entry_price - stop_loss_price) / entry_price) * 100, 2),
                'take_profit_pct': round(((take_profit_price - entry_price) / entry_price) * 100, 2),
                'risk_reward_ratio': round((take_profit_price - entry_price) / (entry_price - stop_loss_price), 2),
                'volatility_used': round(volatility * 100, 2),
                'support_level': support,
                'resistance_level': resistance
            }
            
        except Exception as e:
            logger.error(f"Error calculating stop-loss levels for {symbol}: {e}")
            # Возвращаем консервативные уровни по умолчанию
            return {
                'stop_loss': round(entry_price * 0.95, 2),  # -5%
                'take_profit': round(entry_price * 1.10, 2),  # +10%
                'stop_loss_pct': 5.0,
                'take_profit_pct': 10.0,
                'risk_reward_ratio': 2.0,
                'volatility_used': 2.0,
                'support_level': None,
                'resistance_level': None
            }
    
    def calculate_position_size(self,
                              user_id: int,
                              symbol: str,
                              entry_price: float,
                              signal_confidence: float,
                              strategy_type: str) -> Dict:
        """
        Рассчитывает оптимальный размер позиции
        
        Args:
            user_id: ID пользователя
            symbol: Тикер инструмента
            entry_price: Цена входа
            signal_confidence: Уверенность в сигнале (0-1)
            strategy_type: Тип стратегии
            
        Returns:
            Словарь с рекомендациями по размеру позиции
        """
        try:
            # Получаем профиль пользователя
            try:
                profile = UserProfile.get(UserProfile.user_id == user_id)
            except UserProfile.DoesNotExist:
                profile = UserProfile.get_or_create_profile(user_id)
            
            # Получаем настройки риска
            risk_settings = profile.risk_profile_settings
            available_capital = float(profile.available_capital)
            
            # Рассчитываем уровни stop-loss/take-profit
            levels = self.calculate_stop_loss_levels(
                symbol, entry_price, strategy_type, profile.risk_tolerance
            )
            
            stop_loss_price = levels['stop_loss']
            
            # Базовый риск на сделку
            base_risk_per_trade = risk_settings['max_risk_per_trade']
            
            # Корректировка на уверенность в сигнале
            confidence_multiplier = 0.5 + (signal_confidence * 0.5)  # От 0.5 до 1.0
            adjusted_risk_per_trade = base_risk_per_trade * confidence_multiplier
            
            # Максимальная сумма риска
            max_risk_amount = available_capital * adjusted_risk_per_trade
            
            # Риск на одну акцию
            risk_per_share = abs(entry_price - stop_loss_price)
            
            # Максимальное количество акций
            if risk_per_share > 0:
                max_shares = int(max_risk_amount / risk_per_share)
            else:
                max_shares = 0
            
            # Сумма инвестиций
            investment_amount = max_shares * entry_price
            
            # Проверяем, не превышаем ли доступный капитал
            if investment_amount > available_capital:
                max_shares = int(available_capital / entry_price)
                investment_amount = max_shares * entry_price
                max_risk_amount = max_shares * risk_per_share
            
            # Процент от портфеля
            portfolio_percentage = (investment_amount / available_capital) * 100 if available_capital > 0 else 0
            
            # Проверяем максимальный риск портфеля
            max_portfolio_risk_pct = risk_settings['max_portfolio_risk'] * 100
            if portfolio_percentage > max_portfolio_risk_pct:
                # Уменьшаем позицию до допустимого уровня
                max_investment = available_capital * risk_settings['max_portfolio_risk']
                max_shares = int(max_investment / entry_price)
                investment_amount = max_shares * entry_price
                portfolio_percentage = (investment_amount / available_capital) * 100
                max_risk_amount = max_shares * risk_per_share
            
            # Минимальная проверка
            if max_shares < 1:
                return {
                    'recommended_shares': 0,
                    'investment_amount': 0,
                    'max_risk_amount': 0,
                    'portfolio_percentage': 0,
                    'can_invest': False,
                    'reason': 'Insufficient capital or too high risk per share',
                    'levels': levels
                }
            
            return {
                'recommended_shares': max_shares,
                'investment_amount': round(investment_amount, 2),
                'max_risk_amount': round(max_risk_amount, 2),
                'portfolio_percentage': round(portfolio_percentage, 2),
                'risk_per_trade_pct': round(adjusted_risk_per_trade * 100, 2),
                'confidence_multiplier': round(confidence_multiplier, 2),
                'can_invest': True,
                'levels': levels,
                'user_profile': {
                    'available_capital': available_capital,
                    'risk_tolerance': profile.risk_tolerance,
                    'currency': profile.currency
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                'recommended_shares': 0,
                'investment_amount': 0,
                'max_risk_amount': 0,
                'portfolio_percentage': 0,
                'can_invest': False,
                'reason': f'Calculation error: {str(e)}',
                'levels': {}
            }
    
    def generate_trading_recommendation(self,
                                      user_id: int,
                                      symbol: str,
                                      action: str,
                                      confidence: float,
                                      strategy_type: str,
                                      reasoning: str = "") -> Dict:
        """
        Генерирует полную торговую рекомендацию
        
        Args:
            user_id: ID пользователя
            symbol: Тикер инструмента
            action: Действие ('BUY' или 'SELL')
            confidence: Уверенность в сигнале (0-1)
            strategy_type: Тип стратегии
            reasoning: Обоснование сигнала
            
        Returns:
            Полная торговая рекомендация
        """
        try:
            # Получаем текущую цену
            current_price = self.price_provider.get_current_price(symbol)
            if not current_price:
                return {
                    'error': f'Unable to get current price for {symbol}',
                    'symbol': symbol,
                    'action': action
                }
            
            # Получаем рыночные данные
            market_data = self.price_provider.get_market_data(symbol)
            
            if action.upper() == 'BUY':
                # Рассчитываем размер позиции
                position_calc = self.calculate_position_size(
                    user_id, symbol, current_price, confidence, strategy_type
                )
                
                if not position_calc['can_invest']:
                    return {
                        'symbol': symbol,
                        'action': action,
                        'current_price': current_price,
                        'confidence': round(confidence * 100, 1),
                        'strategy_type': strategy_type,
                        'can_execute': False,
                        'reason': position_calc['reason'],
                        'market_data': market_data,
                        'reasoning': reasoning
                    }
                
                return {
                    'symbol': symbol,
                    'action': action,
                    'current_price': current_price,
                    'confidence': round(confidence * 100, 1),
                    'strategy_type': strategy_type,
                    'can_execute': True,
                    'recommendation': {
                        'shares_to_buy': position_calc['recommended_shares'],
                        'investment_amount': position_calc['investment_amount'],
                        'portfolio_percentage': position_calc['portfolio_percentage'],
                        'max_risk_amount': position_calc['max_risk_amount'],
                        'stop_loss': position_calc['levels']['stop_loss'],
                        'take_profit': position_calc['levels']['take_profit'],
                        'risk_reward_ratio': f"1:{position_calc['levels']['risk_reward_ratio']}",
                        'currency': position_calc['user_profile']['currency']
                    },
                    'risk_management': {
                        'stop_loss_pct': position_calc['levels']['stop_loss_pct'],
                        'take_profit_pct': position_calc['levels']['take_profit_pct'],
                        'max_loss_amount': position_calc['max_risk_amount'],
                        'volatility': position_calc['levels']['volatility_used']
                    },
                    'market_data': market_data,
                    'reasoning': reasoning,
                    'timestamp': market_data['timestamp']
                }
            
            elif action.upper() == 'SELL':
                # Для сигналов продажи - проверяем текущие позиции
                from ..models.user_profile import UserPosition
                
                positions = UserPosition.get_user_positions(user_id, 'open')
                user_position = None
                
                for pos in positions:
                    if pos.symbol == symbol:
                        user_position = pos
                        break
                
                if not user_position:
                    return {
                        'symbol': symbol,
                        'action': action,
                        'current_price': current_price,
                        'confidence': round(confidence * 100, 1),
                        'strategy_type': strategy_type,
                        'can_execute': False,
                        'reason': f'No open position found for {symbol}',
                        'market_data': market_data,
                        'reasoning': reasoning
                    }
                
                # Рассчитываем P&L
                user_position.current_price = current_price
                
                return {
                    'symbol': symbol,
                    'action': action,
                    'current_price': current_price,
                    'confidence': round(confidence * 100, 1),
                    'strategy_type': strategy_type,
                    'can_execute': True,
                    'current_position': {
                        'shares': user_position.shares,
                        'entry_price': float(user_position.entry_price),
                        'current_value': user_position.current_value,
                        'pnl': user_position.pnl,
                        'pnl_percentage': user_position.pnl_percentage,
                        'days_held': (user_position.updated_at - user_position.opened_at).days
                    },
                    'recommendation': {
                        'action': 'SELL ALL',
                        'shares_to_sell': user_position.shares,
                        'expected_proceeds': user_position.current_value,
                        'expected_pnl': user_position.pnl
                    },
                    'market_data': market_data,
                    'reasoning': reasoning,
                    'timestamp': market_data['timestamp']
                }
            
            else:
                return {
                    'error': f'Unknown action: {action}',
                    'symbol': symbol,
                    'action': action
                }
                
        except Exception as e:
            logger.error(f"Error generating trading recommendation: {e}")
            return {
                'error': f'Error generating recommendation: {str(e)}',
                'symbol': symbol,
                'action': action
            }


# Глобальный экземпляр калькулятора позиций
position_sizer = PositionSizer()

