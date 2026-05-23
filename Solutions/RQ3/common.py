from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
import csv
import json
from pathlib import Path
from typing import Dict, List, Literal
import sys


RQ3_DIR = Path(__file__).resolve().parent
ROOT = RQ3_DIR.parents[1]
OUTPUT_DIR = RQ3_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

RQ1_DIR = ROOT / "Solutions" / "RQ1"
RQ2_DIR = ROOT / "Solutions" / "RQ2"
RQ1_OUTPUT_DIR = RQ1_DIR / "outputs"
RQ2_OUTPUT_DIR = RQ2_DIR / "outputs"

RQ1_COMMON_PATH = RQ1_DIR / "common.py"
RQ1_SPEC = spec_from_file_location("rq3_rq1_common_module", RQ1_COMMON_PATH)
if RQ1_SPEC is None or RQ1_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ1 common module from {RQ1_COMMON_PATH}")
RQ1_COMMON = module_from_spec(RQ1_SPEC)
sys.modules[RQ1_SPEC.name] = RQ1_COMMON
RQ1_SPEC.loader.exec_module(RQ1_COMMON)

DATA_DIR = RQ1_COMMON.DATA_DIR
SERVICE_ORDER = RQ1_COMMON.SERVICE_ORDER
CARE_LEVEL_ORDER = RQ1_COMMON.CARE_LEVEL_ORDER
read_xlsx_raw = RQ1_COMMON.read_xlsx_raw
load_service_costs = RQ1_COMMON.load_service_costs
load_community_data = RQ1_COMMON.load_community_data

DAYS_PER_MONTH = 30.0
RADIUS_LIMIT = 1000.0
DEFAULT_SCHEME_VARIANT: Literal["best", "safe"] = "best"
SCHEME_FILE_PREFIX = {"best": "2_1_best_scheme", "safe": "2_1_safe_scheme"}
NON_EMERGENCY_SERVICES = [service for service in SERVICE_ORDER if service != "紧急救助"]
EPS = 1e-9


@dataclass(frozen=True)
class Year5PopulationRecord:
    community: str
    year: int
    self_care: float
    semi_disabled: float
    disabled: float
    elderly_total: float
    new_entrants: float


@dataclass(frozen=True)
class AdjustedDemandSummaryRecord:
    community: str
    service: str
    adjusted_monthly_demand: float


@dataclass(frozen=True)
class AdjustedDemandDetailRecord:
    community: str
    care_level: str
    service: str
    monthly_income: float
    budget_limit: float
    theoretical_per_person: float
    adjusted_per_person: float
    adjustment_scale: float
    population: float
    adjusted_monthly_demand: float


@dataclass(frozen=True)
class SchemeSummaryRecord:
    scheme_type: str
    scheme_code: str
    scheme_detail: str
    station_count: int
    build_cost_wan: float
    geographic_population_coverage: float
    served_population_coverage: float
    served_demand_coverage: float
    average_service_satisfaction: float
    minimum_service_satisfaction: float
    total_raw_served_demand_daily: float
    total_effective_person_times_daily: float
    capacity_safety_rate: float
    max_station_utilization: float
    fully_safe: int
    fully_served_community_count: int
    total_unmet_daily_demand: float
    utilization_variance: float
    annual_net_profit_before_subsidy: float
    annual_net_profit_after_policy_subsidy: float
    weighted_served_population_coverage: float = 0.0
    average_service_access_performance: float = 0.0
    minimum_service_access_performance: float = 0.0
    total_adjusted_demand_daily: float = 0.0
    annual_revenue: float = 0.0
    annual_subsidy: float = 0.0
    annual_direct_cost: float = 0.0
    annual_fixed_cost: float = 0.0
    annual_depreciation: float = 0.0
    annual_total_cost: float = 0.0
    annual_net_profit: float = 0.0
    profit_rate: float = 0.0
    profit_compliant: int = 0


@dataclass(frozen=True)
class StationRecord:
    station_community: str
    scale: str
    daily_capacity: float
    assigned_primary_load: float
    assigned_overflow_load: float
    total_load: float
    utilization: float
    annual_service_revenue: float
    annual_direct_cost: float
    annual_fixed_cost: float
    annual_depreciation: float
    annual_government_subsidy_baseline: float
    annual_net_profit_before_subsidy: float
    annual_net_profit_after_policy_subsidy: float
    annual_revenue: float = 0.0
    annual_subsidy: float = 0.0
    annual_total_cost: float = 0.0
    annual_net_profit: float = 0.0
    profit_rate: float = 0.0
    profit_compliant: int = 0


