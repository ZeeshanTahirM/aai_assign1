\
import random

def spread_fires(model):
    W, H = model.width, model.height
    new_fires = []
    extinguished = 0

    for y in range(H):
        for x in range(W):
            if model.cell_types[y][x] == "fire":
                for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < W and 0 <= ny < H:
                        ct = model.cell_types[ny][nx]
                        if ct in ("empty","road","building","rubble") and random.random() < model.p_fire_spread:
                            new_fires.append((nx,ny))
    for (x,y) in new_fires:
        model.cell_types[y][x] = "fire"
    return {"extinguished": extinguished}

def trigger_aftershocks(model):
    W, H = model.width, model.height
    roads_cleared = 0
    if random.random() < model.p_aftershock:
        x = random.randrange(W)
        y = random.randrange(H)
        if model.cell_types[y][x] in ("road","building"):
            model.cell_types[y][x] = "rubble"
    return {"roads_cleared": roads_cleared}
