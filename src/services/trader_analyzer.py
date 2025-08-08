import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from src.services.bullaware_client import BullAwareClient
from src.models.trader import Trader, Position, db

logger = logging.getLogger(__name__)

class TraderAnalyzer:
    """Service for analyzing traders and calculating scores"""
    
    def __init__(self, bullaware_client: BullAwareClient):
        self.client = bullaware_client
        
        # Scoring weights for day traders
        self.day_trader_weights = {
            'win_rate': 0.25,
            'avg_profit_loss_ratio': 0.20,
            'max_drawdown': -0.20,  # Negative because lower is better
            'consistency_score': 0.15,
            'risk_score': -0.10,    # Negative because lower is better
            'trade_frequency': 0.10
        }
        
        # Scoring weights for long-term investors
        self.long_term_weights = {
            'cagr': 0.25,
            'sharpe_ratio': 0.20,
            'max_drawdown': -0.15,  # Negative because lower is better
            'consistency_score': 0.15,
            'copiers_count': 0.10,
            'holding_period_avg': 0.10,
            'diversification_score': 0.05
        }
    
    def normalize_metric(self, values: List[float], higher_is_better: bool = True) -> List[float]:
        """Normalize metrics to 0-1 scale"""
        if not values or len(values) == 0:
            return []
        
        values = np.array(values)
        min_val = np.min(values)
        max_val = np.max(values)
        
        if max_val == min_val:
            return [0.5] * len(values)  # All equal, return middle value
        
        if higher_is_better:
            normalized = (values - min_val) / (max_val - min_val)
        else:
            normalized = (max_val - values) / (max_val - min_val)
        
        return normalized.tolist()
    
    def calculate_win_rate(self, trades_data: Dict) -> float:
        """Calculate win rate from trades data"""
        if not trades_data or 'trades' not in trades_data:
            return 0.0
        
        trades = trades_data['trades']
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if trade.get('profit', 0) > 0)
        total_trades = len(trades)
        
        return winning_trades / total_trades if total_trades > 0 else 0.0
    
    def calculate_avg_profit_loss_ratio(self, trades_data: Dict) -> float:
        """Calculate average profit to loss ratio"""
        if not trades_data or 'trades' not in trades_data:
            return 0.0
        
        trades = trades_data['trades']
        if not trades:
            return 0.0
        
        profits = [trade.get('profit', 0) for trade in trades if trade.get('profit', 0) > 0]
        losses = [abs(trade.get('profit', 0)) for trade in trades if trade.get('profit', 0) < 0]
        
        if not profits or not losses:
            return 0.0
        
        avg_profit = np.mean(profits)
        avg_loss = np.mean(losses)
        
        return avg_profit / avg_loss if avg_loss > 0 else 0.0
    
    def calculate_consistency_score(self, metrics_history: Dict) -> float:
        """Calculate consistency score based on return volatility"""
        if not metrics_history or 'history' not in metrics_history:
            return 0.0
        
        history = metrics_history['history']
        if not history or len(history) < 2:
            return 0.0
        
        # Extract returns (assuming there's a profit field)
        returns = []
        for i in range(1, len(history)):
            prev_equity = history[i-1].get('equity', 0)
            curr_equity = history[i].get('equity', 0)
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        # Lower volatility = higher consistency
        volatility = np.std(returns)
        # Convert to 0-1 scale where lower volatility gets higher score
        consistency = 1 / (1 + volatility) if volatility > 0 else 1.0
        
        return min(consistency, 1.0)
    
    def calculate_trade_frequency(self, trades_data: Dict) -> float:
        """Calculate trade frequency (trades per month)"""
        if not trades_data or 'trades' not in trades_data:
            return 0.0
        
        trades = trades_data['trades']
        if not trades:
            return 0.0
        
        # Assume trades have date field
        dates = []
        for trade in trades:
            if 'date' in trade:
                try:
                    date = datetime.fromisoformat(trade['date'].replace('Z', '+00:00'))
                    dates.append(date)
                except:
                    continue
        
        if len(dates) < 2:
            return 0.0
        
        dates.sort()
        time_span_months = (dates[-1] - dates[0]).days / 30.44  # Average days per month
        
        return len(trades) / time_span_months if time_span_months > 0 else 0.0
    
    def calculate_cagr(self, metrics_history: Dict) -> float:
        """Calculate Compound Annual Growth Rate"""
        if not metrics_history or 'history' not in metrics_history:
            return 0.0
        
        history = metrics_history['history']
        if not history or len(history) < 2:
            return 0.0
        
        # Sort by date
        history_sorted = sorted(history, key=lambda x: x.get('date', ''))
        
        initial_equity = history_sorted[0].get('equity', 0)
        final_equity = history_sorted[-1].get('equity', 0)
        
        if initial_equity <= 0 or final_equity <= 0:
            return 0.0
        
        # Calculate time span in years
        try:
            start_date = datetime.fromisoformat(history_sorted[0]['date'].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(history_sorted[-1]['date'].replace('Z', '+00:00'))
            years = (end_date - start_date).days / 365.25
        except:
            return 0.0
        
        if years <= 0:
            return 0.0
        
        cagr = (final_equity / initial_equity) ** (1 / years) - 1
        return cagr
    
    def calculate_sharpe_ratio(self, metrics_history: Dict, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        if not metrics_history or 'history' not in metrics_history:
            return 0.0
        
        history = metrics_history['history']
        if not history or len(history) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(history)):
            prev_equity = history[i-1].get('equity', 0)
            curr_equity = history[i].get('equity', 0)
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualize (assuming monthly data)
        annual_return = avg_return * 12
        annual_std = std_return * np.sqrt(12)
        
        sharpe = (annual_return - risk_free_rate) / annual_std
        return sharpe
    
    def calculate_holding_period(self, trades_data: Dict) -> float:
        """Calculate average holding period in days"""
        if not trades_data or 'trades' not in trades_data:
            return 0.0
        
        trades = trades_data['trades']
        if not trades:
            return 0.0
        
        holding_periods = []
        for trade in trades:
            if 'open_date' in trade and 'close_date' in trade:
                try:
                    open_date = datetime.fromisoformat(trade['open_date'].replace('Z', '+00:00'))
                    close_date = datetime.fromisoformat(trade['close_date'].replace('Z', '+00:00'))
                    holding_period = (close_date - open_date).days
                    if holding_period > 0:
                        holding_periods.append(holding_period)
                except:
                    continue
        
        return np.mean(holding_periods) if holding_periods else 0.0
    
    def calculate_diversification_score(self, portfolio_data: Dict) -> float:
        """Calculate portfolio diversification score"""
        if not portfolio_data or 'positions' not in portfolio_data:
            return 0.0
        
        positions = portfolio_data['positions']
        if not positions:
            return 0.0
        
        # Count unique instruments and sectors
        instruments = set()
        sectors = set()
        
        for position in positions:
            if 'instrument' in position:
                instruments.add(position['instrument'])
            if 'sector' in position:
                sectors.add(position['sector'])
        
        # Simple diversification score based on number of instruments
        # More sophisticated version would consider correlations
        diversification = min(len(instruments) / 10.0, 1.0)  # Normalize to max 10 instruments
        
        return diversification
    
    def analyze_trader(self, username: str, trader_type: str) -> Dict:
        """Analyze a single trader and return metrics"""
        try:
            # Get all necessary data
            details = self.client.get_investor_details(username)
            metrics = self.client.get_investor_metrics(username)
            metrics_history = self.client.get_investor_metrics_history(username)
            portfolio = self.client.get_investor_portfolio(username)
            trades = self.client.get_investor_trades(username)
            risk_score_data = self.client.get_investor_risk_score_monthly(username)
            copiers_data = self.client.get_investor_copiers_history(username)
            
            # Calculate metrics
            analysis = {
                'username': username,
                'display_name': details.get('name', username),
                'trader_type': trader_type,
                'win_rate': self.calculate_win_rate(trades),
                'avg_profit_loss_ratio': self.calculate_avg_profit_loss_ratio(trades),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'consistency_score': self.calculate_consistency_score(metrics_history),
                'risk_score': risk_score_data.get('current_risk_score', 0) if risk_score_data else 0,
                'trade_frequency': self.calculate_trade_frequency(trades),
                'cagr': self.calculate_cagr(metrics_history),
                'sharpe_ratio': self.calculate_sharpe_ratio(metrics_history),
                'copiers_count': copiers_data.get('current_copiers', 0) if copiers_data else 0,
                'aum': metrics.get('aum', 0),
                'holding_period_avg': self.calculate_holding_period(trades),
                'diversification_score': self.calculate_diversification_score(portfolio)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing trader {username}: {e}")
            return None
    
    def calculate_trader_score(self, analysis: Dict, trader_type: str) -> float:
        """Calculate final score for a trader"""
        if trader_type == 'day_trader':
            weights = self.day_trader_weights
        else:
            weights = self.long_term_weights
        
        score = 0.0
        for metric, weight in weights.items():
            value = analysis.get(metric, 0)
            if value is not None:
                score += weight * value
        
        return max(0.0, min(1.0, score))  # Clamp to 0-1 range
    
    def get_top_traders(self, trader_type: str, limit: int = 10) -> List[Dict]:
        """Get top traders of specified type"""
        # This would typically involve:
        # 1. Get list of candidate traders
        # 2. Analyze each trader
        # 3. Calculate scores
        # 4. Rank and return top N
        
        # For now, return empty list - will be implemented when we have API key
        logger.info(f"Getting top {limit} {trader_type} traders")
        return []

