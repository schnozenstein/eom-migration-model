"""Run the bilateral Eurostat-flow gravity benchmark and EOM incremental test."""
from __future__ import annotations
import argparse
import json
from eom_empirical.bilateral_gravity import run

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2010)
    parser.add_argument("--end-year", type=int, default=2024)
    args = parser.parse_args()
    result = run(args.start_year, args.end_year)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()
