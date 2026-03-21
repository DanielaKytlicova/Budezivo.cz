"""
Legal/Terms routes for Budeživo.cz
Provides public access to terms of use and legal texts.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from constants.legal_texts import (
    get_current_terms_text,
    get_reservation_checkbox_text,
    get_email_disclaimer,
    CURRENT_TERMS_VERSION
)

router = APIRouter(prefix="/legal", tags=["Legal"])
logger = logging.getLogger(__name__)


# ============ Response Models ============

class TermsArticle(BaseModel):
    number: int
    title: str
    content: str


class TermsResponse(BaseModel):
    title: str
    version: str
    last_updated: str
    articles: List[TermsArticle]


class ReservationTermsResponse(BaseModel):
    version: str
    checkbox_text: str
    email_disclaimer: str


# ============ Public Routes ============

@router.get("/terms", response_model=TermsResponse)
async def get_terms_of_use():
    """
    Get the current Terms of Use document.
    Public endpoint - no auth required.
    """
    terms = get_current_terms_text()
    
    return TermsResponse(
        title=terms["title"],
        version=CURRENT_TERMS_VERSION,
        last_updated=terms["last_updated"],
        articles=[
            TermsArticle(
                number=article["number"],
                title=article["title"],
                content=article["content"].strip()
            )
            for article in terms["articles"]
        ]
    )


@router.get("/reservation-terms", response_model=ReservationTermsResponse)
async def get_reservation_terms():
    """
    Get reservation-related legal texts (checkbox + email disclaimer).
    Public endpoint - used by booking form.
    """
    return ReservationTermsResponse(
        version=CURRENT_TERMS_VERSION,
        checkbox_text=get_reservation_checkbox_text(),
        email_disclaimer=get_email_disclaimer()
    )


@router.get("/terms/version")
async def get_current_version():
    """
    Get just the current version identifier.
    """
    return {"version": CURRENT_TERMS_VERSION}