@dataclass(frozen=True)
class AllocationRecord:
    community: str
    primary_station: str | None
    overflow_station: str | None
    geographic_reachable: int
    actually_served: int
    geographic_population_covered: float
    served_population_covered: float
    raw_served_demand_daily: float
    effective_person_times_daily: float
    primary_load_daily: float
    overflow_load_daily: float
    unmet_load_daily: float
    geographic_satisfaction: float
    response_satisfaction: float
    price_satisfaction: float
    service_satisfaction: float
    adjusted_demand_daily: float = 0.0
    demand_service_ratio: float = 0.0
    service_access_performance: float = 0.0


@dataclass(frozen=True)
class StationScale:
    name: str
    build_cost_wan: float
    daily_fixed_cost: float
    daily_capacity: float


@dataclass
class RQ3Inputs:
    metadata: Dict[str, object]
    year5_population: List[Year5PopulationRecord]
    adjusted_demand_summary: List[AdjustedDemandSummaryRecord]
    adjusted_demand_detail: List[AdjustedDemandDetailRecord]
    q2_summary: SchemeSummaryRecord
    q2_stations: List[StationRecord]
    q2_allocations: List[AllocationRecord]


def validate_high_precision_input_path(path: Path) -> None:
    forbidden_keywords = ["rounded", "report", "summary_rounded"]
    lower_name = path.name.lower()
    assert all(keyword not in lower_name for keyword in forbidden_keywords), (
        f"RQ3 must not read rounded/report inputs: {path.name}"
    )


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def assert_required_columns(
    rows: List[Dict[str, str]],
    required_columns: List[str],
    path: Path,
) -> None:
    assert rows, f"{path.name} is empty"
    missing = [column for column in required_columns if column not in rows[0]]
    assert not missing, f"{path.name} missing required columns: {missing}"


def assert_non_integer_precision(
    rows: List[Dict[str, str]],
    field_names: List[str],
    path: Path,
) -> None:
    found = False
    for row in rows:
        for field_name in field_names:
            value = float(row[field_name])
            if abs(value - round(value)) > 1e-6:
                found = True
                break
        if found:
            break
    assert found, f"{path.name} appears rounded; expected non-integer high-precision values"


def load_rq1_high_precision_metadata() -> Dict[str, object]:
    path = RQ1_OUTPUT_DIR / "rq1_high_precision_metadata.json"
    assert path.exists(), "Missing rq1_high_precision_metadata.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    assert metadata.get("source") == "RQ1", "Unexpected RQ1 metadata source"
    assert metadata.get("precision") == "high", "RQ3 requires high-precision RQ1 outputs"
    assert metadata.get("rounded_for_report") is False, "RQ3 inputs must not be rounded report tables"
    return metadata


def validate_rq1_metadata_file_declared(
    metadata: Dict[str, object],
    expected_file: str,
) -> None:
    files = metadata.get("files", {})
    assert isinstance(files, dict), "RQ1 metadata missing files mapping"
    declared_files = set(files.values())
    legacy_allowed_files = {"1_3_high_precision_adjusted_demand_detail.csv"}
    assert expected_file in declared_files or expected_file in legacy_allowed_files, (
        f"{expected_file} not declared in RQ1 metadata"
    )


def load_year5_population() -> List[Year5PopulationRecord]:
    metadata = load_rq1_high_precision_metadata()
    path = RQ1_OUTPUT_DIR / "1_1_high_precision_year5_population.csv"
    validate_high_precision_input_path(path)
    validate_rq1_metadata_file_declared(metadata, path.name)
    rows = read_csv_rows(path)
    required_columns = [
        "year",
        "community",
        "self_care",
        "semi_disabled",
        "disabled",
        "elderly_total",
        "new_entrants",
    ]
    assert_required_columns(rows, required_columns, path)
    assert all(int(row["year"]) == 5 for row in rows), f"{path.name} must only contain year == 5 rows"
    assert len(rows) == 10, f"{path.name} must contain 10 communities"
    assert_non_integer_precision(rows, ["self_care", "elderly_total"], path)

    records = [
        Year5PopulationRecord(
            community=row["community"],
            year=int(row["year"]),
            self_care=float(row["self_care"]),
            semi_disabled=float(row["semi_disabled"]),
            disabled=float(row["disabled"]),
            elderly_total=float(row["elderly_total"]),
            new_entrants=float(row["new_entrants"]),
        )
        for row in rows
    ]
    records.sort(key=lambda item: item.community)
    for record in records:
        elder_sum = record.self_care + record.semi_disabled + record.disabled
        assert abs(elder_sum - record.elderly_total) < 1e-5, (
            f"Population mismatch in {record.community}: {elder_sum} != {record.elderly_total}"
        )
    return records


