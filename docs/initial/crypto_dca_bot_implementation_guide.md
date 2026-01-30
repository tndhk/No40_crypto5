# 仮想通貨DCAトレーディングボット：実装ガイド（誰でも実装できるステップバイステップ）

Version: 1.1
Date: 2026-01-28
対象読者: プログラミング初級〜中級者

## はじめに

このガイドは、要件定義書 [[Flow/Project/crypto_dca_bot_requirements]] で定義された仮想通貨DCAトレーディングボットを、誰でも実装できるように詳細な手順を記述したものです。

### 前提知識
- 基本的なターミナル操作（cd, ls, mkdir等）
- Gitの基本操作（clone, commit, push）
- Pythonの基本文法（関数、クラス、変数）

### 必要な環境
- macOS（開発環境）
- Python 3.11以上
- Homebrewパッケージマネージャー
- インターネット接続

---

## Phase 1: 環境構築とプロジェクト基盤

推定所要時間: 2-3時間

### Step 1-1: プロジェクトディレクトリ作成

ターミナルを開き、以下のコマンドを実行:

```bash
# プロジェクトディレクトリを作成
mkdir -p ~/projects/crypto-dca-bot
cd ~/projects/crypto-dca-bot

# Gitリポジトリ初期化
git init
```

確認方法:
```bash
pwd
# 出力: /Users/<あなたのユーザー名>/projects/crypto-dca-bot
```

### Step 1-2: uvのインストールと環境構築

uvは高速なPythonパッケージマネージャーです。

```bash
# Homebrewでuvをインストール
brew install uv

# バージョン確認
uv --version
# 出力例: uv 0.x.x
```

### Step 1-3: Python仮想環境の作成

```bash
# Python 3.11で仮想環境を作成
uv venv --python 3.11

# 仮想環境をアクティベート
source .venv/bin/activate

# プロンプトが (.venv) で始まることを確認
# 出力例: (.venv) user@macbook crypto-dca-bot %
```

### Step 1-4: Freqtradeのインストール

```bash
# Freqtradeとその依存関係をインストール
pip install freqtrade[all]

# インストール確認
freqtrade --version
# 出力例: freqtrade 2024.x
```

エラーが出た場合:
- `pip install --upgrade pip` を実行してpipを最新化
- `pip install freqtrade` で最小構成をインストール

### Step 1-5: Freqtrade設定ディレクトリの作成

```bash
# Freqtradeのuser_dataディレクトリを作成
freqtrade create-userdir --userdir user_data

# ディレクトリ構造確認
ls -la user_data/
# 出力: config, data, logs, strategies等のディレクトリが作成される
```

### Step 1-6: プロジェクト構造の作成

```bash
# テストディレクトリ作成
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/validation

# スクリプトディレクトリ作成
mkdir -p scripts

# ノートブックディレクトリ作成
mkdir -p user_data/notebooks

# 追加の設定ディレクトリ
mkdir -p user_data/config
```

最終的なディレクトリ構造:
```
crypto-dca-bot/
├── .venv/                      # 仮想環境（自動生成）
├── user_data/
│   ├── config/                # 設定ファイル置き場
│   ├── strategies/            # 戦略ファイル置き場
│   ├── data/                  # OHLCVデータ（自動生成）
│   ├── logs/                  # ログ（自動生成）
│   ├── backtest_results/      # バックテスト結果（自動生成）
│   └── notebooks/             # 分析用ノートブック
├── tests/
│   ├── unit/                  # ユニットテスト
│   ├── integration/           # 統合テスト
│   └── validation/            # 検証テスト
└── scripts/                   # 便利スクリプト
```

### Step 1-7: pyproject.tomlの作成

プロジェクトの依存関係を管理するファイルを作成:

```bash
# pyproject.tomlを作成
cat > pyproject.toml << 'EOF'
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
EOF
```

### Step 1-8: 開発ツールのインストール

```bash
# 開発用依存関係をインストール
pip install pytest pytest-mock pytest-cov ruff

# インストール確認
pytest --version
# 出力例: pytest 8.x.x
```

### Step 1-9: .gitignoreの作成

Gitで管理しないファイルを指定:

```bash
cat > .gitignore << 'EOF'
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
EOF
```

### Step 1-10: .env.exampleの作成

環境変数のテンプレート:

```bash
cat > .env.example << 'EOF'
# Binance API設定
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Bot設定
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# 環境設定
ENVIRONMENT=dry_run  # dry_run or live
EOF
```

実際の.envファイル作成（後で値を設定）:

```bash
cp .env.example .env
# .envファイルを編集して実際の値を入力（後のステップで実施）
```

### Step 1-11: Makefileの作成

便利なコマンドをまとめたファイル:

```bash
cat > Makefile << 'EOF'
.PHONY: help test backtest hyperopt lint format clean

help:
	@echo "Available commands:"
	@echo "  make test       - Run all tests with coverage"
	@echo "  make backtest   - Run backtest with default config"
	@echo "  make hyperopt   - Run hyperparameter optimization"
	@echo "  make lint       - Run code linter"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean generated files"

test:
	pytest -v --cov=user_data/strategies --cov-report=html --cov-report=term-missing

backtest:
	freqtrade backtesting \
		--config user_data/config/config.backtest.json \
		--strategy DCAStrategy \
		--timerange 20240301-20260127

hyperopt:
	freqtrade hyperopt \
		--config user_data/config/config.hyperopt.json \
		--strategy DCAStrategy \
		--hyperopt-loss SharpeHyperOptLoss \
		--spaces buy sell \
		--epochs 500 \
		--timerange 20240301-20250630

lint:
	ruff check user_data/strategies/ tests/

format:
	ruff format user_data/strategies/ tests/

clean:
	rm -rf user_data/backtest_results/*
	rm -rf user_data/hyperopt_results/*
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
EOF
```

### Step 1-12: conftest.pyの作成（テスト用フィクスチャ）

```bash
cat > tests/conftest.py << 'EOF'
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
EOF
```

### Step 1-13: READMEの作成

```bash
cat > README.md << 'EOF'
# 仮想通貨DCAトレーディングボット

Freqtradeを使用したBinance Japan向けDCA戦略自動売買ボット

## セットアップ

1. リポジトリをクローン
```bash
git clone <your-repo-url>
cd crypto-dca-bot
```

2. 仮想環境を作成・アクティベート
```bash
uv venv --python 3.11
source .venv/bin/activate
```

3. 依存関係をインストール
```bash
pip install freqtrade[all]
pip install pytest pytest-mock pytest-cov ruff
```

4. 環境変数を設定
```bash
cp .env.example .env
# .envファイルを編集してAPIキー等を設定
```

5. テストを実行
```bash
make test
```

## 使い方

### Dry Runモード（デモトレード）
```bash
freqtrade trade --config user_data/config/config.json --strategy DCAStrategy
```

### バックテスト
```bash
make backtest
```

### パラメータ最適化
```bash
make hyperopt
```

## ディレクトリ構造

- `user_data/strategies/`: 戦略ファイル
- `user_data/config/`: 設定ファイル
- `tests/`: テストコード
- `scripts/`: 便利スクリプト

## ドキュメント

- [要件定義書](../tsunotaka/Flow/Project/crypto_dca_bot_requirements.md)
- [実装ガイド](../tsunotaka/Flow/Project/crypto_dca_bot_implementation_guide.md)
EOF
```

### Step 1-14: 初回コミット

```bash
# Gitにファイルを追加
git add .

# 初回コミット
git commit -m "Initial commit: Project structure and configuration"
```

### Phase 1 完了確認チェックリスト

以下のコマンドを実行して全て成功することを確認:

```bash
# 1. Freqtradeバージョン確認
freqtrade --version

# 2. Pytestが動作するか確認
pytest --version

# 3. ディレクトリ構造確認
tree -L 2 -I '.venv|__pycache__'
# または
ls -R

# 4. テスト実行（まだテストファイルがないのでNo tests collectedとなるはずだが、エラーは出ない）
pytest
```

期待される出力:
```
freqtrade --version
# freqtrade 2024.x

pytest --version
# pytest 8.x.x

pytest
# collected 0 items (または No tests collected)
```

Phase 1が完了しました。次はPhase 2に進みます。

---

## Phase 2: DCA戦略のコア実装（TDD）

推定所要時間: 8-12時間

このフェーズでは、テスト駆動開発（TDD）でDCA戦略を実装します。
TDDの流れ: RED（失敗するテストを書く） → GREEN（テストが通る最小実装） → REFACTOR（リファクタリング）

### Step 2-1: テクニカル指標モジュールのテスト作成（RED）

```bash
cat > tests/unit/test_indicators.py << 'EOF'
"""
テクニカル指標のユニットテスト
"""
import pytest
import pandas as pd
import numpy as np
from user_data.strategies.indicators import (
    calculate_ema,
    calculate_rsi,
    calculate_bollinger_bands,
    calculate_volume_sma
)


class TestEMACalculation:
    """EMA（指数移動平均）のテスト"""

    def test_ema_calculation(self):
        """EMA計算が正しく動作するか"""
        df = pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108]
        })
        result = calculate_ema(df, period=3)

        assert 'ema_3' in result.columns
        assert not result['ema_3'].isna().all()
        assert result['ema_3'].iloc[-1] > 100  # 上昇トレンドなので100より上

    def test_ema_with_insufficient_data(self):
        """データが不足している場合はNaNを返す"""
        df = pd.DataFrame({'close': [100, 102]})
        result = calculate_ema(df, period=5)

        assert result['ema_5'].isna().any()


class TestRSICalculation:
    """RSI（相対力指数）のテスト"""

    def test_rsi_calculation(self):
        """RSI計算が正しく動作するか"""
        df = pd.DataFrame({
            'close': [100, 105, 110, 108, 112, 115, 113, 118, 120, 119,
                      122, 125, 123, 127, 130]
        })
        result = calculate_rsi(df, period=14)

        assert 'rsi_14' in result.columns
        assert 0 <= result['rsi_14'].iloc[-1] <= 100

    def test_rsi_overbought(self):
        """上昇トレンドでRSIが70以上になることを確認"""
        df = pd.DataFrame({
            'close': [100 + i*2 for i in range(20)]  # 強い上昇トレンド
        })
        result = calculate_rsi(df, period=14)

        assert result['rsi_14'].iloc[-1] > 70


class TestBollingerBands:
    """ボリンジャーバンドのテスト"""

    def test_bollinger_bands_calculation(self):
        """ボリンジャーバンド計算が正しく動作するか"""
        df = pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                      111, 110, 112, 114, 113, 115, 117, 116, 118, 120]
        })
        result = calculate_bollinger_bands(df, period=20, std=2)

        assert 'bb_upper' in result.columns
        assert 'bb_middle' in result.columns
        assert 'bb_lower' in result.columns

        # 上限 > 中央 > 下限
        assert result['bb_upper'].iloc[-1] > result['bb_middle'].iloc[-1]
        assert result['bb_middle'].iloc[-1] > result['bb_lower'].iloc[-1]


class TestVolumeSMA:
    """出来高移動平均のテスト"""

    def test_volume_sma_calculation(self):
        """出来高SMA計算が正しく動作するか"""
        df = pd.DataFrame({
            'volume': [1000, 1200, 1100, 1300, 1500, 1400, 1600, 1800]
        })
        result = calculate_volume_sma(df, period=5)

        assert 'volume_sma_5' in result.columns
        assert result['volume_sma_5'].iloc[-1] > 1000
EOF
```

