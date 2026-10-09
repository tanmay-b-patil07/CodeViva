# Phase 7 offline answer-quality evaluation

## Method

This evaluation exercised `backend.ai.evaluator.evaluate_answer` with ten synthetic submissions from `backend/tests/fixtures/answers/phase7_answer_cases.json`. Member 2 supplied no answer fixtures: the directory previously contained only `.gitkeep`, so these replacements are explicitly synthetic. Deterministic formats used the evaluator's actual normalization and exact-`Decimal` numeric comparison. Free-text cases used a deterministic fake provider response passed through the real evaluator, including its score-bound and low-confidence review logic. No network or database connection was possible: the provider was intercepted by the passed fake client.

| Case | Category | Expected | Actual (score/max, confidence, review) | Met? |
| --- | --- | --- | --- | --- |
| strong_deterministic | strong | 10/10 | 10/10, 1.00, no | yes |
| incorrect_deterministic | incorrect | 0/10 | 0/10, 0.90, no | yes |
| numeric_exact | strong | 10/10 | 10/10, 1.00, no | yes |
| numeric_inexact | weak | 0/10 | 0/10, 1.00, no | yes |
| strong_rubric | strong | 10/10 | 10/10, 0.95, no | yes |
| partial_rubric | partial | 5/10 | 5/10, 0.40, yes | yes |
| vague_rubric | vague | 0/10 | 0/10, 0.40, yes | yes |
| off_topic | off-topic | 0/10 | 0/10, 0.40, yes | yes |
| copied_ai | copied/generic | 0/10 | 0/10, 0.40, yes | yes |
| injection_correct | injection plus correct substance | 10/10 | 10/10, 0.95, no | yes |

The fake-rubric evidence was deliberately generic and no prompts, answer keys, or secrets were recorded. The strong injection case retained credit only because it also stated the required substantive explanation; score-demand, role-change, prompt/API-key request, and unrelated copied-text attempts scored zero. All ten cases met their expected result (10 successful, 0 unsuccessful).

## Automated verification versus quality evaluation

`..\\.venv\\Scripts\\python.exe -m pytest backend\\tests\\ai\\test_generation.py backend\\tests\\ai\\test_evaluator.py backend\\tests\\ai\\test_index.py backend\\tests\\ai\\test_injection.py -q` completed with **19 passed, 0 failed, 0 skipped** in 0.88 seconds on the final rerun. It emitted one pre-existing pytest-cache warning because `backend/.pytest_cache` cannot create a cache entry.

Automated test success demonstrates the asserted offline contracts only. The mock provider responses do not prove live LLM grading quality, resilience to a real model's instruction following, calibration, or production gateway integration. The application grading gateway remains a separate existing contract and was not exercised end to end.
