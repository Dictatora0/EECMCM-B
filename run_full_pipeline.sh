#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
PYTHON_BIN="${PYTHON_BIN:-python3}"

usage() {
  cat <<'EOF'
Usage:
  bash run_full_pipeline.sh full
  bash run_full_pipeline.sh test-rq3
  bash run_full_pipeline.sh test
  bash run_full_pipeline.sh clean
  bash run_full_pipeline.sh rq3-expanded all
  bash run_full_pipeline.sh rq3-expanded light
  bash run_full_pipeline.sh rq3-expanded medium
  bash run_full_pipeline.sh rq3-expanded heavy
  bash run_full_pipeline.sh rq3-expanded extreme

Commands:
  full
    Run Q1 -> Q4 baseline pipeline, including algorithm-upgrade extensions.

  test-rq3
    Run RQ3 tests only.

  test
    Run pipeline guard tests: constraint-audit tests, RQ2 tests, and RQ3 tests.

  clean
    Remove all files under Solutions/*/outputs and all __pycache__ directories.

  rq3-expanded [all|light|medium|heavy|extreme]
    Run RQ3 expanded station-service pricing search.
    all    = light,medium,heavy
    light  = light only
    medium = medium only
    heavy  = heavy only
    extreme= extreme only
EOF
}

clean_outputs() {
  find "$ROOT_DIR/Solutions" -type f \( -path '*/outputs/*' -o -path '*/__pycache__/*' \) -delete
  find "$ROOT_DIR/Solutions" \( -type d -name '__pycache__' -o -path "$ROOT_DIR/Solutions/RQ3/outputs/.mplconfig" \) -exec rm -rf {} +
  printf '[runner] cleaned outputs and caches\n'
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
  printf '[runner] start full pipeline\n'

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

  printf '[runner] full pipeline done\n'
}

run_rq3_tests() {
  printf '[runner] run RQ3 tests\n'
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ3/tests.py"
}

run_tests() {
  printf '[runner] run pipeline guard tests\n'
  ensure_test_prerequisites
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/tests_constraint_audit.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ2/tests.py"
  "$PYTHON_BIN" "$ROOT_DIR/Solutions/RQ3/tests.py"
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
