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

from mesa import Agent

class Robot(Agent):
    """
    A Robot agent that interacts with the environment.

    :param unique_id: Unique identifier for the agent.
    :type unique_id: int
    :param model: The model object that the agent belongs to.
    :type model: Model
    :param robot_plugin: The robot plugin used for movement.
    :type robot_plugin: MovementPlugin
    :param grass_tassels: Number of grass tassels to collect.
    :type grass_tassels:
    :param autonomy: Autonomy level of the robot.
    :type autonomy: int
    :param speed: Speed of the robot.
    :type speed: float
    :param shear_load: The shear load capacity of the robot.
    :type shear_load: float
    :param base_station: The base station object where the robot can recharge.
    :type base_station: BaseStation
    :param cycles: The number of cycles of the robot.
    :type cycles: int
    """

    def __init__(
            self,
            unique_id,
            model,
            robot_plugin,
            grass_tassels,
            autonomy,
            speed,
            shear_load,
            base_station,
            cycles
    ):
        super().__init__(unique_id, model)

        self.robot_plugin = robot_plugin
        self.grass_tassels = grass_tassels
        self.autonomy = autonomy
        self.cycles = cycles
        self.base_station = base_station
        self.speed = speed
        self.shear_load = shear_load
        self.aux_autonomy = autonomy
        self.first = True

        self.dir = None
        self.path_taken = set()

    def step(self):
        """
        Move the robot using the robot plugin.
        """
        self.robot_plugin.move(self)

    def decrease_autonomy(self, param):
        """
        Decrease the autonomy level of the robot.

        :param param: Amount to decrease the autonomy.
        :type param: int
        """
        self.aux_autonomy -= param

    def reset_autonomy(self):
        """
        Reset the autonomy level of the robot to its initial value.
        """
        self.aux_autonomy = self.autonomy

    def not_first(self):
        """
        Indicate that this is not the first step.
        """
        self.first = False

    def decrease_cycles(self, param):
        """
        Decrease the number of cycles of the robot.

        :param param: Amount to decrease the cycles.
        :type param: int
        """
        self.cycles -= param

class GrassTassel:
    """
    A GrassTassel agent that represents a single grass tassel.

    :param pos: Position of the grass tassel.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.counts = -1
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the grass tassel.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)

    def increment(self):
        """
        Increment the counts of the grass tassel.
        """
        if self.counts == -1:
            self.counts = 1
        else:
            self.counts += 1

class IsolatedArea:
    """
    Represents an isolated area.

    :param pos: Position of the isolated area.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the isolated area.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)

class Opening:
    """
    Represents an opening in the environment.

    :param pos: Position of the opening.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the opening.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)

class BaseStation:
    """
    Represents a base station where robots can recharge.

    :param pos: Position of the base station.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the base station.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)

class SquaredBlockedArea:
    """
    Represents a squared blocked area.

    :param pos: Position of the blocked area.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the blocked area.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)

class CircledBlockedArea:
    """
    Represents a circular blocked area.

    :param pos: Center position of the circle.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the circular blocked area.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)

class GuideLine:
    """
    Represents a guideline for robots to follow.

    :param pos: Position of the guideline.
    :type pos: tuple or list
    """

    def __init__(self, pos):
        self.pos = pos

    @property
    def unique_id(self):
        """
        Return the unique identifier for the guideline.

        :return: Unique identifier.
        :rtype: int
        """
        return id(self)
