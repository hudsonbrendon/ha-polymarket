"""Tests for Polymarket model parsing (pure, no HA, no network)."""

from custom_components.polymarket.models import (
    parse_market,
    parse_portfolio_value,
    parse_position,
)

RAW_MARKET = {
    "id": "1919425",
    "question": "US x Iran permanent peace deal by May 31, 2026?",
    "slug": "us-x-iran-permanent-peace-deal",
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.125", "0.875"]',
    "clobTokenIds": '["72094", "42918"]',
    "volume": "73718769.31",
    "volume24hr": 6875124.59,
    "liquidity": "899934.12",
    "bestBid": 0.12,
    "bestAsk": 0.13,
    "lastTradePrice": 0.13,
    "oneDayPriceChange": 0.01,
    "endDate": "2026-05-31T00:00:00Z",
    "active": True,
    "closed": False,
    "icon": "https://example.com/icon.jpg",
}


def test_parse_market_extracts_core_fields():
    market = parse_market(RAW_MARKET, event_title="US/Iran", event_slug="us-iran")
    assert market.market_id == "1919425"
    assert market.question == "US x Iran permanent peace deal by May 31, 2026?"
    assert market.event_title == "US/Iran"
    assert market.outcomes == ["Yes", "No"]
    assert market.prices == [0.125, 0.875]
    assert market.clob_token_ids == ["72094", "42918"]
    assert market.volume == 73718769.31
    assert market.volume_24hr == 6875124.59
    assert market.liquidity == 899934.12
    assert market.closed is False


def test_parse_market_yes_price_matches_yes_outcome():
    market = parse_market(RAW_MARKET, event_title="x", event_slug="x")
    assert market.yes_price == 0.125
    assert market.yes_token_id == "72094"


def test_parse_market_yes_price_when_yes_is_second():
    raw = {
        **RAW_MARKET,
        "outcomes": '["No", "Yes"]',
        "outcomePrices": '["0.30", "0.70"]',
        "clobTokenIds": '["AAA", "BBB"]',
    }
    market = parse_market(raw, event_title="x", event_slug="x")
    assert market.yes_price == 0.70
    assert market.yes_token_id == "BBB"


def test_parse_market_tolerates_missing_and_malformed_fields():
    market = parse_market(
        {"id": "9", "question": "Q?"}, event_title="x", event_slug="x"
    )
    assert market.market_id == "9"
    assert market.outcomes == []
    assert market.prices == []
    assert market.yes_price is None
    assert market.volume == 0.0
    assert market.clob_token_ids == []
