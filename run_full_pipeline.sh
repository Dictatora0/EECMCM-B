#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<'EOF'
Usage:
  bash run_full_pipeline.sh full
  bash run_full_pipeline.sh plots
  bash run_full_pipeline.sh test
  bash run_full_pipeline.sh test-rq3
  bash run_full_pipeline.sh clean
  bash run_full_pipeline.sh rq3-expanded {all|light|medium|heavy|extreme}

Commands:
  full
    Clean old outputs/caches first, then recompute RQ1 -> RQ4 current main-chain results
    and extension outputs, and finally rebuild unified plots.

  plots
    Rebuild unified paper-ready figures under Solutions/plots/outputs from existing outputs.

  test
    Run pipeline guard tests: constraint audit, plot tests, RQ2 tests, RQ3 tests, and RQ4 tests.
    If prerequisite RQ1/RQ2 outputs are missing, they are generated first.

  test-rq3
    Run RQ3 tests only.

  clean
    Remove generated numeric outputs, plot images/manifests/notes, RQ4 cache files,
    Matplotlib cache files under outputs/.mplconfig, and all __pycache__ directories,
    while preserving outputs/README.md directory guides.

  rq3-expanded [all|light|medium|heavy|extreme]
    Run the RQ3 expanded station-service pricing search for scenarios S0,S4.
    all     = run light, medium, heavy
    light   = run light only
    medium  = run medium only
    heavy   = run heavy only
    extreme = run extreme only
EOF
}

clean_outputs() {
  find "$ROOT_DIR/Solutions" -type f -path '*/outputs/*' ! -name 'README.md' -delete
  find "$ROOT_DIR/Solutions" -type f -path '*/__pycache__/*' -delete
  find "$ROOT_DIR/Solutions" \( -type d -name '__pycache__' -o -path "$ROOT_DIR/Solutions/RQ3/outputs/.mplconfig" -o -path "$ROOT_DIR/Solutions/plots/outputs/.mplconfig" \) -exec rm -rf {} +
  find "$ROOT_DIR/Solutions/RQ4/cache" -type f -name '*.json' -delete
  printf '[runner] cleaned generated outputs, plot artifacts, and caches; kept outputs/README.md files\n'
}

ensure_test_prerequisites() {
  local rq1_meta="$ROOT_DIR/Solutions/RQ1/outputs/rq1_high_precision_metadata.json"
  local rq2_best="$ROOT_DIR/Solutions/RQ2/outputs/2_1_best_scheme_summary.csv"

  if [[ ! -f "$rq1_meta" ]]; then
    printf '[runner] missing RQ1 high-precision outputs; generating prerequisites\n'
    "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_1.py"
    "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_2.py"
    "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_3.py"
  fi

  if [[ ! -f "$rq2_best" ]]; then
    printf '[runner] missing RQ2 best-scheme outputs; generating prerequisites\n'
    "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ2/2_1.py"
  fi
}

run_full() {
  printf '[runner] start full pipeline from clean state\n'
  clean_outputs

  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_1.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_2.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_3.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ1/1_4_validation_extension.py"

  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ2/2_1.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ2/2_2_multiobjective_extension.py"

  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ3/3_1.py" \
    --max-candidate-profiles 64 \
    --max-candidates-per-station 30 \
    --price-grid-level full
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ3/3_4_joint_feasibility_diagnostics.py"

  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ4/4_1.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/plots/build_all_plots.py"

  printf '[runner] full pipeline done\n'
}

run_plots() {
  printf '[runner] build unified plots\n'
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/plots/build_all_plots.py"
}

run_rq3_tests() {
  printf '[runner] run RQ3 tests\n'
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ3/tests.py"
}

run_tests() {
  printf '[runner] run pipeline guard tests\n'
  ensure_test_prerequisites
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/tests_constraint_audit.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/plots/tests.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ2/tests.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ3/tests.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ4/tests.py"
}

run_rq3_expanded() {
  local level="${1:-all}"
  cd "$ROOT_DIR/Solutions/RQ3"

  case "$level" in
    all)
      "$PYTHON_BIN" 3_1.py \
        --expanded-search-only \
        --scenarios S0,S4 \
        --search-levels light,medium,heavy \
        --price-grid full \
        --keep-near-boundary \
        --random-seed 42
      ;;
    light|medium|heavy)
      "$PYTHON_BIN" 3_1.py \
        --expanded-search-only \
        --scenarios S0,S4 \
        --search-level "$level" \
        --price-grid full \
        --keep-near-boundary \
        --random-seed 42
      ;;
    extreme)
      "$PYTHON_BIN" 3_1.py \
        --expanded-search-only \
        --scenarios S0,S4 \
        --search-level extreme \
        --price-grid full \
        --max-candidates-per-station 250 \
        --max-global-combinations 300000 \
        --keep-near-boundary \
        --random-seed 42
      ;;
    *)
      printf '[runner] unknown rq3-expanded level: %s\n' "$level" >&2
      usage
      exit 1
      ;;
  esac
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    full)
      run_full
      ;;
    plots)
      run_plots
      ;;
    test-rq3)
      run_rq3_tests
      ;;
    test)
      run_tests
      ;;
    clean)
      clean_outputs
      ;;
    rq3-expanded)
      run_rq3_expanded "${2:-all}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "${@:-}"
