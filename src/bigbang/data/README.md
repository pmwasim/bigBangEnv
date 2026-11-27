# Vendored data

## `deepset_prompt_injections.jsonl`

- **Source:** [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections) on Hugging Face (train and test splits, 662 rows: 263 injections, 399 benign).
- **License:** Apache-2.0, as declared on the dataset card. Copyright of the original texts remains with their authors and deepset.
- **Fetched:** 2026-11-27 through the Hugging Face dataset-viewer rows API with `scripts/fetch_benchmark.py`; the text is unchanged. Fields: `split`, `index` (row index in that split), `label` (1 = injection), `text`.
- **Use:** the `public_corpus` scenario in `bigbang/evaluation.py`.
