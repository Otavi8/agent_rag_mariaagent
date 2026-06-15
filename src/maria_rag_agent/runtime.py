from __future__ import annotations

import os
import warnings
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _read_quiet_mode_flag() -> bool:
    env_path = PROJECT_ROOT / ".env"
    env_values = dotenv_values(env_path) if env_path.exists() else {}
    raw_value = os.getenv("QUIET_MODE", env_values.get("QUIET_MODE", "true"))
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def configure_runtime() -> bool:
    quiet_mode = _read_quiet_mode_flag()
    if not quiet_mode:
        return False

    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    warnings.filterwarnings(
        "ignore",
        message=r".*allowed_objects.*",
    )
    warnings.filterwarnings(
        "ignore",
        message=r".*default value of `allowed_objects` will change.*",
    )

    try:
        from langchain_core._api.deprecation import LangChainPendingDeprecationWarning

        warnings.filterwarnings(
            "ignore",
            category=LangChainPendingDeprecationWarning,
        )
    except Exception:
        pass

    try:
        from huggingface_hub.utils import logging as hf_logging

        hf_logging.set_verbosity_error()
    except Exception:
        pass

    try:
        from transformers.utils import logging as transformers_logging

        transformers_logging.set_verbosity_error()
        transformers_logging.disable_progress_bar()
    except Exception:
        pass

    return True