テストを実行（失敗することを確認）:

```bash
pytest tests/unit/test_indicators.py -v
# エラーが出るはず（indicators.pyがまだ存在しないため）
```

### Step 2-2: テクニカル指標モジュールの実装（GREEN）

```bash
cat > user_data/strategies/indicators.py << 'EOF'
"""
テクニカル指標計算モジュール

Freqtrade戦略で使用するテクニカル指標を計算する関数群
"""
import pandas as pd
import numpy as np
from pandas import DataFrame
import talib.abstract as ta


def calculate_ema(dataframe: DataFrame, period: int) -> DataFrame:
    """
    EMA（指数移動平均）を計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: EMA期間

    Returns:
        EMAカラムが追加されたDataFrame
    """
    df = dataframe.copy()
    df[f'ema_{period}'] = ta.EMA(df, timeperiod=period)
    return df


def calculate_rsi(dataframe: DataFrame, period: int = 14) -> DataFrame:
    """
    RSI（相対力指数）を計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: RSI期間（デフォルト14）

    Returns:
        RSIカラムが追加されたDataFrame
    """
    df = dataframe.copy()
    df[f'rsi_{period}'] = ta.RSI(df, timeperiod=period)
    return df


def calculate_bollinger_bands(
    dataframe: DataFrame,
    period: int = 20,
    std: int = 2
) -> DataFrame:
    """
    ボリンジャーバンドを計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: 移動平均期間（デフォルト20）
        std: 標準偏差の倍数（デフォルト2）

    Returns:
        bb_upper, bb_middle, bb_lowerカラムが追加されたDataFrame
    """
    df = dataframe.copy()
    bollinger = ta.BBANDS(df, timeperiod=period, nbdevup=std, nbdevdn=std)

    df['bb_upper'] = bollinger['upperband']
    df['bb_middle'] = bollinger['middleband']
    df['bb_lower'] = bollinger['lowerband']

    return df


def calculate_volume_sma(dataframe: DataFrame, period: int) -> DataFrame:
    """
    出来高の単純移動平均を計算

    Args:
        dataframe: OHLCVデータを含むDataFrame
        period: SMA期間

    Returns:
        volume_sma_{period}カラムが追加されたDataFrame
    """
    df = dataframe.copy()
    df[f'volume_sma_{period}'] = df['volume'].rolling(window=period).mean()
    return df
EOF
```

__init__.pyを作成:

```bash
touch user_data/strategies/__init__.py
```

テストを実行（成功することを確認）:

```bash
pytest tests/unit/test_indicators.py -v
# 全テストがPASSするはず
```

### Step 2-3: リスク管理モジュールのテスト作成（RED）

```bash
cat > tests/unit/test_risk_manager.py << 'EOF'
"""
リスク管理モジュールのユニットテスト
"""
import pytest
from user_data.strategies.risk_manager import RiskManager


class TestRiskManager:
    """リスク管理機能のテスト"""

    @pytest.fixture
    def risk_manager(self):
        """RiskManagerインスタンスを返すフィクスチャ"""
        config = {
            'stake_amount': 10000,
            'max_open_trades': 2,
            'max_position_size': 50000,
            'daily_loss_limit': 5000,
            'max_drawdown': 0.15
        }
        return RiskManager(config)

    def test_max_position_size_check(self, risk_manager):
        """最大ポジションサイズチェック"""
        assert risk_manager.check_position_size(30000) is True
        assert risk_manager.check_position_size(60000) is False

    def test_portfolio_allocation_limit(self, risk_manager):
        """ポートフォリオ配分制限"""
        current_positions = [
            {'stake_amount': 10000},
            {'stake_amount': 15000}
        ]
        # 既存25000 + 新規10000 = 35000 < 50000 (OK)
        assert risk_manager.check_portfolio_limit(10000, current_positions) is True

        # 既存25000 + 新規30000 = 55000 > 50000 (NG)
        assert risk_manager.check_portfolio_limit(30000, current_positions) is False

    def test_daily_loss_limit(self, risk_manager):
        """1日の損失上限チェック"""
        trades_today = [
            {'profit_abs': -1000},
            {'profit_abs': -2000},
            {'profit_abs': 500}
        ]
        # 総損失 = -2500 < -5000 (OK)
        assert risk_manager.check_daily_loss_limit(trades_today) is True

        trades_today_bad = [
            {'profit_abs': -3000},
            {'profit_abs': -2500}
        ]
        # 総損失 = -5500 > -5000 (NG)
        assert risk_manager.check_daily_loss_limit(trades_today_bad) is False

    def test_circuit_breaker_on_drawdown(self, risk_manager):
        """ドローダウンでのサーキットブレーカー"""
        assert risk_manager.check_circuit_breaker(0.10) is True  # DD 10% (OK)
        assert risk_manager.check_circuit_breaker(0.16) is False  # DD 16% (NG)

    def test_consecutive_loss_protection(self, risk_manager):
        """連続損失プロテクション"""
        # 連続2回損失 (OK)
        recent_trades = [
            {'profit_abs': -1000},
            {'profit_abs': -500}
        ]
        assert risk_manager.check_consecutive_losses(recent_trades, max_losses=3) is True

        # 連続3回損失 (NG)
        recent_trades_bad = [
            {'profit_abs': -1000},
            {'profit_abs': -500},
            {'profit_abs': -800}
        ]
        assert risk_manager.check_consecutive_losses(recent_trades_bad, max_losses=3) is False

    def test_cooldown_after_stoploss(self, risk_manager):
        """ストップロス後のクールダウン"""
        from datetime import datetime, timedelta

        last_sl_time = datetime.now() - timedelta(hours=2)
        assert risk_manager.check_cooldown(last_sl_time, cooldown_hours=3) is False

        last_sl_time = datetime.now() - timedelta(hours=4)
        assert risk_manager.check_cooldown(last_sl_time, cooldown_hours=3) is True
EOF
```

テストを実行（失敗することを確認）:

```bash
pytest tests/unit/test_risk_manager.py -v
```

### Step 2-4: リスク管理モジュールの実装（GREEN）

```bash
cat > user_data/strategies/risk_manager.py << 'EOF'
"""
リスク管理モジュール

ポジションサイズ、ドローダウン、損失制限等のリスク管理機能
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class RiskManager:
    """
    リスク管理クラス

    トレーディング戦略で使用するリスク管理機能を提供
    """

    def __init__(self, config: Dict):
        """
        Args:
            config: リスク管理設定を含む辞書
                - stake_amount: 1トレードあたりの基準額
                - max_open_trades: 最大同時ポジション数
                - max_position_size: 1ポジションの最大サイズ
                - daily_loss_limit: 1日の最大損失額
                - max_drawdown: 最大ドローダウン率
        """
        self.stake_amount = config.get('stake_amount', 10000)
        self.max_open_trades = config.get('max_open_trades', 2)
        self.max_position_size = config.get('max_position_size', 50000)
        self.daily_loss_limit = config.get('daily_loss_limit', 5000)
        self.max_drawdown = config.get('max_drawdown', 0.15)

    def check_position_size(self, proposed_amount: float) -> bool:
        """
        ポジションサイズが上限を超えていないかチェック

        Args:
            proposed_amount: 提案されたポジションサイズ

        Returns:
            上限以下ならTrue、超過ならFalse
        """
        return proposed_amount <= self.max_position_size

    def check_portfolio_limit(
        self,
        proposed_amount: float,
        current_positions: List[Dict]
    ) -> bool:
        """
        ポートフォリオ全体の配分制限をチェック

        Args:
            proposed_amount: 新規ポジションの提案額
            current_positions: 現在のポジションリスト

        Returns:
            制限内ならTrue、超過ならFalse
        """
        current_total = sum(pos.get('stake_amount', 0) for pos in current_positions)
        return (current_total + proposed_amount) <= self.max_position_size

    def check_daily_loss_limit(self, trades_today: List[Dict]) -> bool:
        """
        1日の損失上限をチェック

        Args:
            trades_today: 当日のトレードリスト

        Returns:
            上限内ならTrue、超過ならFalse
        """
        total_loss = sum(
            trade.get('profit_abs', 0)
            for trade in trades_today
            if trade.get('profit_abs', 0) < 0
        )
        return total_loss >= -self.daily_loss_limit

    def check_circuit_breaker(self, current_drawdown: float) -> bool:
        """
        サーキットブレーカー（ドローダウン上限）をチェック

        Args:
            current_drawdown: 現在のドローダウン率（0.0-1.0）

        Returns:
            上限内ならTrue、超過ならFalse
        """
        return current_drawdown <= self.max_drawdown

    def check_consecutive_losses(
        self,
        recent_trades: List[Dict],
        max_losses: int = 3
    ) -> bool:
        """
        連続損失回数をチェック

        Args:
            recent_trades: 最近のトレードリスト
            max_losses: 許容する最大連続損失回数

        Returns:
            許容範囲内ならTrue、超過ならFalse
        """
        consecutive_losses = 0
        for trade in reversed(recent_trades):
            if trade.get('profit_abs', 0) < 0:
                consecutive_losses += 1
            else:
                break

        return consecutive_losses < max_losses

    def check_cooldown(
        self,
        last_stoploss_time: Optional[datetime],
        cooldown_hours: int = 3
    ) -> bool:
        """
        ストップロス後のクールダウン期間をチェック

        Args:
            last_stoploss_time: 最後のストップロス発生時刻
            cooldown_hours: クールダウン時間（時間）

        Returns:
            クールダウン期間が過ぎていればTrue、まだならFalse
        """
        if last_stoploss_time is None:
            return True

        cooldown_end = last_stoploss_time + timedelta(hours=cooldown_hours)
        return datetime.now() >= cooldown_end
EOF
```

