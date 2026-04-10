import argparse
import sys
from utils import setup_bundle_paths, setup_environment

setup_bundle_paths()
setup_environment()

from gui import main as gui_main  # noqa: E402

def start_api():
    try:
        from api import start_api as run_api
        run_api()
    except ImportError as e:
        print(f"Error: {e}")
        sys.exit(1)

def start_mcp():
    print("Starting GramoVoice MCP Server on Stdio...", file=sys.stderr)
    try:
        from mcp_server import main as mcp_main
        import asyncio
        asyncio.run(mcp_main())
    except ImportError:
        print("Error: mcp package is required for MCP mode.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="GramoVoice Entry Point")
    parser.add_argument("--api", action="store_true", help="Start in API mode")
    parser.add_argument("--mcp", action="store_true", help="Start in MCP mode")
    parser.add_argument("--skip-engine", action="store_true", help="Diagnosis: Skip AI/Audio engines")
    args = parser.parse_args()

    if args.api:
        start_api()
    elif args.mcp:
        start_mcp()
    else:
        gui_main(skip_engine=args.skip_engine)

if __name__ == "__main__":
    main()
