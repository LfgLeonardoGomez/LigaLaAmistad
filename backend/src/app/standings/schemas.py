from sqlmodel import SQLModel


class StandingRead(SQLModel):
    position: int
    team_id: int
    played: int
    won: int
    lost: int
    points: int
    sets_won: int
    sets_lost: int
    sets_diff: int
    games_won: int
    games_lost: int
    games_diff: int
    points_average: float
