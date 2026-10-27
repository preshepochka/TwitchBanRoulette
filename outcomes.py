import logging

from bot import TwitchError
from config_schema import (Action, BanAction, MessageAction, NothingAction,
                           PollAction, RerollAction, TimeoutAction,
                           VipAddAction, VipRemoveAction)

log = logging.getLogger(__name__)


def apply(bot, action: Action, user_id: str, user_name: str) -> bool:
    """Apply an outcome action to a viewer. Returns True on success.

    Network errors are logged instead of raised so that one failed
    request doesn't kill the main loop mid-stream.
    RerollAction is a control-flow action handled by App; here it is
    a no-op that counts as success (redemption gets fulfilled).
    """
    try:
        if isinstance(action, TimeoutAction):
            bot.timeout_user(user_id, action.duration)
        elif isinstance(action, BanAction):
            bot.ban_user(user_id)
        elif isinstance(action, MessageAction):
            bot.send_chat_message(action.text.replace("{user}", user_name))
        elif isinstance(action, PollAction):
            bot.create_poll(action.title, list(action.choices), action.duration)
        elif isinstance(action, VipAddAction):
            bot.add_vip(user_id)
        elif isinstance(action, VipRemoveAction):
            bot.remove_vip(user_id)
        elif isinstance(action, (NothingAction, RerollAction)):
            pass
        else:
            log.error("unknown action type: %r", action.type)
            return False
    except TwitchError as e:
        log.error("action %r failed for user %s: %s", action.type, user_id, e)
        return False
    return True
