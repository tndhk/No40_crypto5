# Phase 1: プロジェクト構造作成計画

## 概要
実装ガイドのPhase 1に従って、プロジェクト構造を作成する。

## 作成するディレクトリ

1. `user_data/strategies/` - 戦略ファイル置き場
2. `user_data/config/` - 設定ファイル置き場
3. `tests/unit/` - ユニットテスト
4. `tests/integration/` - 統合テスト
5. `tests/validation/` - 検証テスト
6. `scripts/` - 便利スクリプト

## 作成するファイル

### 1. `user_data/strategies/__init__.py`（空ファイル）

```python
```

### 2. `tests/__init__.py`（空ファイル）

```python
```

### 3. `tests/unit/__init__.py`（空ファイル）

```python
```

### 4. `tests/conftest.py`（Step 1-12より）

```python
"""
Pytestの共通フィクスチャ定義
"""
import pytest
from freqtrade.configuration import Configuration
from freqtrade.data.dataprovider import DataProvider
from freqtrade.exchange import Exchange
from freqtrade.persistence import Trade
from unittest.mock import MagicMock


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
```

### 5. `pyproject.toml`（Step 1-7より）

```toml
[project]
name = "crypto-dca-bot"
version = "0.1.0"
description = "Cryptocurrency DCA Trading Bot using Freqtrade"
requires-python = ">=3.11"
dependencies = [
    "freqtrade[all]>=2024.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-mock>=3.12.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=user_data/strategies --cov-report=html --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # line too long (handled by formatter)
```

### 6. `.gitignore`（Step 1-9より）

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/

# Freqtrade
user_data/data/
user_data/logs/
user_data/backtest_results/
user_data/hyperopt_results/
user_data/plot/

# Environment variables
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# Jupyter
.ipynb_checkpoints/
```

## 実行手順

1. ディレクトリ作成（mkdir -p）
2. 空の__init__.pyファイル作成
3. conftest.py作成
4. pyproject.toml作成
5. .gitignore作成

## 確認項目

- [ ] 全ディレクトリが存在する
- [ ] 全ファイルが正しい内容で作成されている
- [ ] Pythonパッケージとして認識される（__init__.pyの存在）
