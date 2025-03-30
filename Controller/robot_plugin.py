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
    SquaredBlockedArea, Opening, IsolatedArea, GuideLine
)
from Utils.utils import (
    within_bounds,
    get_grass_tassel,
    mowing_time,
    contains_any_resource, get_contents_at_point,
)


class DefaultMovementPlugin(MovementPlugin, ABC):
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
        super().__init__(grid, base_station_pos, grid_width, grid_height, dim_tassel)
        self.open = False
        self.angle = random.uniform(5, 175)
        self.movement_type = movement_type
        self.boing = boing
        self.cut_diameter = cut_diameter
        self.dim_tassel = dim_tassel
        self.is_in_isolated = False
        self.has_rotated_toward_guide = False
        self.last_discrete_pos = None

    def move(self, agent):
        if self.movement_type == "random":
            self.random_move(agent)
        elif self.movement_type == "systematic":
            self.systematic_move(agent)

    def update_agent_autonomy(self, agent):
        mowing_t = mowing_time(agent.speed, agent.aux_autonomy, self.dim_tassel)
        agent.decrease_autonomy(mowing_t)
        agent.decrease_cycles(mowing_t)

    def random_move(self, agent):
        dx = math.cos(self.angle) * self.dim_tassel
        dy = math.sin(self.angle) * self.dim_tassel
        new_pos = (self.pos[0] + dx, self.pos[1] + dy)
        agent.dir = (dx, dy)

        right_angle = self.angle - math.pi / 2
        right_dx = math.cos(right_angle) * self.dim_tassel
        right_dy = math.sin(right_angle) * self.dim_tassel
        right_pos = (self.pos[0] + right_dx, self.pos[1] + right_dy)

        right_neighbors = self.grid.get_neighbors(pos=right_pos, radius=1.0, include_center=True)
        guide_line_on_right = any(isinstance(obj, GuideLine) for obj in right_neighbors)

        if not guide_line_on_right and self.has_rotated_toward_guide:
            self.has_rotated_toward_guide = False

        if self.is_valid_real_pos(new_pos):
            discrete_pos = self.real_to_discrete(new_pos)

            if discrete_pos == self.last_discrete_pos:
                self.bounce(agent)
                return

            if within_bounds(self.grid_width, self.grid_height, discrete_pos) and not contains_any_resource(
                    self.grid, discrete_pos, [CircledBlockedArea, SquaredBlockedArea], self.grid_width, self.grid_height
            ):
                is_on_opening = contains_any_resource(
                    self.grid, discrete_pos, [Opening], self.grid_width, self.grid_height
                )
                is_in_isolated_area = contains_any_resource(
                    self.grid, discrete_pos, [IsolatedArea], self.grid_width, self.grid_height
                )

                if self.is_in_isolated:
                    if is_in_isolated_area or is_on_opening:
                        if is_on_opening:
                            self.is_in_isolated = False
                        self.grid.move_agent(agent, discrete_pos)
                        self.pos = new_pos
                        self.last_discrete_pos = self.real_to_discrete(self.pos)
                        self.update_agent_autonomy(agent)
                        agent.path_taken.add(self.pos)
                        self.cut(discrete_pos, agent)
                        return
                    else:
                        self.bounce(agent)
                        return
                else:
                    if is_in_isolated_area:
                        if is_on_opening:
                            self.is_in_isolated = True
                            self.grid.move_agent(agent, discrete_pos)
                            self.pos = new_pos
                            self.last_discrete_pos = self.real_to_discrete(self.pos)
                            self.update_agent_autonomy(agent)
                            agent.path_taken.add(self.pos)
                            self.cut(discrete_pos, agent)
                            return
                        else:
                            self.bounce(agent)
                            return
                    else:
                        self.grid.move_agent(agent, discrete_pos)
                        self.pos = new_pos
                        self.last_discrete_pos = self.real_to_discrete(self.pos)
                        self.update_agent_autonomy(agent)
                        agent.path_taken.add(self.pos)
                        self.cut(discrete_pos, agent)
                        return
        self.bounce(agent)

    def systematic_move(self, agent):
        pass

    def cut(self, pos, agent):
        radius = (self.cut_diameter / self.dim_tassel) / 2
        neighbors = self.grid.get_neighbors(pos=pos, include_center=True, radius=radius)
        for neighbor in neighbors:
            neighbor = neighbor.pos
            norm_neighbor = (neighbor[0], neighbor[1])
            grass_tassel = get_grass_tassel(agent.grass_tassels, norm_neighbor)
            if grass_tassel is not None:
                grass_tassel.increment()

    def bounce(self, agent):
        self.move_back(agent)
        if self.boing == "random":
            bounce_angle = random.uniform(5, 175)
            self.angle = (math.radians(bounce_angle) + self.angle) % (2 * math.pi)
            dx = math.cos(self.angle) * self.dim_tassel
            dy = math.sin(self.angle) * self.dim_tassel
            new_real_pos = (self.pos[0] + dx, self.pos[1] + dy)
            discrete_pos = self.real_to_discrete(new_real_pos)
            if self.is_valid_real_pos(new_real_pos) and within_bounds(self.grid_width, self.grid_height, discrete_pos):
                if not contains_any_resource(self.grid, discrete_pos, [CircledBlockedArea, SquaredBlockedArea],
                                             self.grid_width, self.grid_height):
                    self.pos = new_real_pos
                    self.last_discrete_pos = self.real_to_discrete(self.pos)
                    self.grid.move_agent(agent, discrete_pos)
                    self.update_agent_autonomy(agent)
                    agent.path_taken.add(self.pos)
                    self.cut(discrete_pos, agent)

    def is_valid_real_pos(self, real_pos):
        x, y = real_pos
        return 0 <= x < (self.grid_width / self.dim_tassel) and 0 <= y < (self.grid_height / self.dim_tassel)

    def move_back(self, agent):
        num_tass_back = math.floor((self.cut_diameter / self.dim_tassel))
        for _ in range(num_tass_back):
            real_pos = (self.pos[0] - agent.dir[0]), (self.pos[1] - agent.dir[1])
            discrete_pos = self.real_to_discrete(real_pos)
            if (
                    self.is_valid_real_pos(real_pos)
                    and within_bounds(self.grid_width, self.grid_height, discrete_pos)
                    and not contains_any_resource(
                self.grid, discrete_pos, [CircledBlockedArea, SquaredBlockedArea], self.grid_width, self.grid_height
            )
            ):
                self.pos = real_pos
                self.last_discrete_pos = self.real_to_discrete(self.pos)
                self.grid.move_agent(agent, discrete_pos)
                self.update_agent_autonomy(agent)
                agent.path_taken.add(self.pos)
                self.cut(self.real_to_discrete(self.pos), agent)
            else:
                break

    def real_to_discrete(self, real_pos):
        x, y = real_pos
        discrete_pos = math.ceil(x / self.dim_tassel), math.ceil(y / self.dim_tassel)
        if within_bounds(self.grid_width, self.grid_height, discrete_pos):
            return discrete_pos
        else:
            return math.floor(x / self.dim_tassel), math.floor(y / self.dim_tassel)
