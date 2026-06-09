from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from src.config import settings


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    :param data: 要编码到令牌中的数据（必须包含 'sub' 字段）
    :param expires_delta: 可选的自定义过期时间，默认为 settings.ACCESS_TOKEN_EXPIRE_MINUTES
    :return: 编码后的 JWT 字符串
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT 令牌
    :param token: JWT 字符串
    :return: 解码后的 payload 字典
    :raises JWTError: 如果令牌无效或已过期
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise JWTError("Invalid or expired token")
