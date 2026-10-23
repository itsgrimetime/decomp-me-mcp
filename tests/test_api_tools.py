"""Tests for tools that call the decomp.me API, using mocked responses."""

import json

import httpx

from decomp_mcp import server

from .conftest import SCRATCH, MockAPI, text


async def test_get_scratch(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)

    result = await server.handle_get_scratch(client, {"url_or_slug": "https://decomp.me/scratch/abc12"})

    assert "# Scratch: example_func (abc12)" in text(result)
    assert len(api.sent("GET", "/scratch/abc12")) == 1


async def test_compile_uses_scratch_settings_and_override_source(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)
    api.add("POST", "/scratch/abc12/compile", {
        "success": True,
        "diff_output": {"current_score": 0, "max_score": 200, "rows": []},
    })

    result = await server.handle_compile(client, {"url_or_slug": "abc12", "source_code": "int f(void) { return 1; }"})

    assert "PERFECT MATCH" in text(result)
    payload = MockAPI.body(api.sent("POST", "/scratch/abc12/compile")[0])
    assert payload["compiler"] == SCRATCH["compiler"]
    assert payload["compiler_flags"] == SCRATCH["compiler_flags"]
    assert payload["source_code"] == "int f(void) { return 1; }"
    assert payload["include_objects"] is False


async def test_compile_defaults_to_scratch_source(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)
    api.add("POST", "/scratch/abc12/compile", {"diff_output": {"current_score": 50, "max_score": 200}})

    result = await server.handle_compile(client, {"url_or_slug": "abc12"})

    assert "75.0%" in text(result)
    payload = MockAPI.body(api.sent("POST", "/scratch/abc12/compile")[0])
    assert payload["source_code"] == SCRATCH["source_code"]


async def test_compile_failure_shows_compiler_output(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)
    api.add("POST", "/scratch/abc12/compile", {"success": False, "compiler_output": "error: expected ';'"})

    result = await server.handle_compile(client, {"url_or_slug": "abc12"})

    assert "Compilation Failed" in text(result)
    assert "error: expected ';'" in text(result)


async def test_get_compilers_for_platform(api, client):
    api.add("GET", "/compiler/gc_wii", {"gc_wii": [{"id": "mwcc_233_163n", "flags": "-O4"}, "plain_id"]})

    result = await server.handle_get_compilers(client, {"platform": "gc_wii"})

    out = text(result)
    assert "## gc_wii" in out
    assert "**mwcc_233_163n**" in out
    assert "Flags: `-O4`" in out
    assert "- plain_id" in out


async def test_get_compilers_all(api, client):
    api.add("GET", "/compiler", {"n64": [{"id": "gcc"}]})

    result = await server.handle_get_compilers(client, {})

    assert "## n64" in text(result)


def search_results() -> list[dict]:
    def scratch(slug, score, updated):
        return {"type": "scratch", "item": {
            "slug": slug, "name": f"func_{slug}", "platform": "gc_wii", "compiler": "mwcc_233_163n",
            "score": score, "max_score": 100, "last_updated": updated,
            "owner": {"username": "someone", "is_anonymous": False},
        }}

    return [
        scratch("done1", 0, "2024-01-03"),
        scratch("half1", 50, "2024-01-01"),
        scratch("near1", 10, "2024-01-02"),
        {"type": "preset", "item": {"id": 7, "name": "Example Preset", "platform": "gc_wii",
                                    "compiler": "mwcc_233_163n", "num_scratches": 3}},
        {"type": "user", "item": {"username": "someone"}},
    ]


async def test_search_sends_query_params(api, client):
    api.add("GET", "/search", [])

    result = await server.handle_search(client, {"query": "item", "platform": "gc_wii"})

    params = api.sent("GET", "/search")[0].url.params
    assert params["search"] == "item"
    assert params["platform"] == "gc_wii"
    assert "No results found" in text(result)


async def test_search_filters_and_sorts(api, client):
    api.add("GET", "/search", search_results())

    result = await server.handle_search(client, {
        "only_incomplete": True,
        "min_match_percent": 40,
        "sort_by": "match_percent",
    })

    out = text(result)
    assert "# Presets (1 found)" in out
    assert "**Preset ID:** 7" in out
    assert "# Scratches (2 found, incomplete only, ≥40% match)" in out
    assert "done1" not in out
    assert out.index("near1") < out.index("half1")
    assert "**Owner:** someone" in out


async def test_search_max_match_and_limit(api, client):
    api.add("GET", "/search", search_results())

    result = await server.handle_search(client, {"max_match_percent": 95, "sort_by": "last_updated", "limit": 1})

    out = text(result)
    assert "near1" in out
    assert "half1" not in out
    assert "done1" not in out


async def test_search_context_finds_matches_with_line_numbers(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)

    result = await server.handle_search_context(client, {"url_or_slug": "abc12", "pattern": "struct foo", "context_lines": 1})

    out = text(result)
    assert "## Match 1 (line 2)" in out
    assert ">>>     2: typedef struct Foo {" in out
    assert "        1: typedef int s32;" in out


async def test_search_context_max_results(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)

    result = await server.handle_search_context(client, {"url_or_slug": "abc12", "pattern": "s32", "max_results": 2})

    out = text(result)
    assert "## Match 2" in out
    assert "## Match 3" not in out


