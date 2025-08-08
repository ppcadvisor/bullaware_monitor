"""
Демонстрационный скрипт для BullAware Monitor
Показывает все возможности системы
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5001"

def test_enhanced_recommendations():
    """Тестирует улучшенные торговые рекомендации"""
    print("🎯 ТЕСТИРОВАНИЕ УЛУЧШЕННЫХ РЕКОМЕНДАЦИЙ")
    print("=" * 50)
    
    # Тест базовой функциональности
    response = requests.get(f"{BASE_URL}/api/test-enhanced")
    if response.status_code == 200:
        data = response.json()
        test_results = data['test_results']
        
        print(f"📊 Тестовый инструмент: {test_results['symbol']}")
        print(f"💰 Текущая цена: ${test_results['current_price']:.2f}")
        
        calc = test_results['position_calculation']
        if calc['can_invest']:
            print(f"✅ Рекомендация: КУПИТЬ {calc['recommended_shares']} акций")
            print(f"💵 Сумма инвестиций: ${calc['investment_amount']:.2f}")
            print(f"📈 Stop-Loss: ${calc['levels']['stop_loss']:.2f}")
            print(f"📈 Take-Profit: ${calc['levels']['take_profit']:.2f}")
            print(f"⚠️  Максимальный риск: ${calc['max_risk_amount']:.2f}")
            print(f"📊 Процент портфеля: {calc['portfolio_percentage']:.1f}%")
        else:
            print(f"❌ Не можем инвестировать: {calc['reason']}")
    else:
        print(f"❌ Ошибка API: {response.status_code}")
    
    print()

def test_user_profile():
    """Тестирует профиль пользователя"""
    print("👤 ТЕСТИРОВАНИЕ ПРОФИЛЯ ПОЛЬЗОВАТЕЛЯ")
    print("=" * 50)
    
    # Получаем профиль
    response = requests.get(f"{BASE_URL}/api/user-profile?user_id=1")
    if response.status_code == 200:
        data = response.json()
        profile = data['profile']
        
        print(f"💰 Общий капитал: ${profile['total_capital']:,.2f}")
        print(f"💵 Доступный капитал: ${profile['available_capital']:,.2f}")
        print(f"📊 Инвестированный капитал: ${profile['invested_capital']:,.2f}")
        print(f"⚖️  Толерантность к риску: {profile['risk_tolerance']}")
        print(f"📈 Максимальный риск на сделку: {profile['max_risk_per_trade']*100:.1f}%")
        print(f"🌍 Валюта: {profile['currency']}")
        
        capacity = profile['investment_capacity']
        print(f"💡 Доступно для инвестиций: ${capacity['available_amount']:,.2f}")
        print(f"💡 Максимальный риск: ${capacity['max_risk_amount']:,.2f}")
    else:
        print(f"❌ Ошибка получения профиля: {response.status_code}")
    
    print()

def test_position_calculator():
    """Тестирует калькулятор позиций"""
    print("🧮 ТЕСТИРОВАНИЕ КАЛЬКУЛЯТОРА ПОЗИЦИЙ")
    print("=" * 50)
    
    test_data = {
        "user_id": 1,
        "symbol": "TSLA",
        "entry_price": 250.0,
        "confidence": 0.85,
        "strategy_type": "day_trading"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/position-calculator",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        calc = data['calculation']
        
        print(f"📊 Инструмент: {test_data['symbol']}")
        print(f"💰 Цена входа: ${test_data['entry_price']:.2f}")
        print(f"🎯 Уверенность: {test_data['confidence']*100:.0f}%")
        print(f"📈 Стратегия: {test_data['strategy_type']}")
        print()
        
        if calc['can_invest']:
            print(f"✅ Рекомендуемое количество: {calc['recommended_shares']} акций")
            print(f"💵 Сумма инвестиций: ${calc['investment_amount']:,.2f}")
            print(f"📊 Процент портфеля: {calc['portfolio_percentage']:.1f}%")
            print(f"⚠️  Максимальный риск: ${calc['max_risk_amount']:,.2f}")
            
            levels = calc['levels']
            print(f"🔻 Stop-Loss: ${levels['stop_loss']:.2f} (-{levels['stop_loss_pct']:.1f}%)")
            print(f"🔺 Take-Profit: ${levels['take_profit']:.2f} (+{levels['take_profit_pct']:.1f}%)")
            print(f"⚖️  Risk/Reward: 1:{levels['risk_reward_ratio']:.1f}")
        else:
            print(f"❌ Не можем инвестировать: {calc['reason']}")
    else:
        print(f"❌ Ошибка калькулятора: {response.status_code}")
    
    print()

def test_market_data():
    """Тестирует получение рыночных данных"""
    print("📈 ТЕСТИРОВАНИЕ РЫНОЧНЫХ ДАННЫХ")
    print("=" * 50)
    
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    for symbol in symbols:
        response = requests.get(f"{BASE_URL}/api/market-data/{symbol}")
        if response.status_code == 200:
            data = response.json()
            market = data['market_data']
            
            print(f"📊 {symbol} ({market['company_info']['name']})")
            print(f"💰 Цена: ${market['current_price']:.2f}")
            if market['price_change_pct']:
                change_sign = "📈" if market['price_change_pct'] > 0 else "📉"
                print(f"{change_sign} Изменение: {market['price_change_pct']:+.2f}%")
            print(f"📊 Волатильность: {market['volatility']*100:.2f}%")
            if market['support_level'] and market['resistance_level']:
                print(f"🔻 Поддержка: ${market['support_level']:.2f}")
                print(f"🔺 Сопротивление: ${market['resistance_level']:.2f}")
            print()
        else:
            print(f"❌ Ошибка для {symbol}: {response.status_code}")

def main():
    """Запускает полную демонстрацию"""
    print("🚀 ДЕМОНСТРАЦИЯ BULLAWARE MONITOR")
    print("=" * 60)
    print(f"⏰ Время тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        test_enhanced_recommendations()
        test_user_profile()
        test_position_calculator()
        test_market_data()
        
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("🎯 Система готова к использованию!")
        
    except Exception as e:
        print(f"❌ Ошибка во время тестирования: {e}")

if __name__ == "__main__":
    main()

