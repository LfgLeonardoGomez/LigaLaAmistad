"""History exposes the canonical champion pair, including corrected finals."""

from .americano_fixtures import BASE, americano_api, create_event  # noqa: F401
from .test_americano_knockouts import _closed, _save


def test_history_has_no_champion_for_a_draft(americano_api):
    detail = create_event(americano_api)
    assert detail['champion'] is None
    assert americano_api.client.get(BASE).json()[0]['champion'] is None


def test_history_follows_the_winner_and_corrected_winner(americano_api):
    bracket = _closed(americano_api)
    response = _save(americano_api, bracket, score=(6, 0))
    assert response.status_code == 200, response.text
    finished = response.json()
    first = finished['champion']
    history = americano_api.client.get(BASE).json()
    assert history[0]['champion'] == first
    assert history[0]['state'] == 'completed'
    response = _save(americano_api, finished, score=(0, 6))
    assert response.status_code == 200, response.text
    corrected = response.json()
    assert corrected['champion']['id'] != first['id']
    assert americano_api.client.get(BASE).json()[0]['champion'] == corrected['champion']
