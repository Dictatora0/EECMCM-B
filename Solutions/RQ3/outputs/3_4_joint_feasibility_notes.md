# RQ3 Joint Feasibility Diagnostics

本扩展不改变问题3主模型，只将“联合可行性”失败拆解到逐站利润率边界上。

## Interpretation Rules

- `profit_rate < 0`：该站点在当前承接结构下无法保本，需提高相关收费服务收入或降低固定/直接成本压力。
- `profit_rate > 0.08`：该站点超过“微利”上界，需降价、提高公益承接占比，或通过布局调整分担需求。
- `joint feasible` 只能在所有站点都满足 `0 <= profit_rate <= 0.08` 且全局固定点收敛时成立。

## S0 / station_boundary_proxy
- converged = 0
- average_service_access_performance = 0.587364
- minimum_service_access_performance = 0.467485
- joint_feasible = 0
- 卡点站点：
  - A (大型): profit_rate=0.201837, break_even_gap=0.0, over_8pct_excess=0.121837, direction=lower_price_or_expand_public_service_mix
  - C (小型): profit_rate=-1.0, break_even_gap=739000.0, over_8pct_excess=0.0, direction=raise_revenue_or_cut_cost
  - E (大型): profit_rate=0.287228, break_even_gap=0.0, over_8pct_excess=0.207228, direction=lower_price_or_expand_public_service_mix

## S4 / station_boundary_proxy
- converged = 0
- average_service_access_performance = 0.316593
- minimum_service_access_performance = 0.247652
- joint_feasible = 0
- 卡点站点：
  - A (小型): profit_rate=0.153186, break_even_gap=0.0, over_8pct_excess=0.073186, direction=lower_price_or_expand_public_service_mix
  - C (中型): profit_rate=0.243316, break_even_gap=0.0, over_8pct_excess=0.163316, direction=lower_price_or_expand_public_service_mix
  - G (大型): profit_rate=-1.0, break_even_gap=1628500.0, over_8pct_excess=0.0, direction=raise_revenue_or_cut_cost
  - J (大型): profit_rate=-1.0, break_even_gap=1628500.0, over_8pct_excess=0.0, direction=raise_revenue_or_cut_cost
