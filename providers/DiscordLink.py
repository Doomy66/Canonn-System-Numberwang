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
            with open(f'data\\{CSNSettings.FACTION}CSNMessages.pickle', 'rb') as io:
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
    if CSNSettings.WEBHOOK_ID and messages:
        webhook_text: str = ''
        webhook_sentmain: bool = False
        webhook = SyncWebhook.partial(
            CSNSettings.WEBHOOK_ID, CSNSettings.WEBHOOK_TOKEN)
        message: Message
        for message in messages:
            thistext: str = f"{message.emoji}{message.systemname+' : ' if message.systemname else ''}{'~~' if message.complete else ''}{message.text}{'~~ : Mission Complete' if message.complete else ''}\n"
            # Max len for a single hook is 2000 chars. A message can be approx 100 and there is the additional header text.
            if len(webhook_text) < 1850:
                webhook_text += thistext
            else:
                SendMessage(webhook_text, webhook_sentmain)
                webhook_sentmain = True
                webhook_text = thistext

        if webhook_text != '':
            SendMessage(webhook_text, webhook_sentmain)

    else:
        CSNSettings.CSNLog.info(f"Discord : Nothing to Report")
        print("...Nothing to Report to Discord")

    def SendMessage(message: str, isextra: bool) -> None:
        """ Send a message to the Discord Channel """

        print(message)
        if isextra:
            webhook.send(
                f"...continued {CSNSettings.ICONS['csnicon']} \n{message}")
            CSNSettings.CSNLog.info(
                f"Discord extra {len(message)} chars")
        else:
            webhook.send(
                f"{'**Full Report**' if Full else 'Latest News'} {CSNSettings.ICONS['csnicon']} \n{message}")
            CSNSettings.CSNLog.info(f"Discord {len(message)} chars")
