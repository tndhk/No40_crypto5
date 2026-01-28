"""
Pytestの共通フィクスチャ定義
"""
from unittest.mock import MagicMock

import pytest
from freqtrade.exchange import Exchange
from freqtrade.persistence import Trade


@pytest.fixture
def default_conf():
    """デフォルト設定を返すフィクスチャ"""
    return {
        "stake_currency": "JPY",
        "stake_amount": 10000,
        "dry_run": True,
        "exchange": {
            "name": "binance",
            "key": "",
            "secret": "",
            "pair_whitelist": ["BTC/JPY", "ETH/JPY"],
            "pair_blacklist": []
        }
    }


@pytest.fixture
def mock_exchange():
    """モック取引所を返すフィクスチャ"""
    exchange = MagicMock(spec=Exchange)
    exchange.get_min_pair_stake_amount.return_value = 1000
    return exchange


@pytest.fixture
def mock_trade():
    """モックトレードを返すフィクスチャ"""
    trade = MagicMock(spec=Trade)
    trade.open_rate = 1000000
    trade.amount = 0.01
    trade.stake_amount = 10000
    return trade
