from common import (
    OUTPUT_DIR,
    aggregate_theoretical_demand,
    integerize_rows,
    load_community_data,
    load_service_demand,
    load_transition_probabilities,
    project_elderly_population,
    round_rows,
    theoretical_monthly_demand,
    write_csv,
)


def main() -> None:
    communities = load_community_data()
    transition = load_transition_probabilities()
    service_demand = load_service_demand()
    projection = project_elderly_population(communities, transition)
    year5_population = [row for row in projection if row["year"] == 5]
    demand_detail = theoretical_monthly_demand(year5_population, service_demand)
    demand_summary = aggregate_theoretical_demand(demand_detail)
    detail_output_path = OUTPUT_DIR / "1_2_high_precision_theoretical_demand_detail.csv"
    output_path = OUTPUT_DIR / "1_2_high_precision_theoretical_demand.csv"
    report_detail_output_path = OUTPUT_DIR / "1_2_rounded_report_theoretical_demand_detail.csv"
    report_output_path = OUTPUT_DIR / "1_2_rounded_report_theoretical_demand.csv"
    write_csv(detail_output_path, round_rows(demand_detail, digits=6))
    write_csv(output_path, round_rows(demand_summary, digits=6))
    write_csv(
        report_detail_output_path,
        integerize_rows(demand_detail, ["theoretical_monthly_demand"]),
    )
    write_csv(report_output_path, integerize_rows(demand_summary, ["theoretical_monthly_demand"]))
    print(f"Saved theoretical service demand detail to {detail_output_path}")
    print(f"Saved theoretical service demand summary to {output_path}")
    print(f"Saved rounded report detail table to {report_detail_output_path}")
    print(f"Saved rounded report summary table to {report_output_path}")
    print(
        "Validation: "
        f"year-5 population rows = {len(year5_population)}; "
        f"theoretical detail rows = {len(demand_detail)}; "
        f"theoretical summary rows = {len(demand_summary)}"
    )


if __name__ == "__main__":
    main()
