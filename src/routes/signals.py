from flask import Blueprint, jsonify, request
from src.services.bullaware_client import BullAwareClient
from src.services.signal_generator import SignalGenerator
from src.services.trader_scorer import TraderScorer
from src.models.trader import Trader, Signal, db
import os
import logging

logger = logging.getLogger(__name__)

signals_bp = Blueprint('signals', __name__)

# Initialize services
api_key = os.getenv('BULLAWARE_API_KEY', 'dbf32c91665bbf73c1a2a70fd3627dc787d281479d6b9860')
base_url = os.getenv('BULLAWARE_BASE_URL', 'https://api.bullaware.com/v1')

bullaware_client = BullAwareClient(api_key, base_url)
signal_generator = SignalGenerator(bullaware_client)
trader_scorer = TraderScorer(bullaware_client)

@signals_bp.route('/signals/generate', methods=['POST'])
def generate_signals():
    """Generate new trading signals"""
    try:
        strategy_type = request.json.get('strategy_type', 'all') if request.json else 'all'
        
        if strategy_type == 'all':
            result = signal_generator.generate_all_signals()
        else:
            signals = signal_generator.generate_signals_for_strategy(strategy_type)
            signal_generator.save_signals_to_db(signals)
            result = {
                'success': True,
                'signals': {strategy_type: signals},
                'total_signals': len(signals)
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@signals_bp.route('/signals', methods=['GET'])
def get_signals():
    """Get trading signals with filtering"""
    try:
        strategy_type = request.args.get('strategy_type', 'all')
        limit = int(request.args.get('limit', 20))
        min_confidence = float(request.args.get('min_confidence', 0.0))
        
        query = Signal.query.filter_by(is_active=True)
        
        if strategy_type != 'all':
            query = query.filter_by(strategy_type=strategy_type)
        
        if min_confidence > 0:
            query = query.filter(Signal.confidence >= min_confidence)
        
        signals = query.order_by(Signal.confidence.desc(), Signal.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [signal.to_dict() for signal in signals],
            'count': len(signals),
            'filters': {
                'strategy_type': strategy_type,
                'min_confidence': min_confidence,
                'limit': limit
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@signals_bp.route('/signals/<int:signal_id>', methods=['GET'])
def get_signal_details(signal_id):
    """Get detailed information about a specific signal"""
    try:
        signal = Signal.query.get(signal_id)
        
        if not signal:
            return jsonify({'success': False, 'error': 'Signal not found'}), 404
        
        signal_data = signal.to_dict()
        
        # Add supporting trader details
        if signal.supporting_traders:
            import json
            supporting_traders = json.loads(signal.supporting_traders)
            
            # Get trader details
            trader_details = []
            for trader_info in supporting_traders:
                username = trader_info.get('username')
                trader = Trader.query.filter_by(username=username).first()
                if trader:
                    trader_details.append({
                        'username': username,
                        'display_name': trader.display_name,
                        'score': trader.total_score,
                        'rank': trader.rank,
                        'direction': trader_info.get('direction'),
                        'weight': trader_info.get('weight')
                    })
            
            signal_data['supporting_trader_details'] = trader_details
        
        return jsonify({
            'success': True,
            'data': signal_data
        })
        
    except Exception as e:
        logger.error(f"Error getting signal details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@signals_bp.route('/signals/<int:signal_id>/deactivate', methods=['POST'])
def deactivate_signal(signal_id):
    """Deactivate a specific signal"""
    try:
        signal = Signal.query.get(signal_id)
        
        if not signal:
            return jsonify({'success': False, 'error': 'Signal not found'}), 404
        
        signal.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Signal {signal_id} deactivated'
        })
        
    except Exception as e:
        logger.error(f"Error deactivating signal: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@signals_bp.route('/traders/refresh-rankings', methods=['POST'])
def refresh_trader_rankings():
    """Refresh trader rankings and scores"""
    try:
        # Get trader limit from request
        limit = int(request.json.get('limit', 30)) if request.json else 30
        
        # Get top traders from API
        usernames = trader_scorer.get_top_traders_from_api(limit=limit)
        
        if not usernames:
            return jsonify({'success': False, 'error': 'No traders found from API'}), 500
        
        # Analyze and score traders
        scored_traders = trader_scorer.analyze_and_score_traders(usernames)
        
        # Update rankings in database
        trader_scorer.update_trader_rankings(scored_traders)
        
        # Separate by trader type for response
        day_traders = [t for t in scored_traders if t['trader_type'] == 'day_trader']
        long_term_traders = [t for t in scored_traders if t['trader_type'] == 'long_term']
        
        return jsonify({
            'success': True,
            'message': f'Refreshed rankings for {len(scored_traders)} traders',
            'total_traders': len(scored_traders),
            'day_traders': len(day_traders),
            'long_term_traders': len(long_term_traders),
            'top_day_traders': [{'username': t['username'], 'score': t['score']} for t in day_traders[:5]],
            'top_long_term_traders': [{'username': t['username'], 'score': t['score']} for t in long_term_traders[:5]]
        })
        
    except Exception as e:
        logger.error(f"Error refreshing trader rankings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@signals_bp.route('/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get analytics summary"""
    try:
        # Count traders by type
        day_traders_count = Trader.query.filter_by(trader_type='day_trader', is_active=True).count()
        long_term_traders_count = Trader.query.filter_by(trader_type='long_term', is_active=True).count()
        
        # Count signals by type
        day_trading_signals = Signal.query.filter_by(strategy_type='day_trading', is_active=True).count()
        long_term_signals = Signal.query.filter_by(strategy_type='long_term', is_active=True).count()
        
        # Get top signals by confidence
        top_signals = Signal.query.filter_by(is_active=True).order_by(Signal.confidence.desc()).limit(5).all()
        
        # Get recent activity
        recent_signals = Signal.query.filter_by(is_active=True).order_by(Signal.created_at.desc()).limit(10).all()
        
        return jsonify({
            'success': True,
            'data': {
                'traders': {
                    'day_traders': day_traders_count,
                    'long_term_traders': long_term_traders_count,
                    'total': day_traders_count + long_term_traders_count
                },
                'signals': {
                    'day_trading': day_trading_signals,
                    'long_term': long_term_signals,
                    'total': day_trading_signals + long_term_signals
                },
                'top_signals': [
                    {
                        'id': s.id,
                        'instrument': s.instrument,
                        'action': s.action,
                        'confidence': s.confidence,
                        'strategy_type': s.strategy_type
                    } for s in top_signals
                ],
                'recent_activity': [
                    {
                        'id': s.id,
                        'instrument': s.instrument,
                        'action': s.action,
                        'confidence': s.confidence,
                        'strategy_type': s.strategy_type,
                        'created_at': s.created_at.isoformat() if s.created_at else None
                    } for s in recent_signals
                ]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@signals_bp.route('/test/scoring', methods=['POST'])
def test_scoring():
    """Test trader scoring with a specific trader"""
    try:
        username = request.json.get('username') if request.json else None
        
        if not username:
            return jsonify({'success': False, 'error': 'Username required'}), 400
        
        # Analyze single trader
        scored_traders = trader_scorer.analyze_and_score_traders([username])
        
        if not scored_traders:
            return jsonify({'success': False, 'error': f'Could not analyze trader {username}'}), 404
        
        trader_data = scored_traders[0]
        
        return jsonify({
            'success': True,
            'data': trader_data
        })
        
    except Exception as e:
        logger.error(f"Error testing scoring: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

