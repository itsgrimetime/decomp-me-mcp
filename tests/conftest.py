"""Shared fixtures for offline tests.

Every test runs against a mocked decomp.me API. Any request that a test has not
explicitly mocked fails the test, so the suite never touches the network.
"""

import json
from typing import Any, Callable

import httpx
import pytest

from decomp_mcp import server

API = "https://decomp.me/api"

# Synthetic scratch data. Deliberately contains no real game code or assembly.
SCRATCH = {
    "slug": "abc12",
    "name": "example_func",
    "description": "A made-up scratch for tests",
    "platform": "gc_wii",
    "compiler": "mwcc_233_163n",
    "compiler_flags": "-O4,p -nodefaults",
    "language": "C",
    "score": 50,
    "max_score": 200,
    "diff_flags": [],
    "diff_label": "example_func",
    "libraries": [],
    "source_code": "int example_func(void) { return 0; }\n",
    "context": (
        "typedef int s32;\n"
        "typedef struct Foo {\n"
        "    s32 x;\n"
        "    s32 y;\n"
        "} Foo;\n"
        "\n"
        "s32 Foo_GetX(Foo* foo);\n"
    ),
}


class MockAPI:
    """Route table for httpx.MockTransport that records every request."""

    def __init__(self) -> None:
        self.routes: dict[tuple[str, str], Callable[[httpx.Request], httpx.Response]] = {}
        self.requests: list[httpx.Request] = []

    def add(self, method: str, path: str, response: Any = None, status: int = 200, handler=None) -> None:
        """Register a response (JSON body) or a handler for METHOD path."""
        if handler is None:
            handler = lambda request: httpx.Response(status, json=response)
        self.routes[(method, f"{API}{path}")] = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url.copy_with(query=None))
        key = (request.method, url)
        if key not in self.routes:
            pytest.fail(f"Unmocked request: {request.method} {request.url}")
        return self.routes[key](request)

    def sent(self, method: str, path: str) -> list[httpx.Request]:
        """Requests sent to METHOD path."""
        url = f"{API}{path}"
        return [r for r in self.requests if r.method == method and str(r.url.copy_with(query=None)) == url]

    @staticmethod
    def body(request: httpx.Request) -> Any:
        return json.loads(request.content)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Point every state file at a temp dir and clear credentials."""
    monkeypatch.setattr(server, "DECOMP_API_BASE", API)
    monkeypatch.setattr(server, "DECOMP_CLAIMS_FILE", str(tmp_path / "claims.json"))
    monkeypatch.setattr(server, "DECOMP_COMPLETED_FILE", str(tmp_path / "completed.json"))
    monkeypatch.setattr(server, "DECOMP_SCRATCH_TOKENS_FILE", str(tmp_path / "tokens.json"))
    monkeypatch.setattr(server, "DECOMP_COOKIES_FILE", str(tmp_path / "cookies.json"))
    monkeypatch.setattr(server, "DECOMP_CONTEXT_FILE", "")
    monkeypatch.setattr(server, "DECOMP_CLAIM_TIMEOUT", 3600)
    monkeypatch.setattr(server, "CF_CLEARANCE", "")
    return tmp_path


@pytest.fixture(autouse=True)
def api(monkeypatch) -> MockAPI:
    """Mock decomp.me API. Also patches httpx.AsyncClient so call_tool uses it."""
    mock = MockAPI()
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(mock)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(server.httpx, "AsyncClient", client_factory)
    return mock


@pytest.fixture
async def client(api):
    """An httpx client wired to the mock API, for calling handlers directly."""
    async with httpx.AsyncClient() as c:
        yield c


def text(result) -> str:
    """Join the text of a tool result."""
    return "\n".join(item.text for item in result)
