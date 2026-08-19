from datetime import datetime

from app.database import (
    Base,
    engine,
    SessionLocal,
)

from app.models import (
    Provider,
    AppointmentSlot,
)


# =========================================================
# 1. 실제 DB 테이블 생성
# =========================================================

Base.metadata.create_all(
    bind=engine
)


# =========================================================
# 2. DB 연결
# =========================================================

db = SessionLocal()


try:

    # -----------------------------------------------------
    # 이미 김OO 원장이 있는지 확인
    # -----------------------------------------------------

    provider = (
        db.query(Provider)
        .filter(
            Provider.name == "김OO 원장"
        )
        .first()
    )


    # -----------------------------------------------------
    # 없으면 새로 생성
    # -----------------------------------------------------

    if provider is None:

        provider = Provider(
            name="김OO 원장",
            specialty="안과 / 시력교정",
        )

        db.add(provider)

        db.commit()

        db.refresh(provider)

        print(
            "PROVIDER CREATED:",
            provider.id,
            provider.name,
        )

    else:

        print(
            "PROVIDER ALREADY EXISTS:",
            provider.id,
            provider.name,
        )


    # -----------------------------------------------------
    # 14:20 슬롯이 이미 있는지 확인
    # -----------------------------------------------------

    slot_time = datetime(
        2026,
        8,
        22,
        14,
        20,
    )


    slot = (
        db.query(AppointmentSlot)
        .filter(
            AppointmentSlot.provider_id == provider.id,
            AppointmentSlot.start_time == slot_time,
        )
        .first()
    )


    # -----------------------------------------------------
    # 없으면 AVAILABLE 슬롯 생성
    # -----------------------------------------------------

    if slot is None:

        slot = AppointmentSlot(
            provider_id=provider.id,
            start_time=slot_time,
            status="AVAILABLE",
        )

        db.add(slot)

        db.commit()

        db.refresh(slot)

        print(
            "SLOT CREATED:",
            slot.id,
            slot.start_time,
            slot.status,
        )

    else:

        print(
            "SLOT ALREADY EXISTS:",
            slot.id,
            slot.start_time,
            slot.status,
        )


finally:

    db.close()