\
def hospital_queue_state(model):
    return {
        "queues": [{"hospital": list(k), "len": len(v)} for k,v in model.hospital_queues.items()],
        "service_rate": model.hospital_service_rate
    }
