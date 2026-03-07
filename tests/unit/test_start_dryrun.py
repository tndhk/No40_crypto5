"""
start_dryrun.sh の静的テスト
"""

from pathlib import Path


def test_start_dryrun_uses_safe_profile():
    script = Path("scripts/start_dryrun.sh").read_text(encoding="utf-8")

    assert 'SAFE_CONFIG="user_data/config/config.dryrun.safe.json"' in script
    assert 'SAFE_STRATEGY="DCAStrategyBalanced"' in script
    assert '--config "$SAFE_CONFIG"' in script
    assert '--strategy "$SAFE_STRATEGY"' in script
