"""
Run the AutoRAG fair comparison experiment.

Resolves all machine-specific paths at runtime so that the YAML config
stays clean and portable. No hardcoded usernames or absolute paths needed.

Usage:
    python run_autorag_comparison.py
"""

import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent.resolve()
CONFIG_TEMPLATE = HERE / "hotpotqa_autoragsearch_metric.yaml"
PROJECT_DIR = HERE / "autorag_fair_result_v2"
QA_DATA = HERE / "data" / "my_hotpotqa_subset_autorag" / "qa_validation.parquet"
CORPUS_DATA = HERE / "data" / "my_hotpotqa_subset_autorag" / "corpus.parquet"

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


def find_model_snapshot() -> str:
    """Locate the cached model snapshot, falling back to the model ID.

    Discovers the snapshot hash dynamically so this works on any machine
    regardless of which version was cached locally.
    """
    try:
        from huggingface_hub.constants import HF_HUB_CACHE
        snapshots_dir = (
            Path(HF_HUB_CACHE)
            / "models--sentence-transformers--all-MiniLM-L6-v2"
            / "snapshots"
        )
        if snapshots_dir.exists():
            snapshots = [p for p in snapshots_dir.iterdir() if p.is_dir()]
            if snapshots:
                # Use the most recently modified snapshot
                return str(max(snapshots, key=lambda p: p.stat().st_mtime))
    except Exception:
        pass
    return MODEL_ID


def main():
    model_snapshot = find_model_snapshot()
    chroma_path = str(PROJECT_DIR / "resources" / "chroma")

    os.environ["MODEL_SNAPSHOT"] = model_snapshot
    os.environ["CHROMA_PATH"] = chroma_path
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"

    template = CONFIG_TEMPLATE.read_text(encoding="utf-8")
    resolved = os.path.expandvars(template)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(resolved)
        tmp_path = tmp.name

    try:
        from autorag.evaluator import Evaluator

        evaluator = Evaluator(
            qa_data_path=str(QA_DATA),
            corpus_data_path=str(CORPUS_DATA),
            project_dir=str(PROJECT_DIR),
        )
        evaluator.start_trial(tmp_path)
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
