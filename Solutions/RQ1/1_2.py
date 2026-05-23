from common import (
    OUTPUT_DIR,
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
    demand = theoretical_monthly_demand(year5_population, service_demand)
    output_path = OUTPUT_DIR / "1_2_high_precision_theoretical_demand.csv"
    report_output_path = OUTPUT_DIR / "1_2_rounded_report_theoretical_demand.csv"
    write_csv(output_path, round_rows(demand, digits=6))
    write_csv(report_output_path, integerize_rows(demand, ["theoretical_monthly_demand"]))
    print(f"Saved theoretical service demand to {output_path}")
    print(f"Saved rounded report table to {report_output_path}")
    print(f"Validation: year-5 population rows = {len(year5_population)}; theoretical demand rows = {len(demand)}")


if __name__ == "__main__":
    main()
