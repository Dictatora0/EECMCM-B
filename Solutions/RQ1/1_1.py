import json
from datetime import datetime, timezone

from common import (
    OUTPUT_DIR,
    integerize_rows,
    load_community_data,
    load_transition_probabilities,
    project_elderly_population,
    round_rows,
    write_csv,
)


def main() -> None:
    communities = load_community_data()
    transition = load_transition_probabilities()
    results = project_elderly_population(communities, transition)
    output_path = OUTPUT_DIR / "1_1_high_precision_population_by_year.csv"
    year5_output_path = OUTPUT_DIR / "1_1_high_precision_year5_population.csv"
    report_output_path = OUTPUT_DIR / "1_1_rounded_report_elderly_projection.csv"
    metadata_output_path = OUTPUT_DIR / "rq1_high_precision_metadata.json"
    write_csv(
        output_path,
        round_rows(results, digits=6),
    )
    write_csv(
        year5_output_path,
        round_rows([row for row in results if row["year"] == 5], digits=6),
    )
    write_csv(
        report_output_path,
        integerize_rows(
            results,
            ["year", "self_care", "semi_disabled", "disabled", "elderly_total", "new_entrants"],
        ),
    )
    metadata = {
        "source": "RQ1",
        "precision": "high",
        "rounded_for_report": False,
        "contains_years": [1, 2, 3, 4, 5],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intended_downstream": ["RQ2", "RQ3", "RQ4"],
        "files": {
            "population_by_year": "1_1_high_precision_population_by_year.csv",
            "year5_population": "1_1_high_precision_year5_population.csv",
            "theoretical_demand": "1_2_high_precision_theoretical_demand.csv",
            "theoretical_demand_detail": "1_2_high_precision_theoretical_demand_detail.csv",
            "adjusted_demand": "1_3_high_precision_adjusted_demand.csv",
            "adjusted_demand_detail": "1_3_high_precision_adjusted_demand_detail.csv",
        },
    }
    metadata_output_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    initial_total = sum(item.elderly_population for item in communities)
    year5_total = sum(row["elderly_total"] for row in results if row["year"] == 5)
    print(f"Saved elderly projection to {output_path}")
    print(f"Saved year-5 high-precision table to {year5_output_path}")
    print(f"Saved rounded report table to {report_output_path}")
    print(f"Saved metadata to {metadata_output_path}")
    print(f"Validation: loaded {len(communities)} communities; initial elderly total = {initial_total:.4f}")
    print(f"Validation: year-5 elderly total = {year5_total:.4f}")


if __name__ == "__main__":
    main()
