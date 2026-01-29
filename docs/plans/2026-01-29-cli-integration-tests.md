# CLI Integration Tests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add CLI integration tests for monte_carlo.py, analyze_backtest.py, and validate_config.py to achieve 80% test coverage.

**Architecture:** Use unittest.mock to mock sys.argv, sys.exit, and sys.stdout for testing CLI main() functions. Use tempfile for creating test data files. Follow TDD approach with RED-GREEN-REFACTOR cycle.

**Tech Stack:** Python 3, pytest, unittest.mock, tempfile, json

---

## Task 1: Add CLI Integration Tests for monte_carlo.py

**Files:**
- Modify: `tests/unit/test_monte_carlo.py` (add TestMonteCarloMain class at end)
- Test coverage target: lines 162-239 in `scripts/monte_carlo.py`

### Step 1: Write failing test for main() success path

Add to `tests/unit/test_monte_carlo.py`:

```python
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


class TestMonteCarloMain:
    """CLI main関数のテストスイート"""

    def test_main_success_path(self):
        """正常系: バックテスト結果を読み込んでモンテカルロシミュレーションを実行"""
        # テストデータを準備
        backtest_data = {
            "trades": [
                {"profit": 10.0},
                {"profit": -5.0},
                {"profit": 15.0},
                {"profit": -3.0},
                {"profit": 20.0}
            ]
        }

        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            # sys.argvをモック
            with patch("sys.argv", ["monte_carlo.py", temp_path]):
                # sys.exitをモック（呼ばれないことを確認）
                with patch("sys.exit") as mock_exit:
                    # 標準出力をキャプチャ
                    with patch("sys.stdout") as mock_stdout:
                        from scripts.monte_carlo import main
                        main()

                        # sys.exitが呼ばれていないことを確認
                        mock_exit.assert_not_called()
        finally:
            Path(temp_path).unlink()

    def test_main_file_not_found(self):
        """エラー系: ファイルが存在しない場合"""
        with patch("sys.argv", ["monte_carlo.py", "/nonexistent/file.json"]):
            with patch("sys.exit") as mock_exit:
                from scripts.monte_carlo import main
                main()

                # sys.exit(1)が呼ばれることを確認
                mock_exit.assert_called_once_with(1)

    def test_main_invalid_json(self):
        """エラー系: 無効なJSONファイル"""
        # 無効なJSONを含む一時ファイルを作成
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with patch("sys.argv", ["monte_carlo.py", temp_path]):
                with patch("sys.exit") as mock_exit:
                    from scripts.monte_carlo import main
                    main()

                    # sys.exit(1)が呼ばれることを確認
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(temp_path).unlink()

    def test_main_missing_trades(self):
        """エラー系: trades配列が存在しない場合"""
        backtest_data = {"other_field": "value"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["monte_carlo.py", temp_path]):
                with patch("sys.exit") as mock_exit:
                    from scripts.monte_carlo import main
                    main()

                    # sys.exit(1)が呼ばれることを確認
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(temp_path).unlink()

    def test_main_with_custom_simulations(self):
        """オプション引数: --simulationsを指定"""
        backtest_data = {
            "trades": [
                {"profit": 10.0},
                {"profit": -5.0},
                {"profit": 15.0}
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["monte_carlo.py", temp_path, "--simulations", "50"]):
                with patch("sys.exit") as mock_exit:
                    from scripts.monte_carlo import main
                    main()

                    # sys.exitが呼ばれていないことを確認
                    mock_exit.assert_not_called()
        finally:
            Path(temp_path).unlink()

    def test_main_with_custom_seed(self):
        """オプション引数: --seedを指定"""
        backtest_data = {
            "trades": [
                {"profit": 10.0},
                {"profit": -5.0},
                {"profit": 15.0}
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["monte_carlo.py", temp_path, "--seed", "999"]):
                with patch("sys.exit") as mock_exit:
                    from scripts.monte_carlo import main
                    main()

                    # sys.exitが呼ばれていないことを確認
                    mock_exit.assert_not_called()
        finally:
            Path(temp_path).unlink()

    def test_main_unknown_argument(self):
        """エラー系: 不明な引数"""
        backtest_data = {
            "trades": [{"profit": 10.0}]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["monte_carlo.py", temp_path, "--unknown"]):
                with patch("sys.exit") as mock_exit:
                    from scripts.monte_carlo import main
                    main()

                    # sys.exit(1)が呼ばれることを確認
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(temp_path).unlink()

    def test_main_no_arguments(self):
        """エラー系: 引数なし"""
        with patch("sys.argv", ["monte_carlo.py"]):
            with patch("sys.exit") as mock_exit:
                from scripts.monte_carlo import main
                main()

                # sys.exit(1)が呼ばれることを確認
                mock_exit.assert_called_once_with(1)
```

