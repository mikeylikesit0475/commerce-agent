import json
from pathlib import Path


def test_eval_cases_file_schema():
    cases_path = Path(__file__).parent.parent / "evals" / "cases.json"
    assert cases_path.exists(), "evals/cases.json must exist"
    
    with open(cases_path) as f:
        cases = json.load(f)
        
    assert len(cases) >= 15, "Eval dataset must contain at least 15 cases"
    for c in cases:
        assert "id" in c
        assert "name" in c
        assert "prompt" in c
        assert "must_contain" in c
        assert isinstance(c["must_contain"], list)
