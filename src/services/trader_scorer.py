import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from src.services.bullaware_client import BullAwareClient
from src.models.trader import Trader, db

logger = logging.getLogger(__name__)

class TraderScorer:
    """Advanced trader scoring service with metric normalization and ranking"""
    
    def __init__(self, bullaware_client: BullAwareClient):
        self.client = bullaware_client
        
        # Scoring weights for day traders
        self.day_trader_weights = {
            'win_rate': 0.25,
            'profit_loss_ratio': 0.20,
            'max_drawdown': 0.20,      # Will be inverted (lower is better)
            'consistency': 0.15,
            'risk_score': 0.10,        # Will be inverted (lower is better)
            'trade_frequency': 0.10
        }
        
        # Scoring weights for long-term investors
        self.long_term_weights = {
            'cagr': 0.25,
            'sharpe_ratio': 0.20,
            'max_drawdown': 0.15,      # Will be inverted (lower is better)
            'consistency': 0.15,
            'copiers_count': 0.10,
            'holding_period': 0.10,
            'diversification': 0.05
        }
        
        # Metric bounds for normalization (will be updated dynamically)
        self.metric_bounds = {
            'win_rate': (0.0, 1.0),
            'profit_loss_ratio': (0.0, 5.0),
            'max_drawdown': (0.0, 0.5),
            'consistency': (0.0, 1.0),
            'risk_score': (1.0, 10.0),
            'trade_frequency': (0.0, 100.0),
            'cagr': (-0.5, 2.0),
            'sharpe_ratio': (-2.0, 5.0),
            'copiers_count': (0, 50000),
            'holding_period': (1.0, 365.0),
            'diversification': (0.0, 1.0)
        }
    
    def normalize_metric(self, values: List[float], metric_name: str, higher_is_better: bool = True) -> List[float]:
        """Normalize metric values to 0-1 scale using robust normalization"""
        if not values or len(values) == 0:
            return []
        
        values = np.array(values)
        
        # Remove outliers using IQR method
        Q1 = np.percentile(values, 25)
        Q3 = np.percentile(values, 75)
        IQR = Q3 - Q1
        
        # Define outlier bounds
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Use predefined bounds if available, otherwise use data bounds
        if metric_name in self.metric_bounds:
            min_val, max_val = self.metric_bounds[metric_name]
        else:
            min_val = max(np.min(values), lower_bound)
            max_val = min(np.max(values), upper_bound)
        
        # Clip values to bounds
        values_clipped = np.clip(values, min_val, max_val)
        
        if max_val == min_val:
            return [0.5] * len(values)  # All equal, return middle value
        
        # Normalize to 0-1
        if higher_is_better:
            normalized = (values_clipped - min_val) / (max_val - min_val)
        else:
            normalized = (max_val - values_clipped) / (max_val - min_val)
        
        return normalized.tolist()
    
    def extract_metrics_from_api_data(self, username: str) -> Dict:
        """Extract and calculate all metrics from BullAware API data"""
        try:
            # Get all necessary data
            details = self.client.get_investor_details(username)
            metrics = self.client.get_investor_metrics(username)
            portfolio = self.client.get_investor_portfolio(username)
            
            # Extract basic metrics from API response
            investor_data = details.get('investor', {})
            
            extracted_metrics = {
                'username': username,
                'display_name': investor_data.get('fullname', username),
                
                # Basic performance metrics
                'win_rate': investor_data.get('winRatio', 0) / 100.0,  # Convert percentage to decimal
                'return_1_year': investor_data.get('return1Year', 0) / 100.0,
                'return_ytd': investor_data.get('returnYearToDate', 0) / 100.0,
                'annualized_return': investor_data.get('annualizedReturn', 0) / 100.0,
                
                # Risk metrics
                'daily_dd': abs(investor_data.get('dailyDD', 0)) / 100.0,
                'weekly_dd': abs(investor_data.get('weeklyDD', 0)) / 100.0,
                'max_drawdown': max(abs(investor_data.get('dailyDD', 0)), abs(investor_data.get('weeklyDD', 0))) / 100.0,
                
                # Advanced metrics from metrics endpoint
                'sharpe_ratio': metrics.get('sharpeRatio', 0),
                'sortino_ratio': metrics.get('sortinoRatio', 0),
                'calmar_ratio': metrics.get('calmarRatio', 0),
                'beta': metrics.get('beta', 1.0),
                
                # Social metrics
                'copiers_count': investor_data.get('copiers', 0),
                'aum': self._parse_aum(investor_data.get('aum', '0')),
                'trades_count': investor_data.get('trades', 0),
                'weeks_since_registration': investor_data.get('weeksSinceRegistration', 0),
                
                # Portfolio metrics
                'portfolio_positions': len(portfolio.get('positions', [])) if portfolio else 0
            }
            
            # Calculate derived metrics
            extracted_metrics.update(self._calculate_derived_metrics(extracted_metrics, portfolio))
            
            return extracted_metrics
            
        except Exception as e:
            logger.error(f"Error extracting metrics for {username}: {e}")
            return {}
    
    def _parse_aum(self, aum_str: str) -> float:
        """Parse AUM string to numeric value"""
        if not aum_str or aum_str == '0':
            return 0.0
        
        aum_str = aum_str.upper().replace('$', '').replace(',', '')
        
        if 'M+' in aum_str:
            return 5000000.0  # Assume 5M for "5M+" format
        elif 'M' in aum_str:
            return float(aum_str.replace('M', '')) * 1000000
        elif 'K' in aum_str:
            return float(aum_str.replace('K', '')) * 1000
        else:
            try:
                return float(aum_str)
            except:
                return 0.0
    
    def _calculate_derived_metrics(self, metrics: Dict, portfolio: Dict) -> Dict:
        """Calculate derived metrics from basic data"""
        derived = {}
        
        # Calculate profit/loss ratio (simplified)
        win_rate = metrics.get('win_rate', 0)
        if win_rate > 0 and win_rate < 1:
            # Estimate based on win rate and returns
            avg_win = 1.0  # Placeholder
            avg_loss = 0.8  # Placeholder
            derived['profit_loss_ratio'] = avg_win / avg_loss
        else:
            derived['profit_loss_ratio'] = 1.0
        
        # Calculate consistency score based on Sharpe ratio and Sortino ratio
        sharpe = metrics.get('sharpe_ratio', 0)
        sortino = metrics.get('sortino_ratio', 0)
        derived['consistency'] = min((sharpe + sortino) / 4.0, 1.0)  # Normalize to 0-1
        
        # Calculate risk score (inverse of risk-adjusted returns)
        calmar = metrics.get('calmar_ratio', 0)
        if calmar > 0:
            derived['risk_score'] = max(1.0, 10.0 - calmar * 2)  # Scale 1-10, lower is better
        else:
            derived['risk_score'] = 8.0  # Default high risk
        
        # Calculate trade frequency (trades per week)
        weeks_active = max(metrics.get('weeks_since_registration', 1), 1)
        total_trades = metrics.get('trades_count', 0)
        derived['trade_frequency'] = total_trades / weeks_active
        
        # Calculate CAGR (use annualized return as proxy)
        derived['cagr'] = metrics.get('annualized_return', 0)
        
        # Calculate holding period (inverse of trade frequency)
        if derived['trade_frequency'] > 0:
            derived['holding_period'] = min(365.0, 52.0 / derived['trade_frequency'])  # Days
        else:
            derived['holding_period'] = 365.0  # Default to 1 year
        
        # Calculate diversification score
        position_count = metrics.get('portfolio_positions', 0)
        derived['diversification'] = min(position_count / 10.0, 1.0)  # Normalize to max 10 positions
        
        return derived
    
    def classify_trader_type(self, metrics: Dict) -> str:
        """Classify trader as day_trader or long_term based on metrics"""
        trade_frequency = metrics.get('trade_frequency', 0)
        holding_period = metrics.get('holding_period', 365)
        
        # Day trader criteria: high frequency, short holding period
        if trade_frequency > 2.0 and holding_period < 30:  # More than 2 trades per week, less than 30 days holding
            return 'day_trader'
        else:
            return 'long_term'
    
    def calculate_trader_score(self, metrics: Dict, trader_type: str) -> float:
        """Calculate final score for a trader"""
        if trader_type == 'day_trader':
            weights = self.day_trader_weights
            score_metrics = {
                'win_rate': metrics.get('win_rate', 0),
                'profit_loss_ratio': metrics.get('profit_loss_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'consistency': metrics.get('consistency', 0),
                'risk_score': metrics.get('risk_score', 5),
                'trade_frequency': metrics.get('trade_frequency', 0)
            }
        else:  # long_term
            weights = self.long_term_weights
            score_metrics = {
                'cagr': metrics.get('cagr', 0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                'max_drawdown': metrics.get('max_drawdown', 0),
                'consistency': metrics.get('consistency', 0),
                'copiers_count': metrics.get('copiers_count', 0),
                'holding_period': metrics.get('holding_period', 0),
                'diversification': metrics.get('diversification', 0)
            }
        
        # Normalize metrics (simplified - in practice would use population data)
        normalized_metrics = {}
        for metric, value in score_metrics.items():
            if metric in ['max_drawdown', 'risk_score']:
                # Lower is better for these metrics
                normalized_metrics[metric] = max(0, 1 - value)
            else:
                # Higher is better
                if metric == 'copiers_count':
                    normalized_metrics[metric] = min(value / 10000.0, 1.0)  # Normalize to 10k copiers
                elif metric == 'holding_period':
                    normalized_metrics[metric] = min(value / 365.0, 1.0)  # Normalize to 1 year
                elif metric == 'trade_frequency':
                    normalized_metrics[metric] = min(value / 10.0, 1.0)  # Normalize to 10 trades/week
                elif metric == 'sharpe_ratio':
                    normalized_metrics[metric] = min(max(value + 2, 0) / 7.0, 1.0)  # Normalize -2 to 5 range
                elif metric == 'cagr':
                    normalized_metrics[metric] = min(max(value + 0.5, 0) / 2.5, 1.0)  # Normalize -50% to 200% range
                else:
                    normalized_metrics[metric] = min(max(value, 0), 1.0)  # Clamp to 0-1
        
        # Calculate weighted score
        score = 0.0
        for metric, weight in weights.items():
            metric_value = normalized_metrics.get(metric, 0)
            score += weight * metric_value
        
        return max(0.0, min(1.0, score))  # Clamp to 0-1 range
    
    def analyze_and_score_traders(self, usernames: List[str]) -> List[Dict]:
        """Analyze and score a list of traders"""
        scored_traders = []
        
        for username in usernames:
            try:
                logger.info(f"Analyzing trader: {username}")
                
                # Extract metrics
                metrics = self.extract_metrics_from_api_data(username)
                
                if not metrics:
                    logger.warning(f"No metrics extracted for {username}")
                    continue
                
                # Classify trader type
                trader_type = self.classify_trader_type(metrics)
                
                # Calculate score
                score = self.calculate_trader_score(metrics, trader_type)
                
                # Prepare result
                trader_result = {
                    'username': username,
                    'trader_type': trader_type,
                    'score': score,
                    'metrics': metrics
                }
                
                scored_traders.append(trader_result)
                
            except Exception as e:
                logger.error(f"Error analyzing trader {username}: {e}")
                continue
        
        # Sort by score (highest first)
        scored_traders.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_traders
    
    def update_trader_rankings(self, scored_traders: List[Dict]):
        """Update trader rankings in database"""
        try:
            for i, trader_data in enumerate(scored_traders):
                username = trader_data['username']
                trader_type = trader_data['trader_type']
                score = trader_data['score']
                metrics = trader_data['metrics']
                
                # Find or create trader record
                trader = Trader.query.filter_by(username=username).first()
                if not trader:
                    trader = Trader(username=username)
                    db.session.add(trader)
                
                # Update trader data
                trader.display_name = metrics.get('display_name', username)
                trader.trader_type = trader_type
                trader.total_score = score
                trader.rank = i + 1
                trader.last_updated = datetime.utcnow()
                trader.is_active = True
                
                # Update individual metrics
                trader.win_rate = metrics.get('win_rate')
                trader.avg_profit_loss_ratio = metrics.get('profit_loss_ratio')
                trader.max_drawdown = metrics.get('max_drawdown')
                trader.consistency_score = metrics.get('consistency')
                trader.risk_score = metrics.get('risk_score')
                trader.trade_frequency = metrics.get('trade_frequency')
                trader.cagr = metrics.get('cagr')
                trader.sharpe_ratio = metrics.get('sharpe_ratio')
                trader.copiers_count = metrics.get('copiers_count')
                trader.aum = metrics.get('aum')
                trader.holding_period_avg = metrics.get('holding_period')
                trader.diversification_score = metrics.get('diversification')
            
            db.session.commit()
            logger.info(f"Updated rankings for {len(scored_traders)} traders")
            
        except Exception as e:
            logger.error(f"Error updating trader rankings: {e}")
            db.session.rollback()
    
    def get_top_traders_from_api(self, limit: int = 50) -> List[str]:
        """Get list of top trader usernames from BullAware API"""
        try:
            investors_data = self.client.get_investors(limit=limit)
            
            if not investors_data or 'items' not in investors_data:
                logger.error("No investors data received from API")
                return []
            
            usernames = []
            for investor in investors_data['items']:
                username = investor.get('username')
                if username:
                    usernames.append(username)
            
            logger.info(f"Retrieved {len(usernames)} trader usernames from API")
            return usernames
            
        except Exception as e:
            logger.error(f"Error getting traders from API: {e}")
            return []


# Глобальный экземпляр скорера трейдеров
from .bullaware_client import bullaware_client
trader_scorer = TraderScorer(bullaware_client)

