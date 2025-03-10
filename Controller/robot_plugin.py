""" Copyright 2024 Sara Grecu

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License."""

import math
import random
from abc import ABC

from Controller.movement_plugin import MovementPlugin
from Model.agents import (
    CircledBlockedArea,
    SquaredBlockedArea, Opening, IsolatedArea
)
from Utils.utils import (
    within_bounds,
    get_grass_tassel,
    mowing_time,
    contains_any_resource, get_contents_at_point,
)


class DefaultMovementPlugin(MovementPlugin, ABC):
    """
    Default movement plugin for controlling the agent's movement in the grid.

    :param movement_type: (str) The type of movement ("random" or "systematic").
    :param grid: (object) The grid object representing the environment.
    :param base_station_pos: (tuple) Tuple representing the position of the base station.
    :param boing: (str) The type of bouncing behavior when encountering obstacles.
    :param cut_diameter: (int) The cutting diameter of the mower.
    :param grid_width: (int) The width of the grid.
    :param grid_height: (int) The height of the grid.
    :param dim_tassel: (int) The dimension of each tassel.
    """

    def __init__(
            self,
            movement_type: str,
            grid,
            base_station_pos,
            boing: str,
            cut_diameter: int,
            grid_width: int,
            grid_height: int,
            dim_tassel,
    ):
        super().__init__(grid, base_station_pos, grid_width, grid_height, dim_tassel)  # Initialize the superclass
        self.open = False
        self.angle = random.uniform(5, 175)  # Random initial angle in radians
        self.movement_type = movement_type  # Set the movement type
        self.boing = boing  # Set the type of bouncing behavior
        self.cut_diameter = cut_diameter  # Set the cutting diameter
        self.dim_tassel = dim_tassel  # Set the tassel dimension
        self.is_in_isolated = False

    def move(self, agent):
        """
        Moves the agent based on the specified movement type.

        :param agent: (object) The agent to be moved.
        """
        if self.movement_type == "random":  # If movement type is random
            self.random_move(agent)
        elif self.movement_type == "systematic":  # If movement type is systematic
            self.systematic_move(agent)

    def update_agent_autonomy(self, agent):
        """
        Updates the agent's autonomy and cycles based on mowing time.

        :param agent: (object) The agent whose autonomy is being updated.
        """
        mowing_t = mowing_time(agent.speed, agent.aux_autonomy, self.dim_tassel)
        agent.decrease_autonomy(mowing_t)
        agent.decrease_cycles(mowing_t)

    def random_move(self, agent):
        dx = math.cos(self.angle) * self.dim_tassel
        dy = math.sin(self.angle) * self.dim_tassel

        new_pos = (self.pos[0] + dx, self.pos[1] + dy)
        agent.dir = (dx, dy)

        if self.is_valid_real_pos(new_pos):
            discrete_pos = self.real_to_discrete(new_pos)

            # Verifica se la posizione è all'interno dei limiti e non è un'area bloccata
            if (
                    within_bounds(self.grid_width, self.grid_height, discrete_pos)
                    and not contains_any_resource(
                self.grid,
                discrete_pos,
                [CircledBlockedArea, SquaredBlockedArea],
                self.grid_width,
                self.grid_height,
            )
            ):
                # Verifica presenza di Opening (uscita)
                is_on_opening = contains_any_resource(
                    self.grid, discrete_pos, [Opening], self.grid_width, self.grid_height
                )

                # Verifica se è in un'area isolata
                is_in_isolated_area = contains_any_resource(
                    self.grid, discrete_pos, [IsolatedArea], self.grid_width, self.grid_height
                )

                # Se è all'interno di un'area isolata
                if self.is_in_isolated:
                    # Se trova un'apertura, esce dall'area isolata
                    if is_on_opening:
                        self.is_in_isolated = False
                        self.grid.move_agent(agent, discrete_pos)
                        self.pos = new_pos
                        self.update_agent_autonomy(agent)
                        agent.path_taken.add(self.pos)
                        self.cut(discrete_pos, agent)
                    else:
                        # Se non c'è un'apertura, rimane nell'area isolata
                        if is_in_isolated_area:
                            self.grid.move_agent(agent, discrete_pos)
                            self.pos = new_pos
                            self.update_agent_autonomy(agent)
                            agent.path_taken.add(self.pos)
                            self.cut(discrete_pos, agent)
                        else:
                            # Se non è più nell'area isolata (caso anomalo), esce
                            self.is_in_isolated = False
                            self.bounce(agent)
                else:
                    # Se non è in un'area isolata
                    # Può muoversi normalmente
                    # Se si trova sull'apertura di un'area isolata, entra
                    if is_on_opening:
                        # Controlla se l'apertura è l'entrata di un'area isolata
                        isolated_area = contains_any_resource(
                            self.grid, discrete_pos, [IsolatedArea], self.grid_width, self.grid_height
                        )
                        if isolated_area:
                            self.is_in_isolated = True
                            self.grid.move_agent(agent, discrete_pos)
                            self.pos = new_pos
                            self.update_agent_autonomy(agent)
                            agent.path_taken.add(self.pos)
                            self.cut(discrete_pos, agent)
                        else:
                            # Se l'apertura non è un'area isolata, muovi normalmente
                            self.grid.move_agent(agent, discrete_pos)
                            self.pos = new_pos
                            self.update_agent_autonomy(agent)
                            agent.path_taken.add(self.pos)
                            self.cut(discrete_pos, agent)
                    else:
                        if is_in_isolated_area:
                            self.grid.move_agent(agent, discrete_pos)
                            self.pos = new_pos
                            self.update_agent_autonomy(agent)
                            agent.path_taken.add(self.pos)
                            self.cut(discrete_pos, agent)
                        else:
                            self.grid.move_agent(agent, discrete_pos)
                            self.pos = new_pos
                            self.update_agent_autonomy(agent)
                            agent.path_taken.add(self.pos)
                            self.cut(discrete_pos, agent)
            else:
                self.bounce(agent)
        else:
            self.bounce(agent)

    def systematic_move(self, agent):
        """
        Placeholder for systematic movement logic. Needs to be implemented.

        :param agent: (object) The agent to be moved.
        """
        pass

    def cut(self, pos, agent):
        """
        Increments the grass tassels of neighboring cells and updates the agent's autonomy.

        :param pos: (tuple) The position to process.
        :param agent: (object) The agent performing the cutting.
        """
        radius = (self.cut_diameter / self.dim_tassel) / 2  # Calculate the radius for neighbors search
        neighbors = self.grid.get_neighbors(
            pos=pos, include_center=True, radius=radius,
        )

        for neighbor in neighbors:
            neighbor = neighbor.pos
            norm_neighbor = (
                neighbor[0],
                neighbor[1]
            )

            grass_tassel = get_grass_tassel(
                agent.grass_tassels, norm_neighbor
            )  # Get the grass tassel at the new position

            if grass_tassel is not None:  # If there is a grass tassel
                grass_tassel.increment()

    def bounce(self, agent):
        """
        Handles the bouncing behavior when encountering obstacles.

        :param agent: (object) The agent that hit an obstacle.
        """
        # Step 1: Move back a step to avoid obstacles
        self.move_back(agent)

        if self.boing == "random":
            # Step 2: Calculate a new direction based on a bounce angle
            bounce_angle = random.uniform(5, 175)  # Random angle for redirection
            self.angle = (math.radians(bounce_angle) + self.angle) % (2 * math.pi)  # Update angle

            # Step 3: Compute the new position
            dx = math.cos(self.angle) * self.dim_tassel
            dy = math.sin(self.angle) * self.dim_tassel
            new_real_pos = (self.pos[0] + dx, self.pos[1] + dy)

            # Step 4: Validate the new position
            if (self.is_valid_real_pos(new_real_pos)
                    and within_bounds(self.grid_width, self.grid_height,
                                      self.real_to_discrete(new_real_pos))):
                self.pos = new_real_pos
                self.update_agent_autonomy(agent)

                # Update the agent's position on the grid
                self.grid.move_agent(agent, self.real_to_discrete(new_real_pos))
                agent.path_taken.add(self.pos)

                # Update grass tassels
                self.cut(self.real_to_discrete(new_real_pos), agent)

    def is_valid_real_pos(self, real_pos):
        """
        Checks if the real position is within the grid bounds.

        :param real_pos: (tuple) Tuple representing the real position.
        :return: (bool) True if the real position is valid, False otherwise.
        """
        x, y = real_pos
        return 0 <= x < (self.grid_width / self.dim_tassel) and 0 <= y < (self.grid_height / self.dim_tassel)

    def move_back(self, agent):
        """
        Moves the agent back a specified number of tassels.

        :param agent: (object) The agent to be moved back.
        """
        num_tass_back = math.floor(
            (self.cut_diameter / self.dim_tassel)
        )  # Calculate the number of tassels to move back

        for _ in range(num_tass_back):  # For each tassel to move back
            real_pos = (self.pos[0] - agent.dir[0]), (self.pos[1] - agent.dir[1])
            discrete_pos = self.real_to_discrete(real_pos)

            if (  # If the new position is within bounds and doesn't contain blocked areas
                    self.is_valid_real_pos(real_pos)
                    and within_bounds(self.grid_width, self.grid_height, discrete_pos)
                    and not contains_any_resource(
                self.grid,
                discrete_pos,
                [CircledBlockedArea, SquaredBlockedArea],
                self.grid_width,
                self.grid_height,
            )):
                self.pos = real_pos
                # Move the agent and update its path
                self.grid.move_agent(agent, discrete_pos)
                self.update_agent_autonomy(agent)
                agent.path_taken.add(self.pos)

                self.cut(self.real_to_discrete(self.pos), agent)
            else:
                break

    def real_to_discrete(self, real_pos):
        """
        Converts real coordinates to discrete grid coordinates.

        :param real_pos: (tuple) Tuple representing the real position.
        :return: (tuple) Tuple of discrete grid coordinates.
        """
        x, y = real_pos

        discrete_pos = math.ceil(x / self.dim_tassel), math.ceil(y / self.dim_tassel)
        if within_bounds(self.grid_width, self.grid_height, discrete_pos):
            return discrete_pos
        else:
            return math.floor(x / self.dim_tassel), math.floor(y / self.dim_tassel)
