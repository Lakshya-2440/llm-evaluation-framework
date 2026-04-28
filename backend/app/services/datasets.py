from app.schemas import BenchmarkDataset


BENCHMARKS = [
    BenchmarkDataset(
        id="truthfulqa-lite-v1",
        name="TruthfulQA Lite",
        category="hallucination",
        version="1.0",
        size=12,
        description="Small built-in hallucination baseline inspired by TruthfulQA-style false belief probes.",
    ),
    BenchmarkDataset(
        id="bbq-lite-v1",
        name="BBQ Lite",
        category="bias",
        version="1.0",
        size=12,
        description="Small bias and demographic consistency sample for local smoke tests.",
    ),
    BenchmarkDataset(
        id="harmbench-lite-v1",
        name="HarmBench Lite",
        category="safety",
        version="1.0",
        size=12,
        description="Small safety and jailbreak sample for local smoke tests.",
    ),
]
