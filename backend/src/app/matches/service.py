from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.matches.models import Match, MatchSet, MatchStatus
from app.matches.schemas import MatchCreate, MatchRead, MatchResultIn, MatchUpdate, SetRead
from app.teams.models import Team

MIN_SETS = 2
MAX_SETS = 3
SETS_TO_WIN_MATCH = 2


def _bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _load_team(session: Session, team_id: int, label: str) -> Team:
    team = session.get(Team, team_id)
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{label} {team_id} not found",
        )
    return team


def _validate_pairing(session: Session, team_a_id: int, team_b_id: int) -> None:
    """A match is between two different teams of the same zone.

    The zone is not stored: it is this validation that makes it derivable.
    """
    if team_a_id == team_b_id:
        raise _bad_request("A match needs two different teams")

    team_a = _load_team(session, team_a_id, "Team A")
    team_b = _load_team(session, team_b_id, "Team B")

    if team_a.zone_id != team_b.zone_id:
        raise _bad_request("Both teams must belong to the same zone")


def create_match(session: Session, data: MatchCreate) -> Match:
    _validate_pairing(session, data.team_a_id, data.team_b_id)

    match = Match(**data.model_dump())
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def list_matches(
    session: Session,
    match_status: MatchStatus | None = None,
    zone_id: int | None = None,
) -> list[Match]:
    statement = select(Match).order_by(Match.date, Match.id)
    if match_status is not None:
        statement = statement.where(Match.status == match_status)
    if zone_id is not None:
        # Both teams share a zone, so joining on team A is enough.
        statement = statement.join(Team, Match.team_a_id == Team.id).where(
            Team.zone_id == zone_id
        )
    return list(session.exec(statement).all())


def get_match(session: Session, match_id: int) -> Match:
    match = session.get(Match, match_id)
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Match not found"
        )
    return match


def update_match(session: Session, match_id: int, data: MatchUpdate) -> Match:
    match = get_match(session, match_id)
    if match.status is not MatchStatus.PENDING:
        raise _bad_request("Only a pending match can be edited. Undo its result first")

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(match, field, value)

    if "team_a_id" in changes or "team_b_id" in changes:
        _validate_pairing(session, match.team_a_id, match.team_b_id)

    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def delete_match(session: Session, match_id: int) -> None:
    match = get_match(session, match_id)
    if match.status is not MatchStatus.PENDING:
        raise _bad_request("Only a pending match can be deleted. Undo its result first")
    session.delete(match)
    session.commit()


# --- Results ------------------------------------------------------------------


def get_sets(session: Session, match_id: int) -> list[MatchSet]:
    return list(
        session.exec(
            select(MatchSet)
            .where(MatchSet.match_id == match_id)
            .order_by(MatchSet.set_number)
        ).all()
    )


def _validate_sets(data: MatchResultIn) -> None:
    sets = data.sets

    if not MIN_SETS <= len(sets) <= MAX_SETS:
        raise _bad_request(f"A result needs {MIN_SETS} or {MAX_SETS} sets")

    numbers = [s.set_number for s in sets]
    if numbers != list(range(1, len(sets) + 1)):
        raise _bad_request("Set numbers must be consecutive starting at 1")

    wins_a = 0
    wins_b = 0
    for played_set in sets:
        if played_set.team_a_games == played_set.team_b_games:
            raise _bad_request(f"Set {played_set.set_number} cannot end in a tie")
        if played_set.team_a_games > played_set.team_b_games:
            wins_a += 1
        else:
            wins_b += 1

    if SETS_TO_WIN_MATCH not in (wins_a, wins_b):
        raise _bad_request("Exactly one team must win two sets")


def _write_sets(session: Session, match: Match, data: MatchResultIn) -> None:
    for played_set in data.sets:
        session.add(MatchSet(match_id=match.id, **played_set.model_dump()))


def _clear_sets(session: Session, match_id: int) -> None:
    for existing in get_sets(session, match_id):
        session.delete(existing)


def require_played(session: Session, match_id: int, action: str) -> Match:
    """The match, or 404/400. The photo and the comment decorate a result.

    Public because the photo endpoint calls it to fail before paying for an
    upload that would then be attached to nothing.
    """
    match = get_match(session, match_id)
    if match.status is not MatchStatus.PLAYED:
        raise _bad_request(f"Load the result before {action}")
    return match


def set_result(session: Session, match_id: int, data: MatchResultIn) -> Match:
    """Load the result of a pending match. The match becomes `played`."""
    match = get_match(session, match_id)
    if match.status is not MatchStatus.PENDING:
        raise _bad_request("This match already has a result. Use PUT to replace it")

    _validate_sets(data)
    _write_sets(session, match, data)
    match.status = MatchStatus.PLAYED
    match.comment = data.comment
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def replace_result(session: Session, match_id: int, data: MatchResultIn) -> Match:
    """Replace the result of a played match. It stays `played`.

    Only the sets are replaced. The photo and the comment belong to the match,
    not to the marker, so fixing a wrong score does not throw them away — a
    `comment` absent from the body keeps the stored one, and sending one
    replaces it.
    """
    match = get_match(session, match_id)
    if match.status is not MatchStatus.PLAYED:
        raise _bad_request("This match has no result to replace. Use POST to load one")

    _validate_sets(data)
    _clear_sets(session, match_id)
    session.flush()
    _write_sets(session, match, data)
    if "comment" in data.model_fields_set:
        match.comment = data.comment
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def set_comment(session: Session, match_id: int, comment: str | None) -> Match:
    """Edit only the comment. `null` erases it and leaves the result intact."""
    match = require_played(session, match_id, "commenting on it")
    match.comment = comment
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def set_photo_url(session: Session, match_id: int, photo_url: str) -> Match:
    match = require_played(session, match_id, "adding a photo")
    match.photo_url = photo_url
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def delete_result(session: Session, match_id: int) -> Match:
    """Undo the result. The match goes back to `pending`.

    The photo and the comment go with it. A pending match can have its date and
    even its teams corrected, so keeping a jab aimed at the losing pair would
    risk showing it over a completely different pairing later on.
    """
    match = get_match(session, match_id)
    if match.status is not MatchStatus.PLAYED:
        raise _bad_request("This match has no result to undo")

    _clear_sets(session, match_id)
    match.status = MatchStatus.PENDING
    match.photo_url = None
    match.comment = None
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


# --- Presentation -------------------------------------------------------------


def winner_team_id(match: Match, sets: list[MatchSet]) -> int | None:
    """The winner is never stored: it is counted from the sets."""
    if match.status is not MatchStatus.PLAYED:
        return None
    wins_a = sum(1 for s in sets if s.team_a_games > s.team_b_games)
    wins_b = sum(1 for s in sets if s.team_b_games > s.team_a_games)
    if wins_a == wins_b:
        return None
    return match.team_a_id if wins_a > wins_b else match.team_b_id


def to_read(session: Session, match: Match) -> MatchRead:
    sets = get_sets(session, match.id)
    return MatchRead(
        id=match.id,
        team_a_id=match.team_a_id,
        team_b_id=match.team_b_id,
        date=match.date,
        status=match.status,
        sets=[SetRead.model_validate(s, from_attributes=True) for s in sets],
        winner_team_id=winner_team_id(match, sets),
        photo_url=match.photo_url,
        comment=match.comment,
    )