### Step 2: Run test to verify it fails

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/test_monte_carlo.py::TestMonteCarloMain -v
```

Expected: Tests should fail with import errors or assertion failures (this verifies the tests are running)

### Step 3: Fix import issues if needed

The tests use `from scripts.monte_carlo import main` which should work. If there are import issues, verify the test can import properly.

### Step 4: Run tests again to verify they pass

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/test_monte_carlo.py::TestMonteCarloMain -v
```

Expected: All tests in TestMonteCarloMain should PASS

### Step 5: Commit

```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
git add tests/unit/test_monte_carlo.py
git commit -m "test: Add CLI integration tests for monte_carlo.py main()"
```

---

## Task 2: Add CLI Integration Tests for analyze_backtest.py

**Files:**
- Modify: `tests/unit/test_analyze_backtest.py` (add TestAnalyzeBacktestMain class at end)
- Test coverage target: lines 209-250 in `scripts/analyze_backtest.py`

### Step 1: Write failing test for main() function

Add to `tests/unit/test_analyze_backtest.py`:

```python
import sys
from unittest.mock import patch


class TestAnalyzeBacktestMain:
    """CLI main関数のテストスイート"""

    def test_main_success_path(self):
        """正常系: バックテスト結果を読み込んで評価"""
        backtest_data = {
            "strategy": {
                "TestStrategy": {
                    "results_metrics": {
                        "win_rate": 0.60,
                        "profit_factor": 1.8,
                        "sharpe": 1.0,
                        "max_drawdown": 12.0,
                        "trades": 100,
                        "total_profit_pct": 20.0
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["analyze_backtest.py", temp_path]):
                with patch("sys.exit") as mock_exit:
                    from scripts.analyze_backtest import main
                    main()

                    # 全基準を満たすのでsys.exitは呼ばれない
                    mock_exit.assert_not_called()
        finally:
            Path(temp_path).unlink()

    def test_main_file_not_found(self):
        """エラー系: ファイルが存在しない場合"""
        with patch("sys.argv", ["analyze_backtest.py", "/nonexistent/file.json"]):
            with patch("sys.exit") as mock_exit:
                from scripts.analyze_backtest import main
                main()

                # sys.exit(1)が呼ばれることを確認
                mock_exit.assert_called_once_with(1)

    def test_main_invalid_json(self):
        """エラー系: 無効なJSONファイル"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with patch("sys.argv", ["analyze_backtest.py", temp_path]):
                with patch("sys.exit") as mock_exit:
                    from scripts.analyze_backtest import main
                    main()

                    # sys.exit(1)が呼ばれることを確認
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(temp_path).unlink()

    def test_main_missing_required_field(self):
        """エラー系: 必須フィールド欠落"""
        backtest_data = {
            "strategy": {
                "TestStrategy": {
                    "results_metrics": {
                        "win_rate": 0.60,
                        # profit_factor欠落
                        "sharpe": 1.0,
                        "max_drawdown": 12.0,
                        "trades": 100,
                        "total_profit_pct": 20.0
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["analyze_backtest.py", temp_path]):
                with patch("sys.exit") as mock_exit:
                    from scripts.analyze_backtest import main
                    main()

                    # sys.exit(1)が呼ばれることを確認
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(temp_path).unlink()

    def test_main_fails_minimum_criteria(self):
        """エラー系: 最低基準を満たさない場合"""
        backtest_data = {
            "strategy": {
                "TestStrategy": {
                    "results_metrics": {
                        "win_rate": 0.40,  # < 0.50 (最低基準違反)
                        "profit_factor": 1.0,
                        "sharpe": 0.3,
                        "max_drawdown": 25.0,
                        "trades": 20,
                        "total_profit_pct": -5.0
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(backtest_data, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["analyze_backtest.py", temp_path]):
                with patch("sys.exit") as mock_exit:
                    from scripts.analyze_backtest import main
                    main()

                    # 最低基準を満たさないのでsys.exit(1)が呼ばれる
                    mock_exit.assert_called_once_with(1)
        finally:
            Path(temp_path).unlink()

    def test_main_no_arguments(self):
        """エラー系: 引数なし"""
        with patch("sys.argv", ["analyze_backtest.py"]):
            with patch("sys.exit") as mock_exit:
                from scripts.analyze_backtest import main
                main()

                # sys.exit(1)が呼ばれることを確認
                mock_exit.assert_called_once_with(1)
```