async def test_search_context_no_matches(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)

    result = await server.handle_search_context(client, {"url_or_slug": "abc12", "pattern": "NotThere"})

    assert "No matches found" in text(result)


async def test_search_context_invalid_regex(api, client):
    api.add("GET", "/scratch/abc12", SCRATCH)

    result = await server.handle_search_context(client, {"url_or_slug": "abc12", "pattern": "("})

    assert "Invalid regex pattern" in text(result)


async def test_search_context_empty_context(api, client):
    api.add("GET", "/scratch/abc12", {**SCRATCH, "context": ""})

    result = await server.handle_search_context(client, {"url_or_slug": "abc12", "pattern": "x"})

    assert "No context found" in text(result)


async def test_update_scratch(api, client):
    api.add("PATCH", "/scratch/abc12", {"score": 20, "max_score": 200})

    result = await server.handle_update_scratch(client, {"url_or_slug": "abc12", "source_code": "int f;"})

    out = text(result)
    assert "# Scratch Updated" in out
    assert "https://decomp.me/scratch/abc12" in out
    assert "90.0%" in out
    assert MockAPI.body(api.sent("PATCH", "/scratch/abc12")[0]) == {"source_code": "int f;"}


async def test_update_scratch_forbidden(api, client):
    api.add("PATCH", "/scratch/abc12", {"detail": "forbidden"}, status=403)

    result = await server.handle_update_scratch(client, {"url_or_slug": "abc12", "source_code": "int f;"})

    assert "403 Forbidden" in text(result)
    assert "decomp_create_scratch" in text(result)


async def test_create_scratch_claims_and_saves_token(api, client, isolated_state):
    api.add("GET", "/scratch/TnPVM", {**SCRATCH, "context": "/* reference context */"})
    api.add("POST", "/scratch", {"slug": "new01", "claim_token": "tok123"})
    api.add("POST", "/scratch/new01/claim", {"success": True})

    result = await server.handle_create_scratch(client, {"name": "example_func", "target_asm": "placeholder"})

    out = text(result)
    assert "**Slug:** new01" in out
    assert "Owned by you" in out
    payload = MockAPI.body(api.sent("POST", "/scratch")[0])
    assert payload["context"] == "/* reference context */"
    assert payload["diff_label"] == "example_func"
    assert MockAPI.body(api.sent("POST", "/scratch/new01/claim")[0]) == {"token": "tok123"}
    tokens = json.loads((isolated_state / "tokens.json").read_text())
    assert tokens == {"new01": "tok123"}


async def test_create_scratch_reads_local_context_file(api, client, isolated_state, monkeypatch):
    ctx_file = isolated_state / "ctx.c"
    ctx_file.write_text("/* local context */")
    monkeypatch.setattr(server, "DECOMP_CONTEXT_FILE", str(ctx_file))
    api.add("POST", "/scratch", {"slug": "new01"})

    result = await server.handle_create_scratch(client, {"name": "example_func", "target_asm": "placeholder"})

    assert MockAPI.body(api.sent("POST", "/scratch")[0])["context"] == "/* local context */"
    assert api.sent("GET", "/scratch/TnPVM") == []
    assert "Not claimed" in text(result)


async def test_create_scratch_uses_explicit_context(api, client):
    api.add("POST", "/scratch", {"slug": "new01"})

    await server.handle_create_scratch(client, {"name": "f", "target_asm": "placeholder", "context": "/* given */"})

    assert MockAPI.body(api.sent("POST", "/scratch")[0])["context"] == "/* given */"
    assert api.sent("GET", "/scratch/TnPVM") == []


async def test_response_cookies_are_persisted(api, client, isolated_state):
    api.add("GET", "/scratch/abc12", handler=lambda request: httpx.Response(
        200, json=SCRATCH, headers={"Set-Cookie": "sessionid=s3cret; Path=/"}))

    await server.handle_get_scratch(client, {"url_or_slug": "abc12"})

    assert json.loads((isolated_state / "cookies.json").read_text()) == {"sessionid": "s3cret"}
    assert server.get_client_cookies() == {"sessionid": "s3cret"}


async def test_cf_clearance_added_to_cookies(monkeypatch):
    monkeypatch.setattr(server, "CF_CLEARANCE", "cf-value")

    assert server.get_client_cookies() == {"cf_clearance": "cf-value"}


async def test_call_tool_dispatches(api):
    api.add("GET", "/scratch/abc12", SCRATCH)

    result = await server.call_tool("decomp_get_scratch", {"url_or_slug": "abc12"})

    assert "# Scratch: example_func (abc12)" in text(result)


async def test_call_tool_reports_http_errors(api):
    api.add("GET", "/scratch/missing", {"detail": "Not found."}, status=404)

    result = await server.call_tool("decomp_get_scratch", {"url_or_slug": "missing"})

    assert text(result).startswith("Error:")
    assert "404" in text(result)


async def test_call_tool_unknown_tool():
    result = await server.call_tool("decomp_nope", {})

    assert "Unknown tool: decomp_nope" in text(result)


async def test_list_tools_names():
    tools = await server.list_tools()

    names = {tool.name for tool in tools}
    assert len(names) == len(tools) == 12
    assert {"decomp_get_scratch", "decomp_compile", "decomp_claim_function", "decomp_list_completed"} <= names
