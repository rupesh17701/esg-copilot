from app.models.schemas import EnvironmentalMetrics, ExtractedBRSRData
from app.services import brsr_extractor, carbon_intelligence, pdf_parser


def test_carbon_summary_from_sample(sample_text):
    normalized = pdf_parser.normalize_whitespace(sample_text)
    data = brsr_extractor.extract_structured_data(normalized)
    result = carbon_intelligence.analyze_carbon(data)

    assert result.scope1_tco2e == 12500.0
    assert result.scope2_tco2e == 8200.0
    assert result.total_scope12_tco2e == 20700.0
    assert result.scope3_tco2e is None
    assert result.benchmark is not None
    assert result.benchmark.sector == "Textiles"
    assert result.benchmark_position in {"Below average", "Average", "Above average"}
    assert any("Scope 3" in obs for obs in result.observations)


def test_no_emissions_data_yields_unknown_position():
    data = ExtractedBRSRData(sector="Manufacturing", environment=EnvironmentalMetrics())
    result = carbon_intelligence.analyze_carbon(data)
    assert result.benchmark_position == "Unknown"
    assert result.total_scope12_tco2e is None
    assert any("No Scope 1 or Scope 2" in obs for obs in result.observations)


def test_unknown_sector_falls_back_to_default_benchmark():
    data = ExtractedBRSRData(
        sector="Some Niche Sector",
        environment=EnvironmentalMetrics(
            scope1_emissions_tco2e=10, scope2_emissions_tco2e=5, revenue_inr_crore=100
        ),
    )
    result = carbon_intelligence.analyze_carbon(data)
    assert result.benchmark is not None
    assert result.benchmark.typical_intensity_range == carbon_intelligence.DEFAULT_BENCHMARK
