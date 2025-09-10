from .storage import load_data, save_data

def add_event(title, date, time, repeat=None):
    data = load_data()
    event = {
        "type": "event",
        "title": title,
        "date": date,
        "time": time,
        "repeat": repeat
    }
    data["events"].append(event)
    save_data(data)
    return event

def list_events():
    data = load_data()
    return data["events"]
