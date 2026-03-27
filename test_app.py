from datetime import datetime, timedelta, timezone

from arbitrage import scan_opportunities
from tradfi import get_risk_free_rate


def test_get_risk_free_rate():
    for days in [90, 365, 3650]:
        rate = get_risk_free_rate(days)
        assert isinstance(rate, float)
        assert 0 <= rate <= 15


def test_scan_opportunities():
    end_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    mock_events = [
        {
            "id": "1",
            "markets": [
                {
                    "id": "m1",
                    "question": "Will something happen?",
                    "endDate": end_date,
                    "active": True,
                    "closed": False,
                    "outcomes": '["Yes", "No"]',
                    "outcomePrices": '["0.8", "0.2"]',
                    "volumeNum": 1000.0,
                }
            ],
        }
    ]

    opportunities = scan_opportunities(mock_events, threshold=5.0)

    assert len(opportunities) == 1
    opp = opportunities[0]
    assert opp["id"] == "m1"
    assert opp["favorite"] == "Yes"
    assert opp["price"] == 0.8
    assert opp["spread"] > 0
