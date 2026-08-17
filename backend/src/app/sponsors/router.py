from fastapi import APIRouter, Depends, UploadFile, status

from app.auth.deps import get_current_admin
from app.core.images import upload_image
from app.database.session import SessionDep
from app.sponsors import service
from app.sponsors.schemas import SponsorCreate, SponsorRead, SponsorUpdate

router = APIRouter(
    prefix="/admin/sponsors",
    tags=["admin: sponsors"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=SponsorRead, status_code=status.HTTP_201_CREATED)
def create_sponsor(data: SponsorCreate, session: SessionDep):
    return service.create_sponsor(session, data)


@router.get("", response_model=list[SponsorRead])
def list_sponsors(session: SessionDep):
    return service.list_sponsors(session)


@router.patch("/{sponsor_id}", response_model=SponsorRead)
def update_sponsor(sponsor_id: int, data: SponsorUpdate, session: SessionDep):
    return service.update_sponsor(session, sponsor_id, data)


@router.post("/{sponsor_id}/logo", response_model=SponsorRead)
def upload_sponsor_logo(sponsor_id: int, file: UploadFile, session: SessionDep):
    """Upload the sponsor's logo. Not `async`: the Cloudinary call blocks."""
    service.get_sponsor(session, sponsor_id)  # 404 before spending an upload
    return service.set_logo_url(
        session, sponsor_id, upload_image(file, folder="sponsors")
    )


@router.delete("/{sponsor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sponsor(sponsor_id: int, session: SessionDep):
    service.delete_sponsor(session, sponsor_id)
