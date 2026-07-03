from nonebot_plugin_orm import Model
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column


class MsgID(Model):
    __tablename__ = "nonebot_plugin_dcqq_relay_msgid"

    id: Mapped[int] = mapped_column(primary_key=True)
    dcid: Mapped[int] = mapped_column(type_=BigInteger())
    qqid: Mapped[int]
