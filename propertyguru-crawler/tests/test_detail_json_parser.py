from __future__ import annotations

import json
from pathlib import Path

from crawler.parsers.detail_json_parser import DetailJsonParser


def _load_sample_next_data() -> dict:
    sample_path = Path(__file__).resolve().parents[1] / "docs" / "detail_data.json"
    with sample_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def test_build_property_details_from_sample():
    parser = DetailJsonParser(_load_sample_next_data())
    details = parser.build_property_details()

    assert details is not None
    assert details.listing_id == 60046991
    assert details.property_details["home-open-o"] == "Condominium for sale"
    assert "Partially" in details.property_details["furnished-o"]
    assert details.description_title.startswith("Rare new top")
    assert "Rare Integrated" in (details.description or "")
    assert details.amenities is not None and len(details.amenities) >= 5
    assert details.facilities is not None and len(details.facilities) > 5


def test_parse_media_urls_includes_photos_and_floorplan():
    parser = DetailJsonParser(_load_sample_next_data())
    media_urls = parser.parse_media_urls()

    assert media_urls, "media urls should not be empty"
    assert media_urls[0][0] == "image"
    assert media_urls[0][1].startswith("https://sg1-cdn.pgimgs.com/listing/60046991")
    assert any("UFLOO" in url for _, url in media_urls), "floor plan image should be included"


def test_parse_all_returns_full_payload():
    parser = DetailJsonParser(_load_sample_next_data())
    payload = parser.parse_all()

    assert payload["property_details"] is not None
    assert payload["property_details"].listing_id == 60046991
    assert len(payload["amenities"]) >= 5
    assert len(payload["facilities"]) >= 10
    assert payload["media_urls"], "media urls should be present"
