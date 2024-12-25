from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Float, String, Boolean, Integer, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional
import requests

ORCHESTRATOR_URL = "http://localhost:8001"  # URL du service d'orchestration


# Initialisation de la base de données
DATABASE_URL = "sqlite:///./load_balancer.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèle SQLAlchemy pour les ressources PC
class PCResources(Base):
    __tablename__ = "pcs"
    pc_id = Column(String, primary_key=True, index=True)
    cpu_usage = Column(Float)
    ram_usage = Column(Float)
    status = Column(Boolean)  # True pour "active", False pour "inactive"

# Modèle SQLAlchemy pour l'allocation de VM
class VMAllocation(Base):
    __tablename__ = "allocations"
    vm_id = Column(String, primary_key=True, index=True)
    pc_id = Column(String)

class AllocationIndex(Base):
    __tablename__ = "allocation_index"
    id = Column(Integer, primary_key=True)
    index = Column(Integer, default=0)


# Création des tables
Base.metadata.create_all(bind=engine)

# Modèle Pydantic pour les ressources PC
class PCResourcesBase(BaseModel):
    pc_id: str
    cpu_usage: Optional[float] = None
    ram_usage: Optional[float] = None
    status: Optional[bool] = None

    class Config:
        orm_mode = True

# Créer les tables
# Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dépendance pour la session DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Route pour ajouter un PC
@app.post("/pcs/")
async def add_pc(pc: PCResourcesBase, db: Session = Depends(get_db)):
    if db.query(PCResources).filter(PCResources.pc_id == pc.pc_id).first():
        raise HTTPException(status_code=400, detail="PC with this ID already exists.")
    db_pc = PCResources(**pc.dict())
    db.add(db_pc)
    db.commit()
    return {"message": "PC added successfully"}

# Route pour supprimer un PC
@app.delete("/pcs/{pc_id}")
async def remove_pc(pc_id: str, db: Session = Depends(get_db)):
    db_pc = db.query(PCResources).filter(PCResources.pc_id == pc_id).first()
    if not db_pc:
        raise HTTPException(status_code=404, detail="PC not found")
    db.delete(db_pc)
    db.commit()
    return {"message": "PC removed successfully"}

# Route pour mettre à jour le statut d'un PC
@app.put("/pcs/{pc_id}")
async def update_pc_status(pc_id: str, updated_pc: PCResourcesBase, db: Session = Depends(get_db)):
    db_pc = db.query(PCResources).filter(PCResources.pc_id == pc_id).first()
    if not db_pc:
        raise HTTPException(status_code=404, detail="PC not found")
    db_pc.cpu_usage = updated_pc.cpu_usage
    db_pc.ram_usage = updated_pc.ram_usage
    db_pc.status = updated_pc.status
    db.commit()
    return {"message": "PC updated successfully"}

# Route pour allouer une VM
""" @app.post("/allocate_vm/")
async def allocate_vm(vm_id: str, db: Session = Depends(get_db)):
    active_pcs = db.query(PCResources).filter(PCResources.status == True).all()
    if not active_pcs:
        raise HTTPException(status_code=400, detail="No active PCs available for allocation.")
    best_pc = min(active_pcs, key=lambda pc: pc.cpu_usage + pc.ram_usage)
    allocation = VMAllocation(vm_id=vm_id, pc_id=best_pc.pc_id)
    db.add(allocation)
    db.commit()
    return {"message": f"VM {vm_id} allocated to PC {best_pc.pc_id}"} """
@app.post("/allocate_vm/")
async def allocate_vm(vm_id: str, algorithm: str = "weighted", db: Session = Depends(get_db)):
    active_pcs = db.query(PCResources).filter(PCResources.status == True).all()
    if not active_pcs:
        raise HTTPException(status_code=400, detail="No active PCs available for allocation.")
    
    # Choix du PC selon l'algorithme
    if algorithm == "round_robin":
        best_pc = round_robin_allocate(active_pcs, db)
    elif algorithm == "least_connection":
        best_pc = least_connection_allocate(active_pcs, db)
    elif algorithm == "weighted":
        best_pc = weighted_allocation(active_pcs)
    else:
        raise HTTPException(status_code=400, detail="Invalid load balancing algorithm.")
    
    # Créer une allocation
    allocation = VMAllocation(vm_id=vm_id, pc_id=best_pc.pc_id)
    db.add(allocation)
    db.commit()
    
    # Notification à l'orchestrateur
    try:
        requests.post(f"{ORCHESTRATOR_URL}/notify", json={
            "pc_id": best_pc.pc_id,
            "vm_id": vm_id,
            "message": f"VM {vm_id} allocated to PC {best_pc.pc_id}"
        })
    except requests.exceptions.RequestException as e:
        print(f"Failed to notify orchestrator: {e}")
    
    return {"message": f"VM {vm_id} allocated to PC {best_pc.pc_id}"}


""" @app.post("/command/{client_id}")
async def send_command(client_id: str, command: str):
    try:
        await manager.send_message(client_id, f"Command: {command}")
        return {"message": f"Command sent to client {client_id}"}
    except HTTPException as e:
        raise HTTPException(status_code=500, detail=f"Failed to send command: {str(e)}") """



""" @app.post("/pcs/", response_model=PCResourcesBaseBase)
def create_pc(pc: PCResourcesBaseBase):
    # Code pour sauvegarder les données dans la base
    # Exemple fictif pour la réponse
    return pc """

def round_robin_allocate(active_pcs, db):
    allocation_index = db.query(AllocationIndex).first()
    if not allocation_index:
        allocation_index = AllocationIndex(index=0)
        db.add(allocation_index)
        db.commit()

    best_pc = active_pcs[allocation_index.index % len(active_pcs)]
    allocation_index.index = (allocation_index.index + 1) % len(active_pcs)
    db.commit()
    return best_pc

def least_connection_allocate(active_pcs, db):
    pcs_load = {
        pc.pc_id: db.query(VMAllocation).filter(VMAllocation.pc_id == pc.pc_id).count()
        for pc in active_pcs
    }
    best_pc_id = min(pcs_load, key=pcs_load.get)
    return next(pc for pc in active_pcs if pc.pc_id == best_pc_id)

def weighted_allocation(active_pcs):
    def resource_score(pc):
        cpu_weight = 0.7
        ram_weight = 0.3
        return cpu_weight * pc.cpu_usage + ram_weight * pc.ram_usage

    return min(active_pcs, key=resource_score)
