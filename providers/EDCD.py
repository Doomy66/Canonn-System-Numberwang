import requests
import datetime


def LastTickRaw():
    url = "https://tick.edcd.io/api/tick"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
        # '2025-03-23T07:13:18+00:00'
        #  2025-03-22T20:05:16.000Z
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None


def LastTickReadable():
    raw_tick = LastTickRaw()
    eg = '2025-03-23T07:13:18+00:00'
    if raw_tick is not None:
        try:
            readable_format = datetime.datetime.strptime(
                raw_tick, "%Y-%m-%dT%H:%M:%S%z"
            ).strftime('%a %d %b at %H:%M')
            return (readable_format)
        except (ValueError, TypeError) as e:
            print(f"Error converting timestamp: {e}")
    return '<Unknown>'


if __name__ == "__main__":
    print(LastTickRaw())
    print(LastTickReadable())
