from unittest.mock import patch

import pytest

from rag.main import main


@pytest.mark.parametrize(
    "args,host",
    [([], "127.0.0.1"), (["expose=false"], "127.0.0.1"), (["expose=true"], "0.0.0.0")],
)
def test_listen_address(args, host):
    with patch("sys.argv", ["rag", *args]), patch("rag.main.uvicorn.run") as run:
        main()
    assert run.call_args.kwargs["host"] == host
    assert run.call_args.kwargs["port"] == 8123


def test_invalid_expose_does_not_start_server():
    with patch("sys.argv", ["rag", "expose=yes"]), patch("rag.main.uvicorn.run") as run:
        with pytest.raises(SystemExit) as error:
            main()
    assert error.value.code == 2
    run.assert_not_called()
