#!/usr/bin/env python3
"""
Collect successful grant awards from USAspending.gov into the local database.

Run manually or via cron to populate the Winning Grants Library.

Usage:
    python jobs/collect_awards.py
    python jobs/collect_awards.py --agency "National Science Foundation" --state MS
    python jobs/collect_awards.py --quick   # fast run: fewer agencies, lower limits
"""

import argparse
import logging
import sys
import os

# Ensure core/ is on the import path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from awards_library import collect_awards, get_awards_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Target agencies
AGENCIES = [
    "Department of Housing and Urban Development",
    "National Science Foundation",
    "Environmental Protection Agency",
    "Department of Justice",
    "Department of Education",
    "Federal Emergency Management Agency",
    "Department of Energy",
    "Department of Agriculture",
    "Department of Labor",
    "National Institutes of Health",
    "Department of Defense",
    "National Endowment for the Arts",
]

# Focus states: Mississippi + neighbors
FOCUS_STATES = ["MS", "AL", "LA", "TN", "FL", "GA"]


def run_collection(agencies=None, states=None, limit_per_combo=100,
                   min_amount=10000, years_back=3, enrich=True, enrich_max=20):
    """Run the full collection across agencies and states."""
    agencies = agencies or AGENCIES
    states = states or FOCUS_STATES

    total_inserted = 0

    for agency in agencies:
        for state in states:
            logger.info("Collecting: %s / %s", agency, state)
            try:
                inserted = collect_awards(
                    agency=agency,
                    state=state,
                    min_amount=min_amount,
                    years_back=years_back,
                    limit=limit_per_combo,
                    enrich_details=enrich,
                    enrich_max=enrich_max,
                )
                total_inserted += inserted
                logger.info("  -> inserted %d new awards", inserted)
            except Exception as exc:
                logger.error("  -> FAILED: %s", exc)

    # Also collect without state filter for each agency (national awards)
    for agency in agencies:
        logger.info("Collecting national: %s (no state filter)", agency)
        try:
            inserted = collect_awards(
                agency=agency,
                state=None,
                min_amount=min_amount,
                years_back=years_back,
                limit=limit_per_combo,
                enrich_details=enrich,
                enrich_max=enrich_max,
            )
            total_inserted += inserted
            logger.info("  -> inserted %d new awards", inserted)
        except Exception as exc:
            logger.error("  -> FAILED: %s", exc)

    return total_inserted


def main():
    parser = argparse.ArgumentParser(description="Collect grant awards from USAspending.gov")
    parser.add_argument("--agency", help="Single agency name to collect")
    parser.add_argument("--state", help="Single state code (e.g. MS)")
    parser.add_argument("--limit", type=int, default=100, help="Max awards per agency/state combo")
    parser.add_argument("--min-amount", type=int, default=10000, help="Minimum award amount")
    parser.add_argument("--years-back", type=int, default=3, help="How many years back to search")
    parser.add_argument("--no-enrich", action="store_true", help="Skip fetching award details")
    parser.add_argument("--quick", action="store_true", help="Quick run: fewer agencies, lower limits")
    args = parser.parse_args()

    if args.agency:
        # Single agency mode
        agencies = [args.agency]
        states = [args.state] if args.state else FOCUS_STATES
    elif args.quick:
        # Quick mode: top 4 agencies, MS only, limit 50
        agencies = AGENCIES[:4]
        states = ["MS"]
        args.limit = 50
    else:
        agencies = AGENCIES
        states = FOCUS_STATES if not args.state else [args.state]

    logger.info("Starting collection: %d agencies x %d states, limit=%d, min=$%d, years=%d",
                len(agencies), len(states), args.limit, args.min_amount, args.years_back)

    total = run_collection(
        agencies=agencies,
        states=states,
        limit_per_combo=args.limit,
        min_amount=args.min_amount,
        years_back=args.years_back,
        enrich=not args.no_enrich,
    )

    # Print stats
    stats = get_awards_stats()
    logger.info("=" * 60)
    logger.info("Collection complete. %d new awards inserted.", total)
    logger.info("Total awards in DB: %d", stats["total_awards"])
    logger.info("Total award value: $%s", f"{stats['total_amount']:,.0f}")
    logger.info("Average award: $%s", f"{stats['avg_amount']:,.0f}")
    if stats["by_agency"]:
        logger.info("Top agencies:")
        for a in stats["by_agency"][:5]:
            logger.info("  %s: %d awards ($%s)", a["agency"], a["cnt"], f"{a['total']:,.0f}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