def load_adjusted_demand_summary() -> List[AdjustedDemandSummaryRecord]:
    metadata = load_rq1_high_precision_metadata()
    path = RQ1_OUTPUT_DIR / "1_3_high_precision_adjusted_demand.csv"
    validate_high_precision_input_path(path)
    validate_rq1_metadata_file_declared(metadata, path.name)
    rows = read_csv_rows(path)
    required_columns = ["community", "service", "adjusted_monthly_demand"]
    assert_required_columns(rows, required_columns, path)
    assert len(rows) == 10 * len(SERVICE_ORDER), f"{path.name} must contain 10 × 6 rows"
    assert_non_integer_precision(rows, ["adjusted_monthly_demand"], path)

    records = [
        AdjustedDemandSummaryRecord(
            community=row["community"],
            service=row["service"],
            adjusted_monthly_demand=float(row["adjusted_monthly_demand"]),
        )
        for row in rows
    ]
    validate_adjusted_demand_summary(records)
    return sorted(records, key=lambda item: (item.community, SERVICE_ORDER.index(item.service)))


def load_adjusted_demand_detail() -> List[AdjustedDemandDetailRecord]:
    metadata = load_rq1_high_precision_metadata()
    path = RQ1_OUTPUT_DIR / "1_3_high_precision_adjusted_demand_detail.csv"
    validate_high_precision_input_path(path)
    validate_rq1_metadata_file_declared(metadata, path.name)
    rows = read_csv_rows(path)
    required_columns = [
        "community",
        "care_level",
        "service",
        "monthly_income",
        "budget_limit",
        "theoretical_per_person",
        "adjusted_per_person",
        "adjustment_scale",
        "population",
        "adjusted_monthly_demand",
    ]
    assert_required_columns(rows, required_columns, path)
    assert len(rows) == 10 * len(CARE_LEVEL_ORDER) * len(SERVICE_ORDER), (
        f"{path.name} must contain 10 × 3 × 6 rows"
    )
    assert_non_integer_precision(rows, ["population", "adjusted_monthly_demand"], path)

    records = [
        AdjustedDemandDetailRecord(
            community=row["community"],
            care_level=row["care_level"],
            service=row["service"],
            monthly_income=float(row["monthly_income"]),
            budget_limit=float(row["budget_limit"]),
            theoretical_per_person=float(row["theoretical_per_person"]),
            adjusted_per_person=float(row["adjusted_per_person"]),
            adjustment_scale=float(row["adjustment_scale"]),
            population=float(row["population"]),
            adjusted_monthly_demand=float(row["adjusted_monthly_demand"]),
        )
        for row in rows
    ]
    validate_adjusted_demand_detail(records)
    return sorted(
        records,
        key=lambda item: (
            item.community,
            CARE_LEVEL_ORDER.index(item.care_level),
            SERVICE_ORDER.index(item.service),
        ),
    )


def scheme_variant_prefix(scheme_variant: Literal["best", "safe"]) -> str:
    assert scheme_variant in SCHEME_FILE_PREFIX, f"Unsupported scheme variant: {scheme_variant}"
    return SCHEME_FILE_PREFIX[scheme_variant]


