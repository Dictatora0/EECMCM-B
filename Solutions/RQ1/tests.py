from common import (
    CARE_LEVEL_ORDER,
    CommunityRecord,
    SERVICE_ORDER,
    aggregate_adjusted_demand,
    affordability_adjusted_demand,
    project_elderly_population,
    theoretical_monthly_demand,
)


def test_new_entrants_are_based_on_elderly_population() -> None:
    communities = [
        CommunityRecord(
            community="T",
            total_population=1000,
            elderly_population=100,
            self_care=70,
            semi_disabled=20,
            disabled=10,
            monthly_income=3000,
        )
    ]
    transition = {"自理->半失能": 0.1, "半失能->失能": 0.2}
    result = project_elderly_population(communities, transition, years=1, death_rate=0.05, growth_rate=0.07)
    assert len(result) == 1
    assert abs(result[0]["new_entrants"] - 7.0) < 1e-8


def test_emergency_service_is_not_scaled() -> None:
    communities = [
        CommunityRecord(
            community="T",
            total_population=1000,
            elderly_population=100,
            self_care=100,
            semi_disabled=0,
            disabled=0,
            monthly_income=100,
        )
    ]
    year5_population = [
        {
            "community": "T",
            "self_care": 100.0,
            "semi_disabled": 0.0,
            "disabled": 0.0,
        }
    ]
    service_demand = {
        "自理": {"助餐": 10, "日间照料": 10, "上门护理": 10, "康复理疗": 10, "助浴": 10, "紧急救助": 2},
        "半失能": {service: 0 for service in SERVICE_ORDER},
        "失能": {service: 0 for service in SERVICE_ORDER},
    }
    service_costs = {
        service: {"price": 10, "direct_cost": 5} for service in SERVICE_ORDER
    }
    service_costs["紧急救助"]["price"] = 0
    adjusted = affordability_adjusted_demand(communities, year5_population, service_demand, service_costs)
    emergency_rows = [row for row in adjusted if row["service"] == "紧急救助" and row["care_level"] == "自理"]
    assert len(emergency_rows) == 1
    assert emergency_rows[0]["adjusted_per_person"] == emergency_rows[0]["theoretical_per_person"] == 2


def test_summary_shapes_match_problem_one_outputs() -> None:
    year5_population = [
        {"community": f"C{i}", "self_care": 10.0, "semi_disabled": 5.0, "disabled": 2.0}
        for i in range(10)
    ]
    service_demand = {
        level: {service: 1.0 for service in SERVICE_ORDER}
        for level in CARE_LEVEL_ORDER
    }
    demand = theoretical_monthly_demand(year5_population, service_demand)
    assert len(demand) == 10 * len(SERVICE_ORDER)

    adjusted_rows = []
    for i in range(10):
        for level in CARE_LEVEL_ORDER:
            for service in SERVICE_ORDER:
                adjusted_rows.append(
                    {
                        "community": f"C{i}",
                        "care_level": level,
                        "service": service,
                        "adjusted_monthly_demand": 1.0,
                        "adjusted_per_person": 1.0,
                        "theoretical_per_person": 1.0,
                    }
                )
    summary = aggregate_adjusted_demand(adjusted_rows)
    assert len(summary) == 10 * len(SERVICE_ORDER)


def run_all_tests() -> None:
    tests = [
        test_new_entrants_are_based_on_elderly_population,
        test_emergency_service_is_not_scaled,
        test_summary_shapes_match_problem_one_outputs,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
