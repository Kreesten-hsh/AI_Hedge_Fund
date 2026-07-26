# ADR 0001: Use Python 3.11

## Status
Accepted

## Context
Aegis Quant OS requires a stable, performant, and highly compatible Python environment to integrate data science libraries (pandas, numpy), machine learning frameworks (Qlib, PyTorch), and modern async capabilities.

## Decision
We standardize on **Python 3.11**.

## Rationale
- Python 3.11 offers a significant performance boost (10-60%) over 3.10 due to the Faster CPython project.
- It is fully supported by the scientific ecosystem (OpenBB, Qlib) and modern LLM frameworks.
- Python 3.12/3.13 are too recent and cause breaking changes with older C-extensions commonly found in quantitative finance libraries.

## Consequences
- All environments and CI/CD pipelines must strictly enforce `python_version = "3.11"`.
- Developers must use virtual environments (`.venv`) aligned on this exact minor version.
