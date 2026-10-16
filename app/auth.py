import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

# Reuse the Keycloak issuer URL exposed to the browser. FastAPI publishes this
# as an OAuth2 password flow, so Swagger's Authorize dialog obtains the token
# from Keycloak and attaches it to protected requests automatically.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=(
        f"{settings.keycloak_issuer.rstrip('/')}/"
        "protocol/openid-connect/token"
    ),
    auto_error=False,
)


@dataclass(frozen=True)
class Principal:
    subject: str
    username: str
    roles: frozenset[str]


_cached_keys: list[dict[str, Any]] = []
_jwks_expiry = 0.0


async def get_current_principal(
    token: str | None = Depends(oauth2_scheme),
) -> Principal:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        global _cached_keys, _jwks_expiry
        if time.monotonic() >= _jwks_expiry:
            async with httpx.AsyncClient(timeout=3.0) as client:
                signing_key = await client.get(settings.keycloak_jwks_url)
            signing_key.raise_for_status()
            _cached_keys = signing_key.json()["keys"]
            _jwks_expiry = time.monotonic() + 300
        header = jwt.get_unverified_header(token)
        key_data = next(key for key in _cached_keys if key["kid"] == header["kid"])
        key = jwt.PyJWK.from_dict(key_data).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=settings.keycloak_issuer,
            options={"verify_aud": False},
        )
    except (
        httpx.HTTPError,
        KeyError,
        StopIteration,
        jwt.PyJWTError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    realm_access = claims.get("realm_access", {})
    roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    subject = claims.get("sub")
    if not subject or claims.get("azp") != settings.keycloak_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    principal = Principal(
        subject=str(subject),
        username=str(claims.get("preferred_username", subject)),
        roles=frozenset(str(role) for role in roles),
    )
    return principal


async def require_admin(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if "products-admin" not in principal.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )
    return principal


async def require_products_user(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not principal.roles.intersection({"products-user", "products-admin"}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado",
        )
    return principal