テストを実行（成功することを確認）:

```bash
pytest tests/unit/test_risk_manager.py -v
# 全テストがPASSするはず
```

### Step 2-5: DCA戦略のテスト作成（RED）

DCA戦略は長いので、主要部分のテストを作成:

```bash
cat > tests/unit/test_dca_strategy.py << 'EOF'
"""
DCA戦略のユニットテスト
"""
import pytest
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import MagicMock
from freqtrade.persistence import Trade
from user_data.strategies.dca_strategy import DCAStrategy


class TestDCAStrategyEntrySignal:
    """エントリーシグナルのテスト"""

    @pytest.fixture
    def strategy(self, default_conf):
        """DCAStrategyインスタンスを返す"""
        return DCAStrategy(default_conf)

    def test_populate_entry_signal_with_bullish_conditions(self, strategy):
        """強気条件でエントリーシグナルが出ることを確認"""
        df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=100, freq='1h'),
            'open': [100 + i * 0.5 for i in range(100)],
            'high': [101 + i * 0.5 for i in range(100)],
            'low': [99 + i * 0.5 for i in range(100)],
            'close': [100.5 + i * 0.5 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        })

        result = strategy.populate_entry_trend(df, {})

        # 最後の行でエントリーシグナルが出ているはず
        assert result['enter_long'].iloc[-1] == 1

    def test_no_entry_signal_with_bearish_conditions(self, strategy):
        """弱気条件でエントリーシグナルが出ないことを確認"""
        df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=100, freq='1h'),
            'open': [200 - i * 0.5 for i in range(100)],
            'high': [201 - i * 0.5 for i in range(100)],
            'low': [199 - i * 0.5 for i in range(100)],
            'close': [200 - i * 0.5 for i in range(100)],
            'volume': [1000 - i * 5 for i in range(100)]
        })

        result = strategy.populate_entry_trend(df, {})

        # エントリーシグナルが出ていないはず
        assert result['enter_long'].iloc[-1] == 0


class TestDCAStrategyCustomStakeAmount:
    """カスタムステーク額のテスト"""

    @pytest.fixture
    def strategy(self, default_conf):
        return DCAStrategy(default_conf)

    def test_initial_stake_is_divided_by_dca_multiplier(self, strategy):
        """初回ステーク額がDCA倍率で割られることを確認"""
        proposed_stake = 10000
        result = strategy.custom_stake_amount(
            pair='BTC/JPY',
            current_time=datetime.now(timezone.utc),
            current_rate=10000000,
            proposed_stake=proposed_stake,
            min_stake=1000,
            max_stake=50000,
            leverage=1.0,
            entry_tag=None,
            side='long',
            **{}
        )

        expected = proposed_stake / 5.5
        assert result == pytest.approx(expected, rel=0.01)

    def test_stake_respects_min_stake(self, strategy):
        """最小ステーク額を下回らないことを確認"""
        proposed_stake = 1000
        min_stake = 2000

        result = strategy.custom_stake_amount(
            pair='BTC/JPY',
            current_time=datetime.now(timezone.utc),
            current_rate=10000000,
            proposed_stake=proposed_stake,
            min_stake=min_stake,
            max_stake=50000,
            leverage=1.0,
            entry_tag=None,
            side='long',
            **{}
        )

        assert result >= min_stake


class TestDCAStrategyAdjustPosition:
    """ポジション調整（DCA追加購入）のテスト"""

    @pytest.fixture
    def strategy(self, default_conf):
        return DCAStrategy(default_conf)

    @pytest.fixture
    def mock_trade(self):
        """モックトレードオブジェクト"""
        trade = MagicMock(spec=Trade)
        trade.pair = 'BTC/JPY'
        trade.open_rate = 10000000
        trade.stake_amount = 1818  # 10000 / 5.5
        trade.amount = 0.0001818
        trade.nr_of_successful_entries = 1
        trade.open_order_id = None
        return trade

    def test_no_adjustment_when_profit_above_threshold(self, strategy, mock_trade):
        """利益が出ている場合は調整しない"""
        current_rate = 10500000  # +5%
        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=current_rate,
            current_order_rate=current_rate,
            side='long',
            **{}
        )

        assert result is None

    def test_first_dca_at_minus_5_percent(self, strategy, mock_trade):
        """-5%でDCA 1回目が実行される"""
        current_rate = 9500000  # -5%
        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=current_rate,
            current_order_rate=current_rate,
            side='long',
            **{}
        )

        assert result is not None
        assert result > 0  # 追加購入額が正の値

    def test_max_dca_entries_respected(self, strategy, mock_trade):
        """最大DCA回数を超えない"""
        mock_trade.nr_of_successful_entries = 4  # 初回 + DCA 3回
        current_rate = 8000000  # -20%

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=current_rate,
            current_order_rate=current_rate,
            side='long',
            **{}
        )

        assert result is None  # これ以上追加購入しない

    def test_returns_none_when_open_orders_exist(self, strategy, mock_trade):
        """オープンオーダーが存在する場合は調整しない"""
        mock_trade.open_order_id = "12345"
        current_rate = 9500000

        result = strategy.adjust_trade_position(
            trade=mock_trade,
            current_time=datetime.now(timezone.utc),
            current_rate=current_rate,
            current_order_rate=current_rate,
            side='long',
            **{}
        )

        assert result is None


class TestDCAStrategyExitSignal:
    """エグジットシグナルのテスト"""

    @pytest.fixture
    def strategy(self, default_conf):
        return DCAStrategy(default_conf)

    def test_exit_at_take_profit_target(self, strategy):
        """利確目標で売りシグナルが出る"""
        df = pd.DataFrame({
            'date': pd.date_range(start='2024-01-01', periods=100, freq='1h'),
            'open': [100 + i * 0.5 for i in range(100)],
            'high': [101 + i * 0.5 for i in range(100)],
            'low': [99 + i * 0.5 for i in range(100)],
            'close': [100.5 + i * 0.5 for i in range(100)],
            'volume': [1000 for _ in range(100)]
        })

        # populate_indicatorsを先に実行（RSI等を計算）
        df = strategy.populate_indicators(df, {})
        result = strategy.populate_exit_trend(df, {})

        # 強い上昇トレンドなので売りシグナルが出るはず
        assert 'exit_long' in result.columns
EOF
```

テストを実行（失敗することを確認）:

```bash
pytest tests/unit/test_dca_strategy.py -v
```

### Step 2-6: DCA戦略の実装（GREEN）

長いファイルなので、コアロジックを実装:

```bash
cat > user_data/strategies/dca_strategy.py << 'EOF'
"""
DCA (Dollar Cost Averaging) トレーディング戦略

価格下落時に段階的に買い増しを行い、平均取得単価を下げる戦略
"""
from freqtrade.strategy import IStrategy, DecimalParameter
from pandas import DataFrame
import talib.abstract as ta
from datetime import datetime, timezone
from typing import Optional
from freqtrade.persistence import Trade


class DCAStrategy(IStrategy):
    """
    DCA戦略クラス

    主要機能:
    - EMA/RSI/ボリンジャーバンドによるエントリー判定
    - 価格下落時の段階的買い増し（DCA）
    - トレーリングストップによる利確
    - 多層的なリスク管理
    """

    # 基本設定
    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False

    # ポジション調整設定
    position_adjustment_enable = True
    max_entry_position_adjustment = 3
    max_dca_multiplier = 5.5

    # ストップロス設定
    stoploss = -0.20

    # トレーリングストップ設定
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # Hyperoptパラメータ
    dca_threshold = DecimalParameter(
        -0.10, -0.03, default=-0.05, decimals=2,
        space='buy', optimize=True
    )
    take_profit = DecimalParameter(
        0.03, 0.10, default=0.05, decimals=2,
        space='sell', optimize=True
    )

    # プロテクション設定
    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 3
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 20,
                "stop_duration_candles": 48,
                "max_allowed_drawdown": 0.15
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": False
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 48,
                "trade_limit": 2,
                "stop_duration_candles": 24,
                "required_profit": -0.05
            }
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        テクニカル指標を計算

        Args:
            dataframe: OHLCVデータ
            metadata: ペア情報等

        Returns:
            指標が追加されたDataFrame
        """
        # EMA
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=26)

        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # ボリンジャーバンド
        bollinger = ta.BBANDS(
            dataframe,
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2
        )
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']

        # 出来高SMA
        dataframe['volume_sma'] = dataframe['volume'].rolling(window=20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        エントリーシグナルを生成

        条件:
        - EMAゴールデンクロス
        - RSIが過売買域から脱却
        - 価格がボリンジャーバンド下限付近
        - 出来高が平均以上

        Args:
            dataframe: 指標計算済みDataFrame
            metadata: ペア情報等

        Returns:
            enter_longシグナルが追加されたDataFrame
        """
        dataframe.loc[
            (
                # EMAゴールデンクロス
                (dataframe['ema_short'] > dataframe['ema_long']) &

                # RSIが過売買域から脱却（30-50の範囲）
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 50) &

                # 価格がボリンジャーバンド下限付近
                (dataframe['close'] < dataframe['bb_middle']) &

                # 出来高確認
                (dataframe['volume'] > dataframe['volume_sma'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        エグジットシグナルを生成

        条件:
        - RSIが過買域（70以上）
        - 価格がボリンジャーバンド上限に接触

        Args:
            dataframe: 指標計算済みDataFrame
            metadata: ペア情報等

        Returns:
            exit_longシグナルが追加されたDataFrame
        """
        dataframe.loc[
            (
                # RSIが過買域
                (dataframe['rsi'] > 70) &

                # ボリンジャーバンド上限に接触
                (dataframe['close'] >= dataframe['bb_upper'])
            ),
            'exit_long'] = 1

        return dataframe

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: Optional[float],
        max_stake: float,
        leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs
    ) -> float:
        """
        カスタムステーク額を計算

        初回注文は proposed_stake / max_dca_multiplier とし、
        DCA用の資金を確保する

        Args:
            proposed_stake: 設定ファイルで指定されたステーク額
            min_stake: 最小ステーク額
            その他: Freqtradeから渡されるパラメータ

        Returns:
            実際のステーク額
        """
        # 初回注文はDCA倍率で割る
        stake = proposed_stake / self.max_dca_multiplier

        # 最小ステーク額を下回らないようにする
        if min_stake and stake < min_stake:
            stake = min_stake

        return stake

    def adjust_trade_position(
        self,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_order_rate: float,
        side: str,
        **kwargs
    ) -> Optional[float]:
        """
        ポジション調整（DCA追加購入）のロジック

        含み損の度合いに応じて段階的に買い増し:
        - -5%: 基準額 x 1.25
        - -10%: 基準額 x 1.50
        - -15%: 基準額 x 1.75

        Args:
            trade: 現在のトレード
            current_rate: 現在価格
            その他: Freqtradeから渡されるパラメータ

        Returns:
            追加購入額（Noneの場合は追加購入なし）
        """
        # オープンオーダーがある場合は調整しない
        if trade.open_order_id:
            return None

        # 最大DCA回数に達している場合は追加購入しない
        if trade.nr_of_successful_entries >= self.max_entry_position_adjustment + 1:
            return None

        # 含み損率を計算
        profit_ratio = (current_rate - trade.open_rate) / trade.open_rate

        # 利益が出ている場合は部分利確を検討
        if profit_ratio >= float(self.take_profit.value):
            # 部分利確（50%売却）はFreqtradeの標準機能で実装
            return None

        # 基準ステーク額
        base_stake = trade.stake_amount

        # DCAのトリガー判定
        if profit_ratio <= -0.15 and trade.nr_of_successful_entries == 3:
            # DCA 3回目（-15%時）
            return base_stake * 1.75
        elif profit_ratio <= -0.10 and trade.nr_of_successful_entries == 2:
            # DCA 2回目（-10%時）
            return base_stake * 1.50
        elif profit_ratio <= float(self.dca_threshold.value) and trade.nr_of_successful_entries == 1:
            # DCA 1回目（-5%時、デフォルト）
            return base_stake * 1.25

        return None

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:
        """
        カスタム売却ロジック

        Args:
            trade: 現在のトレード
            current_profit: 現在の利益率
            その他: Freqtradeから渡されるパラメータ

        Returns:
            売却理由（Noneの場合は売却しない）
        """
        # トレーリングストップは自動で発動するのでここでは特別な処理なし
        return None
EOF
```

