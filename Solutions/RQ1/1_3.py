from common import (
    OUTPUT_DIR,
    aggregate_adjusted_demand,
    affordability_adjusted_demand,
    integerize_rows,
    load_community_data,
    load_service_costs,
    load_service_demand,
    load_transition_probabilities,
    project_elderly_population,
    round_rows,
    write_csv,
)


def main() -> None:
    communities = load_community_data()
    transition = load_transition_probabilities()
    service_demand = load_service_demand()
    service_costs = load_service_costs()
    projection = project_elderly_population(communities, transition)
    year5_population = [row for row in projection if row["year"] == 5]
    adjusted = affordability_adjusted_demand(
        communities=communities,
        year5_population=year5_population,
        service_demand=service_demand,
        service_costs=service_costs,
    )
    detail_output_path = OUTPUT_DIR / "1_3_high_precision_adjusted_demand_detail.csv"
    report_detail_output_path = OUTPUT_DIR / "1_3_rounded_report_adjusted_demand_detail.csv"
    write_csv(detail_output_path, round_rows(adjusted, digits=6))
    write_csv(report_detail_output_path, round_rows(adjusted))

    summary = aggregate_adjusted_demand(adjusted)
    summary_output_path = OUTPUT_DIR / "1_3_high_precision_adjusted_demand.csv"
    report_summary_output_path = OUTPUT_DIR / "1_3_rounded_report_adjusted_demand.csv"
    write_csv(summary_output_path, round_rows(summary, digits=6))
    write_csv(report_summary_output_path, integerize_rows(summary, ["adjusted_monthly_demand"]))

    print(f"Saved affordability adjusted demand to {detail_output_path}")
    print(f"Saved adjusted service demand summary to {summary_output_path}")
    print(f"Saved rounded report detail table to {report_detail_output_path}")
    print(f"Saved rounded report summary table to {report_summary_output_path}")
    print(
        f"Validation: adjusted detail rows = {len(adjusted)}; "
        f"adjusted summary rows = {len(summary)}"
    )


if __name__ == "__main__":
    main()
