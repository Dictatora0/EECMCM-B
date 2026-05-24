from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile
import csv
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

YEARS = 5
DEATH_RATE = 0.05
ELDER_GROWTH_RATE = 0.07
NEW_ENTRANT_STATE = "自理"

SERVICE_ORDER = ["助餐", "日间照料", "上门护理", "康复理疗", "助浴", "紧急救助"]
CARE_LEVEL_ORDER = ["自理", "半失能", "失能"]
CARE_LEVEL_ALIASES = {"自理": "自理", "半自理": "半失能", "半失能": "半失能", "失能": "失能"}
SPENDING_LIMIT = {"自理": 0.20, "半失能": 0.25, "失能": 0.30}


@dataclass
class CommunityRecord:
    community: str
    total_population: float
    elderly_population: float
    self_care: float
    semi_disabled: float
    disabled: float
    monthly_income: float


def _col_to_idx(col: str) -> int:
    value = 0
    for ch in col:
        if ch.isalpha():
            value = value * 26 + ord(ch.upper()) - 64
    return value - 1


def read_xlsx_raw(path: Path) -> Dict[str, List[List[str]]]:
    with ZipFile(path) as zf:
        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in shared_root.findall("a:si", NS):
                parts = [node.text or "" for node in si.findall(".//a:t", NS)]
                shared_strings.append("".join(parts))

        workbook_root = ET.fromstring(zf.read("xl/workbook.xml"))
        rel_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {node.attrib["Id"]: node.attrib["Target"] for node in rel_root}

        sheets: Dict[str, List[List[str]]] = {}
        for sheet in workbook_root.find("a:sheets", NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = "xl/" + rel_map[rel_id]
            sheet_root = ET.fromstring(zf.read(target))
            rows: List[List[str]] = []
            for row in sheet_root.findall(".//a:sheetData/a:row", NS):
                cells: Dict[int, str] = {}
                max_idx = -1
                for cell in row.findall("a:c", NS):
                    ref = cell.attrib.get("r", "A1")
                    col = "".join(ch for ch in ref if ch.isalpha())
                    idx = _col_to_idx(col)
                    max_idx = max(max_idx, idx)
                    cell_type = cell.attrib.get("t")
                    value_node = cell.find("a:v", NS)
                    if value_node is None:
                        value = ""
                    elif cell_type == "s":
                        value = shared_strings[int(value_node.text)]
                    else:
                        value = value_node.text or ""
                    cells[idx] = value
                rows.append([cells.get(i, "") for i in range(max_idx + 1)])
            sheets[name] = rows
        return sheets


def _clean_text(value: str) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").strip()


def _parse_number(value: str) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    text = text.replace("元", "").replace("%", "").replace("≤", "").replace("＜", "").replace(",", "")
    if "公益免费" in text:
        return 0.0
    number = float(text)
    if "%" in value or number > 1 and any(token in value for token in ["%", "≤ 20", "≤ 25", "≤ 30"]):
        return number / 100
    return number


def load_community_data() -> List[CommunityRecord]:
    sheets = read_xlsx_raw(DATA_DIR / "附件1：小区基础数据.xlsx")
    rows = sheets["人口与老人结构"]
    data_rows = rows[2:]
    records: List[CommunityRecord] = []
    for row in data_rows:
        if not row or not _clean_text(row[0]):
            continue
        records.append(
            CommunityRecord(
                community=_clean_text(row[0]),
                total_population=_parse_number(row[1]),
                elderly_population=_parse_number(row[2]),
                self_care=_parse_number(row[3]),
                semi_disabled=_parse_number(row[4]),
                disabled=_parse_number(row[5]),
                monthly_income=_parse_number(row[6]),
            )
        )
    validate_community_data(records)
    return records


def load_transition_probabilities() -> Dict[str, float]:
    sheets = read_xlsx_raw(DATA_DIR / "附件1：小区基础数据.xlsx")
    rows = sheets["转移概率"]
    values = {}
    for row in rows[2:]:
        if len(row) < 2 or not _clean_text(row[0]):
            continue
        key = _clean_text(row[0])
        values[key] = _parse_number(row[1])
    result = {
        "自理->半失能": values["自理 → 半失能"],
        "半失能->失能": values["半失能 → 失能"],
    }
    validate_transition_probabilities(result)
    return result


def load_service_demand() -> Dict[str, Dict[str, float]]:
    sheets = read_xlsx_raw(DATA_DIR / "附件2：服务需求数据.xlsx")
    rows = sheets["每位老人月均服务需求次数"]
    header = [_clean_text(v) for v in rows[1][1:4]]
    mapping = [CARE_LEVEL_ALIASES[name] for name in header]
    demand: Dict[str, Dict[str, float]] = {level: {} for level in CARE_LEVEL_ORDER}
    for row in rows[2:]:
        service = _clean_text(row[0])
        if not service:
            continue
        for idx, level in enumerate(mapping, start=1):
            demand[level][service] = _parse_number(row[idx])
    validate_service_demand(demand)
    return demand


def load_service_costs() -> Dict[str, Dict[str, float]]:
    sheets = read_xlsx_raw(DATA_DIR / "附件2：服务需求数据.xlsx")
    rows = sheets["服务营收及支出"]
    result: Dict[str, Dict[str, float]] = {}
    for row in rows[2:]:
        service = _clean_text(row[0])
        if not service:
            continue
        result[service] = {
            "price": _parse_number(row[1]),
            "direct_cost": _parse_number(row[2]),
        }
    validate_service_costs(result)
    return result


def validate_community_data(records: List[CommunityRecord]) -> None:
    assert len(records) == 10, f"Expected 10 communities, got {len(records)}"
    for record in records:
        elder_sum = record.self_care + record.semi_disabled + record.disabled
        assert abs(elder_sum - record.elderly_population) < 1e-6, (
            f"Community {record.community} elderly structure does not sum to 60+ total: "
            f"{elder_sum} != {record.elderly_population}"
        )
        assert record.monthly_income > 0, f"Community {record.community} monthly income must be positive"


def validate_transition_probabilities(transition: Dict[str, float]) -> None:
    for key, value in transition.items():
        assert 0 <= value <= 1, f"Transition probability {key} out of range: {value}"


def validate_service_demand(demand: Dict[str, Dict[str, float]]) -> None:
    for level in CARE_LEVEL_ORDER:
        assert level in demand, f"Missing care level: {level}"
        missing = [service for service in SERVICE_ORDER if service not in demand[level]]
        assert not missing, f"Missing services for {level}: {missing}"


def validate_service_costs(service_costs: Dict[str, Dict[str, float]]) -> None:
    missing = [service for service in SERVICE_ORDER if service not in service_costs]
    assert not missing, f"Missing service cost rows: {missing}"
    for service, item in service_costs.items():
        assert item["price"] >= 0, f"Negative price for service {service}"
        assert item["direct_cost"] >= 0, f"Negative direct cost for service {service}"


def project_elderly_population(
    communities: List[CommunityRecord],
    transition: Dict[str, float],
    years: int = YEARS,
    death_rate: float = DEATH_RATE,
    growth_rate: float = ELDER_GROWTH_RATE,
) -> List[Dict[str, float]]:
    results: List[Dict[str, float]] = []
    p12 = transition["自理->半失能"]
    p23 = transition["半失能->失能"]
    for record in communities:
        self_care = record.self_care
        semi_disabled = record.semi_disabled
        disabled = record.disabled
        community_rows: List[Dict[str, float]] = []
        for year in range(1, years + 1):
            total_elderly = self_care + semi_disabled + disabled
            survivors_self = self_care * (1 - death_rate)
            survivors_semi = semi_disabled * (1 - death_rate)
            survivors_disabled = disabled * (1 - death_rate)

            transferred_self_to_semi = survivors_self * p12
            remaining_self = survivors_self - transferred_self_to_semi
            transferred_semi_to_dis = survivors_semi * p23
            remaining_semi = survivors_semi - transferred_semi_to_dis

            entrants = total_elderly * growth_rate

            self_care = remaining_self + entrants
            semi_disabled = transferred_self_to_semi + remaining_semi
            disabled = transferred_semi_to_dis + survivors_disabled

            row = {
                "year": year,
                "community": record.community,
                "self_care": self_care,
                "semi_disabled": semi_disabled,
                "disabled": disabled,
                "elderly_total": self_care + semi_disabled + disabled,
                "new_entrants": entrants,
            }
            results.append(row)
            community_rows.append(row)
        validate_projection_path(record, community_rows, years)
    return results


def theoretical_monthly_demand(
    year5_population: List[Dict[str, float]],
    service_demand: Dict[str, Dict[str, float]],
) -> List[Dict[str, float]]:
    validate_year5_population(year5_population)
    rows: List[Dict[str, float]] = []
    for pop in year5_population:
        counts = {
            "自理": pop["self_care"],
            "半失能": pop["semi_disabled"],
            "失能": pop["disabled"],
        }
        for level in CARE_LEVEL_ORDER:
            for service in SERVICE_ORDER:
                rows.append(
                    {
                        "community": pop["community"],
                        "care_level": level,
                        "service": service,
                        "theoretical_monthly_demand": counts[level] * service_demand[level][service],
                    }
                )
    validate_theoretical_demand_detail(rows)
    return rows


def aggregate_theoretical_demand(rows: List[Dict[str, float]]) -> List[Dict[str, float]]:
    grouped: Dict[tuple[str, str], float] = {}
    for row in rows:
        key = (str(row["community"]), str(row["service"]))
        grouped[key] = grouped.get(key, 0.0) + float(row["theoretical_monthly_demand"])
    result: List[Dict[str, float]] = []
    for community in sorted({key[0] for key in grouped}):
        for service in SERVICE_ORDER:
            result.append(
                {
                    "community": community,
                    "service": service,
                    "theoretical_monthly_demand": grouped.get((community, service), 0.0),
                }
            )
    validate_service_summary(result, "theoretical_monthly_demand")
    return result


def affordability_adjusted_demand(
    communities: List[CommunityRecord],
    year5_population: List[Dict[str, float]],
    service_demand: Dict[str, Dict[str, float]],
    service_costs: Dict[str, Dict[str, float]],
) -> List[Dict[str, float]]:
    validate_year5_population(year5_population)
    income_map = {item.community: item.monthly_income for item in communities}
    pop_map = {item["community"]: item for item in year5_population}
    rows: List[Dict[str, float]] = []
    for community, pop in pop_map.items():
        counts = {
            "自理": pop["self_care"],
            "半失能": pop["semi_disabled"],
            "失能": pop["disabled"],
        }
        income = income_map[community]
        for level in CARE_LEVEL_ORDER:
            theoretical_fee = sum(
                service_demand[level][service] * service_costs[service]["price"]
                for service in SERVICE_ORDER
                if service != "紧急救助"
            )
            budget = income * SPENDING_LIMIT[level]
            scale = min(1.0, budget / theoretical_fee) if theoretical_fee > 0 else 1.0
            for service in SERVICE_ORDER:
                if service == "紧急救助":
                    adjusted_per_person = service_demand[level][service]
                else:
                    adjusted_per_person = service_demand[level][service] * scale
                rows.append(
                    {
                        "community": community,
                        "care_level": level,
                        "service": service,
                        "monthly_income": income,
                        "budget_limit": budget,
                        "theoretical_per_person": service_demand[level][service],
                        "adjusted_per_person": adjusted_per_person,
                        "adjustment_scale": scale,
                        "population": counts[level],
                        "adjusted_monthly_demand": adjusted_per_person * counts[level],
                    }
                )
    validate_adjusted_demand(rows)
    return rows


def aggregate_adjusted_demand(rows: List[Dict[str, float]]) -> List[Dict[str, float]]:
    grouped: Dict[tuple[str, str], float] = {}
    for row in rows:
        key = (str(row["community"]), str(row["service"]))
        grouped[key] = grouped.get(key, 0.0) + float(row["adjusted_monthly_demand"])
    result: List[Dict[str, float]] = []
    for community in sorted({key[0] for key in grouped}):
        for service in SERVICE_ORDER:
            result.append(
                {
                    "community": community,
                    "service": service,
                    "adjusted_monthly_demand": grouped.get((community, service), 0.0),
                }
            )
    validate_service_summary(result, "adjusted_monthly_demand")
    return result


def validate_year5_population(rows: List[Dict[str, float]]) -> None:
    communities = {str(row["community"]) for row in rows}
    assert len(communities) == len(rows), "Year-5 population rows must contain unique communities"
    for row in rows:
        assert row["self_care"] >= 0 and row["semi_disabled"] >= 0 and row["disabled"] >= 0, (
            f"Negative year-5 population for community {row['community']}"
        )


def validate_projection_path(
    record: CommunityRecord,
    rows: List[Dict[str, float]],
    expected_years: int,
) -> None:
    assert len(rows) == expected_years, (
        f"Projection row count mismatch for {record.community}: {len(rows)}"
    )
    for row in rows:
        assert row["self_care"] >= 0 and row["semi_disabled"] >= 0 and row["disabled"] >= 0, (
            f"Negative population found in projection for {record.community}, year {row['year']}"
        )
        reconstructed = row["self_care"] + row["semi_disabled"] + row["disabled"]
        assert abs(reconstructed - row["elderly_total"]) < 1e-6, (
            f"Elderly total mismatch for {record.community}, year {row['year']}"
        )
        assert row["new_entrants"] >= 0, (
            f"New entrants must be non-negative for {record.community}, year {row['year']}"
        )


def validate_service_summary(rows: List[Dict[str, float]], field: str) -> None:
    communities = {str(row["community"]) for row in rows}
    expected = len(communities) * len(SERVICE_ORDER)
    assert len(rows) == expected, f"Expected {expected} summary rows, got {len(rows)}"
    for row in rows:
        assert row[field] >= 0, f"Negative demand found for {row['community']}-{row['service']}"


def validate_adjusted_demand(rows: List[Dict[str, float]]) -> None:
    communities = {str(row["community"]) for row in rows}
    expected = len(communities) * len(CARE_LEVEL_ORDER) * len(SERVICE_ORDER)
    assert len(rows) == expected, f"Expected {expected} adjusted demand rows, got {len(rows)}"
    for row in rows:
        if row["service"] != "紧急救助":
            assert row["adjusted_per_person"] <= row["theoretical_per_person"] + 1e-8, (
                f"Adjusted demand exceeds theoretical demand for "
                f"{row['community']}-{row['care_level']}-{row['service']}"
            )
        else:
            assert abs(row["adjusted_per_person"] - row["theoretical_per_person"]) < 1e-8, (
                f"Emergency demand should not be scaled for "
                f"{row['community']}-{row['care_level']}"
            )


def validate_theoretical_demand_detail(rows: List[Dict[str, float]]) -> None:
    communities = {str(row["community"]) for row in rows}
    expected = len(communities) * len(CARE_LEVEL_ORDER) * len(SERVICE_ORDER)
    assert len(rows) == expected, f"Expected {expected} theoretical detail rows, got {len(rows)}"
    for row in rows:
        assert row["care_level"] in CARE_LEVEL_ORDER, f"Unexpected care level: {row['care_level']}"
        assert row["service"] in SERVICE_ORDER, f"Unexpected service: {row['service']}"
        assert row["theoretical_monthly_demand"] >= 0, (
            f"Negative theoretical demand found for {row['community']}-{row['care_level']}-{row['service']}"
        )


def write_csv(path: Path, rows: List[Dict[str, float]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def round_rows(rows: List[Dict[str, float]], digits: int = 4) -> List[Dict[str, float]]:
    rounded: List[Dict[str, float]] = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            if isinstance(value, float):
                new_row[key] = round(value, digits)
            else:
                new_row[key] = value
        rounded.append(new_row)
    return rounded


def integerize_rows(rows: List[Dict[str, float]], fields: List[str]) -> List[Dict[str, float]]:
    integerized: List[Dict[str, float]] = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            if key in fields and isinstance(value, (int, float)):
                new_row[key] = int(round(float(value)))
            else:
                new_row[key] = value
        integerized.append(new_row)
    return integerized


def population_transition_matrix(
    transition: Dict[str, float],
    death_rate: float = DEATH_RATE,
    growth_rate: float = ELDER_GROWTH_RATE,
) -> List[List[float]]:
    survival = 1.0 - death_rate
    p12 = transition["自理->半失能"]
    p23 = transition["半失能->失能"]
    return [
        [survival * (1.0 - p12) + growth_rate, growth_rate, growth_rate],
        [survival * p12, survival * (1.0 - p23), 0.0],
        [0.0, survival * p23, survival],
    ]


def apply_population_transition(
    state: List[float],
    transition_matrix: List[List[float]],
) -> List[float]:
    return [
        sum(transition_matrix[row_idx][col_idx] * state[col_idx] for col_idx in range(3))
        for row_idx in range(3)
    ]


def project_elderly_population_matrix(
    communities: List[CommunityRecord],
    transition: Dict[str, float],
    years: int = YEARS,
    death_rate: float = DEATH_RATE,
    growth_rate: float = ELDER_GROWTH_RATE,
) -> List[Dict[str, float]]:
    matrix = population_transition_matrix(
        transition=transition,
        death_rate=death_rate,
        growth_rate=growth_rate,
    )
    results: List[Dict[str, float]] = []
    for record in communities:
        state = [record.self_care, record.semi_disabled, record.disabled]
        community_rows: List[Dict[str, float]] = []
        for year in range(1, years + 1):
            previous_total = sum(state)
            state = apply_population_transition(state, matrix)
            row = {
                "year": year,
                "community": record.community,
                "self_care": state[0],
                "semi_disabled": state[1],
                "disabled": state[2],
                "elderly_total": sum(state),
                "new_entrants": previous_total * growth_rate,
            }
            results.append(row)
            community_rows.append(row)
        validate_projection_path(record, community_rows, years)
    return results


def aggregate_population_metrics(rows: List[Dict[str, float]], year: int | None = None) -> Dict[str, float]:
    filtered = [row for row in rows if year is None or int(row["year"]) == year]
    total_self = sum(float(row["self_care"]) for row in filtered)
    total_semi = sum(float(row["semi_disabled"]) for row in filtered)
    total_disabled = sum(float(row["disabled"]) for row in filtered)
    total_elderly = sum(float(row["elderly_total"]) for row in filtered)
    disabled_share = total_disabled / total_elderly if total_elderly > 1e-12 else 0.0
    return {
        "self_care": total_self,
        "semi_disabled": total_semi,
        "disabled": total_disabled,
        "elderly_total": total_elderly,
        "disabled_share": disabled_share,
    }


def aggregate_service_metric(rows: List[Dict[str, float]], field: str) -> float:
    return sum(float(row[field]) for row in rows)
