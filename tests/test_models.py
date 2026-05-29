"""Tests for Polymarket model parsing (pure, no HA, no network)."""

from custom_components.polymarket.models import (
    Portfolio,
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


RAW_POSITION = {
    "title": "Will the U.S. invade Iran before 2027?",
    "outcome": "No",
    "size": 225642.18,
    "avgPrice": 0.6721,
    "curPrice": 0.825,
    "currentValue": 186154.79,
    "cashPnl": 34495.49,
    "percentPnl": 22.74,
    "slug": "will-the-us-invade-iran-before-2027",
    "endDate": "2026-12-31",
}


def test_parse_position_extracts_fields():
    pos = parse_position(RAW_POSITION)
    assert pos.title == "Will the U.S. invade Iran before 2027?"
    assert pos.outcome == "No"
    assert pos.size == 225642.18
    assert pos.cur_price == 0.825
    assert pos.current_value == 186154.79
    assert pos.cash_pnl == 34495.49
    assert pos.percent_pnl == 22.74
    assert pos.slug == "will-the-us-invade-iran-before-2027"


def test_parse_position_tolerates_missing_fields():
    pos = parse_position({"title": "Q"})
    assert pos.title == "Q"
    assert pos.size == 0.0
    assert pos.current_value == 0.0
    assert pos.outcome == ""


def test_parse_portfolio_value_reads_first_entry():
    assert parse_portfolio_value([{"user": "0xabc", "value": 720942.30}]) == 720942.30


def test_parse_portfolio_value_handles_empty():
    assert parse_portfolio_value([]) == 0.0
    assert parse_portfolio_value(None) == 0.0


def _pos(value: float, pnl: float) -> "object":
    return parse_position(
        {"title": "t", "currentValue": value, "cashPnl": pnl, "size": 1}
    )


def test_portfolio_aggregates():
    portfolio = Portfolio(
        wallet="0xabc",
        value=1000.0,
        positions=[_pos(600.0, 50.0), _pos(400.0, -10.0)],
    )
    assert portfolio.position_count == 2
    assert portfolio.total_cash_pnl == 40.0
    assert portfolio.largest_position.current_value == 600.0


def test_portfolio_empty_largest_is_none():
    portfolio = Portfolio(wallet="0xabc", value=0.0, positions=[])
    assert portfolio.largest_position is None