テストを実行:

```bash
pytest tests/unit/test_dca_strategy.py -v
# いくつかのテストがPASSするはず（完全ではないかもしれない）
```

### Step 2-7: 全テストの実行とカバレッジ確認

```bash
# 全テストを実行
make test

# カバレッジレポートを確認
open htmlcov/index.html
```

目標: カバレッジ80%以上

### Step 2-8: 市場環境判定モジュールのテスト作成（RED）

新規要件FR-015に対応する市場環境判定機能を実装します。

```bash
cat > tests/unit/test_market_regime.py << 'EOF'
"""
市場環境判定モジュールのユニットテスト
"""
import pytest
import pandas as pd
from user_data.strategies.market_regime import MarketRegime


class TestMarketRegime:
    """市場環境判定のテスト"""

    @pytest.fixture
    def market_regime(self):
        """MarketRegimeインスタンスを返す"""
        return MarketRegime()

    def test_bullish_trend_detection(self, market_regime):
        """強気トレンド判定"""
        df = pd.DataFrame({
            'close': [100 + i for i in range(100)],
            'ema_50': [99 + i for i in range(100)],
            'ema_200': [98 + i for i in range(100)],
            'adx': [30 for _ in range(100)]
        })

        result = market_regime.detect_regime(df)
        assert result == 'bullish'

    def test_bearish_trend_detection(self, market_regime):
        """弱気トレンド判定"""
        df = pd.DataFrame({
            'close': [200 - i for i in range(100)],
            'ema_50': [199 - i for i in range(100)],
            'ema_200': [201 - i for i in range(100)],
            'adx': [28 for _ in range(100)]
        })

        result = market_regime.detect_regime(df)
        assert result == 'bearish'

    def test_sideways_detection(self, market_regime):
        """レンジ相場判定"""
        df = pd.DataFrame({
            'close': [100 for _ in range(100)],
            'ema_50': [100 for _ in range(100)],
            'ema_200': [100 for _ in range(100)],
            'adx': [15 for _ in range(100)]
        })

        result = market_regime.detect_regime(df)
        assert result == 'sideways'

    def test_should_suppress_entry_in_bear_market(self, market_regime):
        """ベアマーケットでエントリー抑制"""
        assert market_regime.should_suppress_entry('bearish') is True
        assert market_regime.should_suppress_entry('bullish') is False
        assert market_regime.should_suppress_entry('sideways') is False
EOF
```

テストを実行（失敗することを確認）:

```bash
pytest tests/unit/test_market_regime.py -v
```

### Step 2-9: 市場環境判定モジュールの実装（GREEN）

```bash
cat > user_data/strategies/market_regime.py << 'EOF'
"""
市場環境判定モジュール

長期EMAとADXを使用してトレンド方向と強度を判定
"""
import pandas as pd
from pandas import DataFrame
import talib.abstract as ta


class MarketRegime:
    """
    市場環境を判定するクラス

    判定基準:
    - Bullish: EMA50 > EMA200 かつ ADX > 25
    - Bearish: EMA50 < EMA200 かつ ADX > 25
    - Sideways: ADX < 20
    """

    def __init__(self):
        self.adx_strong_threshold = 25
        self.adx_weak_threshold = 20

    def detect_regime(self, dataframe: DataFrame) -> str:
        """
        市場環境を判定

        Args:
            dataframe: EMA50, EMA200, ADXを含むDataFrame

        Returns:
            'bullish', 'bearish', 'sideways'のいずれか
        """
        if dataframe.empty or len(dataframe) < 1:
            return 'unknown'

        last_row = dataframe.iloc[-1]

        ema_50 = last_row.get('ema_50', 0)
        ema_200 = last_row.get('ema_200', 0)
        adx = last_row.get('adx', 0)

        # サイドウェイ判定（ADXが低い）
        if adx < self.adx_weak_threshold:
            return 'sideways'

        # トレンド判定
        if ema_50 > ema_200 and adx > self.adx_strong_threshold:
            return 'bullish'
        elif ema_50 < ema_200 and adx > self.adx_strong_threshold:
            return 'bearish'
        else:
            return 'sideways'

    def should_suppress_entry(self, regime: str) -> bool:
        """
        エントリーを抑制すべきか判定

        Args:
            regime: 市場環境（'bullish', 'bearish', 'sideways'）

        Returns:
            ベアトレンド時はTrue、それ以外はFalse
        """
        return regime == 'bearish'

    def add_regime_indicators(self, dataframe: DataFrame) -> DataFrame:
        """
        市場環境判定用の指標を追加

        Args:
            dataframe: OHLCVデータ

        Returns:
            EMA50, EMA200, ADXが追加されたDataFrame
        """
        df = dataframe.copy()

        # 長期EMA
        df['ema_50'] = ta.EMA(df, timeperiod=50)
        df['ema_200'] = ta.EMA(df, timeperiod=200)

        # ADX（トレンド強度）
        df['adx'] = ta.ADX(df, timeperiod=14)

        return df
EOF
```

テストを実行（成功することを確認）:

```bash
pytest tests/unit/test_market_regime.py -v
```

### Step 2-10: スリッページ保護モジュールのテスト作成（RED）

新規要件FR-014に対応するスリッページ保護機能を実装します。

```bash
cat > tests/unit/test_slippage_protection.py << 'EOF'
"""
スリッページ保護モジュールのユニットテスト
"""
import pytest
from user_data.strategies.slippage_protection import SlippageProtection


class TestSlippageProtection:
    """スリッページ保護のテスト"""

    @pytest.fixture
    def slippage_protection(self):
        """SlippageProtectionインスタンスを返す"""
        return SlippageProtection(max_slippage=0.005)  # 0.5%

    def test_allows_order_within_threshold(self, slippage_protection):
        """許容範囲内の注文は通す"""
        expected_price = 10000000
        current_price = 10030000  # +0.3%

        result = slippage_protection.check_slippage(expected_price, current_price)
        assert result is True

    def test_blocks_order_exceeding_threshold(self, slippage_protection):
        """許容範囲を超える注文はブロック"""
        expected_price = 10000000
        current_price = 10070000  # +0.7%

        result = slippage_protection.check_slippage(expected_price, current_price)
        assert result is False

    def test_negative_slippage_within_threshold(self, slippage_protection):
        """マイナス方向のスリッページも許容範囲内ならOK"""
        expected_price = 10000000
        current_price = 9960000  # -0.4%

        result = slippage_protection.check_slippage(expected_price, current_price)
        assert result is True

    def test_calculates_slippage_percentage(self, slippage_protection):
        """スリッページ率を正しく計算"""
        expected_price = 10000000
        current_price = 10050000

        slippage_pct = slippage_protection.calculate_slippage_percentage(
            expected_price, current_price
        )
        assert slippage_pct == pytest.approx(0.005, rel=0.001)  # 0.5%
EOF
```

テストを実行（失敗することを確認）:

```bash
pytest tests/unit/test_slippage_protection.py -v
```

### Step 2-11: スリッページ保護モジュールの実装（GREEN）

```bash
cat > user_data/strategies/slippage_protection.py << 'EOF'
"""
スリッページ保護モジュール

注文時の価格乖離を制限し、想定外の価格での約定を防ぐ
"""


class SlippageProtection:
    """
    スリッページ保護クラス

    注文予定価格と現在市場価格の乖離をチェックし、
    許容範囲を超える場合は注文をスキップする
    """

    def __init__(self, max_slippage: float = 0.005):
        """
        Args:
            max_slippage: 最大許容スリッページ率（デフォルト0.5%）
        """
        self.max_slippage = max_slippage

    def check_slippage(self, expected_price: float, current_price: float) -> bool:
        """
        スリッページが許容範囲内かチェック

        Args:
            expected_price: 注文予定価格
            current_price: 現在市場価格

        Returns:
            許容範囲内ならTrue、超過ならFalse
        """
        if expected_price <= 0 or current_price <= 0:
            return False

        slippage_pct = abs(self.calculate_slippage_percentage(
            expected_price, current_price
        ))

        return slippage_pct <= self.max_slippage

    def calculate_slippage_percentage(
        self,
        expected_price: float,
        current_price: float
    ) -> float:
        """
        スリッページ率を計算

        Args:
            expected_price: 注文予定価格
            current_price: 現在市場価格

        Returns:
            スリッページ率（正の値は上振れ、負の値は下振れ）
        """
        return (current_price - expected_price) / expected_price
EOF
```

