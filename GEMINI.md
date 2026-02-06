# Gemini CLI 作業メモ (2026-02-05)

## 1. 開発・実行環境の注意点
- **PYTHONPATH の設定**: `scripts/` 配下のスクリプトを実行する際、プロジェクトルートから `export PYTHONPATH=$PYTHONPATH:.` を行わないと、内部モジュールのインポートエラー (`ModuleNotFoundError`) が発生する。
- **ログ・レポートへのアクセス**: `.gitignore` や設定により `read_file` ツールが `user_data/logs/` 内のファイルを拒否する場合がある。その際は `run_shell_command` で `cat` や `tail` を使用して回避する。

## 2. データベース関連 (SQLite)
- **ドライラン用DB**: 稼働中のデータは `./tradesv3.dryrun.sqlite` に保存されている（`user_data/` ではない場合があるため `find` で要確認）。
- **カラム名**: 取引利益を確認する際は `close_profit_abs` (金額) や `close_profit` (比率) を使用する。`close_profit_pct` は存在しない場合がある。
- **API クライアント**: `scripts/freqtrade_api_client.py` が空を返す場合、ボットの API サーバーが未起動か、設定が合っていない可能性がある。その場合は SQLite 直接参照が確実。

## 3. ボットの状況と課題
- **損切りの深さ**: `DCAStrategy` において、-15% 〜 -18% という深いストップロスが連続発生している。
- **課題**: 現在のボットは下落相場でのナンピン（DCA）が機能せず、そのまま底を抜けて損切りされるパターンに陥っている。エントリー条件の厳格化、またはストップロス位置の再検討が必要。
