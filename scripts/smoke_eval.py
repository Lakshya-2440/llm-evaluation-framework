from sdk.python.llmeval_client import LlmEvalClient


client = LlmEvalClient()
run = client.start_eval(
    {
        "categories": ["hallucination", "safety"],
        "attacks_per_category": 2,
        "rounds": 2,
        "use_mart": True,
        "success_threshold": 6,
    }
)
print("run_id", run["id"])
print(client.wait(run["id"]))
