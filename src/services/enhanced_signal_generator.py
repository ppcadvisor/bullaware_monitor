"""
Улучшенный сервис для генерации торговых сигналов с управлением капиталом
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import statistics

from .bullaware_client import bullaware_client
from .trader_scorer import trader_scorer
from .position_sizer import position_sizer
from .price_provider import price_provider

logger = logging.getLogger(__name__)

class EnhancedSignalGenerator:
    """Улучшенный генератор торговых сигналов с управлением капиталом"""
    
    def __init__(self):
        self.bullaware_client = bullaware_client
        self.trader_scorer = trader_scorer
        self.position_sizer = position_sizer
        self.price_provider = price_provider
        
        # Пороги консенсуса
        self.consensus_thresholds = {
            'day_trading': {
                'min_consensus': 0.60,  # 60% консенсус
                'min_traders': 3,       # Минимум 3 трейдера
                'confidence_boost': 1.2  # Буст уверенности для дейтрейдинга
            },
            'long_term': {
                'min_consensus': 0.70,  # 70% консенсус
                'min_traders': 4,       # Минимум 4 трейдера
                'confidence_boost': 1.0  # Базовая уверенность
            }
        }
    
    def analyze_trader_positions(self, traders: List[Dict], strategy_type: str) -> Dict[str, Dict]:
        """
        Анализирует позиции трейдеров и находит консенсус
        
        Args:
            traders: Список топ-трейдеров
            strategy_type: Тип стратегии
            
        Returns:
            Словарь с консенсусом по инструментам
        """
        instrument_consensus = {}
        
        for trader in traders:
            trader_username = trader.get('username', '')
            
            # Получаем позиции трейдера
            positions = self.bullaware_client.get_trader_positions(trader_username)
            
            if not positions:
                continue
            
            for position in positions:
                instrument = position.get('instrument', '')
                direction = position.get('direction', '').lower()  # 'long' или 'short'
                size = position.get('size', 0)
                
                if not instrument or not direction or size <= 0:
                    continue
                
                # Инициализируем консенсус для инструмента
                if instrument not in instrument_consensus:
                    instrument_consensus[instrument] = {
                        'long_votes': [],
                        'short_votes': [],
                        'total_weight': 0,
                        'traders': []
                    }
                
                # Добавляем голос трейдера
                trader_score = trader.get('score', 0.5)
                vote_weight = trader_score * size  # Вес = скор * размер позиции
                
                if direction == 'long':
                    instrument_consensus[instrument]['long_votes'].append(vote_weight)
                elif direction == 'short':
                    instrument_consensus[instrument]['short_votes'].append(vote_weight)
                
                instrument_consensus[instrument]['total_weight'] += vote_weight
                instrument_consensus[instrument]['traders'].append({
                    'username': trader_username,
                    'direction': direction,
                    'size': size,
                    'score': trader_score,
                    'weight': vote_weight
                })
        
        return instrument_consensus
    
    def calculate_consensus_signals(self, consensus_data: Dict, strategy_type: str) -> List[Dict]:
        """
        Рассчитывает сигналы на основе консенсуса
        
        Args:
            consensus_data: Данные консенсуса по инструментам
            strategy_type: Тип стратегии
            
        Returns:
            Список торговых сигналов
        """
        signals = []
        thresholds = self.consensus_thresholds[strategy_type]
        
        for instrument, data in consensus_data.items():
            long_weight = sum(data['long_votes'])
            short_weight = sum(data['short_votes'])
            total_weight = data['total_weight']
            
            if total_weight == 0:
                continue
            
            # Рассчитываем консенсус
            long_consensus = long_weight / total_weight
            short_consensus = short_weight / total_weight
            
            # Определяем направление сигнала
            signal_direction = None
            consensus_strength = 0
            
            if long_consensus >= thresholds['min_consensus']:
                signal_direction = 'BUY'
                consensus_strength = long_consensus
            elif short_consensus >= thresholds['min_consensus']:
                signal_direction = 'SELL'
                consensus_strength = short_consensus
            
            # Проверяем минимальное количество трейдеров
            total_traders = len(data['traders'])
            if signal_direction and total_traders >= thresholds['min_traders']:
                
                # Рассчитываем уверенность в сигнале
                confidence = min(consensus_strength * thresholds['confidence_boost'], 1.0)
                
                # Создаем обоснование
                supporting_traders = [
                    t for t in data['traders'] 
                    if t['direction'] == ('long' if signal_direction == 'BUY' else 'short')
                ]
                
                reasoning = self._generate_reasoning(
                    instrument, signal_direction, supporting_traders, 
                    consensus_strength, strategy_type
                )
                
                signals.append({
                    'instrument': instrument,
                    'action': signal_direction,
                    'confidence': confidence,
                    'consensus_strength': consensus_strength,
                    'strategy_type': strategy_type,
                    'supporting_traders': supporting_traders,
                    'total_traders': total_traders,
                    'reasoning': reasoning,
                    'generated_at': datetime.now().isoformat()
                })
        
        # Сортируем по уверенности
        signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        return signals
    
    def _generate_reasoning(self, instrument: str, action: str, traders: List[Dict], 
                          consensus: float, strategy_type: str) -> str:
        """Генерирует текстовое обоснование сигнала"""
        
        trader_count = len(traders)
        consensus_pct = round(consensus * 100, 1)
        
        # Топ трейдеры по весу
        top_traders = sorted(traders, key=lambda x: x['weight'], reverse=True)[:3]
        trader_names = [t['username'] for t in top_traders]
        
        action_text = "увеличили позиции" if action == "BUY" else "сократили позиции"
        strategy_text = "дейтрейдеры" if strategy_type == "day_trading" else "долгосрочные инвесторы"
        
        reasoning = f"{trader_count} топовых {strategy_text} ({consensus_pct}% консенсус) {action_text} в {instrument}. "
        
        if trader_names:
            reasoning += f"Ключевые трейдеры: {', '.join(trader_names[:2])}"
            if len(trader_names) > 2:
                reasoning += f" и еще {len(trader_names) - 2}"
        
        return reasoning
    
    def generate_signals_for_strategy(self, strategy_type: str, limit: int = 10) -> List[Dict]:
        """
        Генерирует сигналы для конкретной стратегии
        
        Args:
            strategy_type: Тип стратегии ('day_trading' или 'long_term')
            limit: Максимальное количество сигналов
            
        Returns:
            Список торговых сигналов
        """
        try:
            # Получаем топ-трейдеров для стратегии
            top_traders = self.trader_scorer.get_top_traders_by_strategy(strategy_type, limit=20)
            
            if not top_traders:
                logger.warning(f"No top traders found for strategy {strategy_type}")
                return []
            
            # Анализируем позиции трейдеров
            consensus_data = self.analyze_trader_positions(top_traders, strategy_type)
            
            if not consensus_data:
                logger.warning(f"No consensus data found for strategy {strategy_type}")
                return []
            
            # Генерируем сигналы
            signals = self.calculate_consensus_signals(consensus_data, strategy_type)
            
            return signals[:limit]
            
        except Exception as e:
            logger.error(f"Error generating signals for {strategy_type}: {e}")
            return []
    
    def generate_enhanced_recommendations(self, user_id: int, strategy_type: str = None, limit: int = 5) -> List[Dict]:
        """
        Генерирует улучшенные торговые рекомендации с управлением капиталом
        
        Args:
            user_id: ID пользователя
            strategy_type: Тип стратегии (None для всех)
            limit: Максимальное количество рекомендаций
            
        Returns:
            Список полных торговых рекомендаций
        """
        try:
            recommendations = []
            
            # Определяем стратегии для анализа
            strategies = [strategy_type] if strategy_type else ['day_trading', 'long_term']
            
            for strategy in strategies:
                # Генерируем базовые сигналы
                signals = self.generate_signals_for_strategy(strategy, limit * 2)
                
                for signal in signals:
                    # Генерируем полную рекомендацию с управлением капиталом
                    recommendation = self.position_sizer.generate_trading_recommendation(
                        user_id=user_id,
                        symbol=signal['instrument'],
                        action=signal['action'],
                        confidence=signal['confidence'],
                        strategy_type=signal['strategy_type'],
                        reasoning=signal['reasoning']
                    )
                    
                    # Добавляем дополнительную информацию из сигнала
                    if 'error' not in recommendation:
                        recommendation.update({
                            'consensus_strength': signal['consensus_strength'],
                            'supporting_traders_count': len(signal['supporting_traders']),
                            'supporting_traders': signal['supporting_traders'][:3],  # Топ-3
                            'signal_generated_at': signal['generated_at']
                        })
                        
                        recommendations.append(recommendation)
            
            # Сортируем по уверенности и возможности исполнения
            recommendations.sort(key=lambda x: (
                x.get('can_execute', False),
                x.get('confidence', 0)
            ), reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating enhanced recommendations: {e}")
            return []
    
    def get_market_overview(self, user_id: int) -> Dict:
        """
        Получает обзор рынка и возможностей
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Обзор рыночных возможностей
        """
        try:
            # Генерируем рекомендации для обеих стратегий
            day_trading_signals = self.generate_enhanced_recommendations(user_id, 'day_trading', 3)
            long_term_signals = self.generate_enhanced_recommendations(user_id, 'long_term', 3)
            
            # Получаем профиль пользователя
            from ..models.user_profile import UserProfile, UserPosition
            
            try:
                profile = UserProfile.get(UserProfile.user_id == user_id)
                portfolio_summary = UserPosition.get_portfolio_summary(user_id)
            except UserProfile.DoesNotExist:
                profile = UserProfile.get_or_create_profile(user_id)
                portfolio_summary = {
                    'total_positions': 0,
                    'total_investment': 0,
                    'total_current_value': 0,
                    'total_pnl': 0,
                    'total_pnl_percentage': 0,
                    'positions': []
                }
            
            # Подсчитываем статистику
            executable_signals = [
                s for s in (day_trading_signals + long_term_signals) 
                if s.get('can_execute', False)
            ]
            
            return {
                'user_profile': {
                    'available_capital': float(profile.available_capital),
                    'invested_capital': float(profile.invested_capital),
                    'risk_tolerance': profile.risk_tolerance,
                    'currency': profile.currency
                },
                'portfolio_summary': portfolio_summary,
                'market_opportunities': {
                    'day_trading': {
                        'total_signals': len(day_trading_signals),
                        'executable_signals': len([s for s in day_trading_signals if s.get('can_execute', False)]),
                        'top_signals': day_trading_signals[:3]
                    },
                    'long_term': {
                        'total_signals': len(long_term_signals),
                        'executable_signals': len([s for s in long_term_signals if s.get('can_execute', False)]),
                        'top_signals': long_term_signals[:3]
                    }
                },
                'summary': {
                    'total_opportunities': len(executable_signals),
                    'avg_confidence': round(statistics.mean([s['confidence'] for s in executable_signals]), 1) if executable_signals else 0,
                    'potential_investment': sum([
                        s.get('recommendation', {}).get('investment_amount', 0) 
                        for s in executable_signals
                    ]),
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating market overview: {e}")
            return {
                'error': f'Error generating market overview: {str(e)}',
                'generated_at': datetime.now().isoformat()
            }


# Глобальный экземпляр улучшенного генератора сигналов
enhanced_signal_generator = EnhancedSignalGenerator()

