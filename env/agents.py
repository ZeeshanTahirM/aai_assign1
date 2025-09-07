\
from mesa import Agent

class BaseAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.command = None

    def set_command(self, cmd):
        self.command = cmd

    def step(self):
        # Default: do movement and optional act in step; SimultaneousActivation will call advance()
        if not self.command:
            return
        if self.command.get("type") == "move":
            to = tuple(self.command.get("to", self.pos))
            if self.model.grid.out_of_bounds(to) is False:
                self.model.grid.move_agent(self, to)
        elif self.command.get("type") == "act":
            self._do_act(self.command)

    def advance(self):
        # with SimultaneousActivation, we separate state commit here if needed
        pass

    def _do_act(self, cmd):
        pass


class Survivor(Agent):
    def __init__(self, unique_id, model, life_deadline=200):
        super().__init__(unique_id, model)
        self.life_deadline = life_deadline
        self._picked = False
        self._dead = False

    def step(self):
        if not self._picked:
            self.life_deadline -= 1
            if self.life_deadline <= 0:
                self._dead = True

    def advance(self):
        pass


class MedicAgent(BaseAgent):
    kind = "medic"
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        self.carrying = False
        self.carrying_id = None

    def _do_act(self, cmd):
        action = cmd.get("action_name")
        if action == "pickup_survivor":
            cell_agents = self.model.grid.get_cell_list_contents([self.pos])
            surv = next((a for a in cell_agents if isinstance(a, Survivor)), None)
            if surv and not self.carrying:
                self.carrying = True
                self.carrying_id = surv.unique_id
                surv._picked = True  # defer removal to model.step()

        elif action == "drop_at_hospital":
            x, y = self.pos
            if self.model.cell_type(x, y) == "hospital" and self.carrying:
                self.model.add_to_hospital_queue(self.pos, str(self.carrying_id))
                self.carrying = False
                self.carrying_id = None


class TruckAgent(BaseAgent):
    kind = "truck"
    def __init__(self, unique_id, model, mode="water", water_max=30, tools_max=10):
        super().__init__(unique_id, model)
        self.mode = mode
        self.water_max = water_max
        self.tools_max = tools_max
        self.water = water_max
        self.tools = tools_max

    def _do_act(self, cmd):
        action = cmd.get("action_name")
        x, y = self.pos

        if action == "extinguish" and self.water > 0:
            if self.model.cell_type(x, y) == "fire":
                # change the map cell and count it
                self.model.cell_types[y][x] = "road"
                self.water -= 1
                self.model.fires_extinguished += 1

        elif action == "clear_rubble" and self.tools > 0:
            if self.model.cell_type(x, y) == "rubble":
                self.model.cell_types[y][x] = "road"
                self.tools -= 1
                self.model.roads_cleared += 1


class DroneAgent(BaseAgent):
    kind = "drone"
    def __init__(self, unique_id, model, battery_max=80):
        super().__init__(unique_id, model)
        self.battery_max = battery_max
        self.battery = battery_max

    def step(self):
        # Simple drain; movement handled by BaseAgent
        self.battery = max(0, self.battery - 1)
        super().step()

from .agents import Survivor  # noqa
