import pytest
from pydantic import ValidationError

from rag.config import Settings


def test_retry_delays_parse_from_environment_shape() -> None:
    settings = Settings(rabbitmq_retry_delays="2,4,8")
    assert settings.rabbitmq_retry_delays == (2, 4, 8)


def test_exactly_three_retry_delays_are_required() -> None:
    with pytest.raises(ValidationError):
        Settings(rabbitmq_retry_delays="1,2")
