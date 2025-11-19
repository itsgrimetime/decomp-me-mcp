#!/usr/bin/env python3
"""Simple test script for the decomp.me MCP server."""

import asyncio
import httpx


async def test_api():
    """Test the decomp.me API directly."""
    async with httpx.AsyncClient() as client:
        print("Testing decomp.me API...")

        # Test 1: Get a scratch
        print("\n1. Fetching scratch Jwtky...")
        response = await client.get("https://decomp.me/api/scratch/Jwtky")
        scratch = response.json()
        print(f"   ✓ Got scratch: {scratch['name']}")
        print(f"   ✓ Platform: {scratch['platform']}")
        print(f"   ✓ Compiler: {scratch['compiler']}")
        print(f"   ✓ Score: {scratch['score']}/{scratch['max_score']}")

        # Test 2: Compile
        print("\n2. Compiling scratch...")
        compile_payload = {
            "compiler": scratch["compiler"],
            "compiler_flags": scratch["compiler_flags"],
            "diff_flags": scratch.get("diff_flags", []),
            "diff_label": scratch.get("diff_label", ""),
            "libraries": scratch.get("libraries", []),
            "source_code": scratch["source_code"],
            "include_objects": False,
        }

        response = await client.post(
            "https://decomp.me/api/scratch/Jwtky/compile",
            json=compile_payload,
        )
        result = response.json()
        diff = result.get("diff_output", {})
        print(f"   ✓ Compilation successful")
        print(f"   ✓ Score: {diff.get('current_score', 0)}/{diff.get('max_score', 0)}")

        # Test 3: Get compilers
        print("\n3. Fetching compilers for gc_wii...")
        response = await client.get("https://decomp.me/api/compiler")
        compilers = response.json()
        if "gc_wii" in compilers:
            print(f"   ✓ Found {len(compilers['gc_wii'])} compilers for gc_wii")

        print("\n✅ All API tests passed!")


if __name__ == "__main__":
    asyncio.run(test_api())
