\
import random

def scan_with_noise(model, center, radius=1, fp=0.1, fn=0.1):
    cx, cy = center
    detections = {"fires": [], "survivors": []}
    W, H = model.width, model.height
    for dy in range(-radius, radius+1):
        for dx in range(-radius, radius+1):
            x, y = cx+dx, cy+dy
            if 0<=x<W and 0<=y<H:
                is_fire = (model.cell_types[y][x] == "fire")
                if is_fire and random.random() > fn:
                    detections["fires"].append([x,y])
                elif (not is_fire) and random.random() < fp:
                    detections["fires"].append([x,y])
    for a in model.schedule.agents:
        if getattr(a, "pos", None) and getattr(a, "life_deadline", None) is not None:
            ax, ay = a.pos
            if abs(ax-cx) <= radius and abs(ay-cy) <= radius:
                if random.random() > fn:
                    detections["survivors"].append([ax, ay])
    return detections