テストを実行（成功することを確認）:

```bash
pytest tests/unit/test_slippage_protection.py -v
```

### Step 2-12: DCA戦略への新機能統合

既存のDCA戦略に市場環境判定とスリッページ保護を統合します。

```bash
# dca_strategy.pyを編集
nano user_data/strategies/dca_strategy.py
```

以下の変更を追加:

1. importセクションに追加:
```python
from user_data.strategies.market_regime import MarketRegime
from user_data.strategies.slippage_protection import SlippageProtection
```

2. __init__メソッドに追加:
```python
def __init__(self, config: dict) -> None:
    super().__init__(config)
    self.market_regime = MarketRegime()
    self.slippage_protection = SlippageProtection(max_slippage=0.005)
```

3. populate_indicatorsメソッドに追加:
```python
# 市場環境判定用指標を追加
dataframe = self.market_regime.add_regime_indicators(dataframe)
```

4. populate_entry_trendメソッドに市場環境フィルタを追加:
```python
# 市場環境判定
regime = self.market_regime.detect_regime(dataframe)

dataframe.loc[
    (
        # 既存の条件 ...

        # 市場環境フィルタ（ベアトレンド時はエントリー抑制）
        ~self.market_regime.should_suppress_entry(regime)
    ),
    'enter_long'] = 1
```

### Step 2-13: DCA/利確閾値のHyperoptパラメータ化

要件FR-002とFR-003の修正に対応し、DCA閾値と利確閾値の範囲を拡張します。

dca_strategy.pyのHyperoptパラメータ部分を以下のように修正:

```python
# Hyperoptパラメータ（dca_strategy.pyの該当箇所を修正）

# DCA 1回目の閾値（-5%〜-10%に拡張）
dca_threshold_1 = DecimalParameter(
    -0.10, -0.05, default=-0.07, decimals=2,
    space='buy', optimize=True
)

# DCA 2回目の閾値（-8%〜-15%に拡張）
dca_threshold_2 = DecimalParameter(
    -0.15, -0.08, default=-0.12, decimals=2,
    space='buy', optimize=True
)

# DCA 3回目の閾値（-12%〜-20%に拡張）
dca_threshold_3 = DecimalParameter(
    -0.20, -0.12, default=-0.18, decimals=2,
    space='buy', optimize=True
)

# 利確閾値（+5%〜+15%に拡張）
take_profit_threshold = DecimalParameter(
    0.05, 0.15, default=0.08, decimals=2,
    space='sell', optimize=True
)

# 利確時の売却率（25%〜50%）
take_profit_sell_ratio = DecimalParameter(
    0.25, 0.50, default=0.33, decimals=2,
    space='sell', optimize=True
)
```

adjust_trade_positionメソッドを修正:

```python
def adjust_trade_position(
    self,
    trade: Trade,
    current_time: datetime,
    current_rate: float,
    current_order_rate: float,
    side: str,
    **kwargs
) -> Optional[float]:
    """
    ポジション調整（DCA追加購入）のロジック（更新版）

    Hyperoptで最適化可能な閾値を使用
    """
    if trade.open_order_id:
        return None

    if trade.nr_of_successful_entries >= self.max_entry_position_adjustment + 1:
        return None

    profit_ratio = (current_rate - trade.open_rate) / trade.open_rate
    base_stake = trade.stake_amount

    # DCAのトリガー判定（Hyperopt対応）
    if (profit_ratio <= float(self.dca_threshold_3.value) and
        trade.nr_of_successful_entries == 3):
        return base_stake * 1.75
    elif (profit_ratio <= float(self.dca_threshold_2.value) and
          trade.nr_of_successful_entries == 2):
        return base_stake * 1.50
    elif (profit_ratio <= float(self.dca_threshold_1.value) and
          trade.nr_of_successful_entries == 1):
        return base_stake * 1.25

    return None
```

テストを更新:

```bash
# test_dca_strategy.pyのテストケースを新しい閾値に合わせて更新
nano tests/unit/test_dca_strategy.py

# 例: test_first_dca_at_minus_5_percent -> test_first_dca_at_minus_7_percent
# current_rate = 9500000 -> current_rate = 9300000  # -7%
```

### Phase 2 完了確認チェックリスト

```bash
# 1. 全テストがパスすることを確認
pytest -v

# 2. カバレッジが80%以上であることを確認
pytest --cov=user_data/strategies --cov-report=term-missing

# 3. コードスタイルチェック
make lint

# 4. 新機能のテストを個別に確認
pytest tests/unit/test_market_regime.py tests/unit/test_slippage_protection.py -v

# 5. コミット
git add .
git commit -m "Phase 2: Implement DCA strategy with market regime, slippage protection, and Hyperopt enhancements"
```

---

## Phase 3: パラメータ設計と設定ファイル

推定所要時間: 2-3時間

### Step 3-1: Dry Run設定ファイルの作成

```bash
cat > user_data/config/config.json << 'EOF'
{
  "max_open_trades": 2,
  "stake_currency": "JPY",
  "stake_amount": 10000,
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "JPY",

  "dry_run": true,
  "dry_run_wallet": 50000,

  "cancel_open_orders_on_exit": false,

  "unfilledtimeout": {
    "entry": 10,
    "exit": 30
  },

  "entry_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1,
    "price_last_balance": 0.0,
    "check_depth_of_market": {
      "enabled": false,
      "bids_to_ask_delta": 1
    }
  },

  "exit_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1
  },

  "exchange": {
    "name": "binance",
    "key": "",
    "secret": "",
    "ccxt_config": {
      "enableRateLimit": true,
      "rateLimit": 200
    },
    "ccxt_async_config": {
      "enableRateLimit": true,
      "rateLimit": 200
    },
    "pair_whitelist": [
      "BTC/JPY",
      "ETH/JPY"
    ],
    "pair_blacklist": []
  },

  "pairlists": [
    {
      "method": "StaticPairList"
    }
  ],

  "telegram": {
    "enabled": true,
    "token": "${TELEGRAM_TOKEN}",
    "chat_id": "${TELEGRAM_CHAT_ID}",
    "notification_settings": {
      "status": "on",
      "warning": "on",
      "startup": "on",
      "entry": "on",
      "entry_fill": "on",
      "entry_cancel": "on",
      "exit": "on",
      "exit_fill": "on",
      "exit_cancel": "on",
      "protection_trigger": "on",
      "protection_trigger_global": "on"
    }
  },

  "api_server": {
    "enabled": true,
    "listen_ip_address": "127.0.0.1",
    "listen_port": 8080,
    "verbosity": "info",
    "enable_openapi": false,
    "jwt_secret_key": "changeme",
    "CORS_origins": [],
    "username": "freqtrader",
    "password": "changeme"
  },

  "bot_name": "crypto-dca-bot",
  "initial_state": "running",
  "force_entry_enable": false,
  "internals": {
    "process_throttle_secs": 5
  }
}
EOF
```

### Step 3-2: バックテスト設定ファイルの作成

```bash
cat > user_data/config/config.backtest.json << 'EOF'
{
  "max_open_trades": 2,
  "stake_currency": "JPY",
  "stake_amount": 10000,
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "JPY",

  "dry_run": true,
  "dry_run_wallet": 50000,

  "timeframe": "1h",

  "exchange": {
    "name": "binance",
    "pair_whitelist": [
      "BTC/JPY",
      "ETH/JPY"
    ]
  },

  "pairlists": [
    {
      "method": "StaticPairList"
    }
  ],

  "fee": 0.0005
}
EOF
```

### Step 3-3: Hyperopt設定ファイルの作成

```bash
cat > user_data/config/config.hyperopt.json << 'EOF'
{
  "max_open_trades": 2,
  "stake_currency": "JPY",
  "stake_amount": 10000,
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "JPY",

  "dry_run": true,
  "dry_run_wallet": 50000,

  "timeframe": "1h",

  "exchange": {
    "name": "binance",
    "pair_whitelist": [
      "BTC/JPY",
      "ETH/JPY"
    ]
  },

  "pairlists": [
    {
      "method": "StaticPairList"
    }
  ],

  "fee": 0.0005,

  "hyperopt_random_state": 42,
  "hyperopt_min_trades": 30,
  "hyperopt_loss": "SharpeHyperOptLoss"
}
EOF
```

### Step 3-4: ライブ設定ファイルの作成（テンプレート）

```bash
cat > user_data/config/config.live.json << 'EOF'
{
  "max_open_trades": 2,
  "stake_currency": "JPY",
  "stake_amount": 10000,
  "tradable_balance_ratio": 0.99,
  "fiat_display_currency": "JPY",

  "dry_run": false,

  "cancel_open_orders_on_exit": false,

  "unfilledtimeout": {
    "entry": 10,
    "exit": 30
  },

  "entry_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1,
    "price_last_balance": 0.0,
    "check_depth_of_market": {
      "enabled": false,
      "bids_to_ask_delta": 1
    }
  },

  "exit_pricing": {
    "price_side": "same",
    "use_order_book": true,
    "order_book_top": 1
  },

  "exchange": {
    "name": "binance",
    "key": "${BINANCE_API_KEY}",
    "secret": "${BINANCE_API_SECRET}",
    "ccxt_config": {
      "enableRateLimit": true,
      "rateLimit": 200
    },
    "ccxt_async_config": {
      "enableRateLimit": true,
      "rateLimit": 200
    },
    "pair_whitelist": [
      "BTC/JPY",
      "ETH/JPY"
    ],
    "pair_blacklist": []
  },

  "pairlists": [
    {
      "method": "StaticPairList"
    }
  ],

  "telegram": {
    "enabled": true,
    "token": "${TELEGRAM_TOKEN}",
    "chat_id": "${TELEGRAM_CHAT_ID}",
    "notification_settings": {
      "status": "on",
      "warning": "on",
      "startup": "on",
      "entry": "on",
      "entry_fill": "on",
      "entry_cancel": "on",
      "exit": "on",
      "exit_fill": "on",
      "exit_cancel": "on",
      "protection_trigger": "on",
      "protection_trigger_global": "on"
    }
  },

  "api_server": {
    "enabled": true,
    "listen_ip_address": "127.0.0.1",
    "listen_port": 8080,
    "verbosity": "info",
    "enable_openapi": false,
    "jwt_secret_key": "CHANGE_THIS_TO_RANDOM_STRING",
    "CORS_origins": [],
    "username": "freqtrader",
    "password": "CHANGE_THIS_PASSWORD"
  },

  "bot_name": "crypto-dca-bot-live",
  "initial_state": "running",
  "force_entry_enable": false,
  "internals": {
    "process_throttle_secs": 5
  }
}
EOF
```

