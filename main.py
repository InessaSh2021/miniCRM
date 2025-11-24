from fastapi import FastAPI
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.encoders import jsonable_encoder

from database import SessionLocal, engine
from models import Base, Operator, Source, SourceOperatorConfig, Lead, Contact
from schemas import LeadCreate, ContactResponse

# инициализация базы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lead Routing Service (simplified)")

# зависимость сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/leads/{source_name}/contacts", response_model=ContactResponse)
def create_contact(source_name: str, payload: LeadCreate, db: Session = next(get_db())):

    # 1) найти или создать лид по external_id
    lead = db.query(Lead).filter(Lead.external_id == payload.external_id).first()
    if not lead:
        lead = Lead(external_id=payload.external_id, name=payload.name, email=payload.email, phone=payload.phone)
        db.add(lead)
        db.commit()
        db.refresh(lead)

    # 2) источник
    source = db.query(Source).filter(Source.name == source_name).first()
    if not source:
        source = Source(name=source_name)
        db.add(source)
        db.commit()
        db.refresh(source)

    # 3) выбрать оператора (любой активный с лимитом)
    configs = db.query(SourceOperatorConfig).filter(SourceOperatorConfig.source_id == source.id).all()
    candidate = None
    for cfg in configs:
        op = cfg.operator
        if not op.is_active:
            continue
        current_load = db.query(Contact).filter(Contact.operator_id == op.id).count()
        if current_load < op.max_active_leads:
            candidate = op
            break

    # 4) создать контакт
    contact = Contact(lead_id=lead.id, source_id=source.id, operator_id=candidate.id if candidate else None)
    db.add(contact)
    db.commit()
    db.refresh(contact)

    return ContactResponse(
        contact_id=contact.id,
        lead_id=lead.id,
        operator_id=candidate.id if candidate else None
    )

# эндпоинты для тестирования
@app.get("/operators")
def list_operators(db: Session = next(get_db())):
    return [{"id": o.id, "name": o.name, "active": o.is_active} for o in db.query(Operator).all()]

@app.get("/leads")
def list_leads(db: Session = next(get_db())):
    return [{"id": l.id, "external_id": l.external_id, "name": l.name} for l in db.query(Lead).all()]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)