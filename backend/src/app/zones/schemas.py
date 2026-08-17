from sqlmodel import SQLModel


class ZoneRead(SQLModel):
    id: int
    name: str
