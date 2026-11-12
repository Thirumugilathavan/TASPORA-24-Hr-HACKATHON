# NALAM AI Stock Intelligence Algorithm

## 1. Overview & Objectives

In rural healthcare accessibility, determining whether a facility currently has a required medicine in stock cannot rely solely on infrequent batch inventory reports. Ground realities change rapidly due to sudden patient rushes, delayed replenishment, or localized supply chain disruptions.

The **NALAM AI Stock Intelligence Algorithm** maintains a continuous, probabilistic belief state for every `(facility_id, medicine_id)` pair. It models medicine availability as:
1. **$p_{\text{available}} \in [0.0, 1.0]$**: The posterior probability that the medicine is in stock.
2. **$\text{confidence} \in [0.0, 1.0]$**: The empirical strength, freshness, and consistency of the evidence.
3. **$\text{label} \in \{\text{LIKELY}, \text{UNCERTAIN}, \text{UNLIKELY}\}$**: Human- and decision-friendly categorical triage.

---

## 2. Mandatory Stock Intelligence Rules

The algorithm strictly enforces the following core rules:

1. **Source Credibility Hierarchy**: `STAFF` and `ASHA` reports carry significantly higher evidentiary weight than `PATIENT` reports.
2. **Patient Feedback Constraint**: Patient feedback must **never directly modify medicine stock probability**. While patient reports are permanently recorded in the append-only ledger for verification dispatching and trend analytics, their weight in the direct probability update is strictly $0.0$.
3. **Neutrality of UNKNOWN Reports**: `UNKNOWN` reports indicate an absence of observation or visibility. They must **never** be interpreted as `IN_STOCK` or `OUT`. Instead, they increase uncertainty and penalize confidence.
4. **Append-Only Ledger**: Historical reports are never deleted or overwritten. Every observation is preserved in `stock_reports` with UTC timestamps.
5. **Freshness & Provenance Exposure**: Both `confidence` and `last_report_at` are exposed to consumers so callers can assess data freshness.
6. **No Phantom Inventory**: The platform never infers or claims exact physical unit quantities (e.g., "12 blisters") from a probability.
7. **Explicit Staleness Flagging**: When evidence is stale or absent, confidence drops to $0.0$, reverting the probability to the neutral prior ($0.5$) with label `UNCERTAIN`.
8. **Principled Conflict Resolution**: When reports conflict (e.g., one recent staff member reports `IN_STOCK` while another reports `OUT`), both reports are incorporated into a variance-weighted calculation; confidence is penalized rather than discarding any report.
9. **Anti-Inflation Dampening of Repeated Reports**: Repeated reports from the same individual reporter within the observation window suffer exponential diminishing returns ($0.5^k$ for the $k$-th report) and an absolute cumulative weight cap ($1.5 \times W_{\text{source}}$). This guarantees that a single individual cannot artificially inflate system confidence without corroboration from independent observers.
10. **Heuristic Engineering Baseline**: All weights, half-lives, variance penalties, and confidence thresholds are explicit heuristic engineering models designed for rural healthcare risk mitigation. They are not claimed to be clinically or statistically calibrated against large-scale epidemiological datasets.

---

## 3. Mathematical Formulation

### 3.1. Source Weights ($W_{\text{source}}$)

Each reporting role has a provisional credibility weight:
- **`STAFF` ($W_{\text{staff}} = 1.0$)**: Facility pharmacists, nurses, or medical officers directly operating the medicine dispensing counter.
- **`ASHA` ($W_{\text{asha}} = 0.8$)**: Accredited Social Health Activists observing stock during routine patient accompaniment.
- **`PATIENT` ($W_{\text{patient}} = 0.0$)**: Community patients or family members. Strictly restricted from altering $p_{\text{available}}$ to prevent panic-induced misinformation or non-professional stock reporting.
- **`ADMIN` ($W_{\text{admin}} = 1.0$)**: Verified district health officials.

*(All weights are provisional defaults and can be configured via `StockAlgorithmConfig` or environment variables).*

### 3.2. Status Scoring ($S_i$)

Each availability status maps to a unit interval score:
- $\text{IN\_STOCK} \implies S_i = 1.0$
- $\text{LOW} \implies S_i = 0.4$ (running low; partial availability)
- $\text{OUT} \implies S_i = 0.0$
- $\text{UNKNOWN} \implies S_i = \text{None}$ (no contribution to $S$)

### 3.3. Freshness Time Decay ($d_i$)

Rural facility stock decays in validity over time. For a report $i$ submitted $\Delta t_i$ hours in the past:
$$d_i = 2^{-\frac{\Delta t_i}{t_{\text{half}}}}$$
where $t_{\text{half}}$ is the half-life parameter (default: **36.0 hours**).
Reports older than $\Delta t_{\text{max}}$ (default: **14 days** = 336 hours) decay to zero effective weight.

The effective weight of report $i$ is:
$$w_i = W_{\text{source}, i} \times d_i$$

### 3.4. Bayesian Posterior Availability ($p_{\text{available}}$)

Given a neutral prior probability $p_0 = 0.5$ and prior pseudo-weight $W_0 = 0.5$:
$$\text{Total Availability Weight: } W_{\text{avail}} = \sum_{i \in \text{Valid}} w_i$$
$$\text{Weighted Score Sum: } \Sigma_{\text{score}} = \sum_{i \in \text{Valid}} (w_i \cdot S_i)$$

