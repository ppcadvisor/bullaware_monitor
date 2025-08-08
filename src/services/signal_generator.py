import logging
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from src.services.bullaware_client import BullAwareClient
from src.models.trader import Trader, Position, Signal, db

logger = logging.getLogger(__name__)

class SignalGenerator:
    """Service for generating trading signals based on top traders consensus"""
    
    def __init__(self, bullaware_client: BullAwareClient):
        self.client = bullaware_client
        
        # Signal generation thresholds
        self.consensus_thresholds = {
            'day_trading': {
                'buy': 0.6,   # 60% consensus for buy signal
                'sell': 0.6,  # 60% consensus for sell signal
                'min_traders': 3  # Minimum number of traders for signal
            },
            'long_term': {
                'buy': 0.7,   # 70% consensus for buy signal
                'sell': 0.7,  # 70% consensus for sell signal
                'min_traders': 4  # Minimum number of traders for signal
            }
        }
        
        # Confidence scoring weights
        self.confidence_weights = {
            'consensus_strength': 0.4,
            'trader_quality': 0.3,
            'position_size': 0.2,
            'recent_performance': 0.1
        }
    
    def get_top_traders_positions(self, trader_type: str, limit: int = 10) -> List[Dict]:
        """Get current positions of top traders"""
        try:
            # Get top traders from database
            top_traders = Trader.query.filter_by(
                trader_type=trader_type, 
                is_active=True
            ).order_by(Trader.rank.asc()).limit(limit).all()
            
            if not top_traders:
                logger.warning(f"No top traders found for type: {trader_type}")
                return []
            
            traders_positions = []
            
            for trader in top_traders:
                try:
                    # Get current portfolio from API
                    portfolio_data = self.client.get_investor_portfolio(trader.username)
                    
                    if portfolio_data and 'positions' in portfolio_data:
                        trader_info = {
                            'username': trader.username,
                            'score': trader.total_score or 0,
                            'rank': trader.rank or 999,
                            'positions': portfolio_data['positions']
                        }
                        traders_positions.append(trader_info)
                        
                        # Update positions in database
                        self._update_trader_positions(trader.username, portfolio_data['positions'])
                        
                except Exception as e:
                    logger.error(f"Error getting positions for trader {trader.username}: {e}")
                    continue
            
            return traders_positions
            
        except Exception as e:
            logger.error(f"Error getting top traders positions: {e}")
            return []
    
    def _update_trader_positions(self, username: str, positions_data: List[Dict]):
        """Update trader positions in database"""
        try:
            # Clear existing positions
            Position.query.filter_by(trader_username=username).delete()
            
            # Add new positions
            for pos_data in positions_data:
                position = Position(
                    trader_username=username,
                    instrument=pos_data.get('symbol', ''),
                    direction='long' if pos_data.get('direction', 1) > 0 else 'short',
                    size=pos_data.get('value', 0),
                    current_price=pos_data.get('currentPrice', 0),
                    pnl=pos_data.get('netProfit', 0)
                )
                db.session.add(position)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating positions for {username}: {e}")
            db.session.rollback()
    
    def calculate_instrument_consensus(self, traders_positions: List[Dict], instrument: str) -> Dict:
        """Calculate consensus for a specific instrument"""
        long_weight = 0.0
        short_weight = 0.0
        total_weight = 0.0
        supporting_traders = []
        
        for trader_data in traders_positions:
            trader_score = trader_data['score']
            trader_weight = max(trader_score, 0.1)  # Minimum weight to avoid zero
            
            for position in trader_data['positions']:
                if position.get('symbol') == instrument:
                    direction = position.get('direction', 1)
                    position_size = position.get('value', 0)
                    
                    # Weight by trader score and position size
                    position_weight = trader_weight * min(position_size / 100.0, 1.0)  # Normalize position size
                    
                    if direction > 0:  # Long position
                        long_weight += position_weight
                    else:  # Short position
                        short_weight += position_weight
                    
                    total_weight += position_weight
                    
                    supporting_traders.append({
                        'username': trader_data['username'],
                        'direction': 'long' if direction > 0 else 'short',
                        'weight': position_weight,
                        'score': trader_score,
                        'position_size': position_size
                    })
        
        if total_weight == 0:
            return {
                'instrument': instrument,
                'consensus': 0.0,
                'direction': 'neutral',
                'supporting_traders': [],
                'trader_count': 0
            }
        
        # Calculate consensus (-1 to 1, where -1 is full short, 1 is full long)
        consensus = (long_weight - short_weight) / total_weight
        
        # Determine dominant direction
        if abs(consensus) < 0.1:
            direction = 'neutral'
        elif consensus > 0:
            direction = 'long'
        else:
            direction = 'short'
        
        return {
            'instrument': instrument,
            'consensus': consensus,
            'direction': direction,
            'supporting_traders': supporting_traders,
            'trader_count': len(supporting_traders),
            'long_weight': long_weight,
            'short_weight': short_weight,
            'total_weight': total_weight
        }
    
    def calculate_signal_confidence(self, consensus_data: Dict, strategy_type: str) -> float:
        """Calculate confidence score for a signal"""
        consensus_strength = abs(consensus_data['consensus'])
        trader_count = consensus_data['trader_count']
        supporting_traders = consensus_data['supporting_traders']
        
        # Consensus strength component (0-1)
        consensus_score = min(consensus_strength, 1.0)
        
        # Trader quality component (average score of supporting traders)
        if supporting_traders:
            avg_trader_score = np.mean([t['score'] for t in supporting_traders])
            trader_quality_score = min(avg_trader_score, 1.0)
        else:
            trader_quality_score = 0.0
        
        # Position size component (average position size)
        if supporting_traders:
            avg_position_size = np.mean([t['position_size'] for t in supporting_traders])
            position_size_score = min(avg_position_size / 10.0, 1.0)  # Normalize to 0-1
        else:
            position_size_score = 0.0
        
        # Recent performance component (placeholder - would need historical data)
        recent_performance_score = 0.7  # Default value
        
        # Calculate weighted confidence
        confidence = (
            self.confidence_weights['consensus_strength'] * consensus_score +
            self.confidence_weights['trader_quality'] * trader_quality_score +
            self.confidence_weights['position_size'] * position_size_score +
            self.confidence_weights['recent_performance'] * recent_performance_score
        )
        
        # Apply trader count penalty if too few traders
        min_traders = self.consensus_thresholds[strategy_type]['min_traders']
        if trader_count < min_traders:
            confidence *= trader_count / min_traders
        
        return min(confidence, 1.0)
    
    def generate_signals_for_strategy(self, strategy_type: str) -> List[Dict]:
        """Generate trading signals for a specific strategy"""
        try:
            logger.info(f"Generating signals for strategy: {strategy_type}")
            
            # Get top traders positions
            traders_positions = self.get_top_traders_positions(strategy_type)
            
            if not traders_positions:
                logger.warning(f"No trader positions found for {strategy_type}")
                return []
            
            # Collect all unique instruments
            instruments = set()
            for trader_data in traders_positions:
                for position in trader_data['positions']:
                    symbol = position.get('symbol')
                    if symbol:
                        instruments.add(symbol)
            
            logger.info(f"Found {len(instruments)} unique instruments")
            
            signals = []
            thresholds = self.consensus_thresholds[strategy_type]
            
            for instrument in instruments:
                # Calculate consensus for this instrument
                consensus_data = self.calculate_instrument_consensus(traders_positions, instrument)
                
                # Check if consensus meets threshold
                consensus_strength = abs(consensus_data['consensus'])
                trader_count = consensus_data['trader_count']
                
                if (consensus_strength >= thresholds['buy'] and 
                    trader_count >= thresholds['min_traders']):
                    
                    # Determine action
                    if consensus_data['consensus'] > 0:
                        action = 'buy'
                    else:
                        action = 'sell'
                    
                    # Calculate confidence
                    confidence = self.calculate_signal_confidence(consensus_data, strategy_type)
                    
                    # Create signal
                    signal_data = {
                        'instrument': instrument,
                        'action': action,
                        'strategy_type': strategy_type,
                        'confidence': confidence,
                        'consensus_strength': consensus_strength,
                        'supporting_traders': json.dumps([
                            {
                                'username': t['username'],
                                'direction': t['direction'],
                                'weight': t['weight']
                            } for t in consensus_data['supporting_traders']
                        ]),
                        'reasoning': self._generate_reasoning(consensus_data, action, strategy_type)
                    }
                    
                    signals.append(signal_data)
            
            # Sort by confidence (highest first)
            signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            logger.info(f"Generated {len(signals)} signals for {strategy_type}")
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {strategy_type}: {e}")
            return []
    
    def _generate_reasoning(self, consensus_data: Dict, action: str, strategy_type: str) -> str:
        """Generate human-readable reasoning for the signal"""
        trader_count = consensus_data['trader_count']
        consensus_strength = abs(consensus_data['consensus'])
        direction = consensus_data['direction']
        
        reasoning = f"{action.upper()} signal for {consensus_data['instrument']} "
        reasoning += f"based on {trader_count} top {strategy_type.replace('_', ' ')} traders "
        reasoning += f"with {consensus_strength:.1%} consensus strength. "
        reasoning += f"Traders are predominantly {direction} on this instrument."
        
        return reasoning
    
    def save_signals_to_db(self, signals: List[Dict]):
        """Save generated signals to database"""
        try:
            # Deactivate old signals
            Signal.query.filter_by(is_active=True).update({'is_active': False})
            
            # Add new signals
            for signal_data in signals:
                signal = Signal(
                    instrument=signal_data['instrument'],
                    action=signal_data['action'],
                    strategy_type=signal_data['strategy_type'],
                    confidence=signal_data['confidence'],
                    consensus_strength=signal_data['consensus_strength'],
                    supporting_traders=signal_data['supporting_traders'],
                    reasoning=signal_data['reasoning']
                )
                db.session.add(signal)
            
            db.session.commit()
            logger.info(f"Saved {len(signals)} signals to database")
            
        except Exception as e:
            logger.error(f"Error saving signals to database: {e}")
            db.session.rollback()
    
    def generate_all_signals(self) -> Dict:
        """Generate signals for all strategies"""
        try:
            all_signals = {}
            
            # Generate signals for day trading
            day_trading_signals = self.generate_signals_for_strategy('day_trading')
            all_signals['day_trading'] = day_trading_signals
            
            # Generate signals for long term
            long_term_signals = self.generate_signals_for_strategy('long_term')
            all_signals['long_term'] = long_term_signals
            
            # Save all signals to database
            all_signals_list = day_trading_signals + long_term_signals
            self.save_signals_to_db(all_signals_list)
            
            return {
                'success': True,
                'signals': all_signals,
                'total_signals': len(all_signals_list),
                'day_trading_count': len(day_trading_signals),
                'long_term_count': len(long_term_signals)
            }
            
        except Exception as e:
            logger.error(f"Error generating all signals: {e}")
            return {
                'success': False,
                'error': str(e),
                'signals': {}
            }