### Step 3-5: 環境変数の設定

.envファイルを編集:

```bash
# エディタで開く
nano .env
```

以下の内容を記入（実際の値は後で取得）:

```
# Binance API設定（Phase 6で設定）
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Telegram Bot設定（次のステップで取得）
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# 環境設定
ENVIRONMENT=dry_run
```

### Step 3-6: Telegram Bot設定

Telegram Botを作成してトークンとチャットIDを取得します。

1. Telegramで@BotFatherを検索して開く
2. `/newbot` コマンドを送信
3. ボット名を入力（例: Crypto DCA Bot）
4. ボットユーザー名を入力（例: crypto_dca_bot_12345）
5. トークンが発行される（例: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz）
6. トークンを.envファイルの `TELEGRAM_TOKEN` に設定

チャットIDの取得:

```bash
# ボットにメッセージを送信後、以下のコマンドで確認
curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
# 出力されるJSONから "chat": {"id": 123456789} を探す
```

チャットIDを.envファイルの `TELEGRAM_CHAT_ID` に設定

### Step 3-7: Telegram手動クローズコマンドの実装（FR-016対応）

新規要件FR-016に対応する`/forceclose`コマンドを実装します。

Freqtradeでは、Telegramコマンドは主に設定ファイルで有効化されますが、カスタムコマンドを追加する場合は戦略ファイル内でカスタム処理を実装します。

dca_strategy.pyに以下を追加:

```python
# dca_strategy.pyのメソッドとして追加

def custom_command_forceclose(
    self,
    pair: str,
    trade: Trade,
    current_time: datetime,
    current_rate: float,
    **kwargs
) -> Optional[str]:
    """
    手動クローズコマンド用のカスタムロジック

    Telegramの /forceclose コマンド経由で呼び出される

    Args:
        pair: 通貨ペア
        trade: クローズするトレード
        current_rate: 現在価格

    Returns:
        クローズ理由
    """
    return 'force_closed_by_user'
```

config.jsonのTelegramセクションにカスタムコマンドを追加（Freqtrade標準機能を利用）:

```json
"telegram": {
  "enabled": true,
  "token": "${TELEGRAM_TOKEN}",
  "chat_id": "${TELEGRAM_CHAT_ID}",
  "notification_settings": {
    // ... 既存設定 ...
  },
  "enabled_commands": [
    "status",
    "balance",
    "stop",
    "start",
    "forcesell",  // 注: forcecloseはforcesellコマンドで実装
    "help"
  ]
}
```

注: Freqtradeでは `/forcesell <pair>` コマンドが標準で用意されており、これを `/forceclose` の代わりに使用します。

使用方法:
```
/forcesell BTC/JPY  # BTC/JPYペアを強制決済
/forcesell all      # すべてのポジションを強制決済
```

### Step 3-8: データダウンロードスクリプトの作成

```bash
cat > scripts/download_data.sh << 'EOF'
#!/bin/bash
# OHLCVデータをダウンロードするスクリプト

set -e

echo "Downloading OHLCV data from Binance..."

freqtrade download-data \
  --exchange binance \
  --pairs BTC/JPY ETH/JPY \
  --timerange 20240301-20260127 \
  --timeframes 1h 4h 1d \
  --config user_data/config/config.backtest.json

echo "Data download complete!"
echo "Data location: user_data/data/binance/"
EOF

chmod +x scripts/download_data.sh
```

### Step 3-9: 設定検証スクリプトの作成（NFR-010対応）

起動時に設定ファイルのスキーマ検証を行うスクリプトを作成します。

```bash
cat > scripts/validate_config.py << 'EOF'
#!/usr/bin/env python3
"""
設定ファイル検証スクリプト（NFR-010対応）

起動前に設定ファイルの妥当性をチェック
"""
import json
import sys
from pathlib import Path


def validate_config(config_path: str) -> bool:
    """
    設定ファイルを検証

    Args:
        config_path: 設定ファイルパス

    Returns:
        検証合格ならTrue、不合格ならFalse
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {config_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config file: {e}")
        return False

    # 必須パラメータチェック
    required_fields = [
        'max_open_trades',
        'stake_currency',
        'stake_amount',
        'dry_run'
    ]

    for field in required_fields:
        if field not in config:
            print(f"ERROR: Missing required field: {field}")
            return False

    # 値の妥当性チェック
    if config['stake_amount'] <= 0:
        print("ERROR: stake_amount must be positive")
        return False

    if config['max_open_trades'] <= 0:
        print("ERROR: max_open_trades must be positive")
        return False

    # ライブモードでの高額stake確認
    if not config['dry_run'] and config['stake_amount'] > 50000:
        print("WARNING: Large stake_amount in live mode!")
        print(f"  stake_amount: {config['stake_amount']}")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted by user")
            return False

    print("✓ Config validation passed")
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python validate_config.py <config_file>")
        sys.exit(1)

    config_path = sys.argv[1]
    if validate_config(config_path):
        sys.exit(0)
    else:
        sys.exit(1)
EOF

chmod +x scripts/validate_config.py
```

使用方法:
```bash
# ライブ設定ファイルを検証
python scripts/validate_config.py user_data/config/config.live.json
```

### Step 3-10: ハートビート送信スクリプトの作成（NFR-011対応）

外部監視サービス（UptimeRobot等）へのハートビート送信を実装します。

```bash
cat > scripts/heartbeat.sh << 'EOF'
#!/bin/bash
# ハートビート送信スクリプト（NFR-011対応）
# 5分ごとにcronで実行することを想定

set -e

# 環境変数からハートビートURLを取得
if [ -z "$HEARTBEAT_URL" ]; then
    echo "WARNING: HEARTBEAT_URL not set, skipping heartbeat"
    exit 0
fi

# ボットの稼働確認
if ! pgrep -f "freqtrade trade" > /dev/null; then
    echo "ERROR: Freqtrade process not running!"
    # ハートビートを送信しない（監視サービスがアラートを出す）
    exit 1
fi

# ハートビート送信
curl -s -o /dev/null -w "%{http_code}" "$HEARTBEAT_URL" > /tmp/heartbeat_response.txt
HTTP_CODE=$(cat /tmp/heartbeat_response.txt)

if [ "$HTTP_CODE" == "200" ]; then
    echo "Heartbeat sent successfully"
else
    echo "WARNING: Heartbeat failed with HTTP $HTTP_CODE"
fi
EOF

chmod +x scripts/heartbeat.sh
```

.envファイルに追加:
```bash
# .envに以下を追加
echo "" >> .env
echo "# ハートビートURL（UptimeRobot等）" >> .env
echo "HEARTBEAT_URL=https://heartbeat.uptimerobot.com/your-monitor-id" >> .env
```

cron設定（5分ごとに実行）:
```bash
# crontabを編集
crontab -e

# 以下を追加
*/5 * * * * /path/to/crypto-dca-bot/scripts/heartbeat.sh >> /var/log/heartbeat.log 2>&1
```

### Step 3-11: DBバックアップスクリプトの作成（NFR-012対応）

tradesv3.sqliteの日次バックアップを実装します。

```bash
cat > scripts/backup_db.sh << 'EOF'
#!/bin/bash
# DBバックアップスクリプト（NFR-012対応）
# 日次でcronで実行することを想定

set -e

# バックアップディレクトリ
BACKUP_DIR="$HOME/crypto-dca-bot-backups"
mkdir -p "$BACKUP_DIR"

# DBファイルパス
DB_PATH="user_data/tradesv3.sqlite"
LIVE_DB_PATH="user_data/tradesv3.dryrun.sqlite"

# タイムスタンプ
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting database backup..."

# Dry Run DBのバックアップ
if [ -f "$DB_PATH" ]; then
    cp "$DB_PATH" "$BACKUP_DIR/tradesv3_${TIMESTAMP}.sqlite"
    echo "✓ Backed up: $DB_PATH"
fi

# Live DBのバックアップ
if [ -f "$LIVE_DB_PATH" ]; then
    cp "$LIVE_DB_PATH" "$BACKUP_DIR/tradesv3_live_${TIMESTAMP}.sqlite"
    echo "✓ Backed up: $LIVE_DB_PATH"
fi

# 30日以上古いバックアップを削除
find "$BACKUP_DIR" -name "tradesv3_*.sqlite" -mtime +30 -delete
echo "✓ Cleaned up old backups (>30 days)"

# バックアップ数を表示
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/tradesv3_*.sqlite 2>/dev/null | wc -l)
echo "Total backups: $BACKUP_COUNT"
echo "Backup directory: $BACKUP_DIR"
EOF

chmod +x scripts/backup_db.sh
```

cron設定（毎日午前3時に実行）:
```bash
# crontabを編集
crontab -e

# 以下を追加
0 3 * * * /path/to/crypto-dca-bot/scripts/backup_db.sh >> /var/log/db_backup.log 2>&1
```

手動バックアップの実行:
```bash
./scripts/backup_db.sh
```

復旧手順のドキュメント化:

