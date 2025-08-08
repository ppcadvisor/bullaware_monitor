"""
API эндпоинты для улучшенных торговых рекомендаций с управлением капиталом
"""
from flask import Blueprint, request, jsonify
import logging

from ..services.enhanced_signal_generator import enhanced_signal_generator
from ..services.position_sizer import position_sizer
from ..services.price_provider import price_provider
from ..models.user_profile import UserProfile, UserPosition

logger = logging.getLogger(__name__)

enhanced_signals_bp = Blueprint('enhanced_signals', __name__)

@enhanced_signals_bp.route('/api/enhanced-recommendations', methods=['POST'])
def get_enhanced_recommendations():
    """Получить улучшенные торговые рекомендации с управлением капиталом"""
    try:
        data = request.get_json() or {}
        
        # Параметры запроса
        user_id = data.get('user_id', 1)  # Дефолтный пользователь
        strategy_type = data.get('strategy_type')  # None для всех стратегий
        limit = data.get('limit', 5)
        
        # Генерируем рекомендации
        recommendations = enhanced_signal_generator.generate_enhanced_recommendations(
            user_id=user_id,
            strategy_type=strategy_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'total_count': len(recommendations),
            'user_id': user_id,
            'strategy_type': strategy_type
        })
        
    except Exception as e:
        logger.error(f"Error getting enhanced recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_bp.route('/api/market-overview', methods=['POST'])
def get_market_overview():
    """Получить обзор рынка и возможностей для пользователя"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 1)
        
        # Получаем обзор рынка
        overview = enhanced_signal_generator.get_market_overview(user_id)
        
        return jsonify({
            'success': True,
            'overview': overview
        })
        
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_bp.route('/api/user-profile', methods=['GET', 'POST'])
def manage_user_profile():
    """Управление профилем пользователя"""
    try:
        if request.method == 'GET':
            # Получение профиля
            user_id = request.args.get('user_id', 1, type=int)
            
            try:
                profile = UserProfile.get(UserProfile.user_id == user_id)
            except UserProfile.DoesNotExist:
                profile = UserProfile.get_or_create_profile(user_id)
            
            return jsonify({
                'success': True,
                'profile': {
                    'user_id': profile.user_id,
                    'total_capital': float(profile.total_capital),
                    'available_capital': float(profile.available_capital),
                    'invested_capital': float(profile.invested_capital),
                    'currency': profile.currency,
                    'risk_tolerance': profile.risk_tolerance,
                    'max_risk_per_trade': float(profile.max_risk_per_trade),
                    'max_portfolio_risk': float(profile.max_portfolio_risk),
                    'preferred_strategies': profile.preferred_strategies.split(','),
                    'enable_notifications': profile.enable_notifications,
                    'investment_capacity': profile.investment_capacity,
                    'risk_profile_settings': profile.risk_profile_settings
                }
            })
            
        elif request.method == 'POST':
            # Обновление профиля
            data = request.get_json()
            user_id = data.get('user_id', 1)
            
            try:
                profile = UserProfile.get(UserProfile.user_id == user_id)
            except UserProfile.DoesNotExist:
                profile = UserProfile.get_or_create_profile(user_id)
            
            # Обновляем поля
            if 'total_capital' in data:
                profile.total_capital = data['total_capital']
                profile.available_capital = data['total_capital'] - profile.invested_capital
            
            if 'risk_tolerance' in data:
                profile.risk_tolerance = data['risk_tolerance']
            
            if 'max_risk_per_trade' in data:
                profile.max_risk_per_trade = data['max_risk_per_trade']
            
            if 'max_portfolio_risk' in data:
                profile.max_portfolio_risk = data['max_portfolio_risk']
            
            if 'preferred_strategies' in data:
                profile.preferred_strategies = ','.join(data['preferred_strategies'])
            
            if 'currency' in data:
                profile.currency = data['currency']
            
            if 'enable_notifications' in data:
                profile.enable_notifications = data['enable_notifications']
            
            if 'notification_email' in data:
                profile.notification_email = data['notification_email']
            
            profile.save()
            
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully',
                'profile': {
                    'user_id': profile.user_id,
                    'total_capital': float(profile.total_capital),
                    'available_capital': float(profile.available_capital),
                    'risk_tolerance': profile.risk_tolerance,
                    'currency': profile.currency
                }
            })
            
    except Exception as e:
        logger.error(f"Error managing user profile: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_signals_bp.route('/api/test-enhanced', methods=['GET'])
def test_enhanced():
    """Тестовый эндпоинт для проверки работы улучшенной системы"""
    try:
        # Тестируем получение цены
        test_symbol = 'NVDA'
        current_price = price_provider.get_current_price(test_symbol)
        
        # Тестируем расчет позиции
        if current_price:
            position_calc = position_sizer.calculate_position_size(
                user_id=1,
                symbol=test_symbol,
                entry_price=current_price,
                signal_confidence=0.8,
                strategy_type='long_term'
            )
        else:
            position_calc = {'error': 'Could not get price'}
        
        return jsonify({
            'success': True,
            'test_results': {
                'symbol': test_symbol,
                'current_price': current_price,
                'position_calculation': position_calc,
                'yfinance_working': current_price is not None,
                'position_sizer_working': 'error' not in position_calc
            }
        })
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