### Step 2: Run test to verify it fails

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/test_analyze_backtest.py::TestAnalyzeBacktestMain -v
```

Expected: Tests should run (may fail initially but confirms they execute)

### Step 3: Verify tests pass

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/test_analyze_backtest.py::TestAnalyzeBacktestMain -v
```

Expected: All tests in TestAnalyzeBacktestMain should PASS

### Step 4: Commit

```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
git add tests/unit/test_analyze_backtest.py
git commit -m "test: Add CLI integration tests for analyze_backtest.py main()"
```

---

## Task 3: Add CLI Integration Tests for validate_config.py

**Files:**
- Modify: `tests/unit/test_validate_config.py` (add TestValidateConfigMain class at end)
- Test coverage target: lines 131-156 in `scripts/validate_config.py`

### Step 1: Write failing test for main() function

Add to `tests/unit/test_validate_config.py`:

```python
from unittest.mock import patch


class TestValidateConfigMain:
    """CLI main関数のテストスイート"""

    def test_main_valid_config(self):
        """正常系: 正常な設定ファイル"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["validate_config.py", temp_path]):
                from scripts.validate_config import main
                exit_code = main()

                # 正常終了（exit code 0）
                assert exit_code == 0
        finally:
            Path(temp_path).unlink()

    def test_main_invalid_config(self):
        """エラー系: 無効な設定ファイル"""
        config = {
            "max_open_trades": 0,  # 無効（0以下）
            "stake_currency": "JPY",
            "stake_amount": 10000,
            "dry_run": True,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["validate_config.py", temp_path]):
                from scripts.validate_config import main
                exit_code = main()

                # エラー終了（exit code 1）
                assert exit_code == 1
        finally:
            Path(temp_path).unlink()

    def test_main_file_not_found(self):
        """エラー系: ファイルが存在しない場合"""
        with patch("sys.argv", ["validate_config.py", "/nonexistent/config.json"]):
            from scripts.validate_config import main
            exit_code = main()

            # エラー終了（exit code 1）
            assert exit_code == 1

    def test_main_invalid_json(self):
        """エラー系: 無効なJSONファイル"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json")
            temp_path = f.name

        try:
            with patch("sys.argv", ["validate_config.py", temp_path]):
                from scripts.validate_config import main
                exit_code = main()

                # エラー終了（exit code 1）
                assert exit_code == 1
        finally:
            Path(temp_path).unlink()

    def test_main_missing_required_fields(self):
        """エラー系: 必須フィールド欠落"""
        config = {
            "max_open_trades": 2,
            # stake_currency欠落
            "stake_amount": 10000,
            "dry_run": True,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["validate_config.py", temp_path]):
                from scripts.validate_config import main
                exit_code = main()

                # エラー終了（exit code 1）
                assert exit_code == 1
        finally:
            Path(temp_path).unlink()

    def test_main_no_arguments(self):
        """エラー系: 引数なし"""
        with patch("sys.argv", ["validate_config.py"]):
            from scripts.validate_config import main
            exit_code = main()

            # エラー終了（exit code 1）
            assert exit_code == 1

    def test_main_with_warnings(self):
        """警告あり: ライブモードで高額ステーク"""
        config = {
            "max_open_trades": 2,
            "stake_currency": "JPY",
            "stake_amount": 100000,  # > 50000
            "dry_run": False,  # ライブモード
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(config, f)
            temp_path = f.name

        try:
            with patch("sys.argv", ["validate_config.py", temp_path]):
                from scripts.validate_config import main
                exit_code = main()

                # 警告があっても正常終了（exit code 0）
                assert exit_code == 0
        finally:
            Path(temp_path).unlink()
```

