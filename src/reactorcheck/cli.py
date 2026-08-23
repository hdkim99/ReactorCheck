"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from reactorcheck import __version__
from reactorcheck.io import (
    export_csv_bundle,
    export_excel,
    load_config,
    read_table,
    suggest_mappings,
)
from reactorcheck.plotting import save_result_plot
from reactorcheck.service import analyze_file


def build_parser() -> argparse.ArgumentParser:
    """Create the public CLI parser."""
    parser = argparse.ArgumentParser(prog="reactorcheck", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze = subparsers.add_parser("analyze", help="Analyze reactor CSV/XLSX data")
    analyze.add_argument("data", type=Path)
    analyze.add_argument("--config", "-c", type=Path, required=True)
    analyze.add_argument(
        "--output", "-o", type=Path, required=True, help=".xlsx file or CSV bundle directory"
    )
    analyze.add_argument("--plot", type=Path)
    suggest = subparsers.add_parser("suggest", help="Suggest species mappings for user review")
    suggest.add_argument("data", type=Path)
    suggest.add_argument("--output", "-o", type=Path)
    subparsers.add_parser("gui", help="Launch the desktop GUI")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run CLI and return a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            result = analyze_file(args.data, load_config(args.config))
            if args.output.suffix.lower() == ".xlsx":
                export_excel(result, args.output)
            else:
                export_csv_bundle(result, args.output)
            if args.plot:
                save_result_plot(result, args.plot)
            print(f"Analyzed {len(result.processed)} rows; QC issues: {len(result.qc_issues)}")
            return 0
        if args.command == "suggest":
            text = json.dumps(suggest_mappings(read_table(args.data)), indent=2) + "\n"
            if args.output:
                args.output.write_text(text, encoding="utf-8")
            else:
                print(text, end="")
            return 0
        if args.command == "gui":
            from reactorcheck.gui import main as gui_main

            gui_main()
            return 0
    except (OSError, ValueError) as exc:
        print(f"reactorcheck: error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
