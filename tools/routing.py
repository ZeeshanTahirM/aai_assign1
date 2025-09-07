\
from heapq import heappush, heappop

def manhattan(a, b): 
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def shortest_path(model_like, start, goal, avoid=("fire","rubble")):
    """A* path on 4-connected grid avoiding cell types in `avoid`.
       model_like: object with width, height, cell_types[y][x]
    """
    W, H = model_like.width, model_like.height
    start, goal = tuple(start), tuple(goal)
    blocked = set(avoid)

    def passable(x, y):
        ct = model_like.cell_types[y][x]
        return ct not in blocked

    openq = []
    heappush(openq, (0+manhattan(start,goal), 0, start, None))
    came = {}
    cost_so_far = {start: 0}

    while openq:
        _, g, cur, parent = heappop(openq)
        if cur not in came:
            came[cur] = parent
        if cur == goal:
            break
        x,y = cur
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx,ny = x+dx, y+dy
            if 0<=nx<W and 0<=ny<H and passable(nx,ny):
                ng = g + 1
                if (nx,ny) not in cost_so_far or ng < cost_so_far[(nx,ny)]:
                    cost_so_far[(nx,ny)] = ng
                    heappush(openq, (ng+manhattan((nx,ny),goal), ng, (nx,ny), cur))

    if goal not in came and goal != start:
        return {"status":"blocked","path":[], "cost": None}
    # reconstruct
    node = goal
    path = [node]
    while node != start:
        node = came.get(node, start)
        path.append(node)
        if node == start: break
    path.reverse()
    return {"status":"ok","path":path,"cost":len(path)}