def load_q2_scheme_summary(
    scheme_variant: Literal["best", "safe"] = DEFAULT_SCHEME_VARIANT,
) -> SchemeSummaryRecord:
    prefix = scheme_variant_prefix(scheme_variant)
    path = RQ2_OUTPUT_DIR / f"{prefix}_summary.csv"
    rows = read_csv_rows(path)
    required_columns = [
        "scheme_type",
        "scheme_code",
        "scheme_detail",
        "station_count",
        "build_cost_wan",
        "geographic_population_coverage",
        "served_population_coverage",
        "weighted_served_population_coverage",
        "served_demand_coverage",
        "average_service_satisfaction",
        "minimum_service_satisfaction",
        "average_service_access_performance",
        "minimum_service_access_performance",
        "total_adjusted_demand_daily",
        "total_raw_served_demand_daily",
        "total_effective_person_times_daily",
        "capacity_safety_rate",
        "max_station_utilization",
        "fully_safe",
        "fully_served_community_count",
        "total_unmet_daily_demand",
        "utilization_variance",
        "annual_revenue",
        "annual_subsidy",
        "annual_direct_cost",
        "annual_fixed_cost",
        "annual_depreciation",
        "annual_total_cost",
        "annual_net_profit_before_subsidy",
        "annual_net_profit_after_policy_subsidy",
        "annual_net_profit",
        "profit_rate",
        "profit_compliant",
    ]
    assert_required_columns(rows, required_columns, path)
    assert len(rows) == 1, f"{path.name} must contain exactly one summary row"
    row = rows[0]
    return SchemeSummaryRecord(
        scheme_type=row["scheme_type"],
        scheme_code=row["scheme_code"],
        scheme_detail=row["scheme_detail"],
        station_count=int(float(row["station_count"])),
        build_cost_wan=float(row["build_cost_wan"]),
        geographic_population_coverage=float(row["geographic_population_coverage"]),
        served_population_coverage=float(row["served_population_coverage"]),
        weighted_served_population_coverage=float(row["weighted_served_population_coverage"]),
        served_demand_coverage=float(row["served_demand_coverage"]),
        average_service_satisfaction=float(row["average_service_satisfaction"]),
        minimum_service_satisfaction=float(row["minimum_service_satisfaction"]),
        average_service_access_performance=float(row["average_service_access_performance"]),
        minimum_service_access_performance=float(row["minimum_service_access_performance"]),
        total_adjusted_demand_daily=float(row["total_adjusted_demand_daily"]),
        total_raw_served_demand_daily=float(row["total_raw_served_demand_daily"]),
        total_effective_person_times_daily=float(row["total_effective_person_times_daily"]),
        capacity_safety_rate=float(row["capacity_safety_rate"]),
        max_station_utilization=float(row["max_station_utilization"]),
        fully_safe=int(float(row["fully_safe"])),
        fully_served_community_count=int(float(row["fully_served_community_count"])),
        total_unmet_daily_demand=float(row["total_unmet_daily_demand"]),
        utilization_variance=float(row["utilization_variance"]),
        annual_revenue=float(row["annual_revenue"]),
        annual_subsidy=float(row["annual_subsidy"]),
        annual_direct_cost=float(row["annual_direct_cost"]),
        annual_fixed_cost=float(row["annual_fixed_cost"]),
        annual_depreciation=float(row["annual_depreciation"]),
        annual_total_cost=float(row["annual_total_cost"]),
        annual_net_profit_before_subsidy=float(row["annual_net_profit_before_subsidy"]),
        annual_net_profit_after_policy_subsidy=float(row["annual_net_profit_after_policy_subsidy"]),
        annual_net_profit=float(row["annual_net_profit"]),
        profit_rate=float(row["profit_rate"]),
        profit_compliant=int(float(row["profit_compliant"])),
    )


