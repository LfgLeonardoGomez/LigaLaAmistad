from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.sponsors.models import Sponsor
from app.sponsors.schemas import SponsorCreate, SponsorUpdate


def create_sponsor(session: Session, data: SponsorCreate) -> Sponsor:
    sponsor = Sponsor(**data.model_dump())
    session.add(sponsor)
    session.commit()
    session.refresh(sponsor)
    return sponsor


def list_sponsors(session: Session, only_active: bool = False) -> list[Sponsor]:
    statement = select(Sponsor).order_by(Sponsor.id)
    if only_active:
        statement = statement.where(Sponsor.is_active == True)  # noqa: E712
    return list(session.exec(statement).all())


def get_sponsor(session: Session, sponsor_id: int) -> Sponsor:
    sponsor = session.get(Sponsor, sponsor_id)
    if sponsor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sponsor not found"
        )
    return sponsor


def set_logo_url(session: Session, sponsor_id: int, logo_url: str) -> Sponsor:
    sponsor = get_sponsor(session, sponsor_id)
    sponsor.logo_url = logo_url
    session.add(sponsor)
    session.commit()
    session.refresh(sponsor)
    return sponsor


def update_sponsor(session: Session, sponsor_id: int, data: SponsorUpdate) -> Sponsor:
    sponsor = get_sponsor(session, sponsor_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sponsor, field, value)
    session.add(sponsor)
    session.commit()
    session.refresh(sponsor)
    return sponsor


def delete_sponsor(session: Session, sponsor_id: int) -> None:
    sponsor = get_sponsor(session, sponsor_id)
    session.delete(sponsor)
    session.commit()
