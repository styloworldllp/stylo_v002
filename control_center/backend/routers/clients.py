# ─────────────────────────────────────────────────────────────────────────────
# control_center/backend/routers/clients.py
#
# CRUD endpoints for client records (the organisations that purchase sites).
# All routes require a valid JWT (Depends(get_current_user)).
#
# Endpoints:
#   GET    /api/clients      — list all clients
#   POST   /api/clients      — create a new client (name + email required)
#   PUT    /api/clients/{id} — update any client field
#   DELETE /api/clients/{id} — delete client record
#
# Note: there is no cascade guard on delete — in production you should
# check for associated sites before allowing deletion.
# ─────────────────────────────────────────────────────────────────────────────
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import Client

router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientCreate(BaseModel):
    name: str
    email: str
    company: str = ""
    phone: str = ""


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None


@router.get("")
async def list_clients(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Client))
    return result.scalars().all()


@router.post("", status_code=201)
async def create_client(body: ClientCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    client = Client(**body.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return {"id": client.id, "name": client.name, "email": client.email}


@router.put("/{client_id}")
async def update_client(client_id: int, body: ClientUpdate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(client, field, value)

    await db.commit()
    return {"ok": True}


@router.delete("/{client_id}")
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    await db.delete(client)
    await db.commit()
    return {"ok": True}
