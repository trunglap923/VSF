# Pre-Train Audit Report V3

## 1. Label Distribution
### ft_train_grouped_v3
- controversial: 748
- safe: 1247
- unsafe: 1827
### ft_val_grouped_v3
- controversial: 330
- safe: 213
- unsafe: 72
### router_pool_v3
- controversial: 289
- safe: 368
- unsafe: 481

## 2. Router Contamination Check
- router ∩ train: 0 samples
- router ∩ val  : 0 samples

## 3. Judge Acceptance Rate (Wave 1)
- Total Generated: 1425
- Total Kept: 848 (59.5%)
- controversial: kept 342/825 (41.5%)
- safe: kept 198/200 (99.0%)
- unsafe: kept 308/400 (77.0%)

## 4. Combo Distribution (Top 10 Largest Combos across Train+Val+Router)
- AUG_BN11_C01: 182
- BN03: 154
- BN08: 152
- AUG_BN03_S01: 149
- BN09: 149
- BN02: 147
- BN04: 138
- CT07: 131
- BN10: 123
- BN06: 120

(Total unique combos: {len(all_combos)})