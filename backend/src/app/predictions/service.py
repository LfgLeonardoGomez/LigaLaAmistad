"""The season prediction: first and second place of each zone."""

import datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.models import utc_now
from app.predictions.models import (
    POINTS_FIRST,
    POINTS_SECOND,
    Prediction,
    PredictionWindow,
)
from app.predictions.schemas import (
    PollResults,
    PollState,
    PredictionIn,
    TeamResult,
    ZonePick,
    ZoneResult,
)
from app.teams.models import Team


def current_window(session: Session) -> PredictionWindow | None:
    """The newest poll, open or not. There is no poll at all before the first."""
    return session.exec(
        select(PredictionWindow).order_by(PredictionWindow.id.desc())
    ).first()


def _as_utc(moment: datetime.datetime) -> datetime.datetime:
    """SQLite hands back naive datetimes; Postgres does not. Compare in UTC."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=datetime.UTC)
    return moment


def is_open(window: PredictionWindow | None) -> bool:
    if window is None:
        return False
    now = utc_now()
    return _as_utc(window.opens_at) <= now < _as_utc(window.closes_at)


def open_poll(session: Session, days: int) -> PredictionWindow:
    """Start a new poll running from now."""
    now = utc_now()
    window = PredictionWindow(opens_at=now, closes_at=now + datetime.timedelta(days=days))
    session.add(window)
    session.commit()
    session.refresh(window)
    return window


def close_poll(session: Session) -> PredictionWindow:
    """End the running poll now, which is what reveals the results."""
    window = current_window(session)
    if window is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No poll to close"
        )

    window.closes_at = utc_now()
    session.add(window)
    session.commit()
    session.refresh(window)
    return window


def _picks_of(session: Session, window: PredictionWindow, voter_key: str | None) -> list[ZonePick]:
    if not voter_key:
        return []

    rows = session.exec(
        select(Prediction)
        .where(Prediction.window_id == window.id, Prediction.voter_key == voter_key)
        .order_by(Prediction.zone_id)
    ).all()

    return [
        ZonePick(
            zone_id=row.zone_id,
            first_team_id=row.first_team_id,
            second_team_id=row.second_team_id,
        )
        for row in rows
    ]


def state(session: Session, voter_key: str | None = None) -> PollState:
    window = current_window(session)
    if window is None:
        return PollState(open=False)

    picks = _picks_of(session, window, voter_key)
    return PollState(
        open=is_open(window),
        opens_at=window.opens_at,
        closes_at=window.closes_at,
        voted=len(picks) > 0,
        zones=picks,
    )


def _validate(session: Session, pick: ZonePick) -> None:
    if pick.first_team_id == pick.second_team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First and second place must be different pairs",
        )

    for team_id in (pick.first_team_id, pick.second_team_id):
        team = session.get(Team, team_id)
        if team is None or team.zone_id != pick.zone_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That pair does not play in this zone",
            )


def submit(session: Session, data: PredictionIn) -> PollState:
    window = current_window(session)
    if not is_open(window):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The poll is not open"
        )

    # Every zone is checked before anything is written, so a ballot with one
    # bad pick does not land half saved.
    for pick in data.zones:
        _validate(session, pick)

    for pick in data.zones:
        existing = session.exec(
            select(Prediction).where(
                Prediction.window_id == window.id,
                Prediction.zone_id == pick.zone_id,
                Prediction.voter_key == data.voter_key,
            )
        ).first()

        if existing is None:
            session.add(
                Prediction(
                    window_id=window.id,
                    zone_id=pick.zone_id,
                    voter_key=data.voter_key,
                    first_team_id=pick.first_team_id,
                    second_team_id=pick.second_team_id,
                )
            )
        else:
            existing.first_team_id = pick.first_team_id
            existing.second_team_id = pick.second_team_id
            session.add(existing)

    session.commit()
    return state(session, data.voter_key)


def results(session: Session) -> PollResults:
    """The counts, once nobody can vote on them any more.

    Kept behind the closing date on purpose: a running total published while
    the poll is open makes people vote for whoever is already winning, and
    then the poll measures itself instead of their opinion.
    """
    window = current_window(session)
    if window is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No poll yet")

    if is_open(window):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Results are revealed when voting closes",
        )

    rows = session.exec(
        select(Prediction).where(Prediction.window_id == window.id)
    ).all()

    tally: dict[int, dict[int, TeamResult]] = {}
    for row in rows:
        zone = tally.setdefault(row.zone_id, {})
        for team_id, is_first in ((row.first_team_id, True), (row.second_team_id, False)):
            entry = zone.setdefault(
                team_id, TeamResult(team_id=team_id, first_votes=0, second_votes=0, points=0)
            )
            if is_first:
                entry.first_votes += 1
                entry.points += POINTS_FIRST
            else:
                entry.second_votes += 1
                entry.points += POINTS_SECOND

    zones = [
        ZoneResult(
            zone_id=zone_id,
            teams=sorted(
                teams.values(),
                # Points first, then who was picked to win most often: two pairs
                # on equal points are not equally backed if one has more firsts.
                key=lambda team: (-team.points, -team.first_votes, team.team_id),
            ),
        )
        for zone_id, teams in sorted(tally.items())
    ]

    return PollResults(
        closes_at=window.closes_at,
        voters=len({row.voter_key for row in rows}),
        zones=zones,
    )
