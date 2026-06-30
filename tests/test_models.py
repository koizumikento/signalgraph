from __future__ import annotations

import pytest
from pydantic import ValidationError

from helpers import make_signal


def test_trend_signal_accepts_absolute_http_url() -> None:
    signal = make_signal(url="https://example.com/signal")

    assert signal.source_url == "https://example.com/signal"


def test_trend_signal_rejects_non_url_source() -> None:
    with pytest.raises(ValidationError, match="source_url must be an absolute"):
        make_signal(url="not-a-url")


def test_trend_signal_rejects_non_http_url() -> None:
    with pytest.raises(ValidationError, match="source_url must be an absolute"):
        make_signal(url="ftp://example.com/signal")