def load_q2_stations(
    scheme_variant: Literal["best", "safe"] = DEFAULT_SCHEME_VARIANT,
) -> List[StationRecord]:
    prefix = scheme_variant_prefix(scheme_variant)
    path = RQ2_OUTPUT_DIR / f"{prefix}_stations.csv"
    rows = read_csv_rows(path)
    required_columns = [
        "station_community",
        "scale",
        "daily_capacity",
        "assigned_primary_load",
        "assigned_overflow_load",
        "total_load",
        "utilization",
        "annual_service_revenue",
        "annual_revenue",
        "annual_subsidy",
        "annual_direct_cost",
        "annual_fixed_cost",
        "annual_depreciation",
        "annual_government_subsidy_baseline",
        "annual_total_cost",
        "annual_net_profit_before_subsidy",
        "annual_net_profit_after_policy_subsidy",
        "annual_net_profit",
        "profit_rate",
        "profit_compliant",
    ]
    assert_required_columns(rows, required_columns, path)
    records = [
        StationRecord(
            station_community=row["station_community"],
            scale=row["scale"],
            daily_capacity=float(row["daily_capacity"]),
            assigned_primary_load=float(row["assigned_primary_load"]),
            assigned_overflow_load=float(row["assigned_overflow_load"]),
            total_load=float(row["total_load"]),
            utilization=float(row["utilization"]),
            annual_service_revenue=float(row["annual_service_revenue"]),
            annual_revenue=float(row["annual_revenue"]),
            annual_subsidy=float(row["annual_subsidy"]),
            annual_direct_cost=float(row["annual_direct_cost"]),
            annual_fixed_cost=float(row["annual_fixed_cost"]),
            annual_depreciation=float(row["annual_depreciation"]),
            annual_government_subsidy_baseline=float(row["annual_government_subsidy_baseline"]),
            annual_total_cost=float(row["annual_total_cost"]),
            annual_net_profit_before_subsidy=float(row["annual_net_profit_before_subsidy"]),
            annual_net_profit_after_policy_subsidy=float(row["annual_net_profit_after_policy_subsidy"]),
            annual_net_profit=float(row["annual_net_profit"]),
            profit_rate=float(row["profit_rate"]),
            profit_compliant=int(float(row["profit_compliant"])),
        )
        for row in rows
    ]
    assert records, f"{path.name} must contain at least one station"
    return sorted(records, key=lambda item: item.station_community)


def load_q2_allocations(
    scheme_variant: Literal["best", "safe"] = DEFAULT_SCHEME_VARIANT,
) -> List[AllocationRecord]:
    prefix = scheme_variant_prefix(scheme_variant)
    path = RQ2_OUTPUT_DIR / f"{prefix}_allocations.csv"
    rows = read_csv_rows(path)
    required_columns = [
        "community",
        "primary_station",
        "overflow_station",
        "geographic_reachable",
        "actually_served",
        "geographic_population_covered",
        "served_population_covered",
        "adjusted_demand_daily",
        "raw_served_demand_daily",
        "effective_person_times_daily",
        "demand_service_ratio",
        "service_access_performance",
        "primary_load_daily",
        "overflow_load_daily",
        "unmet_load_daily",
        "geographic_satisfaction",
        "response_satisfaction",
        "price_satisfaction",
        "service_satisfaction",
    ]
    assert_required_columns(rows, required_columns, path)
    assert len(rows) == 10, f"{path.name} must contain 10 community rows"

    records = [
        AllocationRecord(
            community=row["community"],
            primary_station=normalize_optional_station_name(row["primary_station"]),
            overflow_station=normalize_optional_station_name(row["overflow_station"]),
            geographic_reachable=int(float(row["geographic_reachable"])),
            actually_served=int(float(row["actually_served"])),
            geographic_population_covered=float(row["geographic_population_covered"]),
            served_population_covered=float(row["served_population_covered"]),
            adjusted_demand_daily=float(row["adjusted_demand_daily"]),
            raw_served_demand_daily=float(row["raw_served_demand_daily"]),
            effective_person_times_daily=float(row["effective_person_times_daily"]),
            demand_service_ratio=float(row["demand_service_ratio"]),
            service_access_performance=float(row["service_access_performance"]),
            primary_load_daily=float(row["primary_load_daily"]),
            overflow_load_daily=float(row["overflow_load_daily"]),
            unmet_load_daily=float(row["unmet_load_daily"]),
            geographic_satisfaction=float(row["geographic_satisfaction"]),
            response_satisfaction=float(row["response_satisfaction"]),
            price_satisfaction=float(row["price_satisfaction"]),
            service_satisfaction=float(row["service_satisfaction"]),
        )
        for row in rows
    ]
    records.sort(key=lambda item: item.community)
    validate_allocation_records(records)
    return records


def normalize_optional_station_name(value: str) -> str | None:
    text = value.strip()
    return text or None


def load_station_scales() -> Dict[str, StationScale]:
    sheets = read_xlsx_raw(DATA_DIR / "附件3：服务站建设与运营成本.xlsx")
    rows = sheets["服务站建设与运营成本"]
    result: Dict[str, StationScale] = {}
    for row in rows[2:5]:
        scale = str(row[0]).strip()
        if not scale:
            continue
        result[scale] = StationScale(
            name=scale,
            build_cost_wan=float(row[1]),
            daily_fixed_cost=float(row[2]),
            daily_capacity=float(row[3]),
        )
    assert set(result) == {"小型", "中型", "大型"}, "Station scale sheet is incomplete"
    return result


