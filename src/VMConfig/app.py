from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Initialisation de la base de données
DATABASE_URL = "sqlite:///./vm_config.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèle de table SQLAlchemy
class VMTemplate(Base):
    __tablename__ = "templates"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    cpu = Column(Integer)
    ram = Column(Integer)
    storage = Column(Integer)

# Création des tables
Base.metadata.create_all(bind=engine)

# Modèle Pydantic
class VMTemplateBase(BaseModel):
    name: str
    cpu: int
    ram: int
    storage: int

    class Config:
        orm_mode = True

class VMTemplateCreate(VMTemplateBase):
    id: str

# Dépendance pour la session DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# Routes
@app.post("/templates/")
async def save_template(template: VMTemplateCreate, db: Session = Depends(get_db)):
    if db.query(VMTemplate).filter(VMTemplate.id == template.id).first():
        raise HTTPException(status_code=400, detail="Template with this ID already exists.")
    db_template = VMTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    return {"message": "Template saved successfully"}

@app.get("/templates/")
async def get_templates(db: Session = Depends(get_db)):
    templates = db.query(VMTemplate).all()
    return {"templates": [template.__dict__ for template in templates]}

@app.put("/templates/{template_id}")
async def update_template(template_id: str, updated_template: VMTemplateBase, db: Session = Depends(get_db)):
    db_template = db.query(VMTemplate).filter(VMTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    db_template.name = updated_template.name
    db_template.cpu = updated_template.cpu
    db_template.ram = updated_template.ram
    db_template.storage = updated_template.storage
    db.commit()
    return {"message": "Template updated successfully"}

@app.delete("/templates/{template_id}")
async def delete_template(template_id: str, db: Session = Depends(get_db)):
    db_template = db.query(VMTemplate).filter(VMTemplate.id == template_id).first()
    if not db_template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(db_template)
    db.commit()
    return {"message": "Template deleted successfully"}
