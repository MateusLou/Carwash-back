from sqlalchemy import Column, Integer, String, Boolean, Float
from database.database import Base

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    age = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)
    # 'dono' vê a plataforma inteira; 'funcionario' opera tudo menos o painel
    # de números. Nasce funcionario: privilégio se concede, não se herda.
    role = Column(String(20), nullable=False, server_default="funcionario")
    reset_pwd_token = Column(String(255), nullable=True)
    reset_pwd_token_sent_at = Column(Float, nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email}, is_active={self.is_active})>"
