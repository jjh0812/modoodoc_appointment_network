from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.database import Base


# =========================================================
# Decision Feedback
#
# DecisionEvent
# = 사용자가 실제로 한 행동
#
# SHOWN
# SELECTED
# HELD
# CONFIRMED
#
#
# DecisionFeedback
# = 사용자가 직접 밝힌 이유
#
# 예:
# "가격이 괜찮아서 선택"
# "시간이 맞지 않아서 선택하지 않음"
# =========================================================

class DecisionFeedback(Base):

    __tablename__ = "decision_feedback"


    # =====================================================
    # Primary Key
    # =====================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )


    # =====================================================
    # 어떤 Patient Intent에 대한 피드백인가
    # =====================================================

    intent_id: Mapped[int] = mapped_column(
        ForeignKey(
            "patient_intents.id"
        ),
        index=True,
        nullable=False,
    )


    # =====================================================
    # 어떤 Candidate에 대한 피드백인가
    #
    # SELECTION_REASON
    # → Candidate 존재
    #
    # NO_SELECTION_REASON
    # → NULL
    # =====================================================

    candidate_match_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "candidate_matches.id"
        ),
        index=True,
        nullable=True,
    )


    # =====================================================
    # Feedback 종류
    #
    # SELECTION_REASON
    # NO_SELECTION_REASON
    # =====================================================

    feedback_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )


    # =====================================================
    # 사용자가 선택한 이유 코드
    #
    # 예:
    #
    # [
    #     "PRICE",
    #     "AVAILABILITY"
    # ]
    # =====================================================

    reason_codes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )


    # =====================================================
    # 기타 직접 입력
    # =====================================================

    free_text: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


    # =====================================================
    # Feedback 유입 채널
    #
    # AI_SIMULATOR
    # WEB
    # MCP
    # =====================================================

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )


    # =====================================================
    # 중복 제출 방지
    #
    # 같은 요청이 retry되어도
    # Feedback은 하나만 생성
    # =====================================================

    idempotency_key: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )


    # =====================================================
    # 생성 시각
    # =====================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
