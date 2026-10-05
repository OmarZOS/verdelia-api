# test_runner/__main__.py
"""CLI entry point for the test runner.

Run with:

    python -m test_runner --profile smoke
    python -m test_runner --profile standard --url http://localhost:9000
    python -m test_runner --profile stress --skip-boundary

The profile controls how much data is generated. See
`test_runner/context.py` for the profile definitions.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from context import PROFILES
from test_runner import TestRunner


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="test_runner",
        description=(
            "Verdelia API test runner. Generates users, organisations, "
            "suppliers, products, services, and staff rules against a "
            "running backend."
        ),
    )
    parser.add_argument(
        "--url",
        default="http://localhost:9000",
        help="Base URL of the API under test (default: %(default)s)",
    )
    parser.add_argument(
        "--profile",
        choices=list(PROFILES.keys()),
        default="standard",
        help="Volume profile: how much data to generate (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-users",
        action="store_true",
        help="Reuse users from the context file instead of creating new ones",
    )
    parser.add_argument(
        "--skip-login",
        action="store_true",
        help="Skip the login step — only useful when tokens are already valid",
    )
    parser.add_argument(
        "--skip-subscriptions",
        action="store_true",
        help="Skip the plan catalogue and subscription scenarios",
    )
    parser.add_argument(
        "--skip-boundary",
        action="store_true",
        help="Skip the metering boundary probes (they are slow on paid tiers)",
    )
    parser.add_argument(
        "--context-file",
        default="test_context.json",
        help="Path to the persisted test state (default: %(default)s)",
    )
    parser.add_argument(
        "--clear-context",
        action="store_true",
        help="Delete the context file before starting",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    """Execute the runner. Returns a process exit code."""
    if args.clear_context:
        path = Path(args.context_file)
        if path.exists():
            path.unlink()
            print(f"🗑️ Cleared context file: {args.context_file}")
        else:
            print(f"ℹ️ No context file to clear at {args.context_file}")

    profile = PROFILES[args.profile]

    async with TestRunner(args.url) as runner:
        await runner.run(
            profile=profile,
            skip_users=args.skip_users,
            skip_login=args.skip_login,
            skip_subscriptions=args.skip_subscriptions,
            skip_boundary=args.skip_boundary,
            context_file=args.context_file,
        )

    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        return asyncio.run(_run(args))
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())