"""
API эндпоинты для улучшенных торговых рекомендаций с детализацией трейдеров
"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime

from ..services.enhanced_signal_generator_v2 import enhanced_signal_generator_v2
from ..services.position_sizer import position_sizer
from ..services.price_provider import price_provider
from ..models.user_profile import UserProfile, UserPosition

logger = logging.getLogger(__name__)

enhanced_signals_v2_bp = Blueprint('enhanced_signals_v2', __name__)

@enhanced_signals_v2_bp.route('/api/v2/enhanced-recommendations', methods=['POST'])
def get_enhanced_recommendations_v2():
    """Получить улучшенные торговые рекомендации с детализацией трейдеров"""
    try:
        data = request.get_json() or {}
        
        # Параметры запроса
        user_id = data.get('user_id', 1)
        strategy_type = data.get('strategy_type')
        limit = data.get('limit', 5)
        
        # Генерируем рекомендации с детализацией трейдеров
        recommendations = enhanced_signal_generator_v2.generate_enhanced_recommendations(
            user_id=user_id,
            strategy_type=strategy_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'total_count': len(recommendations),
            'user_id': user_id,
            'strategy_type': strategy_type,
            'version': '2.0'
        })
        
    except Exception as e:
        logger.error(f"Error getting enhanced recommendations v2: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_v2_bp.route('/api/v2/market-overview', methods=['POST'])
def get_market_overview_v2():
    """Получить обзор рынка с детализацией трейдеров"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 1)
        
        # Получаем обзор рынка
        overview = enhanced_signal_generator_v2.get_market_overview(user_id)
        
        return jsonify({
            'success': True,
            'overview': overview,
            'version': '2.0'
        })
        
    except Exception as e:
        logger.error(f"Error getting market overview v2: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_v2_bp.route('/api/v2/trader-consensus/<symbol>', methods=['GET'])
def get_trader_consensus(symbol):
    """Получить детальный консенсус трейдеров по конкретному инструменту"""
    try:
        symbol = symbol.upper()
        
        # Получаем топ-трейдеров
        from ..services.trader_scorer import trader_scorer
        top_traders = trader_scorer.get_top_traders(limit=20)
        
        if not top_traders:
            return jsonify({
                'success': False,
                'error': 'No traders found'
            }), 404
        
        # Анализируем консенсус
        instrument_consensus = enhanced_signal_generator_v2._analyze_instrument_consensus(top_traders)
        
        if symbol not in instrument_consensus:
            return jsonify({
                'success': False,
                'error': f'No consensus data found for {symbol}'
            }), 404
        
        consensus_data = instrument_consensus[symbol]
        
        # Получаем рыночные данные
        market_data = price_provider.get_market_data(symbol)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'consensus': consensus_data,
            'market_data': market_data,
            'analysis_timestamp': enhanced_signal_generator_v2._generate_reasoning(
                consensus_data, market_data or {}, 
                'BUY' if consensus_data['consensus_direction'] == 'LONG' else 'SELL'
            )
        })
        
    except Exception as e:
        logger.error(f"Error getting trader consensus for {symbol}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_v2_bp.route('/api/v2/trader-details/<username>', methods=['GET'])
def get_trader_details(username):
    """Получить детальную информацию о конкретном трейдере"""
    try:
        from ..services.bullaware_client import bullaware_client
        
        # Получаем информацию о трейдере
        trader_info = bullaware_client.get_investor_info(username)
        if not trader_info:
            return jsonify({
                'success': False,
                'error': f'Trader {username} not found'
            }), 404
        
        # Получаем портфель трейдера
        portfolio = bullaware_client.get_investor_portfolio(username)
        
        # Получаем статистику
        stats = bullaware_client.get_investor_stats(username)
        
        # Рассчитываем скор трейдера
        from ..services.trader_scorer import trader_scorer
        score_data = trader_scorer.calculate_trader_score(trader_info, stats or {})
        
        return jsonify({
            'success': True,
            'trader': {
                'username': username,
                'info': trader_info,
                'portfolio': portfolio or [],
                'stats': stats or {},
                'score': score_data,
                'analysis_timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting trader details for {username}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_v2_bp.route('/api/v2/demo-recommendation', methods=['GET'])
def get_demo_recommendation():
    """Получить демонстрационную рекомендацию с полной детализацией"""
    try:
        # Создаем демонстрационную рекомендацию
        demo_recommendation = {
            'symbol': 'NVDA',
            'company_name': 'NVIDIA Corporation',
            'action': 'BUY',
            'current_price': 180.77,
            'confidence': 0.85,
            'strategy_type': 'long_term',
            
            # Финансовые детали
            'position_details': {
                'recommended_shares': 5,
                'investment_amount': 903.85,
                'portfolio_percentage': 9.0,
                'max_risk_amount': 22.90,
                'stop_loss': 176.19,
                'take_profit': 182.04,
                'risk_reward_ratio': 0.28
            },
            
            # Детали трейдеров и консенсуса
            'trader_analysis': {
                'total_traders_analyzed': 8,
                'consensus_percentage': 75.0,
                'average_trader_score': 8.2,
                'primary_strategy': 'long_term',
                'supporting_traders': [
                    {
                        'username': 'JeppeKirkBonde',
                        'score': 8.5,
                        'strategy_type': 'long_term',
                        'direction': 'LONG',
                        'position_size': 15000,
                        'weight': 0.85,
                        'portfolio_percentage': 15.2
                    },
                    {
                        'username': 'TradingMaster',
                        'score': 7.8,
                        'strategy_type': 'day_trading',
                        'direction': 'LONG',
                        'position_size': 8500,
                        'weight': 0.78,
                        'portfolio_percentage': 8.5
                    },
                    {
                        'username': 'InvestorPro',
                        'score': 8.2,
                        'strategy_type': 'mixed',
                        'direction': 'LONG',
                        'position_size': 12000,
                        'weight': 0.82,
                        'portfolio_percentage': 12.0
                    }
                ],
                'consensus_breakdown': {
                    'long': {
                        'percentage': 75.0,
                        'traders': 6,
                        'total_weight': 4.8
                    },
                    'short': {
                        'percentage': 25.0,
                        'traders': 2,
                        'total_weight': 1.6
                    }
                }
            },
            
            # Рыночные данные
            'market_context': {
                'volatility': 0.0169,
                'support_level': 162.02,
                'resistance_level': 183.88,
                'price_change_pct': 2.1,
                'volume': 45000000
            },
            
            # Обоснование
            'reasoning': 'BUY рекомендация основана на анализе 8 топ-трейдеров eToro. Консенсус: 75.0% трейдеров поддерживают позицию. Средняя оценка трейдеров: 8.2/10. Основная стратегия: long_term. Ведущий трейдер: JeppeKirkBonde (скор: 8.5/10). Волатильность: 1.7%.',
            
            'timestamp': datetime.now().isoformat(),
            'signal_id': f"NVDA_BUY_DEMO_{int(datetime.now().timestamp())}"
        }
        
        return jsonify({
            'success': True,
            'demo_recommendation': demo_recommendation,
            'note': 'This is a demonstration recommendation showing the full transparency features'
        })
        
    except Exception as e:
        logger.error(f"Error generating demo recommendation: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

