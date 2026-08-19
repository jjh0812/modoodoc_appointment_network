from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AppointmentSlot,
    SlotHold,
)


# =========================================================
# 만료된 HOLD가 있으면 해제
#
# 중요:
# 여기서는 commit() 하지 않는다.
#
# 실제 commit은 이 함수를 호출한 API가 담당한다.
# =========================================================

def release_expired_hold(
    slot: AppointmentSlot,
    db: Session,
):

    # -----------------------------------------------------
    # 1. HELD 상태가 아니면 확인할 필요 없음
    # -----------------------------------------------------

    if slot.status != "HELD":
        return False


    # -----------------------------------------------------
    # 2. 현재 슬롯의 ACTIVE HOLD 찾기
    # -----------------------------------------------------

    hold = (
        db.query(SlotHold)
        .filter(
            SlotHold.slot_id == slot.id,
            SlotHold.status == "ACTIVE",
        )
        .first()
    )


    # -----------------------------------------------------
    # 3. ACTIVE HOLD가 없으면 종료
    # -----------------------------------------------------

    if hold is None:
        return False


    # -----------------------------------------------------
    # 4. 현재 UTC 시간
    # -----------------------------------------------------

    now = datetime.utcnow()


    # -----------------------------------------------------
    # 5. 아직 HOLD 시간이 남아 있으면 그대로 유지
    # -----------------------------------------------------

    if hold.expires_at > now:
        return False


    # -----------------------------------------------------
    # 6. 만료 처리
    #
    # ACTIVE → EXPIRED
    # HELD   → AVAILABLE
    # -----------------------------------------------------

    hold.status = "EXPIRED"

    slot.status = "AVAILABLE"


    # -----------------------------------------------------
    # 7. 변경 내용을 PostgreSQL에 전달
    #
    # commit은 아님.
    # 현재 transaction은 계속 유지된다.
    # -----------------------------------------------------

    db.flush()

    return True