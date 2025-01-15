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

from abc import abstractmethod


class MovementPlugin:
    def __init__(self, grid, pos, grid_width, grid_height, dim_tassel):
        """
        Initialize the MovementPlugin with the grid and initial position.

        :param dim_tassel:
        :param grid: The grid on which the movement will take place.
        :type grid: Any
        :param pos: The initial position of the agent on the grid.
        :type pos: tuple or list
        :param grid_width: The width of the grid.
        :type grid_width: int
        :param grid_height: The height of the grid.
        :type grid_height: int
        """
        self.grid = grid
        self.pos = (pos[0] * dim_tassel, pos[1] * dim_tassel)

        # Calculate the width and height of the grid
        self.grid_width = grid_width
        self.grid_height = grid_height

    @abstractmethod
    def move(self, agent):
        """
        Move the character according to the rules defined by the specific subclass.

        :param agent: The Agent object representing the character being moved.
        :type agent: Agent
        """
        pass

    @abstractmethod
    def bounce(self, agent):
        """
        Make the robot "boing" (bounce back) according to the rules defined by the specific subclass.
        """
        pass

    @abstractmethod
    def cut(self, pos, agent):
        """
        Make the robot "counts" according to the rules defined by the specific subclass.
        """
        pass
