from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

from maxapi import Bot
from maxapi.enums.attachment import AttachmentType
from maxapi.enums.sender_action import SenderAction
from maxapi.types import ButtonsPayload, CallbackButton
from maxapi.types.attachments.attachment import Attachment

ButtonRow = Sequence[CallbackButton]


def build_inline_keyboard(rows: Iterable[ButtonRow]) -> Attachment:
    """
    Convert rows of CallbackButtons to a MAX inline keyboard attachment.
    """

    return Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=ButtonsPayload(buttons=[list(row) for row in rows])
    )


def keyboard_from_pairs(rows: Iterable[Iterable[Tuple[str, str]]]) -> Attachment:
    """
    Helper that accepts plain (text, payload) tuples and returns an attachment.
    """

    return build_inline_keyboard(
        [
            [CallbackButton(text=text, payload=payload) for text, payload in row]
            for row in rows
        ]
    )


async def send_typing(bot: Bot, chat_id: int | None) -> None:
    """
    Fire MAX typing indicator if chat_id is known.
    """

    if chat_id is None:
        return

    await bot.send_action(chat_id=chat_id, action=SenderAction.TYPING_ON)
