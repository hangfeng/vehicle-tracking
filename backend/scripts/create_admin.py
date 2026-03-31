"""
创建初始集团管理员账号。
用法：docker compose exec backend python scripts/create_admin.py
"""
import asyncio
import uuid
from app.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.auth import hash_password
from sqlalchemy import select


PHONE = "13900000000"
PASSWORD = "admin123456"
NAME = "集团管理员"


async def main():
    async with AsyncSessionLocal() as db:
        existing = await db.execute(select(User).where(User.phone == PHONE))
        if existing.scalar_one_or_none():
            print(f"账号 {PHONE} 已存在，无需重复创建")
            return
        user = User(
            id=uuid.uuid4(),
            factory_id=None,
            name=NAME,
            phone=PHONE,
            password_hash=hash_password(PASSWORD),
            role=UserRole.group_admin,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        print(f"✓ 创建成功")
        print(f"  手机号：{PHONE}")
        print(f"  密  码：{PASSWORD}")
        print(f"  角  色：集团管理员")


if __name__ == "__main__":
    asyncio.run(main())