### Step 2: Run test to verify it fails

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/test_validate_config.py::TestValidateConfigMain -v
```

Expected: Tests should run (may fail initially but confirms they execute)

### Step 3: Verify tests pass

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/test_validate_config.py::TestValidateConfigMain -v
```

Expected: All tests in TestValidateConfigMain should PASS

### Step 4: Commit

```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
git add tests/unit/test_validate_config.py
git commit -m "test: Add CLI integration tests for validate_config.py main()"
```

---

## Task 4: Verify Coverage Reaches 80%

**Files:**
- Run coverage analysis on all test files

### Step 1: Run all tests with coverage

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/ --cov=scripts --cov-report=term-missing
```

Expected: Coverage report showing 80%+ for:
- scripts/monte_carlo.py
- scripts/analyze_backtest.py
- scripts/validate_config.py

### Step 2: Verify specific line coverage

Check that the following lines are now covered:
- `scripts/monte_carlo.py`: lines 162-239 (main function)
- `scripts/analyze_backtest.py`: lines 209-250 (main function)
- `scripts/validate_config.py`: lines 131-156 (main function)

Expected: All previously uncovered lines in main() functions should now show as covered

### Step 3: If coverage is below 80%, identify missing lines

Run:
```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
python3 -m pytest tests/unit/ --cov=scripts --cov-report=html
open htmlcov/index.html
```

Expected: HTML coverage report shows which lines are still uncovered

### Step 4: Add additional tests if needed

If coverage is still below 80%, add targeted tests for the specific uncovered lines. Focus on edge cases in the main() functions.

### Step 5: Final commit

```bash
cd /Users/takahiko_tsunoda/work/dev/No40_Crypto5
git add tests/unit/
git commit -m "test: Add CLI integration tests to reach 80% coverage

- Add TestMonteCarloMain for monte_carlo.py CLI (lines 162-239)
- Add TestAnalyzeBacktestMain for analyze_backtest.py CLI (lines 209-250)
- Add TestValidateConfigMain for validate_config.py CLI (lines 131-156)
- Coverage now 80%+ for all scripts

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Verification Checklist

After completing all tasks:

- [ ] All tests in TestMonteCarloMain pass
- [ ] All tests in TestAnalyzeBacktestMain pass
- [ ] All tests in TestValidateConfigMain pass
- [ ] Overall coverage for scripts/monte_carlo.py is 80%+
- [ ] Overall coverage for scripts/analyze_backtest.py is 80%+
- [ ] Overall coverage for scripts/validate_config.py is 80%+
- [ ] No test failures in existing test suites
- [ ] Code follows immutability principles (no mutations in tests)
- [ ] All tests use proper mocking for sys.argv, sys.exit, sys.stdout
- [ ] Temporary files are properly cleaned up in all tests

---

## Notes

1. The tests use `unittest.mock.patch` to mock system functions without side effects
2. Temporary files are created and cleaned up using try/finally blocks
3. All tests follow the existing test structure and naming conventions
4. Tests verify both success paths and error paths for comprehensive coverage
5. The main() functions are tested in isolation without actually executing CLI commands
