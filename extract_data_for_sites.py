#!/usr/bin/env python3
"""Command-line tool to extract and export data (titles and metadata) for configured or individual archived sites.

This script can operate in two modes:

1. Extract for all configured sites (default):
   - Reads site configuration from config.py
   - Extracts title and metadata from each site's Arquivo.pt archived version
   - Exports results to TSV file

2. Extract for a specific site:
   - Accepts site host and version as arguments
   - Extracts title and metadata for that specific site
   - Displays results and optionally exports to TSV

Usage:
    # Extract all configured sites to data.tsv
    python extract_data_for_sites.py

    # Extract for a specific site (not in config)
    python extract_data_for_sites.py --site example.com --version 20230101120000

    # Extract to custom output file
    python extract_data_for_sites.py --output results.tsv

    # Extract specific site with custom timeout
    python extract_data_for_sites.py --site example.com --version 20230101120000 --timeout 30

    # Specify custom config file
    python extract_data_for_sites.py --config /path/to/config.py --output results.tsv

    # Enable verbose logging
    python extract_data_for_sites.py --verbose
"""

import argparse
import logging
import sys
from pathlib import Path

# Add current directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent))

from data_extractor import (
    export_site_to_tsv,
    export_to_tsv,
    extract_site_metadata,
)


def main():
    """Main entry point for the metadata extraction script."""
    parser = argparse.ArgumentParser(
        description="Extract and export metadata for configured or individual archived sites"
    )

    parser.add_argument(
        "--site",
        "-s",
        help="Extract metadata for a specific site (not in config). Must be used with --version.",
    )

    parser.add_argument(
        "--version",
        help="Version timestamp for the site (e.g., 20200117175504). Required when using --site.",
    )

    parser.add_argument(
        "--output",
        "-o",
        default="data.tsv",
        help="Output TSV file path (default: data.tsv)",
    )

    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=30,
        help="Request timeout in seconds per site (default: 30)",
    )

    parser.add_argument(
        "--wayback-server",
        "-w",
        default="https://arquivo.pt/noFrame/replay/",
        help="Arquivo.pt noFrame server URL (default: https://arquivo.pt/noFrame/replay/)",
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to custom config.py file (default: uses local config.py)",
    )

    parser.add_argument(
        "--verbose",
        "-vv",
        action="store_true",
        help="Enable verbose logging output",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger = logging.getLogger(__name__)

    # Validate arguments
    if args.site and not args.version:
        logger.error("--version is required when using --site")
        print("Error: --version is required when using --site")
        print("Example: python extract_metadata_for_sites.py --site example.com --version 20230101120000")
        sys.exit(1)

    if args.version and not args.site:
        logger.error("--site is required when using --version")
        print("Error: --site is required when using --version")
        sys.exit(1)

    # Handle specific site extraction
    if args.site:
        print(f"Extracting data for: {args.site}")
        print(f"Version: {args.version}")
        print(f"Wayback server: {args.wayback_server}")
        print("-" * 70)

        title, metadata = extract_site_metadata(
            args.site, args.version, args.wayback_server, args.timeout
        )

        # Print results
        print(f"\n✓ Site Title: {title}")
        if metadata:
            print(f"✓ Found {len(metadata)} metadata tag(s):\n")
            for i, tag in enumerate(metadata, 1):
                print(f"  {i}. {tag}")
        else:
            print("✗ No metadata found for this site")

        # Export to TSV if requested
        if args.output:
            results = {args.site: (title, metadata)}
            export_to_tsv(results, args.output)
            print(f"\nData also exported to: {args.output}")

        return 0

    # Import configuration for bulk extraction
    try:
        if args.config:
            # Load custom config file
            spec = __import__("importlib.util").util.spec_from_file_location(
                "config", args.config
            )
            config = __import__("importlib.util").util.module_from_spec(spec)
            spec.loader.exec_module(config)
            archive_config = config.ARCHIVE_CONFIG
        else:
            # Use local config.py
            from config import ARCHIVE_CONFIG

            archive_config = ARCHIVE_CONFIG

        logger.info(
            "Loaded configuration with %d sites", len(archive_config)
        )

    except ImportError as e:
        logger.error("Failed to import config: %s", str(e))
        print("Error: Could not import configuration. Make sure config.py exists.")
        sys.exit(1)

    # Extract metadata for all configured sites
    print(f"Extracting data for {len(archive_config)} sites...")
    print(f"Wayback server: {args.wayback_server}")
    print(f"Timeout per site: {args.timeout} seconds")
    print(f"Output file: {args.output}")
    print(f"Appending to existing file: {Path(args.output).exists()}")
    print()

    # Initialize output file with header if it doesn't exist
    if not Path(args.output).exists():
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write("Site\tTitle\tMetadata\n")
            logger.info("Created new TSV file %s with header", args.output)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error creating TSV file %s: %s", args.output, str(e))
            print(f"Error creating output file: {str(e)}")
            return 1

    # Extract and export each site incrementally
    sites_with_data = 0
    for site, site_config in archive_config.items():
        # Only process sites with a defined version
        if not isinstance(site_config, dict) or "version" not in site_config:
            logger.info("Skipping %s: no version defined", site)
            continue

        version = site_config["version"]
        logger.info("Processing %s (version: %s)", site, version)
        print(f"Processing: {site}...", end=" ", flush=True)

        try:
            # Extract metadata for this site
            title, metadata = extract_site_metadata(
                site, version, args.wayback_server, args.timeout
            )

            # Export immediately to TSV
            export_site_to_tsv(site, title, metadata, args.output)
            print("✓")

            # Count sites with data
            if title or len(metadata) > 0:
                sites_with_data += 1

        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error processing %s: %s", site, str(e))
            print(f"✗ (error: {str(e)})")

    # Summary
    logger.info(
        "Extracted data for %d/%d sites",
        sites_with_data,
        len(archive_config),
    )
    print("\n✓ Extraction complete!")
    print(f"  Sites processed: {sites_with_data}/{len(archive_config)}")
    print(f"  Data saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