```bash
cat > docs/RECOVERY.md << 'EOF'
# データベース復旧手順

## 概要
tradesv3.sqliteが破損した場合やデータを復元したい場合の手順

## 復旧ステップ

### 1. ボットを停止
```bash
# Telegramで /stop
# または
freqtrade stop
```

### 2. バックアップの確認
```bash
ls -lh ~/crypto-dca-bot-backups/
```

### 3. 復元したいバックアップを選択
```bash
# 例: 2026年1月27日のバックアップを復元
BACKUP_FILE="tradesv3_20260127_030000.sqlite"
```

### 4. 現在のDBをバックアップ（念のため）
```bash
cp user_data/tradesv3.sqlite user_data/tradesv3.sqlite.backup
```

### 5. バックアップから復元
```bash
cp ~/crypto-dca-bot-backups/$BACKUP_FILE user_data/tradesv3.sqlite
```

### 6. ボットを再起動
```bash
freqtrade trade --config user_data/config/config.live.json --strategy DCAStrategy
```

### 7. データ整合性確認
```bash
# Telegramで /status
# または
freqtrade show-trades
```

## 注意事項
- 復元後、最新のトレード情報が失われる可能性があります
- Binance Web画面と照合して、オープンポジションが正しいか確認してください
- 不整合がある場合は、手動で調整が必要です
EOF
```

### Step 3-12: 設定ファイルにスリッページ許容値を追加

config.live.jsonとconfig.jsonにスリッページ設定を追加:

```bash
# config.jsonとconfig.live.jsonの両方に以下を追加
nano user_data/config/config.json
```

以下のセクションを追加:

```json
{
  // ... 既存設定 ...

  "order_types": {
    "entry": "limit",
    "exit": "limit",
    "emergency_exit": "market",
    "force_entry": "market",
    "force_exit": "market",
    "stoploss": "market",
    "stoploss_on_exchange": false,
    "stoploss_on_exchange_interval": 60
  },

  "order_time_in_force": {
    "entry": "GTC",
    "exit": "GTC"
  },

  "custom_strategy_params": {
    "max_slippage": 0.005
  }
}
```

### Phase 3 完了確認チェックリスト

```bash
# 1. 設定ファイルが正しく作成されているか確認
ls -la user_data/config/

# 2. .envファイルが作成されているか確認
cat .env

# 3. 設定ファイルのJSON構文チェック
python -m json.tool user_data/config/config.json
python -m json.tool user_data/config/config.backtest.json

# 4. コミット
git add .
git commit -m "Phase 3: Add configuration files and parameter settings"
```

---

## Phase 4: バックテストと最適化

推定所要時間: 3-5時間（データダウンロード含む）

### Step 4-1: OHLCVデータのダウンロード

```bash
# データダウンロードスクリプトを実行
./scripts/download_data.sh
```

注意: Binance Japan BTC/JPYは2024年3月以降のデータのみ利用可能

### Step 4-2: バックテストの実行

```bash
# バックテスト実行
freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20240301-20260127
```

出力例:
```
=========================================== BACKTESTING REPORT ===========================================
|   Pair |   Entries |   Avg Profit % |   Tot Profit JPY |   Tot Profit % |   Avg Duration |   Win  Draw  Loss  Win% |
|--------+-----------+----------------+------------------+----------------+----------------+-------------------------|
|  Total |        50 |           2.15 |         5375.00 |          10.75 |       2d 8h    |    32     0    18   64.0 |
=============================================================================================================
```

### Step 4-3: バックテスト結果の分析

バックテスト結果は `user_data/backtest_results/` に保存されます。

```bash
# 最新のバックテスト結果を確認
ls -lt user_data/backtest_results/

# HTMLレポートを開く（生成されている場合）
open user_data/backtest_results/backtest-result-*.html
```

合格基準チェック:

| メトリクス | 最低基準 | 目標値 | 実際の値 |
|-----------|---------|--------|---------|
| 勝率 | >= 50% | >= 60% | ? |
| プロフィットファクター | >= 1.2 | >= 1.5 | ? |
| Sharpe比 | >= 0.5 | >= 1.0 | ? |
| 最大ドローダウン | <= 20% | <= 15% | ? |
| 最低トレード数 | >= 30 | - | ? |

### Step 4-4: ウォークフォワード分析

データを分割してIn-sample/Out-of-sample検証:

```bash
# In-sample期間（2024/03 - 2025/06）
freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20240301-20250630 \
  --export trades

# Out-of-sample期間（2025/07 - 2025/12）
freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20250701-20251231 \
  --export trades

# 最終確認期間（2026/01）
freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20260101-20260127 \
  --export trades
```

In-sample と Out-of-sample のパフォーマンス差を確認:

劣化率 = (Out-of-sample Sharpe - In-sample Sharpe) / In-sample Sharpe
目標: 劣化率 <= 30%

### Step 4-5: Hyperoptによるパラメータ最適化

```bash
# Hyperopt実行（時間がかかるので注意）
freqtrade hyperopt \
  --config user_data/config/config.hyperopt.json \
  --strategy DCAStrategy \
  --hyperopt-loss SharpeHyperOptLoss \
  --spaces buy sell \
  --epochs 500 \
  --timerange 20240301-20250630 \
  --job-workers 4
```

最適化結果の例:
```
Best result:
    512/500:    100 trades. Avg profit  2.34%. Total profit  0.11678900 JPY (  11.68%). Avg duration 2d 6h. Objective: -1.23456

    Buy hyperspace params:
    {
        "dca_threshold": -0.048,
    }

    Sell hyperspace params:
    {
        "take_profit": 0.062
    }
```

### Step 4-6: 最適化パラメータの適用

Hyperoptで得られた最適パラメータを戦略ファイルに反映:

```bash
# dca_strategy.pyを編集
nano user_data/strategies/dca_strategy.py
```

以下の行を最適化結果で置き換え:

```python
# 変更前
dca_threshold = DecimalParameter(-0.10, -0.03, default=-0.05, ...)
take_profit = DecimalParameter(0.03, 0.10, default=0.05, ...)

# 変更後（Hyperoptの結果に基づく）
dca_threshold = DecimalParameter(-0.10, -0.03, default=-0.048, ...)
take_profit = DecimalParameter(0.03, 0.10, default=0.062, ...)
```

### Step 4-7: 最適化後のバックテスト

```bash
# パラメータ更新後にバックテスト再実行
freqtrade backtesting \
  --config user_data/config/config.backtest.json \
  --strategy DCAStrategy \
  --timerange 20240301-20260127
```

### Phase 4 完了確認チェックリスト

```bash
# 1. バックテスト結果が合格基準を満たしているか確認
# （手動でメトリクスをチェック）

# 2. ウォークフォワード分析で過学習していないか確認
# （In-sample と Out-of-sample の劣化率が30%以内）

# 3. 最適化結果を戦略に反映したか確認
grep "dca_threshold.*default" user_data/strategies/dca_strategy.py

# 4. コミット
git add .
git commit -m "Phase 4: Complete backtesting and hyperparameter optimization"
```

---

## Phase 5: Dry Run検証（最低2週間）

推定所要時間: 2週間（監視期間）

### Step 5-1: Dry Runモードの起動

```bash
# 仮想環境をアクティベート
source .venv/bin/activate

# Dry Runモードでボットを起動
freqtrade trade \
  --config user_data/config/config.json \
  --strategy DCAStrategy
```

ターミナルに以下のようなログが表示されます:

```
2026-01-27 10:00:00 - freqtrade - INFO - Starting freqtrade 2024.x
2026-01-27 10:00:00 - freqtrade - INFO - Dry run is enabled
2026-01-27 10:00:00 - freqtrade - INFO - Using DB: "sqlite:///user_data/tradesv3.dryrun.sqlite"
2026-01-27 10:00:00 - freqtrade - INFO - Starting worker
```

### Step 5-2: バックグラウンドでの実行（推奨）

```bash
# tmuxセッションを作成
tmux new -s freqtrade

# Dry Run起動
freqtrade trade --config user_data/config/config.json --strategy DCAStrategy

# tmuxからデタッチ: Ctrl-b d

# tmuxに再アタッチ
tmux attach -t freqtrade
```

### Step 5-3: 毎日の監視チェックリスト

毎日以下を確認:

1. ボット稼働状況

```bash
# Telegramで /status コマンドを送信
# または
freqtrade status
```

2. ログ確認

```bash
tail -f user_data/logs/freqtrade.log
```

3. 注文履歴確認

```bash
# Telegramで /trades コマンドを送信
# または
freqtrade show-trades --trade-ids all
```

4. パフォーマンスメトリクス

```bash
freqtrade performance
```

### Step 5-4: 監視スプレッドシート（推奨）

Googleスプレッドシートやエクセルで以下を記録:

| 日付 | 稼働時間 | 注文数 | 利益/損失 | APIエラー | 備考 |
|------|---------|-------|----------|-----------|------|
| 2026-01-27 | 24h | 2 | +0.5% | 0 | 初日 |
| 2026-01-28 | 24h | 1 | -0.3% | 0 | - |
| ... | ... | ... | ... | ... | ... |

### Step 5-5: 合格基準の確認（2週間後）

| メトリクス | 基準 | 実際の値 | 合否 |
|-----------|------|---------|------|
| 稼働率 | >= 99% | ? | ? |
| APIエラー率 | < 1% | ? | ? |
| 注文正確性 | 100% | ? | ? |
| バックテストとの乖離 | Sharpe比差 0.3以内 | ? | ? |

### Step 5-6: 問題発生時の対応

よくある問題と対処法:

1. APIエラー連続発生

```bash
# ログ確認
tail -f user_data/logs/freqtrade.log | grep ERROR

# レート制限の可能性 -> config.jsonのrateLimit値を増やす
nano user_data/config/config.json
# "rateLimit": 200 -> "rateLimit": 500
```

2. 予期しない注文

```bash
# 緊急停止
# Telegramで /stop コマンド
# または
freqtrade stop

# ログを確認して原因調査
grep "enter_long" user_data/logs/freqtrade.log
```

3. ボットが停止している

```bash
# プロセス確認
ps aux | grep freqtrade

# 停止している場合は再起動
freqtrade trade --config user_data/config/config.json --strategy DCAStrategy
```

### Phase 5 完了確認チェックリスト

```bash
# 1. 2週間以上の連続稼働を確認
# （手動でログとTelegram通知を確認）

# 2. 合格基準を満たしているか確認
# （スプレッドシートでメトリクスをまとめる）

# 3. 問題なければPhase 6（ライブ移行）へ進む準備
git add .
git commit -m "Phase 5: Complete Dry Run validation (2 weeks)"
```

---

## Phase 6: ライブ移行

推定所要時間: 1-2時間（初期セットアップ）+ 3-4週間（段階的投入期間）

注意: この段階から実際の資金を使用します。慎重に進めてください。

### Step 6-1: Binance Japan APIキーの作成