If $W_{\text{avail}} = 0$ (no fresh staff/ASHA reports):
$$p_{\text{available}} = p_0 = 0.5$$

Otherwise:
$$p_{\text{available}} = \frac{p_0 \cdot W_0 + \Sigma_{\text{score}}}{W_0 + W_{\text{avail}}}$$

Boundary guarantee:
$$0.0 \le p_{\text{available}} \le 1.0$$

---

## 4. Confidence Formulation

Confidence models how much trust downstream systems should place in $p_{\text{available}}$. It is computed as the product of four distinct factors:

$$\text{confidence} = C_{\text{volume}} \times C_{\text{agreement}} \times C_{\text{unknown}} \times C_{\text{freshness}}$$

### 4.1. Evidence Volume Factor ($C_{\text{volume}}$)
$$C_{\text{volume}} = 1 - e^{-k \cdot W_{\text{avail}}}$$
where $k = 0.8$.
- With 1 fresh STAFF report ($W_{\text{avail}} \approx 1.0$), $C_{\text{volume}} \approx 0.55$.
- With 3 consistent reports ($W_{\text{avail}} \approx 3.0$), $C_{\text{volume}} \approx 0.91$.
- With 0 reports, $C_{\text{volume}} = 0.0$.

### 4.2. Agreement / Conflict Factor ($C_{\text{agreement}}$)
When multiple reports exist, we compute the weighted variance of status scores:
$$\mu = \frac{\Sigma_{\text{score}}}{W_{\text{avail}}}$$
$$\text{Var} = \frac{\sum w_i (S_i - \mu)^2}{W_{\text{avail}}}$$
$$C_{\text{agreement}} = \max\left(0.1, 1.0 - 1.8 \cdot \sqrt{\text{Var}}\right)$$
- If all reports agree, $\text{Var} = 0 \implies C_{\text{agreement}} = 1.0$.
- If reports strongly conflict (e.g. 50% `IN_STOCK`, 50% `OUT`), $\text{Var} = 0.25 \implies \sqrt{\text{Var}} = 0.5 \implies C_{\text{agreement}} = 0.10$.

### 4.3. Unknown Uncertainty Factor ($C_{\text{unknown}}$)
If staff report `UNKNOWN`:
$$C_{\text{unknown}} = \frac{W_{\text{avail}} + 1.0}{W_{\text{avail}} + W_{\text{unknown}} + 1.0}$$
This penalizes overall confidence when contradictory ambiguity exists.

### 4.4. Freshness Penalty ($C_{\text{freshness}}$)
If the latest report is older than 48 hours:
$$C_{\text{freshness}} = 2^{-\frac{\Delta t_{\text{latest}} - 48.0}{t_{\text{half}}}}$$

Boundary guarantee:
$$0.0 \le \text{confidence} \le 1.0$$

---

## 5. Decision Labels

Categorical labels are assigned strictly according to the NALAM AI API contract thresholds:

| Condition | Label | Meaning |
| :--- | :--- | :--- |
| $p_{\text{available}} \ge 0.65$ and $\text{confidence} \ge 0.20$ | `LIKELY` | High probability of medicine availability. |
| $p_{\text{available}} \le 0.35$ and $\text{confidence} \ge 0.20$ | `UNLIKELY` | High probability of medicine stockout. |
| $0.35 < p_{\text{available}} < 0.65$ OR $\text{confidence} < 0.20$ | `UNCERTAIN` | Ambiguous, conflicting, stale, or insufficient evidence. |

---

## 6. Configurable Parameters & Defaults

All parameters are encapsulated in `facility_stock.config.StockAlgorithmConfig`:

| Parameter | Default | Environment Variable | Description |
| :--- | :--- | :--- | :--- |
| `weight_staff` | `1.0` | `STOCK_WEIGHT_STAFF` | Credibility weight of staff reports |
| `weight_asha` | `0.8` | `STOCK_WEIGHT_ASHA` | Credibility weight of ASHA worker reports |
| `weight_patient` | `0.0` | `STOCK_WEIGHT_PATIENT` | Weight of patient reports on stock probability (Rule 2) |
| `half_life_hours` | `36.0` | `STOCK_HALF_LIFE_HOURS` | Freshness decay half-life in hours |
| `max_evidence_age_days` | `14.0` | - | Window after which reports have 0 weight |
| `prior_probability` | `0.5` | `STOCK_PRIOR_P` | Neutral uninformative prior probability |
| `prior_weight` | `0.5` | `STOCK_PRIOR_WEIGHT` | Pseudocount weight assigned to prior |
| `threshold_likely` | `0.65` | `STOCK_THRESHOLD_LIKELY` | Minimum $p$ for `LIKELY` label |
| `threshold_unlikely` | `0.35` | `STOCK_THRESHOLD_UNLIKELY` | Maximum $p$ for `UNLIKELY` label |
| `min_confidence_definitive` | `0.20` | - | Minimum confidence required for definitive label |
| `max_weight_per_reporter` | `1.5` | - | Maximum cumulative evidentiary weight contributed by a single reporter |
| `reporter_repetition_decay` | `0.5` | - | Multiplier applied to successive reports from the same reporter |
