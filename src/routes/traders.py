from flask import Blueprint, jsonify, request
from src.services.bullaware_client import BullAwareClient
from src.services.trader_analyzer import TraderAnalyzer
from src.models.trader import Trader, Position, Signal, db
import os
import logging

logger = logging.getLogger(__name__)

traders_bp = Blueprint('traders', __name__)

# Initialize services
api_key = os.getenv('BULLAWARE_API_KEY', 'dbf32c91665bbf73c1a2a70fd3627dc787d281479d6b9860')
base_url = os.getenv('BULLAWARE_BASE_URL', 'https://api.bullaware.com/v1')

bullaware_client = BullAwareClient(api_key, base_url)
trader_analyzer = TraderAnalyzer(bullaware_client)

@traders_bp.route('/traders', methods=['GET'])
def get_traders():
    """Get list of traders with optional filtering"""
    try:
        trader_type = request.args.get('type', 'all')  # 'day_trader', 'long_term', or 'all'
        limit = int(request.args.get('limit', 10))
        
        query = Trader.query
        
        if trader_type != 'all':
            query = query.filter_by(trader_type=trader_type)
        
        traders = query.filter_by(is_active=True).order_by(Trader.rank.asc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [trader.to_dict() for trader in traders],
            'count': len(traders)
        })
        
    except Exception as e:
        logger.error(f"Error getting traders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@traders_bp.route('/traders/<username>', methods=['GET'])
def get_trader_details(username):
    """Get detailed information about a specific trader"""
    try:
        trader = Trader.query.filter_by(username=username).first()
        
        if not trader:
            return jsonify({'success': False, 'error': 'Trader not found'}), 404
        
        # Get current positions
        positions = Position.query.filter_by(trader_username=username).all()
        
        trader_data = trader.to_dict()
        trader_data['positions'] = [pos.to_dict() for pos in positions]
        
        return jsonify({
            'success': True,
            'data': trader_data
        })
        
    except Exception as e:
        logger.error(f"Error getting trader details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@traders_bp.route('/traders/refresh', methods=['POST'])
def refresh_traders():
    """Refresh trader data from BullAware API"""
    try:
        # Get list of investors from BullAware
        investors_data = bullaware_client.get_investors(limit=50)
        
        if not investors_data or 'items' not in investors_data:
            return jsonify({'success': False, 'error': 'No data from BullAware API'}), 500
        
        updated_traders = []
        
        for investor in investors_data['items'][:20]:  # Limit to 20 to respect rate limits
            username = investor.get('username')
            if not username:
                continue
            
            try:
                # Analyze trader (this will make several API calls)
                analysis = trader_analyzer.analyze_trader(username, 'long_term')  # Default to long_term
                
                if analysis:
                    # Update or create trader record
                    trader = Trader.query.filter_by(username=username).first()
                    if not trader:
                        trader = Trader(username=username)
                        db.session.add(trader)
                    
                    # Update trader data
                    for key, value in analysis.items():
                        if hasattr(trader, key):
                            setattr(trader, key, value)
                    
                    # Calculate score
                    trader.total_score = trader_analyzer.calculate_trader_score(analysis, analysis['trader_type'])
                    
                    updated_traders.append(username)
                    
            except Exception as e:
                logger.error(f"Error analyzing trader {username}: {e}")
                continue
        
        # Commit changes
        db.session.commit()
        
        # Update ranks
        update_trader_ranks()
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(updated_traders)} traders',
            'updated_traders': updated_traders
        })
        
    except Exception as e:
        logger.error(f"Error refreshing traders: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@traders_bp.route('/signals', methods=['GET'])
def get_signals():
    """Get trading signals"""
    try:
        strategy_type = request.args.get('type', 'all')  # 'day_trading', 'long_term', or 'all'
        limit = int(request.args.get('limit', 20))
        
        query = Signal.query.filter_by(is_active=True)
        
        if strategy_type != 'all':
            query = query.filter_by(strategy_type=strategy_type)
        
        signals = query.order_by(Signal.created_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [signal.to_dict() for signal in signals],
            'count': len(signals)
        })
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@traders_bp.route('/api-test', methods=['GET'])
def test_api():
    """Test BullAware API connection"""
    try:
        # Test basic API call
        investors = bullaware_client.get_investors(limit=3)
        
        return jsonify({
            'success': True,
            'message': 'API connection successful',
            'sample_data': investors
        })
        
    except Exception as e:
        logger.error(f"API test failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def update_trader_ranks():
    """Update trader ranks based on scores"""
    try:
        # Update ranks for day traders
        day_traders = Trader.query.filter_by(trader_type='day_trader', is_active=True).order_by(Trader.total_score.desc()).all()
        for i, trader in enumerate(day_traders):
            trader.rank = i + 1
        
        # Update ranks for long-term traders
        long_term_traders = Trader.query.filter_by(trader_type='long_term', is_active=True).order_by(Trader.total_score.desc()).all()
        for i, trader in enumerate(long_term_traders):
            trader.rank = i + 1
        
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Error updating trader ranks: {e}")
        raise