1. Binance Japan (https://www.binance.com/ja) にログイン
2. アカウント -> API管理
3. 「APIキーを作成」をクリック
4. APIキー名を入力（例: crypto-dca-bot）
5. 権限設定:
   - Spot & Margin Trading: 有効
   - Withdrawals: 無効（重要）
   - Futures: 無効
6. IP制限（推奨）:
   - ローカル開発時: 自宅のIPアドレスを設定
   - VPS移行後: VPSのIPアドレスに変更
7. APIキーとシークレットをコピー

### Step 6-2: .envファイルの更新

```bash
# .envファイルを編集
nano .env
```

以下のように更新:

```
# Binance API設定
BINANCE_API_KEY=<実際のAPIキー>
BINANCE_API_SECRET=<実際のシークレット>

# Telegram Bot設定
TELEGRAM_TOKEN=<実際のBotトークン>
TELEGRAM_CHAT_ID=<実際のチャットID>

# 環境設定
ENVIRONMENT=live
```

### Step 6-3: ライブ設定ファイルの最終確認

```bash
# config.live.jsonを確認
cat user_data/config/config.live.json

# 重要: dry_run が false になっているか確認
grep "dry_run" user_data/config/config.live.json
# 出力: "dry_run": false
```

### Step 6-4: 段階的資金投入計画

Week 1: 少額テスト（1-2万円）

```bash
# config.live.jsonを編集
nano user_data/config/config.live.json
```

以下のパラメータを変更:

```json
{
  "max_open_trades": 1,
  "stake_amount": 5000,
  "dry_run_wallet": null
}
```

ライブモードで起動:

```bash
# tmuxセッションを作成
tmux new -s freqtrade-live

# ライブモードで起動
freqtrade trade --config user_data/config/config.live.json --strategy DCAStrategy

# tmuxからデタッチ: Ctrl-b d
```

Week 2: 5万円に増額

```bash
# ボットを停止
# Telegramで /stop

# config.live.jsonを編集
nano user_data/config/config.live.json
```

```json
{
  "max_open_trades": 2,
  "stake_amount": 10000
}
```

```bash
# ボット再起動
freqtrade trade --config user_data/config/config.live.json --strategy DCAStrategy
```

Week 3-4: 目標金額（10-30万円）

同様に `stake_amount` を調整して徐々に資金を投入

### Step 6-5: 毎日の監視（ライブモード）

Dry Runと同じ監視項目に加えて:

1. 実際の残高確認

```bash
# Telegramで /balance コマンド
```

2. 実トレード履歴

```bash
# Telegramで /trades コマンド
```

3. 損益レポート

```bash
freqtrade profit
```

4. Binance取引履歴との照合

Binance Japan Webサイトで注文履歴を確認し、ボットの注文と一致しているか確認

### Step 6-6: 異常時対応フロー

| 状況 | 対応 |
|------|------|
| DD 10% | 通知受信、状況注視（正常範囲内） |
| DD 15% | サーキットブレーカー自動発動（新規注文停止） |
| DD 20% | 手動停止 `/stop`、原因分析 |
| API連続5回エラー | 手動介入、APIキー確認 |
| 予期しない大量注文 | 即座に `/stop`、全ポジション手動決済 |

### Step 6-7: 緊急停止手順

```bash
# 方法1: Telegram
# /stop コマンドを送信

# 方法2: CLI
freqtrade stop

# 方法3: プロセスKill
ps aux | grep freqtrade
kill <PID>

# 全ポジション手動決済（Binance Webサイト）
# オープンオーダーをすべてキャンセル
# ポジションを市場価格で決済
```

### Phase 6 完了確認チェックリスト

```bash
# 1. 段階的資金投入が完了したか確認
# （Week 3-4で目標金額に到達）

# 2. 実績メトリクスを記録
freqtrade show-trades
freqtrade profit

# 3. バックテストとの乖離を確認
# （実トレード Sharpe比 vs バックテスト Sharpe比）

# 4. 次のフェーズ（Docker + VPS）への準備
git add .
git commit -m "Phase 6: Complete live trading migration"
```

---

## Phase 7: Docker + VPS移行

推定所要時間: 3-4時間

### Step 7-1: Dockerfileの作成

```bash
cat > Dockerfile << 'EOF'
FROM freqtradeorg/freqtrade:stable

# ユーザーデータをコピー
COPY user_data /freqtrade/user_data

# 環境変数ファイルをコピー
COPY .env /freqtrade/.env

WORKDIR /freqtrade

CMD ["trade", "--config", "/freqtrade/user_data/config/config.live.json", "--strategy", "DCAStrategy"]
EOF
```

### Step 7-2: docker-compose.ymlの作成

```bash
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  freqtrade:
    image: freqtradeorg/freqtrade:stable
    container_name: crypto-dca-bot
    restart: unless-stopped
    volumes:
      - ./user_data:/freqtrade/user_data
    ports:
      - "8080:8080"
    command: >
      trade
      --config /freqtrade/user_data/config/config.live.json
      --strategy DCAStrategy
    env_file:
      - .env
    environment:
      - TZ=Asia/Tokyo
EOF
```

### Step 7-3: ローカルでDockerテスト

```bash
# Dockerイメージをビルド
docker-compose build

# Dry Runモードでテスト
# まず config.live.json の dry_run を一時的に true に変更
docker-compose up -d

# ログ確認
docker-compose logs -f

# 問題なければ停止
docker-compose down
```

### Step 7-4: VPSの選択と契約

推奨VPS:

1. さくらVPS（推奨度☆4）
   - プラン: 2GBメモリ
   - 料金: 約1,000円/月
   - メリット: 国内、サポート充実
   - デメリット: 海外VPSより若干高い

2. Vultr Tokyo（推奨度☆4）
   - プラン: 2GB RAM
   - 料金: $6/月
   - メリット: 安価、東京リージョン
   - デメリット: 英語サポートのみ

いずれかのVPSを契約してください。

### Step 7-5: VPSへのSSH接続設定

```bash
# SSH公開鍵を生成（まだ持っていない場合）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 公開鍵をVPSに登録
ssh-copy-id root@<VPS_IP>

# SSH接続確認
ssh root@<VPS_IP>
```

### Step 7-6: VPSへの環境構築

VPSにSSH接続後:

```bash
# Dockerインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Docker Composeインストール
apt-get install -y docker-compose-plugin

# Gitインストール
apt-get install -y git

# リポジトリをクローン
git clone <your-repo-url> /opt/crypto-dca-bot
cd /opt/crypto-dca-bot
```

### Step 7-7: .envファイルの設定（VPS）

```bash
# .envファイルを作成（ローカルからコピー）
nano .env
```

実際のAPIキーとトークンを設定

### Step 7-8: Binance API IP制限の更新

1. Binance Japan -> API管理
2. 既存のAPIキーを編集
3. IP制限をVPSのIPアドレスに変更

### Step 7-9: VPSでDocker起動

```bash
# Docker Composeで起動
cd /opt/crypto-dca-bot
docker-compose up -d

# ログ確認
docker-compose logs -f

# ステータス確認
docker-compose ps
```

### Step 7-10: systemdでの自動起動設定（オプション）

```bash
cat > /etc/systemd/system/crypto-dca-bot.service << 'EOF'
[Unit]
Description=Crypto DCA Trading Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/crypto-dca-bot
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# サービス有効化
systemctl enable crypto-dca-bot.service
systemctl start crypto-dca-bot.service
```

### Step 7-11: 監視とメンテナンス

```bash
# ログ確認
docker-compose logs --tail=100 -f

# ボット再起動
docker-compose restart

# 設定更新時
git pull
docker-compose down
docker-compose up -d

# Dockerコンテナのリソース使用状況
docker stats crypto-dca-bot
```

### Phase 7 完了確認チェックリスト

```bash
# 1. VPS上でボットが稼働しているか確認
docker-compose ps

# 2. Telegram通知が届くか確認
# /status コマンドを送信

# 3. ローカルのボットを停止
# （VPS版に移行完了）

# 4. 最終コミット
git add .
git commit -m "Phase 7: Complete Docker and VPS migration"
git push
```

---

## 付録A: トラブルシューティング

### Q1: `freqtrade: command not found`

仮想環境がアクティベートされていない可能性:

```bash
source .venv/bin/activate
which freqtrade
```

### Q2: テストが失敗する

依存関係の問題:

```bash
pip install --upgrade freqtrade pytest pytest-mock
pytest -v
```

### Q3: バックテストでデータが不足

データをダウンロード:

```bash
./scripts/download_data.sh
```

### Q4: APIエラー: "Signature invalid"

APIキーとシークレットが正しいか確認:

```bash
# .envファイルを確認
cat .env

# Binance APIキーの設定を再確認
```

### Q5: Telegram通知が届かない

トークンとチャットIDを確認:

```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
curl https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```

---

## 付録B: 便利なコマンド一覧

```bash
# テスト実行
make test

# バックテスト
make backtest

# Hyperopt
make hyperopt

# コードフォーマット
make format

# リント
make lint

# クリーンアップ
make clean

# Dry Run起動
freqtrade trade --config user_data/config/config.json --strategy DCAStrategy

# ライブモード起動
freqtrade trade --config user_data/config/config.live.json --strategy DCAStrategy

# ステータス確認
freqtrade status

# 利益確認
freqtrade profit

# トレード履歴
freqtrade show-trades

# バージョン確認
freqtrade --version
```

---

## 付録C: 参考リンク

- Freqtrade公式ドキュメント: https://www.freqtrade.io/
- Binance API仕様: https://binance-docs.github.io/apidocs/
- Telegram Bot API: https://core.telegram.org/bots/api
- TA-Lib (テクニカル指標): https://ta-lib.org/
- Docker公式ドキュメント: https://docs.docker.com/

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|---------|
| 1.0 | 2026-01-27 | 初版作成 |
| 1.1 | 2026-01-28 | Phase 2にStep 2-8〜2-13追加（市場環境判定、スリッページ保護、Hyperoptパラメータ化）、Phase 3にStep 3-7〜3-12追加（Telegram手動クローズ、設定検証、ハートビート、DBバックアップ） |

---

## まとめ

このガイドに従うことで、仮想通貨DCAトレーディングボットを0から構築できます。
各フェーズを慎重に進め、テストと検証を怠らないようにしてください。

疑問点や問題が発生した場合は、付録Aのトラブルシューティングを参照するか、
Freqtrade公式ドキュメントを確認してください。

成功を祈ります。
