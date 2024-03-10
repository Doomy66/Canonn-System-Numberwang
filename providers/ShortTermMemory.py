# For saving registers and other general states between runs
import json

STM = dict()


def LoadSTM(location: str = 'data\STM.json') -> None:
    global STM
    print("Load STM")
    try:
        with open(location, 'r') as io:
            STM = json.load(io)
    except:
        pass


def SaveSTM(location: str = 'data\STM.json') -> None:
    global STM
    print("Save STM")
    with open(location, 'w', encoding='utf-8') as io:
        json.dump(STM, io, indent=4)


# Auto Init
LoadSTM()
