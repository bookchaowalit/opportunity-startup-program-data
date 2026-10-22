"""Capture the official Google for Startups accelerator page through the shared lake runtime."""

import argparse
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

from .cli import resource, validate
from .observability import init_sentry, report_exit


class Text(HTMLParser):
    """Extract visible page text while ignoring executable content."""

    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def _normalize_generic(raw, source, checked_at):
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    text = " ".join(" ".join(parser.parts).split())
    folded = text.casefold()
    markers = source.get("required_markers") or [source["title"]]
    if not all(marker.casefold() in folded for marker in markers):
        raise ValueError("generic startup-program source drift or challenge page")
    record_id = source["id"]
    item = {
        "id": record_id,
        "title": source["title"],
        "category": source["category"],
        "source_url": source["source_url"],
        "provider": source["provider"],
        "status": source.get("status", "unknown"),
        "deadline": {"kind": source.get("deadline_kind", "unknown"), "at": None},
        "eligible_countries": source.get("eligible_countries", ["GLOBAL"]),
        "eligibility_text": source["eligibility_text"],
        "value": {
            "kind": source.get("value_kind", "in_kind"),
            "amount": source.get("value_amount"),
            "currency": source.get("value_currency"),
            "guaranteed": source.get("value_guaranteed"),
        },
        "cost": {"fee_amount": None, "currency": None, "auto_renewal": None, "notes": source["cost_notes"]},
        "terms": {
            "startup_stage": None,
            "equity_required": None,
            "cohort_start": None,
            "incorporation_required": None,
            **source.get("normalized_terms", {}),
        },
        "related_records": [],
        "provenance": {
            "evidence_kind": "captured",
            "source_id": source["id"],
            "source_record_id": record_id,
            "checked_at": checked_at,
            "raw_object_key": None,
            "bronze_manifest_key": None,
        },
    }
    return {
        "schema_version": source["schema_version"],
        "source": source["product"],
        "retrieved_at": checked_at,
        "data_status": "live",
        "items": [item],
    }


def normalize(raw, source, checked_at):
    """Turn the public program page into a conservative startup-program record."""
    if source.get("generic_html"):
        return _normalize_generic(raw, source, checked_at)
    if source["id"] != "google-startups-accelerator-us":
        raise ValueError("unknown startup program source")
    parser = Text()
    parser.feed(raw.decode("utf-8"))
    text = " ".join(" ".join(parser.parts).split())
    folded = text.casefold()
    required: tuple[str, ...] = (
        "united states",
        "ten-week accelerator program",
        "seed to series a",
        "equity-free support",
        "product credits",
        "commitment from cto",
    )
    if not all(marker.casefold() in folded for marker in required):
        raise ValueError("Google for Startups source drift or challenge page")

    # The public page describes the program and its criteria but does not expose
    # a current application window, so availability stays unknown rather than
    # being promoted to open.
    item = {
        "id": source["id"],
        "title": "Google for Startups Accelerator: United States",
        "category": source["category"],
        "source_url": source["source_url"],
        "provider": source["provider"],
        "status": "unknown",
        "deadline": {"kind": "unknown", "at": None},
        "eligible_countries": ["US"],
        "eligibility_text": (
            "Google describes this as a ten-week hybrid accelerator for technology "
            "startups based in the United States, ideally from Seed to Series A, "
            "with technical participation requirements. Verify the current intake "
            "window and eligibility before applying."
        ),
        "value": {
            "kind": "in_kind",
            "amount": None,
            "currency": None,
            "guaranteed": False,
        },
        "cost": {
            "fee_amount": None,
            "currency": None,
            "auto_renewal": None,
            "notes": (
                "No application fee is stated on the captured page; product credits "
                "and other benefits are subject to eligibility review and approval."
            ),
        },
        "terms": {
            # The page says "ideally from Seed to Series A": a soft range that no
            # single contract stage captures, so the stage is not asserted ("any"
            # would wrongly claim idea-stage startups qualify).
            "startup_stage": None,
            "equity_required": False,
            "cohort_start": None,
            "incorporation_required": None,
        },
        "related_records": [],
        "provenance": {
            "evidence_kind": "captured",
            "source_id": source["id"],
            "source_record_id": source["id"],
            "checked_at": checked_at,
            "raw_object_key": None,
            "bronze_manifest_key": None,
        },
    }
    return {
        "schema_version": source["schema_version"],
        "source": source["product"],
        "retrieved_at": checked_at,
        "data_status": "live",
        "items": [item],
    }


def source_config(source_id=None):
    if source_id is None:
        return resource("source.json")
    if not re.fullmatch(r"[a-z0-9-]+", source_id):
        raise ValueError("invalid source id")
    base = resource("source.json")
    if base["id"] == source_id:
        return base
    try:
        return resource("source-" + source_id + ".json")
    except FileNotFoundError:
        raise ValueError("unknown source id") from None


def main(argv=None):
    selector = argparse.ArgumentParser(add_help=False)
    selector.add_argument("--source-id")
    selected, remaining = selector.parse_known_args(argv)
    root = os.environ.get("SOLO_DATA_LAKE_ROOT")
    if not root:
        print("Set SOLO_DATA_LAKE_ROOT to the local shared capture/lake runtime.", file=sys.stderr)
        return 2
    runtime = Path(root).resolve() / "infra/scripts"
    if not (runtime / "discovery/capture_runtime.py").is_file():
        print("Shared discovery runtime is unavailable.", file=sys.stderr)
        return 2
    sys.path.insert(0, str(runtime))
    from discovery.capture_runtime import VERSION, run

    if VERSION != 1:
        raise RuntimeError("unsupported shared capture runtime")
    source = source_config(selected.source_id)
    sentry = init_sentry(source["id"])
    return report_exit(sentry, source["id"], run(source, normalize, validate, remaining))


if __name__ == "__main__":
    raise SystemExit(main())
