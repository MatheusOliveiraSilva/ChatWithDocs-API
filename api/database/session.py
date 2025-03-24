from api.database.models import SessionLocal

def get_db():
    """
    Dependency que fornece uma sessão do banco de dados.
    Deve ser usada com Depends() do FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 