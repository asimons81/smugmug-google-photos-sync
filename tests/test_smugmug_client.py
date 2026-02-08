import json

import pytest

from src.api.smugmug_client import SmugMugClient


def test_normalize_payload_accepts_dict():
    payload = {"Response": {"User": {"Name": "Test"}}}
    assert SmugMugClient._normalize_payload(payload) == payload


def test_normalize_payload_parses_json_string():
    payload = json.dumps({"Response": {"User": {"Name": "Test"}}})
    parsed = SmugMugClient._normalize_payload(payload)
    assert parsed["Response"]["User"]["Name"] == "Test"


def test_normalize_payload_rejects_plain_string():
    payload = "not json"
    with pytest.raises(ValueError):
        SmugMugClient._normalize_payload(payload)
