# job_server/auth_backend.py
from abc import ABC, abstractmethod

class AuthBackend(ABC):
    @abstractmethod
    def authenticate_user(self, username: str, password: str) -> bool:
        pass