def load_distance_matrix() -> Dict[str, Dict[str, float]]:
    sheets = read_xlsx_raw(DATA_DIR / "附件4：小区间距离矩阵.xlsx")
    rows = sheets["小区间距离矩阵"]
    header = [str(x).strip() for x in rows[1][1:11]]
    matrix: Dict[str, Dict[str, float]] = {}
    for row in rows[2:12]:
        community = str(row[0]).strip()
        if not community:
            continue
        matrix[community] = {header[idx - 1]: float(row[idx]) for idx in range(1, 11)}
    assert len(matrix) == 10, "Distance matrix must contain 10 communities"
    return matrix


def load_satisfaction_rules() -> Dict[str, List[tuple[float, float]]]:
    sheets = read_xlsx_raw(DATA_DIR / "附件5：满意度评分规则.xlsx")
    rows = sheets["满意度评分规则"]
    assert rows[2][0].startswith("因素 1"), "Unexpected satisfaction rules layout"
    return {
        "distance": [
            (300.0, 1.00),
            (500.0, 0.90),
            (650.0, 0.75),
            (1000.0, 0.60),
        ],
        "response": [
            (0.60, 1.00),
            (0.75, 0.93),
            (0.85, 0.85),
            (0.95, 0.72),
            (1.00, 0.60),
        ],
    }


def load_rq3_inputs(
    scheme_variant: Literal["best", "safe"] = DEFAULT_SCHEME_VARIANT,
) -> RQ3Inputs:
    metadata = load_rq1_high_precision_metadata()
    year5_population = load_year5_population()
    adjusted_demand_summary = load_adjusted_demand_summary()
    adjusted_demand_detail = load_adjusted_demand_detail()
    q2_summary = load_q2_scheme_summary(scheme_variant=scheme_variant)
    q2_stations = load_q2_stations(scheme_variant=scheme_variant)
    q2_allocations = load_q2_allocations(scheme_variant=scheme_variant)

    station_count = len(q2_stations)
    assert station_count == q2_summary.station_count, (
        f"Station count mismatch: stations={station_count}, summary={q2_summary.station_count}"
    )
    assert len(q2_allocations) == len(year5_population) == 10, "RQ3 expects 10 communities in Q1 and Q2 inputs"
    assert {item.community for item in q2_allocations} == {item.community for item in year5_population}, (
        "Community set mismatch between Q1 year-5 population and Q2 allocations"
    )
    return RQ3Inputs(
        metadata=metadata,
        year5_population=year5_population,
        adjusted_demand_summary=adjusted_demand_summary,
        adjusted_demand_detail=adjusted_demand_detail,
        q2_summary=q2_summary,
        q2_stations=q2_stations,
        q2_allocations=q2_allocations,
    )


def population_by_community(records: List[Year5PopulationRecord]) -> Dict[str, Year5PopulationRecord]:
    return {record.community: record for record in records}


def adjusted_demand_summary_map(
    records: List[AdjustedDemandSummaryRecord],
) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, Dict[str, float]] = {}
    for record in records:
        grouped.setdefault(record.community, {})[record.service] = record.adjusted_monthly_demand
    return grouped


def adjusted_demand_detail_map(
    records: List[AdjustedDemandDetailRecord],
) -> Dict[str, Dict[str, Dict[str, AdjustedDemandDetailRecord]]]:
    grouped: Dict[str, Dict[str, Dict[str, AdjustedDemandDetailRecord]]] = {}
    for record in records:
        grouped.setdefault(record.community, {}).setdefault(record.care_level, {})[record.service] = record
    return grouped


def stations_by_community(records: List[StationRecord]) -> Dict[str, StationRecord]:
    return {record.station_community: record for record in records}


def allocations_by_community(records: List[AllocationRecord]) -> Dict[str, AllocationRecord]:
    return {record.community: record for record in records}


