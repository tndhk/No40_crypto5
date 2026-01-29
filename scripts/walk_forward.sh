#!/usr/bin/env bash
# Walk-Forward Analysis Script
#
# This script performs walk-forward analysis on backtests to validate
# strategy robustness across different time periods.
#
# Time Periods:
#   IS  (In-Sample):      2024/03 - 2025/06 (Training period)
#   OOS (Out-Of-Sample):  2025/07 - 2025/12 (Validation period)
#   FINAL (Final Test):   2026/01           (Final verification)

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKTEST_DIR="${PROJECT_ROOT}/user_data/backtest_results"
LOG_FILE="${PROJECT_ROOT}/user_data/logs/walk_forward.log"

# Strategy configuration
STRATEGY="${STRATEGY:-DCAStrategy}"
TIMEFRAME="${TIMEFRAME:-1h}"
STAKE_AMOUNT="${STAKE_AMOUNT:-100}"

# Time periods
IS_START="20240301"
IS_END="20250630"
OOS_START="20250701"
OOS_END="20251231"
FINAL_START="20260101"
FINAL_END="20260131"

# ============================================================================
# Logging Functions
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"

    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# ============================================================================
# Validation Functions
# ============================================================================

validate_environment() {
    log_info "Validating environment..."

    # Check if Freqtrade is available
    if ! command -v freqtrade &> /dev/null; then
        log_error "Freqtrade command not found. Please install freqtrade."
        return 1
    fi

    # Check if Python is available
    if ! command -v python &> /dev/null; then
        log_error "Python command not found."
        return 1
    fi

    # Check if analyze_backtest.py exists
    if [[ ! -f "${SCRIPT_DIR}/analyze_backtest.py" ]]; then
        log_error "analyze_backtest.py not found at ${SCRIPT_DIR}/analyze_backtest.py"
        return 1
    fi

    # Create necessary directories
    mkdir -p "${BACKTEST_DIR}"
    mkdir -p "$(dirname "${LOG_FILE}")"

    log_success "Environment validation passed"
    return 0
}

# ============================================================================
# Backtest Execution Functions
# ============================================================================

run_backtest() {
    local period_name="$1"
    local start_date="$2"
    local end_date="$3"
    local output_file="$4"

    log_info "Running backtest for ${period_name} period (${start_date} - ${end_date})..."

    # Run Freqtrade backtest
    # Note: Using --export trades to generate JSON results
    if freqtrade backtesting \
        --strategy "${STRATEGY}" \
        --timeframe "${TIMEFRAME}" \
        --timerange "${start_date}-${end_date}" \
        --stake-amount "${STAKE_AMOUNT}" \
        --export trades \
        --export-filename "${output_file}" \
        2>&1 | tee -a "${LOG_FILE}"; then
        log_success "Backtest completed for ${period_name}"
        return 0
    else
        log_error "Backtest failed for ${period_name}"
        return 1
    fi
}

# ============================================================================
# Analysis Functions
# ============================================================================

analyze_backtest_results() {
    local period_name="$1"
    local results_file="$2"

    log_info "Analyzing backtest results for ${period_name}..."

    # Check if results file exists
    if [[ ! -f "${results_file}" ]]; then
        log_error "Results file not found: ${results_file}"
        return 1
    fi

    # Run analysis script
    if python "${SCRIPT_DIR}/analyze_backtest.py" "${results_file}" 2>&1 | tee -a "${LOG_FILE}"; then
        log_success "Analysis completed for ${period_name}"
        return 0
    else
        log_error "Analysis failed for ${period_name} (minimum criteria not met)"
        return 1
    fi
}

# ============================================================================
# OOS Degradation Calculation
# ============================================================================

