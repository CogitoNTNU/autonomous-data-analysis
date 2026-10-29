"""Test cases for evaluating the Critic Agent."""

from dataclasses import dataclass
from typing import Literal

from backend.app.contracts.models import (
    AnalysisResult,
    Finding,
    Interpretation,
    WarningEvent,
)


@dataclass(frozen=True)
class EvalCase:
    name: str
    domain: str
    user_query: str
    results: tuple[AnalysisResult, ...]
    interpretation: Interpretation
    expected: Literal["approved", "revise"]
    review_note: str


def _interpretation(
    summary: str,
    *findings: tuple[str, str],
    limitations: tuple[str, ...] = (),
) -> Interpretation:
    return Interpretation(
        summary=summary,
        findings=[Finding(claim=claim, result_ids=[ref]) for claim, ref in findings],
        limitations=list(limitations),
    )


def build_cases() -> tuple[EvalCase, ...]:
    """Build the 12 evaluation cases."""
    penguins = AnalysisResult(
        result_id="penguin_stats",
        step_id="describe_mass",
        dataset_version="penguins-v1",
        method="descriptive_statistics",
        parameters={"columns": ["body_mass_g"]},
        sample_size=100,
        values={
            "columns": {
                "body_mass_g": {
                    "mean": 4000.0,
                    "median": 3500.0,
                    "std": 1232.4720450266416,
                    "min": 3000.0,
                    "max": 6000.0,
                    "n": 80,
                    "missing_rate": 0.2,
                }
            },
            "status": "ok",
        },
    )
    sales = AnalysisResult(
        result_id="region_totals",
        step_id="aggregate_sales",
        dataset_version="sales-v1",
        method="group_aggregate",
        sample_size=60,
        parameters={
            "group_by": ["region"],
            "aggregations": [
                {
                    "column": "order_value_usd",
                    "function": "sum",
                    "alias": "revenue_usd",
                },
                {"column": "order_value_usd", "function": "count", "alias": "orders"},
            ],
        },
        values={
            "groups": [
                {"region": "North", "revenue_usd": 12000, "orders": 40},
                {"region": "South", "revenue_usd": 6000, "orders": 20},
            ],
            "group_count": 2,
            "group_sizes": [40, 20],
            "status": "ok",
        },
    )
    order_stats = AnalysisResult(
        result_id="order_stats",
        step_id="describe_orders",
        dataset_version="sales-v1",
        method="descriptive_statistics",
        parameters={"columns": ["order_value_usd"]},
        sample_size=60,
        values={
            "columns": {
                "order_value_usd": {
                    "mean": 300.0,
                    "median": 300.0,
                    "std": 100.84389681792214,
                    "min": 200.0,
                    "max": 400.0,
                    "n": 60,
                    "missing_rate": 0.0,
                }
            },
            "status": "ok",
        },
    )
    traffic = AnalysisResult(
        result_id="channel_counts",
        step_id="count_channels",
        dataset_version="traffic-v1",
        method="categorical_analysis",
        parameters={"column": "channel", "normalize": False},
        sample_size=100,
        values={
            "column": "channel",
            "categories": [
                {"value": "organic", "count": 36},
                {"value": "paid", "count": 24},
            ],
            "category_count": 2,
            "omitted_categories": 0,
            "mode": ["organic"],
            "observed_count": 60,
            "missing_count": 40,
            "normalized": False,
            "status": "partial",
        },
        warnings=[
            WarningEvent(
                code="HIGH_MISSING_RATE",
                message="channel missing=0.40",
                source="categorical_analysis",
                step_id="count_channels",
            )
        ],
    )
    shares = traffic.model_copy(
        deep=True,
        update={
            "result_id": "channel_shares",
            "step_id": "channel_proportions",
            "parameters": {"column": "channel", "normalize": True},
            "values": {
                **traffic.values,
                "categories": [
                    {"value": "organic", "proportion": 0.6},
                    {"value": "paid", "proportion": 0.4},
                ],
                "normalized": True,
            },
            "warnings": [
                traffic.warnings[0].model_copy(
                    update={"step_id": "channel_proportions"}
                )
            ],
        },
    )
    mass_query = "Report mean recorded body mass and the number of observed weights."
    totals_query = "Report total revenue in USD and order counts for each region."
    channel_query = (
        "Report website session channels and important attribution limitations."
    )
    totals = "North revenue is $12,000 from 40 orders; South revenue is $6,000 from 20 orders."
    attribution = "40 of 100 sessions have no recorded channel; observed channels may not represent all sessions."
    return (
        EvalCase(
            "penguins_units",
            "penguins",
            mass_query,
            (penguins,),
            _interpretation(
                "Mean body mass is 4 kg across 80 observed weights.",
                ("The mean is 4 kg across 80 observed weights.", "penguin_stats"),
                limitations=("Missing weights were excluded.",),
            ),
            "approved",
            "The units are equivalent, and 80 weights were observed.",
        ),
        EvalCase(
            "penguins_multiple_statistics",
            "penguins",
            "Report median body mass and its observed range.",
            (penguins,),
            _interpretation(
                "The median is 3,500 g, with weights ranging from 3,000 to 6,000 g.",
                ("Median body mass is 3,500 g.", "penguin_stats"),
                ("Observed weights range from 3,000 to 6,000 g.", "penguin_stats"),
                limitations=("Missing weights were excluded.",),
            ),
            "approved",
            "The median and range match the analysis result.",
        ),
        EvalCase(
            "penguins_wrong_count",
            "penguins",
            mass_query,
            (penguins,),
            _interpretation(
                "Mean body mass is 4 kg across 100 observed weights.",
                ("The mean is 4 kg across 100 observed weights.", "penguin_stats"),
                limitations=("Missing weights were excluded.",),
            ),
            "revise",
            "There are 80 observed weights; 100 is the total row count.",
        ),
        EvalCase(
            "penguins_missing_reference",
            "penguins",
            mass_query,
            (penguins,),
            _interpretation(
                "Mean body mass is 4 kg across 80 observed weights.",
                ("The mean is 4 kg across 80 observed weights.", "missing_result"),
                limitations=("Missing weights were excluded.",),
            ),
            "revise",
            "Replace missing_result with penguin_stats.",
        ),
        EvalCase(
            "sales_totals",
            "sales",
            totals_query,
            (sales,),
            _interpretation(
                totals,
                ("North revenue is $12,000 from 40 orders.", "region_totals"),
                ("South revenue is $6,000 from 20 orders.", "region_totals"),
            ),
            "approved",
            "Both regional revenue totals and order counts are correct.",
        ),
        EvalCase(
            "sales_multiple_results",
            "sales",
            "Report regional revenue totals and the overall mean order value.",
            (sales, order_stats),
            _interpretation(
                "Regional totals and average order value describe different measures.",
                (totals, "region_totals"),
                ("Overall mean order value is $300.", "order_stats"),
            ),
            "approved",
            "Each finding cites the result that supports it.",
        ),
        EvalCase(
            "sales_unrelated_reference",
            "sales",
            totals_query,
            (sales, order_stats),
            _interpretation(
                totals,
                (totals, "order_stats"),
            ),
            "revise",
            "Order statistics do not show regional totals; cite region_totals.",
        ),
        EvalCase(
            "sales_unsupported_causality",
            "sales",
            totals_query,
            (sales,),
            _interpretation(
                totals,
                (totals, "region_totals"),
                (
                    "Moving a store to North will cause its revenue to rise.",
                    "region_totals",
                ),
            ),
            "revise",
            "Keep the revenue totals, but remove the causal claim.",
        ),
        EvalCase(
            "traffic_counts",
            "traffic",
            channel_query,
            (traffic,),
            _interpretation(
                "Among attributed sessions, organic is the most common channel.",
                (
                    "There are 36 organic sessions and 24 paid sessions.",
                    "channel_counts",
                ),
                limitations=(attribution,),
            ),
            "approved",
            "The counts are correct, and missing channels are acknowledged.",
        ),
        EvalCase(
            "traffic_proportions",
            "traffic",
            channel_query,
            (shares,),
            _interpretation(
                "Organic is the most common recorded channel.",
                (
                    "Among 60 attributed sessions, 60% are organic and 40% paid.",
                    "channel_shares",
                ),
                limitations=(attribution,),
            ),
            "approved",
            "The percentages use recorded channels, and missing values are acknowledged.",
        ),
        EvalCase(
            "traffic_wrong_denominator",
            "traffic",
            channel_query,
            (shares,),
            _interpretation(
                "Organic accounts for 60% of all 100 sessions.",
                ("60% of all sessions are organic.", "channel_shares"),
            ),
            "revise",
            "The 60% share applies to 60 sessions with recorded channels, not all 100.",
        ),
        EvalCase(
            "traffic_ignored_warning",
            "traffic",
            channel_query,
            (traffic,),
            _interpretation(
                "The channel analysis has no important data-quality limitations.",
                (
                    "There are 36 organic sessions and 24 paid sessions.",
                    "channel_counts",
                ),
            ),
            "revise",
            "Mention the warning: 40 sessions have no recorded channel.",
        ),
    )
