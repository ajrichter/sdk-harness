"""CLI entry point for migration harness."""

import argparse
import asyncio
import sys
from pathlib import Path

from migration_harness.orchestrator import Orchestrator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="REST-to-GraphQL migration harness"
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to migration configuration JSON file",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show pipeline status and exit",
    )

    args = parser.parse_args()

    # Verify config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        return 1

    try:
        orchestrator = Orchestrator.from_config_file(str(config_path))

        if args.status:
            # Show status
            status = orchestrator.get_pipeline_status()
            if status:
                print(f"Pipeline status: {status}")
            else:
                print("Pipeline not yet started")
            return 0

        # Run pipeline
        print(f"Starting migration pipeline with config: {args.config}")
        success = asyncio.run(orchestrator.run_pipeline())

        if success:
            print("Pipeline completed successfully!")
            return 0
        else:
            print("Pipeline failed", file=sys.stderr)
            return 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
