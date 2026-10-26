from pydantic import BaseModel, Field


class Credentials(BaseModel):
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    authenticated: bool
    username: str


class RegistrationResponse(BaseModel):
    registered: bool
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
