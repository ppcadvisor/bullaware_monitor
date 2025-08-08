from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Trader(db.Model):
    __tablename__ = 'traders'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    display_name = db.Column(db.String(200))
    trader_type = db.Column(db.String(20), nullable=False)  # 'day_trader' or 'long_term'
    
    # Metrics
    win_rate = db.Column(db.Float)
    avg_profit_loss_ratio = db.Column(db.Float)
    max_drawdown = db.Column(db.Float)
    consistency_score = db.Column(db.Float)
    risk_score = db.Column(db.Float)
    trade_frequency = db.Column(db.Float)
    cagr = db.Column(db.Float)
    sharpe_ratio = db.Column(db.Float)
    copiers_count = db.Column(db.Integer)
    aum = db.Column(db.Float)
    holding_period_avg = db.Column(db.Float)
    diversification_score = db.Column(db.Float)
    
    # Calculated score
    total_score = db.Column(db.Float)
    rank = db.Column(db.Integer)
    
    # Metadata
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Trader {self.username} ({self.trader_type})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'display_name': self.display_name,
            'trader_type': self.trader_type,
            'win_rate': self.win_rate,
            'avg_profit_loss_ratio': self.avg_profit_loss_ratio,
            'max_drawdown': self.max_drawdown,
            'consistency_score': self.consistency_score,
            'risk_score': self.risk_score,
            'trade_frequency': self.trade_frequency,
            'cagr': self.cagr,
            'sharpe_ratio': self.sharpe_ratio,
            'copiers_count': self.copiers_count,
            'aum': self.aum,
            'holding_period_avg': self.holding_period_avg,
            'diversification_score': self.diversification_score,
            'total_score': self.total_score,
            'rank': self.rank,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'is_active': self.is_active
        }

class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    trader_username = db.Column(db.String(100), db.ForeignKey('traders.username'), nullable=False)
    instrument = db.Column(db.String(50), nullable=False)
    direction = db.Column(db.String(10), nullable=False)  # 'long' or 'short'
    size = db.Column(db.Float)
    open_price = db.Column(db.Float)
    current_price = db.Column(db.Float)
    pnl = db.Column(db.Float)
    open_date = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    trader = db.relationship('Trader', backref=db.backref('positions', lazy=True))
    
    def __repr__(self):
        return f'<Position {self.trader_username} {self.instrument} {self.direction}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'trader_username': self.trader_username,
            'instrument': self.instrument,
            'direction': self.direction,
            'size': self.size,
            'open_price': self.open_price,
            'current_price': self.current_price,
            'pnl': self.pnl,
            'open_date': self.open_date.isoformat() if self.open_date else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class Signal(db.Model):
    __tablename__ = 'signals'
    
    id = db.Column(db.Integer, primary_key=True)
    instrument = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(10), nullable=False)  # 'buy' or 'sell'
    strategy_type = db.Column(db.String(20), nullable=False)  # 'day_trading' or 'long_term'
    confidence = db.Column(db.Float, nullable=False)
    consensus_strength = db.Column(db.Float)
    supporting_traders = db.Column(db.Text)  # JSON string of trader usernames and weights
    reasoning = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Signal {self.instrument} {self.action} ({self.strategy_type})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'instrument': self.instrument,
            'action': self.action,
            'strategy_type': self.strategy_type,
            'confidence': self.confidence,
            'consensus_strength': self.consensus_strength,
            'supporting_traders': self.supporting_traders,
            'reasoning': self.reasoning,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

