import requests
import datetime


def LastTickRaw():
    url = "http://tick.infomancer.uk/galtick.json"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()['lastGalaxyTick']
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def LastTickReadable():
    raw_tick = LastTickRaw()
    if raw_tick is not None:
        try:
            readable_format = datetime.datetime.strptime(
                raw_tick, "%Y-%m-%dT%H:%M:%S.%fZ"
            ).strftime('%a %d %b at %H:%M')
            return (readable_format)
        except (ValueError, TypeError) as e:
            print(f"Error converting timestamp: {e}")
    return '<Unknown>'


if __name__ == "__main__":
    print(LastTickRaw())
    print(LastTickReadable())
