import logging

from bot import TwitchError
from config_schema import (Action, BanAction, MessageAction, NothingAction,
                           TimeoutAction, VipAddAction, VipRemoveAction)

log = logging.getLogger(__name__)


def apply(bot, action: Action, user_id: str, user_name: str) -> bool:
    """Apply an action to a viewer. Returns True on success.

    Network errors are logged instead of raised so that one failed
    request doesn't kill the main loop mid-stream.
    PollAction, SoundAction and RerollAction are control-flow actions
    handled by App; passing them here is treated as an error.
    """
    try:
        if isinstance(action, TimeoutAction):
            bot.timeout_user(user_id, action.duration)
        elif isinstance(action, BanAction):
            bot.ban_user(user_id)
        elif isinstance(action, MessageAction):
            bot.send_chat_message(action.text.replace("{user}", user_name))
        elif isinstance(action, VipAddAction):
            bot.add_vip(user_id)
        elif isinstance(action, VipRemoveAction):
            bot.remove_vip(user_id)
        elif isinstance(action, NothingAction):
            pass
        else:
            log.error("unknown action type: %r", action.type)
            return False
    except TwitchError as e:
        log.error("action %r failed for user %s: %s", action.type, user_id, e)
        return False
    return True
