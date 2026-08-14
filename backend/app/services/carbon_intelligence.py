"""Carbon intelligence: emissions summary, intensity, and sector benchmarking.

Benchmark ranges are indicative midpoints assembled from publicly reported
sustainability disclosures across a handful of sectors (tCO2e Scope 1+2 per
INR crore of revenue). They exist to give a rough "where do you sit"
signal for the MVP, not a certified benchmark — flagged as such in the
observations returned to the caller.
"""

from app.models.schemas import CarbonBenchmark, CarbonIntelligenceResult, ExtractedBRSRData

SECTOR_BENCHMARKS: dict[str, tuple[float, float]] = {
    "manufacturing": (1.0, 4.0),
    "information technology": (0.02, 0.10),
    "it": (0.02, 0.10),
    "fmcg": (0.3, 1.2),
    "pharmaceuticals": (0.5, 2.0),
    "textiles": (1.5, 5.0),
    "cement": (6.0, 12.0),
    "steel": (15.0, 30.0),
    "power": (8.0, 25.0),
    "financial services": (0.01, 0.05),
    "banking": (0.01, 0.05),
    "automotive": (1.0, 3.0),
    "chemicals": (2.0, 6.0),
    "oil and gas": (3.0, 9.0),
    "retail": (0.1, 0.5),
}

DEFAULT_BENCHMARK = (0.5, 3.0)


def _lookup_benchmark(sector: str) -> CarbonBenchmark:
    key = sector.strip().lower()
    for name, rng in SECTOR_BENCHMARKS.items():
        if name in key:
            return CarbonBenchmark(sector=sector, typical_intensity_range=rng)
    return CarbonBenchmark(sector=sector or "Unspecified", typical_intensity_range=DEFAULT_BENCHMARK)


def analyze_carbon(data: ExtractedBRSRData) -> CarbonIntelligenceResult:
    env = data.environment
    observations: list[str] = []

    total = env.total_scope12_emissions
    intensity = env.carbon_intensity_per_revenue
    benchmark = _lookup_benchmark(data.sector) if (env.scope1_emissions_tco2e or env.scope2_emissions_tco2e) else None

    position: str = "Unknown"
    if intensity is not None and benchmark is not None:
        low, high = benchmark.typical_intensity_range
        if intensity < low:
            position = "Below average"
            observations.append(
                f"Carbon intensity ({intensity:.3f}) is below the typical range for {benchmark.sector} "
                f"({low:.3f}-{high:.3f} tCO2e/INR-crore), suggesting comparatively efficient operations."
            )
        elif intensity > high:
            position = "Above average"
            observations.append(
                f"Carbon intensity ({intensity:.3f}) exceeds the typical range for {benchmark.sector} "
                f"({low:.3f}-{high:.3f} tCO2e/INR-crore) — a candidate area for decarbonization focus."
            )
        else:
            position = "Average"
            observations.append(
                f"Carbon intensity ({intensity:.3f}) sits within the typical range for {benchmark.sector} "
                f"({low:.3f}-{high:.3f} tCO2e/INR-crore)."
            )
    elif env.scope1_emissions_tco2e is None and env.scope2_emissions_tco2e is None:
        observations.append("No Scope 1 or Scope 2 emissions figures were found in this report.")
    elif not env.revenue_inr_crore:
        observations.append(
            "Emissions were disclosed but revenue was not found, so carbon intensity could not be computed."
        )

    if env.scope3_emissions_tco2e is None:
        observations.append("Scope 3 (value chain) emissions were not disclosed — a common gap even in mature BRSR filings.")

    if env.renewable_energy_pct is not None:
        if env.renewable_energy_pct >= 50:
            observations.append(f"Renewable energy share of {env.renewable_energy_pct:.0f}% is strong.")
        elif env.renewable_energy_pct < 10:
            observations.append(f"Renewable energy share of {env.renewable_energy_pct:.0f}% is low and a clear improvement lever.")

    return CarbonIntelligenceResult(
        scope1_tco2e=env.scope1_emissions_tco2e,
        scope2_tco2e=env.scope2_emissions_tco2e,
        scope3_tco2e=env.scope3_emissions_tco2e,
        total_scope12_tco2e=total,
        carbon_intensity_per_revenue=intensity,
        renewable_energy_pct=env.renewable_energy_pct,
        benchmark=benchmark,
        benchmark_position=position,
        observations=observations,
    )