calculate_oos_degradation() {
    local is_results="$1"
    local oos_results="$2"

    log_info "Calculating OOS degradation..."

    # Extract metrics from both results using Python
    python << EOF
import json
import sys

def extract_metrics(json_path):
    """Extract key metrics from backtest results"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)

        strategy_data = data['strategy']
        strategy_name = next(iter(strategy_data.keys()))
        metrics = strategy_data[strategy_name]['results_metrics']

        return {
            'total_profit_pct': float(metrics.get('total_profit_pct', 0)),
            'win_rate': float(metrics.get('win_rate', 0)),
            'profit_factor': float(metrics.get('profit_factor', 0)),
            'sharpe_ratio': float(metrics.get('sharpe', 0)),
            'max_drawdown': float(metrics.get('max_drawdown', 0)),
        }
    except Exception as e:
        print(f"Error extracting metrics from {json_path}: {e}", file=sys.stderr)
        sys.exit(1)

def calculate_degradation(is_metrics, oos_metrics):
    """Calculate percentage degradation from IS to OOS"""
    results = []

    for key in ['total_profit_pct', 'win_rate', 'profit_factor', 'sharpe_ratio']:
        is_val = is_metrics[key]
        oos_val = oos_metrics[key]

        if is_val == 0:
            degradation = 0 if oos_val == 0 else float('inf')
        else:
            degradation = ((is_val - oos_val) / abs(is_val)) * 100

        results.append(f"{key}: IS={is_val:.2f}, OOS={oos_val:.2f}, Degradation={degradation:.2f}%")

    # For max_drawdown, lower is better, so invert the calculation
    is_dd = is_metrics['max_drawdown']
    oos_dd = oos_metrics['max_drawdown']
    dd_change = ((oos_dd - is_dd) / abs(is_dd)) * 100 if is_dd != 0 else 0
    results.append(f"max_drawdown: IS={is_dd:.2f}%, OOS={oos_dd:.2f}%, Change={dd_change:.2f}%")

    return results

# Main execution
is_metrics = extract_metrics('${is_results}')
oos_metrics = extract_metrics('${oos_results}')
degradation_results = calculate_degradation(is_metrics, oos_metrics)

print("\n=== OOS Degradation Analysis ===")
for result in degradation_results:
    print(f"  {result}")
print()

# Warning thresholds
total_profit_deg = ((is_metrics['total_profit_pct'] - oos_metrics['total_profit_pct']) / abs(is_metrics['total_profit_pct'])) * 100 if is_metrics['total_profit_pct'] != 0 else 0
if total_profit_deg > 30:
    print("WARNING: Total profit degradation exceeds 30% - possible overfitting!")
    sys.exit(1)

print("OOS degradation analysis completed successfully")
EOF

    if [[ $? -eq 0 ]]; then
        log_success "OOS degradation analysis completed"
        return 0
    else
        log_error "OOS degradation analysis failed or degradation too high"
        return 1
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log_info "Starting walk-forward analysis for strategy: ${STRATEGY}"
    log_info "Timeframe: ${TIMEFRAME}, Stake Amount: ${STAKE_AMOUNT}"

    # Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi

    # Define result file paths
    local is_results="${BACKTEST_DIR}/backtest-result-${STRATEGY}-IS.json"
    local oos_results="${BACKTEST_DIR}/backtest-result-${STRATEGY}-OOS.json"
    local final_results="${BACKTEST_DIR}/backtest-result-${STRATEGY}-FINAL.json"

    # ========================================================================
    # Phase 1: In-Sample (IS) Backtest
    # ========================================================================
    log_info "=========================================="
    log_info "Phase 1: In-Sample Period"
    log_info "=========================================="

    if ! run_backtest "IS" "${IS_START}" "${IS_END}" "${is_results}"; then
        log_error "IS backtest failed"
        exit 1
    fi

    if ! analyze_backtest_results "IS" "${is_results}"; then
        log_error "IS analysis failed - strategy does not meet minimum criteria"
        exit 1
    fi

    # ========================================================================
    # Phase 2: Out-of-Sample (OOS) Backtest
    # ========================================================================
    log_info "=========================================="
    log_info "Phase 2: Out-of-Sample Period"
    log_info "=========================================="

    if ! run_backtest "OOS" "${OOS_START}" "${OOS_END}" "${oos_results}"; then
        log_error "OOS backtest failed"
        exit 1
    fi

    if ! analyze_backtest_results "OOS" "${oos_results}"; then
        log_error "OOS analysis failed - strategy does not meet minimum criteria"
        exit 1
    fi

    # ========================================================================
    # Phase 3: OOS Degradation Analysis
    # ========================================================================
    log_info "=========================================="
    log_info "Phase 3: OOS Degradation Analysis"
    log_info "=========================================="

    if ! calculate_oos_degradation "${is_results}" "${oos_results}"; then
        log_error "OOS degradation too high - possible overfitting"
        exit 1
    fi

    # ========================================================================
    # Phase 4: Final Validation Period
    # ========================================================================
    log_info "=========================================="
    log_info "Phase 4: Final Validation Period"
    log_info "=========================================="

    if ! run_backtest "FINAL" "${FINAL_START}" "${FINAL_END}" "${final_results}"; then
        log_error "Final backtest failed"
        exit 1
    fi

    if ! analyze_backtest_results "FINAL" "${final_results}"; then
        log_error "Final analysis failed - strategy does not meet minimum criteria"
        exit 1
    fi

    # ========================================================================
    # Summary
    # ========================================================================
    log_info "=========================================="
    log_info "Walk-Forward Analysis Summary"
    log_info "=========================================="
    log_success "All phases completed successfully!"
    log_info "Results saved to:"
    log_info "  IS:    ${is_results}"
    log_info "  OOS:   ${oos_results}"
    log_info "  FINAL: ${final_results}"
    log_info "Log file: ${LOG_FILE}"

    return 0
}

# Run main function
main "$@"
