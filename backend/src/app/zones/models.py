from sqlmodel import Field, SQLModel


class Zone(SQLModel, table=True):
    """A league zone. Exactly two exist and both are created by seed."""

    __tablename__ = "zones"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, unique=True, index=True)
