# Sending to the registered Discord Channel
from classes.Message import Message
import CSNSettings
import pickle
from discord import SyncWebhook


def WriteDiscord(Full: bool, messages: list[Message]) -> None:
    """ Write the messages to Discord Channel either a full report, or just the changes since last time """
    messages = list(filter(lambda _: _.isDiscord, messages))
    # Load Old Messages
    oldmessages: list[Message] = []

    if not Full:
        try:
            CSNSettings.CSNLog.info('Load Saved Messages')
            with open(f'data\\{CSNSettings.myfaction}CSNMessages.pickle', 'rb') as io:
                oldmessages = pickle.load(io)
        except:
            pass

        for message in oldmessages:
            if message in messages:
                # Remove Unchanged Messages
                messages.remove(message)
            elif (message.systemname not in list(x.systemname for x in messages)) and message.isDiscord:
                # Add Old Message as Complete
                message.complete = True
                messages.append(message)

    print(f"Discord Webhook : {'Full' if Full else 'Update'}...")
    if CSNSettings.wh_id and messages:
        webhook_text: str = ''
        webhook_extra: str = ''
        webhook = SyncWebhook.partial(CSNSettings.wh_id, CSNSettings.wh_token)
        message: Message
        for message in messages:
            thistext: str = f"{message.emoji}{message.systemname} : {'~~' if message.complete else ''}{message.text}{'~~ : Mission Complete' if message.complete else ''}\n"
            # Max len for a single hook is 2000 chars. A message can be approx 100 and there is the additional header text.
            if len(webhook_text) < 1850:
                webhook_text += thistext
            else:
                webhook_extra += thistext

        if webhook_text != '':
            print(webhook_text)
            webhook.send(
                f"{'**Full Report**' if Full else 'Latest News'} {CSNSettings.dIcons['csnicon']} \n{webhook_text}")
            CSNSettings.CSNLog.info(f"Discord {len(webhook_text)} chars")

        if webhook_extra != '':
            print(webhook_extra)
            webhook.send(
                f"...continued {CSNSettings.dIcons['csnicon']} \n{webhook_extra}")
            CSNSettings.CSNLog.info(
                f"Discord extra {len(webhook_extra)} chars")
    else:
        CSNSettings.CSNLog.info(f"Discord : Nothing to Report")
        print("...Nothing to Report to Discord")
