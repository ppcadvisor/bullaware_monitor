"""
Улучшенный сервис для генерации торговых сигналов с детализацией трейдеров
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

class EnhancedSignalGeneratorV2:
    """Улучшенный генератор торговых сигналов с прозрачностью трейдеров"""
    
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
    
    def _analyze_instrument_consensus(self, traders: List[Dict]) -> Dict[str, Dict]:
        """
        Анализирует консенсус трейдеров по инструментам
        
        Returns:
            Словарь с детальным анализом консенсуса по каждому инструменту
        """
        instrument_data = {}
        
        for trader in traders:
            trader_username = trader.get('username', 'Unknown')
            trader_score = trader.get('score', 0)
            trader_strategy = trader.get('strategy_type', 'mixed')
            
            # Получаем позиции трейдера
            try:
                positions = self.bullaware_client.get_investor_portfolio(trader_username)
                if not positions:
                    continue
                    
                for position in positions:
                    instrument = position.get('instrument', '').upper()
                    if not instrument or len(instrument) < 2:
                        continue
                    
                    # Определяем направление позиции
                    direction = 'LONG' if position.get('is_buy', True) else 'SHORT'
                    position_size = abs(float(position.get('amount', 0)))
                    
                    if position_size < 100:  # Игнорируем мелкие позиции
                        continue
                    
                    # Инициализируем данные по инструменту
                    if instrument not in instrument_data:
                        instrument_data[instrument] = {
                            'traders': [],
                            'long_votes': 0,
                            'short_votes': 0,
                            'total_weight': 0,
                            'positions': []
                        }
                    
                    # Добавляем трейдера и его позицию
                    trader_info = {
                        'username': trader_username,
                        'score': trader_score,
                        'strategy_type': trader_strategy,
                        'direction': direction,
                        'position_size': position_size,
                        'weight': trader_score / 10.0,  # Нормализуем вес
                        'portfolio_percentage': position.get('percentage', 0)
                    }
                    
                    instrument_data[instrument]['traders'].append(trader_info)
                    instrument_data[instrument]['positions'].append(position)
                    
                    # Подсчитываем голоса с весами
                    weight = trader_score / 10.0
                    if direction == 'LONG':
                        instrument_data[instrument]['long_votes'] += weight
                    else:
                        instrument_data[instrument]['short_votes'] += weight
                    
                    instrument_data[instrument]['total_weight'] += weight
                    
            except Exception as e:
                logger.error(f"Error getting positions for trader {trader_username}: {e}")
                continue
        
        # Анализируем консенсус
        consensus_results = {}
        
        for instrument, data in instrument_data.items():
            if len(data['traders']) < 2:  # Нужно минимум 2 трейдера
                continue
            
            total_weight = data['total_weight']
            long_percentage = (data['long_votes'] / total_weight) * 100 if total_weight > 0 else 0
            short_percentage = (data['short_votes'] / total_weight) * 100 if total_weight > 0 else 0
            
            # Определяем консенсус
            consensus_direction = 'LONG' if long_percentage > short_percentage else 'SHORT'
            consensus_percentage = max(long_percentage, short_percentage)
            
            # Рассчитываем среднюю оценку трейдеров
            average_score = statistics.mean([t['score'] for t in data['traders']])
            
            # Определяем основную стратегию
            strategy_counts = {}
            for trader in data['traders']:
                strategy = trader['strategy_type']
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            
            primary_strategy = max(strategy_counts.items(), key=lambda x: x[1])[0] if strategy_counts else 'mixed'
            
            # Создаем детальный анализ консенсуса
            consensus_breakdown = {
                'long': {
                    'percentage': round(long_percentage, 1),
                    'traders': [t for t in data['traders'] if t['direction'] == 'LONG'],
                    'total_weight': data['long_votes']
                },
                'short': {
                    'percentage': round(short_percentage, 1),
                    'traders': [t for t in data['traders'] if t['direction'] == 'SHORT'],
                    'total_weight': data['short_votes']
                }
            }
            
            # Сортируем трейдеров по весу (влиянию)
            supporting_traders = sorted(
                [t for t in data['traders'] if t['direction'] == consensus_direction],
                key=lambda x: x['weight'],
                reverse=True
            )
            
            consensus_results[instrument] = {
                'total_traders': len(data['traders']),
                'consensus_direction': consensus_direction,
                'consensus_percentage': round(consensus_percentage, 1),
                'confidence': min(consensus_percentage / 100.0, 1.0),
                'average_score': round(average_score, 1),
                'primary_strategy': primary_strategy,
                'supporting_traders': supporting_traders[:5],  # Топ-5 поддерживающих трейдеров
                'consensus_breakdown': consensus_breakdown,
                'all_traders': data['traders']
            }
        
        return consensus_results
    
    def _determine_action(self, consensus_data: Dict) -> str:
        """Определяет торговое действие на основе консенсуса"""
        direction = consensus_data['consensus_direction']
        confidence = consensus_data['confidence']
        
        # Минимальный порог уверенности
        if confidence < 0.6:
            return 'HOLD'
        
        return 'BUY' if direction == 'LONG' else 'SELL'
    
    def _generate_reasoning(self, consensus_data: Dict, market_data: Dict, action: str) -> str:
        """Генерирует обоснование для рекомендации"""
        traders_count = consensus_data['total_traders']
        consensus_pct = consensus_data['consensus_percentage']
        avg_score = consensus_data['average_score']
        strategy = consensus_data['primary_strategy']
        
        top_trader = consensus_data['supporting_traders'][0] if consensus_data['supporting_traders'] else None
        
        reasoning_parts = [
            f"{action} рекомендация основана на анализе {traders_count} топ-трейдеров eToro",
            f"Консенсус: {consensus_pct}% трейдеров поддерживают позицию",
            f"Средняя оценка трейдеров: {avg_score}/10",
            f"Основная стратегия: {strategy}"
        ]
        
        if top_trader:
            reasoning_parts.append(f"Ведущий трейдер: {top_trader['username']} (скор: {top_trader['score']}/10)")
        
        # Добавляем рыночный контекст
        if market_data.get('volatility'):
            vol_pct = market_data['volatility'] * 100
            reasoning_parts.append(f"Волатильность: {vol_pct:.1f}%")
        
        return ". ".join(reasoning_parts) + "."
    
    def generate_enhanced_recommendations(self, user_id: int = 1, strategy_type: str = None, limit: int = 5) -> List[Dict]:
        """
        Генерирует улучшенные торговые рекомендации с детализацией трейдеров
        """
        try:
            logger.info(f"Generating enhanced recommendations for user {user_id}, strategy: {strategy_type}")
            
            # Получаем топ-трейдеров
            top_traders = self.trader_scorer.get_top_traders(
                strategy_type=strategy_type,
                limit=20  # Берем больше для анализа консенсуса
            )
            
            if not top_traders:
                logger.warning("No traders found")
                return []
            
            # Анализируем консенсус по инструментам
            instrument_consensus = self._analyze_instrument_consensus(top_traders)
            
            recommendations = []
            
            for instrument, consensus_data in list(instrument_consensus.items())[:limit]:
                try:
                    # Получаем рыночные данные
                    market_data = self.price_provider.get_market_data(instrument)
                    if not market_data or not market_data.get('current_price'):
                        continue
                    
                    current_price = market_data['current_price']
                    
                    # Определяем действие на основе консенсуса
                    action = self._determine_action(consensus_data)
                    if action == 'HOLD':
                        continue
                    
                    # Рассчитываем размер позиции
                    confidence = consensus_data['confidence']
                    position_calc = self.position_sizer.calculate_position_size(
                        user_id=user_id,
                        symbol=instrument,
                        entry_price=current_price,
                        signal_confidence=confidence,
                        strategy_type=strategy_type or 'mixed'
                    )
                    
                    if not position_calc.get('can_invest'):
                        continue
                    
                    # Создаем детальную рекомендацию с информацией о трейдерах
                    recommendation = {
                        'symbol': instrument,
                        'company_name': market_data.get('company_info', {}).get('name', instrument),
                        'action': action,
                        'current_price': current_price,
                        'confidence': confidence,
                        'strategy_type': consensus_data['primary_strategy'],
                        
                        # Финансовые детали
                        'position_details': {
                            'recommended_shares': position_calc['recommended_shares'],
                            'investment_amount': position_calc['investment_amount'],
                            'portfolio_percentage': position_calc['portfolio_percentage'],
                            'max_risk_amount': position_calc['max_risk_amount'],
                            'stop_loss': position_calc['levels']['stop_loss'],
                            'take_profit': position_calc['levels']['take_profit'],
                            'risk_reward_ratio': position_calc['levels']['risk_reward_ratio']
                        },
                        
                        # Детали трейдеров и консенсуса
                        'trader_analysis': {
                            'total_traders_analyzed': consensus_data['total_traders'],
                            'consensus_percentage': consensus_data['consensus_percentage'],
                            'average_trader_score': consensus_data['average_score'],
                            'primary_strategy': consensus_data['primary_strategy'],
                            'supporting_traders': consensus_data['supporting_traders'],
                            'consensus_breakdown': consensus_data['consensus_breakdown']
                        },
                        
                        # Рыночные данные
                        'market_context': {
                            'volatility': market_data.get('volatility', 0),
                            'support_level': market_data.get('support_level'),
                            'resistance_level': market_data.get('resistance_level'),
                            'price_change_pct': market_data.get('price_change_pct'),
                            'volume': market_data.get('volume')
                        },
                        
                        # Обоснование
                        'reasoning': self._generate_reasoning(consensus_data, market_data, action),
                        
                        'timestamp': datetime.now().isoformat(),
                        'signal_id': f"{instrument}_{action}_{int(datetime.now().timestamp())}"
                    }
                    
                    recommendations.append(recommendation)
                    
                except Exception as e:
                    logger.error(f"Error processing instrument {instrument}: {e}")
                    continue
            
            logger.info(f"Generated {len(recommendations)} enhanced recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating enhanced recommendations: {e}")
            return []
    
    def get_market_overview(self, user_id: int = 1) -> Dict:
        """Получает обзор рынка и возможностей для пользователя"""
        try:
            # Получаем рекомендации для всех стратегий
            all_recommendations = self.generate_enhanced_recommendations(user_id, limit=10)
            day_trading_recs = self.generate_enhanced_recommendations(user_id, 'day_trading', limit=5)
            long_term_recs = self.generate_enhanced_recommendations(user_id, 'long_term', limit=5)
            
            # Анализируем общие тренды
            total_signals = len(all_recommendations)
            buy_signals = len([r for r in all_recommendations if r['action'] == 'BUY'])
            sell_signals = len([r for r in all_recommendations if r['action'] == 'SELL'])
            
            # Средняя уверенность
            avg_confidence = statistics.mean([r['confidence'] for r in all_recommendations]) if all_recommendations else 0
            
            # Топ инструменты по уверенности
            top_opportunities = sorted(all_recommendations, key=lambda x: x['confidence'], reverse=True)[:3]
            
            return {
                'summary': {
                    'total_signals': total_signals,
                    'buy_signals': buy_signals,
                    'sell_signals': sell_signals,
                    'average_confidence': round(avg_confidence, 2),
                    'market_sentiment': 'Bullish' if buy_signals > sell_signals else 'Bearish' if sell_signals > buy_signals else 'Neutral'
                },
                'strategies': {
                    'day_trading': {
                        'signals_count': len(day_trading_recs),
                        'avg_confidence': round(statistics.mean([r['confidence'] for r in day_trading_recs]), 2) if day_trading_recs else 0
                    },
                    'long_term': {
                        'signals_count': len(long_term_recs),
                        'avg_confidence': round(statistics.mean([r['confidence'] for r in long_term_recs]), 2) if long_term_recs else 0
                    }
                },
                'top_opportunities': top_opportunities,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return {}

# Глобальный экземпляр улучшенного генератора
enhanced_signal_generator_v2 = EnhancedSignalGeneratorV2()