def initial_service_satisfaction_by_community(
    records: List[AllocationRecord],
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for record in records:
        served = record.actually_served == 1 and record.raw_served_demand_daily > EPS
        result[record.community] = record.service_satisfaction if served else 0.0
    return result


def initial_primary_station_by_community(
    records: List[AllocationRecord],
) -> Dict[str, str | None]:
    return {record.community: record.primary_station for record in records}


def initial_overflow_station_by_community(
    records: List[AllocationRecord],
) -> Dict[str, str | None]:
    return {record.community: record.overflow_station for record in records}


def base_price_by_service() -> Dict[str, float]:
    service_costs = load_service_costs()
    return {service: service_costs[service]["price"] for service in SERVICE_ORDER}


def direct_cost_by_service() -> Dict[str, float]:
    service_costs = load_service_costs()
    return {service: service_costs[service]["direct_cost"] for service in SERVICE_ORDER}


def recommended_price_candidates() -> Dict[str, List[float]]:
    base_prices = base_price_by_service()
    result: Dict[str, List[float]] = {}
    for service in SERVICE_ORDER:
        if service == "紧急救助":
            result[service] = [0.0]
            continue
        base = base_prices[service]
        result[service] = [base, 1.1 * base, 1.2 * base, 1.3 * base]
    return result


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def validate_adjusted_demand_summary(records: List[AdjustedDemandSummaryRecord]) -> None:
    by_community: Dict[str, set[str]] = {}
    for record in records:
        assert record.service in SERVICE_ORDER, f"Unexpected service in adjusted demand summary: {record.service}"
        by_community.setdefault(record.community, set()).add(record.service)
        assert record.adjusted_monthly_demand >= 0, "Adjusted monthly demand must be non-negative"
    for community, services in by_community.items():
        assert services == set(SERVICE_ORDER), f"Adjusted demand summary incomplete for community {community}"
    assert len(by_community) == 10, "Adjusted demand summary must cover 10 communities"


def validate_adjusted_demand_detail(records: List[AdjustedDemandDetailRecord]) -> None:
    by_key: Dict[tuple[str, str], set[str]] = {}
    for record in records:
        assert record.care_level in CARE_LEVEL_ORDER, f"Unexpected care level: {record.care_level}"
        assert record.service in SERVICE_ORDER, f"Unexpected service in adjusted demand detail: {record.service}"
        assert record.adjusted_per_person <= record.theoretical_per_person + 1e-6, (
            "Adjusted per-person demand must not exceed theoretical per-person demand"
        )
        assert record.adjustment_scale <= 1 + 1e-6, "Adjustment scale must not exceed 1"
        assert record.adjustment_scale >= 0, "Adjustment scale must be non-negative"
        by_key.setdefault((record.community, record.care_level), set()).add(record.service)
    for key, services in by_key.items():
        assert services == set(SERVICE_ORDER), f"Adjusted demand detail incomplete for {key}"
    assert len(by_key) == 10 * len(CARE_LEVEL_ORDER), "Adjusted demand detail must cover all communities and care levels"


def validate_allocation_records(records: List[AllocationRecord]) -> None:
    communities = [record.community for record in records]
    assert len(set(communities)) == len(communities) == 10, "Q2 allocations must contain 10 unique communities"
    for record in records:
        if record.actually_served == 0 or record.raw_served_demand_daily <= EPS:
            assert abs(record.service_satisfaction) <= 1e-6, (
                f"Unserved community {record.community} must have service_satisfaction = 0"
            )
            assert abs(record.effective_person_times_daily) <= 1e-6, (
                f"Unserved community {record.community} must have effective_person_times_daily = 0"
            )
            assert abs(record.service_access_performance) <= 1e-6, (
                f"Unserved community {record.community} must have service_access_performance = 0"
            )
        else:
            assert 0.6 - 1e-9 <= record.service_satisfaction <= 1.0 + 1e-9, (
                f"Served community {record.community} must have service_satisfaction in [0.6, 1.0]"
            )
            assert 0.0 - 1e-9 <= record.service_access_performance <= 1.0 + 1e-9, (
                f"Service access performance must be in [0, 1] for {record.community}"
            )
        if record.primary_station is None:
            assert record.actually_served == 0 or record.raw_served_demand_daily <= EPS, (
                f"Served community {record.community} must have a primary station"
            )
        assert record.unmet_load_daily >= -1e-6, f"Unmet load must be non-negative for {record.community}"


if __name__ == "__main__":
    inputs = load_rq3_inputs()
    print(
        json.dumps(
            {
                "scheme_code": inputs.q2_summary.scheme_code,
                "station_count": inputs.q2_summary.station_count,
                "community_count": len(inputs.year5_population),
                "adjusted_demand_rows": len(inputs.adjusted_demand_summary),
                "adjusted_demand_detail_rows": len(inputs.adjusted_demand_detail),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
