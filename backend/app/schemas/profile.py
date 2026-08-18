from __future__ import annotations

from pydantic import BaseModel, Field


class ErfahrungItem(BaseModel):
    firma: str = ""
    position: str = ""
    zeitraum: str = ""
    beschreibung: str = ""


class AusbildungItem(BaseModel):
    institution: str = ""
    abschluss: str = ""
    zeitraum: str = ""


class SpracheItem(BaseModel):
    sprache: str = ""
    niveau: str = ""


class ProfileOut(BaseModel):
    name: str
    adresse: str
    telefon: str
    email: str
    wunschjobtitel: list[str]
    wunschort: str
    umkreis_km: int
    arbeitszeit: str
    berufserfahrung: list[ErfahrungItem]
    ausbildung: list[AusbildungItem]
    skills: list[str]
    sprachen: list[SpracheItem]
    zertifikate: list[str]
    cover_letter_hinweise: str
    match_threshold: int
    auto_send_enabled: bool

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    name: str = ""
    adresse: str = ""
    telefon: str = ""
    email: str = ""
    wunschjobtitel: list[str] = Field(default_factory=list)
    wunschort: str = ""
    umkreis_km: int = 25
    arbeitszeit: str = "vz"
    berufserfahrung: list[ErfahrungItem] = Field(default_factory=list)
    ausbildung: list[AusbildungItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    sprachen: list[SpracheItem] = Field(default_factory=list)
    zertifikate: list[str] = Field(default_factory=list)
    cover_letter_hinweise: str = ""


class ProfileImportSuggestion(BaseModel):
    name: str = ""
    adresse: str = ""
    telefon: str = ""
    email: str = ""
    wunschjobtitel: list[str] = Field(default_factory=list)
    berufserfahrung: list[ErfahrungItem] = Field(default_factory=list)
    ausbildung: list[AusbildungItem] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    sprachen: list[SpracheItem] = Field(default_factory=list)
    zertifikate: list[str] = Field(default_factory=list)


class AttachmentOut(BaseModel):
    id: int
    filename: str
    content_type: str
    size_bytes: int

    model_config = {"from_attributes": True}
