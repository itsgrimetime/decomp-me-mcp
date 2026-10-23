"""Tests for the local claim and completion tracking tools (no API calls)."""

import json
import time

from decomp_mcp import server

from .conftest import text


async def test_claim_then_list_then_release():
    result = await server.handle_claim_function({"function_name": "fn_a", "agent_id": "agent-1"})
    assert "Claimed:** `fn_a`" in text(result)

    result = await server.handle_list_claims({})
    assert "**fn_a** - claimed by `agent-1`" in text(result)

    result = await server.handle_release_function({"function_name": "fn_a"})
    assert "Released:** `fn_a`" in text(result)

    result = await server.handle_list_claims({})
    assert "No functions are currently claimed" in text(result)


async def test_claim_conflict():
    await server.handle_claim_function({"function_name": "fn_a", "agent_id": "agent-1"})

    result = await server.handle_claim_function({"function_name": "fn_a", "agent_id": "agent-2"})

    assert "Claim Failed" in text(result)
    assert "agent-1" in text(result)


async def test_stale_claims_expire(isolated_state):
    stale = {"fn_old": {"agent_id": "agent-1", "timestamp": time.time() - 7200}}
    (isolated_state / "claims.json").write_text(json.dumps(stale))

    result = await server.handle_claim_function({"function_name": "fn_old", "agent_id": "agent-2"})

    assert "Claimed:** `fn_old`" in text(result)


async def test_release_unclaimed():
    result = await server.handle_release_function({"function_name": "fn_a"})
    assert "was not claimed" in text(result)

    await server.handle_claim_function({"function_name": "fn_b"})
    result = await server.handle_release_function({"function_name": "fn_a"})
    assert "was not claimed" in text(result)


async def test_complete_releases_claim_and_blocks_new_claims(isolated_state):
    await server.handle_claim_function({"function_name": "fn_a", "agent_id": "agent-1"})

    result = await server.handle_complete_function({
        "function_name": "fn_a",
        "match_percent": 97.5,
        "scratch_slug": "abc12",
        "notes": "register diffs only",
    })

    out = text(result)
    assert "**Match:** 97.5%" in out
    assert "**Notes:** register diffs only" in out
    assert "fn_a" not in json.loads((isolated_state / "claims.json").read_text())

    result = await server.handle_claim_function({"function_name": "fn_a", "agent_id": "agent-2"})
    assert "already completed" in text(result)
    assert "97.5%" in text(result)


async def test_list_completed_sorted_and_filtered():
    await server.handle_complete_function({"function_name": "fn_low", "match_percent": 40.0, "scratch_slug": "s1"})
    await server.handle_complete_function({"function_name": "fn_high", "match_percent": 100.0, "scratch_slug": "s2", "committed": True})
    await server.handle_complete_function({"function_name": "fn_mid", "match_percent": 80.0, "scratch_slug": "s3"})

    out = text(await server.handle_list_completed({}))
    assert "# Completed Functions (3 total)" in out
    assert out.index("fn_high") < out.index("fn_mid") < out.index("fn_low")
    assert "✅ **fn_high**" in out

    out = text(await server.handle_list_completed({"min_match": 75}))
    assert "(2 total)" in out
    assert "fn_low" not in out

    out = text(await server.handle_list_completed({"min_match": 101}))
    assert "No functions with ≥101% match found" in out


async def test_list_completed_empty():
    result = await server.handle_list_completed({})
    assert "No functions have been completed yet" in text(result)


async def test_coordination_tools_via_call_tool():
    result = await server.call_tool("decomp_claim_function", {"function_name": "fn_a"})
    assert "Claimed:** `fn_a`" in text(result)

    result = await server.call_tool("decomp_list_claims", {})
    assert "**fn_a**" in text(result)
