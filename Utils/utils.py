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

import cProfile
import json
import math
import os
import pstats
import random
from io import StringIO

from Model.agents import (
    BaseStation,
    GuideLine,
    SquaredBlockedArea,
    CircledBlockedArea,
    IsolatedArea,
)

def validate_and_adjust_base_station(coords, grid_width, grid_height, grid):
    """
    Validates and adjusts the base station coordinates.

    :param coords: Tuple (x, y) - Base station coordinates to validate.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param grid: ContinuousSpace - Grid where the base station is placed.
    :return: Tuple (x, y) - Valid or adjusted coordinates of the base station.
    """
    # Check if coordinates are valid and not on restricted areas
    if (
            coords is None
            or not within_bounds(grid_width, grid_height, coords)
            or contains_any_resource(
        grid,
        coords,
        [SquaredBlockedArea, CircledBlockedArea, IsolatedArea],
        grid_width,
        grid_height,
    )
    ):
        # If invalid, try to find a nearby valid position
        def maybe_move_to_adjacent_valid_tile():
            x, y = coords if coords else (0, 0)
            offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for dx, dy in offsets:
                new_x, new_y = x + dx, y + dy
                if within_bounds(
                        grid_width, grid_height, (new_x, new_y)
                ) and not contains_any_resource(
                    grid,
                    (new_x, new_y),
                    [SquaredBlockedArea, CircledBlockedArea, IsolatedArea],
                    grid_width,
                    grid_height,
                ):
                    return new_x, new_y
            return coords

        return maybe_move_to_adjacent_valid_tile()
    return coords


def perimeter_try_generating_base_station(grid_width, grid_height, base_station, grid):
    """
    Attempts to generate a base station along the grid's perimeter.

    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param base_station: Tuple (x, y) or None - Initial base station coordinates.
    :param grid: ContinuousSpace - Grid where the base station is placed.
    :return: Tuple (x, y) - Valid coordinates of the base station.
    """

    def generate_perimeter_pair(width, height):
        """
        Generates random perimeter coordinates.

        :param width: int - Grid width.
        :param height: int - Grid height.
        :return: Tuple (x, y) - Perimeter coordinates.
        """
        side = random.choice([0, 1])
        if side == 0:
            return 0, random.randint(0, width)
        else:
            return random.randint(0, height), 0

    while base_station is None:
        try:
            tmp_bs = generate_perimeter_pair(grid_width, grid_height)
            base_station = validate_and_adjust_base_station(tmp_bs, grid_width, grid_height, grid)
        except ValueError:
            base_station = None
    return base_station


def big_center_try_generating_base_station(center_tassel, grid_width, grid_height, base_station, biggest_blocked_area,
                                           grid):
    """
    Attempts to place the base station near the center of the largest blocked area.

    :param center_tassel: Tuple (x, y) - Central tassel coordinates.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param base_station: Tuple (x, y) or None - Initial base station coordinates.
    :param biggest_blocked_area: List of coordinates - Coordinates of the largest blocked area.
    :param grid: ContinuousSpace - Grid where the base station is placed.
    :return: Tuple (x, y) or None - Valid coordinates of the base station or None.
    """
    if biggest_blocked_area:
        while base_station is None:
            try:
                tmp_bs = generate_biggest_center_pair(center_tassel, biggest_blocked_area)
                base_station = validate_and_adjust_base_station(tmp_bs, grid_width, grid_height, grid)
            except ValueError:
                base_station = None
        return base_station
    else:
        return None

class StationGuidelinesStrategy:
    """
    Base class for strategies to locate a base station within a grid.
    """

    def __init__(self):
        pass

    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height):
        """
        Abstract method to locate a base station within the grid.

        :param grid: ContinuousSpace - Grid where the base station is placed.
        :param center_tassel: Tuple (x, y) - Coordinates of the central tassel.
        :param biggest_blocked_area: List of coordinates - Coordinates of the largest blocked area.
        :param grid_width: int - Grid width.
        :param grid_height: int - Grid height.
        :return: Tuple (x, y) or None - Coordinates of the base station or None.
        """
        pass

class PerimeterPairStrategy(StationGuidelinesStrategy):
    """
    Strategy to place a base station along the grid's perimeter.
    """
    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height):
        """
        Places a base station on the grid's perimeter.

        :param grid: ContinuousSpace - Grid where the base station is placed.
        :param center_tassel: Tuple (x, y) - Coordinates of the central tassel.
        :param biggest_blocked_area: List of coordinates - Coordinates of the largest blocked area.
        :param grid_width: int - Grid width.
        :param grid_height: int - Grid height.
        :return: Tuple (x, y) or None - Coordinates of the base station or None.
        """
        base_station = None
        attempt_limit = 35

        for _ in range(attempt_limit):
            base_station = perimeter_try_generating_base_station(grid_width, grid_height, base_station, grid)
            if base_station is not None and add_base_station(grid, base_station, grid_width, grid_height):
                print(f"BASE STATION: {base_station}")
                return base_station
        return None

class BiggestRandomPairStrategy(StationGuidelinesStrategy):
    """
    Strategy to place a base station randomly in the largest blocked area.
    """

    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height):
        """
        Places a base station randomly in the largest blocked area.

        :param grid: ContinuousSpace - Grid where the base station is placed.
        :param center_tassel: Tuple (x, y) - Coordinates of the central tassel.
        :param biggest_blocked_area: List of coordinates - Coordinates of the largest blocked area.
        :param grid_width: int - Grid width.
        :param grid_height: int - Grid height.
        :return: Tuple (x, y) or None - Coordinates of the base station or None.
        """
        base_station = None
        attempt_limit = 35

        def generate_biggest_pair(bba):
            """
            Generates random coordinates within the largest blocked area.

            :param bba: List of coordinates - Coordinates of the largest blocked area.
            :return: Tuple (x, y) - Coordinates within the largest blocked area.
            """
            random_choice = random.choice(bba) if bba else None
            return random_choice

        while base_station is None:
            try:
                tmp_bs = generate_biggest_pair(biggest_blocked_area)
                base_station = validate_and_adjust_base_station(tmp_bs, grid_width, grid_height, grid)
            except ValueError:
                base_station = None

        for _ in range(attempt_limit):
            if base_station is not None and add_base_station(grid, base_station, grid_width, grid_height):
                return base_station
        return None

class BiggestCenterPairStrategy(StationGuidelinesStrategy):
    """
    Strategy to place the base station near the center of the largest blocked area.
    """

    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height):
        """
        Places the base station near the center of the largest blocked area.

        :param grid: ContinuousSpace - Grid where the base station is placed.
        :param center_tassel: Tuple (x, y) - Coordinates of the central tassel.
        :param biggest_blocked_area: List of coordinates - Coordinates of the largest blocked area.
        :param grid_width: int - Grid width.
        :param grid_height: int - Grid height.
        :return: Tuple (x, y) or None - Coordinates of the base station or None.
        """
        base_station = None
        attempt_limit = 35

        for _ in range(attempt_limit):
            base_station = big_center_try_generating_base_station(center_tassel, grid_width, grid_height, base_station,
                                                                  biggest_blocked_area, grid)
            if base_station is not None and add_base_station(grid, base_station, grid_width, grid_height):
                return base_station
        return None

def mowing_time(speed_robot, autonomy_robot_seconds, dim_tassel, k=1):
    """
    Estimates the time required for the robot to mow a given area.

    :param speed_robot: float - Robot's speed in units per second.
    :param autonomy_robot_seconds: int - Robot's autonomy in seconds.
    :param dim_tassel: float - Total area to be mowed.
    :param k: float - Multiplier for the estimated time.
    :return: float - Estimated mowing time in seconds.
    """
    # Calculate total estimated time
    total_time_seconds = (dim_tassel / speed_robot) * k

    # Check if autonomy is sufficient
    if total_time_seconds > autonomy_robot_seconds:
        print("Warning: The robot's autonomy might not be sufficient.")
        return 0

    return total_time_seconds

def get_contents_at_point(space, x, y, tol=1e-5):
    """
    Retrieves the contents of the grid at a specific point.

    :param space: ContinuousSpace - Grid to query.
    :param x: float - X-coordinate of the point.
    :param y: float - Y-coordinate of the point.
    :param tol: float - Tolerance for neighbor search.
    :return: List - Contents of the grid at (x, y).
    """
    try:
        neighbors = space.get_neighbors((x, y), 0)
        contents = [agent for agent in neighbors if abs(agent.pos[0] - x) < tol and abs(agent.pos[1] - y) < tol]
        return contents
    except ValueError as e:
        if "operands could not be broadcast together" in str(e):
            return []
        raise


def euclidean_distance(p1, p2):
    """
    Calculates the Euclidean distance between two points.

    :param p1: Tuple (x, y) - First point.
    :param p2: Tuple (x, y) - Second point.
    :return: float - Distance between the two points.
    """
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

def generate_biggest_center_pair(center_tassel, biggest_blocked_area):
    """
    Generates the nearest point in the largest blocked area relative to the center tassel.

    :param center_tassel: Tuple (x, y) - Central tassel coordinates.
    :param biggest_blocked_area: List of coordinates - Coordinates of the largest blocked area.
    :return: Tuple (x, y) or None - Nearest point in the largest blocked area.
    """
    if not biggest_blocked_area:
        return None

    nearest_tuple = min(biggest_blocked_area, key=lambda pos: euclidean_distance(pos, center_tassel))
    return nearest_tuple


def load_data_from_file(file_path):
    """
    Loads data from a JSON file.

    :param file_path: str - Path to the JSON file.
    :return: Tuple (dict, dict, dict) or None - Robot, environment, and simulator data.
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as json_file:
        data = json.load(json_file)

    return data.get("robot", {}), data.get("env", {}), data.get("simulator", {})


def put_station_guidelines(strategy, grid, grid_width, grid_height, random_corner_perimeter, central_tassel,
                           biggest_area_blocked):
    """
    Places station guidelines on the grid.

    :param strategy: Strategy object - Strategy to locate the base station.
    :param grid: ContinuousSpace - Grid where the base station is placed.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param random_corner_perimeter: Tuple (x, y) - Random corner on the grid perimeter.
    :param central_tassel: Tuple (x, y) - Central tassel coordinates.
    :param biggest_area_blocked: List of coordinates - Coordinates of the largest blocked area.
    :return: Tuple (x, y) or None - Coordinates of the base station or None.
    """
    base_station_pos = strategy.locate_base_station(grid, central_tassel, biggest_area_blocked, grid_width, grid_height)

    if base_station_pos:
        draw_line(base_station_pos[0], base_station_pos[1], random_corner_perimeter[0], random_corner_perimeter[1],
                  grid, grid_width, grid_height)

        farthest_point = find_farthest_point(grid_width, grid_height, base_station_pos[0], base_station_pos[1])
        if farthest_point is not None:
            draw_line(base_station_pos[0], base_station_pos[1], farthest_point[0], farthest_point[1], grid, grid_width,
                      grid_height)

    return base_station_pos



def contains_any_resource(grid, pos, resource_types, grid_width, grid_height):
    """
    Checks if a position contains any of the specified resource types.

    :param grid: ContinuousSpace - Grid to query.
    :param pos: Tuple (x, y) - Position to check.
    :param resource_types: List - List of resource types to check for.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :return: bool - True if any resource type is found, False otherwise.
    """
    for rtype in resource_types:
        if contains_resource(grid, pos, rtype, grid_width, grid_height):
            return True
    return False


def draw_line(x1, y1, x2, y2, grid, grid_width, grid_height):
    """
    Draws a line on the grid between two points.

    :param x1: float - Starting X-coordinate.
    :param y1: float - Starting Y-coordinate.
    :param x2: float - Ending X-coordinate.
    :param y2: float - Ending Y-coordinate.
    :param grid: ContinuousSpace - Grid where the line is drawn.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :return: Set of tuples - Cells modified with guidelines.
    """
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1

    x, y = x1, y1
    cells_to_add = set()
    err = dx - dy

    while (x, y) != (x2, y2):
        if within_bounds(grid_width, grid_height, (x, y)):
            if not contains_any_resource(grid, (x, y),
                                         [CircledBlockedArea, SquaredBlockedArea, IsolatedArea, BaseStation],
                                         grid_width, grid_height):
                cells_to_add.add((x, y))
                add_resource(grid, GuideLine((x, y)), x, y, grid_width, grid_height)

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            elif e2 < dx:
                err += dx
                y += sy
        else:
            break

    if within_bounds(grid_width, grid_height, (x2, y2)):
        if not contains_any_resource(grid, (x2, y2),
                                     [CircledBlockedArea, SquaredBlockedArea, IsolatedArea, BaseStation],
                                     grid_width, grid_height):
            cells_to_add.add((x2, y2))
            add_resource(grid, GuideLine((x2, y2)), x2, y2, grid_width, grid_height)

    return cells_to_add


def draw_guideline_inside_isolated_area(grid, base_station, area_tassels, grid_width, grid_height, depth_percent=0.25):
    """
    Force a guideline from the base station into the isolated area, ignoring cell contents.

    :param grid: The grid where the guideline will be applied.
    :param base_station: Tuple (x, y) indicating the base station position.
    :param area_tassels: List of (x, y) coordinates representing the isolated area.
    :param grid_width: Grid width.
    :param grid_height: Grid height.
    :param depth_percent: How far into the area (towards the center) the guideline should go.
    """
    if not area_tassels or not base_station:
        return

    # Compute center of the area
    area_x = [t[0] for t in area_tassels]
    area_y = [t[1] for t in area_tassels]
    center = (sum(area_x) // len(area_x), sum(area_y) // len(area_y))

    # Direction vector from base station to area center
    dx = center[0] - base_station[0]
    dy = center[1] - base_station[1]
    dist = math.sqrt(dx ** 2 + dy ** 2)

    # Normalize direction
    if dist == 0:
        return
    ux, uy = dx / dist, dy / dist

    # Steps to reach the desired depth
    steps = int(dist * depth_percent)

    # Apply guideline step by step from the base station
    for i in range(steps + 1):
        x = int(round(base_station[0] + ux * i))
        y = int(round(base_station[1] + uy * i))
        if within_bounds(grid_width, grid_height, (x, y)):
            set_guideline_cell(x, y, grid, grid_width, grid_height)


def contains_resource(grid, cell, resource, grid_width, grid_height):
    """
    Checks if a specific resource is present at a given cell.

    :param grid: ContinuousSpace - Grid to query.
    :param cell: Tuple (x, y) - Cell coordinates.
    :param resource: Type - Resource type to check for.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :return: bool - True if the resource is found, False otherwise.
    """
    x, y = cell
    if 0 <= x < grid_width and 0 <= y < grid_height:
        cell_contents = get_contents_at_point(grid, x, y)
        specific_agent = next((agent for agent in cell_contents if isinstance(agent, resource)), None)
        return specific_agent is not None
    else:
        return False


def add_base_station(grid, position, grid_width, grid_height):
    """
    Adds a base station to the grid at the specified position.

    :param grid: ContinuousSpace - Grid where the base station is added.
    :param position: Tuple (x, y) - Coordinates where to place the base station.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :return: bool - True if the base station was added successfully, False otherwise.
    """
    base_station = BaseStation((position[0], position[1]))
    return add_resource(grid, base_station, position[0], position[1], grid_width, grid_height)


def set_guideline_cell(x, y, grid, grid_width, grid_height):
    """
    Sets a guideline cell at the specified position if valid and not blocked.

    :param x: int - X-coordinate of the cell.
    :param y: int - Y-coordinate of the cell.
    :param grid: ContinuousSpace - Grid where the guideline cell is added.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :return: bool - True if the guideline cell was added successfully, False otherwise.
    """
    if not within_bounds(grid_width, grid_height, (x, y)):
        return False

    blocked_areas = [CircledBlockedArea, SquaredBlockedArea]

    if not contains_any_resource(grid, (x, y), blocked_areas, grid_width, grid_height):
        add_resource(grid, GuideLine((x, y)), x, y, grid_width, grid_height)


def add_resource(grid, resource, x, y, grid_width, grid_height):
    """
    Adds a resource to the grid at the specified position.

    :param grid: ContinuousSpace - Grid where the resource is added.
    :param resource: Agent - Resource to be added.
    :param x: float - X-coordinate of the position.
    :param y: float - Y-coordinate of the position.
    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :return: bool - True if the resource was added successfully, False otherwise.
    """
    if within_bounds(grid_width, grid_height, (x, y)):
        grid.place_agent(resource, (x, y))
        return True
    else:
        return False


def within_bounds(grid_width, grid_height, pos):
    """
    Checks if a position is within the grid boundaries.

    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param pos: Tuple (x, y) - Position to check.
    :return: bool - True if the position is within bounds, False otherwise.
    """
    return 0 <= pos[0] < grid_width and 0 <= pos[1] < grid_height


def find_farthest_point(grid_width, grid_height, fx, fy):
    """
    Finds the farthest point from the given coordinates within the grid.

    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param fx: int - X-coordinate of the reference point.
    :param fy: int - Y-coordinate of the reference point.
    :return: Tuple (x, y) - Coordinates of the farthest point.
    """
    max_dist = 0
    result = (-1, -1)

    eligible_points = [(0, grid_height), (grid_width, 0), (0, 0), (grid_width, grid_height)]

    for point in eligible_points:
        dist = euclidean_distance((fx, fy), point)
        if dist > max_dist:
            max_dist = dist
            result = point
            if dist > grid_width or dist > grid_height:
                return result

    return result


def populate_perimeter_guidelines(grid_width, grid_height, grid):
    """
    Populates the grid's perimeter with guideline cells.

    :param grid_width: int - Grid width.
    :param grid_height: int - Grid height.
    :param grid: ContinuousSpace - Grid where guideline cells are added.
    """
    for y in range(grid_height):
        set_guideline_cell(grid_width - 1, y, grid, grid_width, grid_height)
        set_guideline_cell(0, y, grid, grid_width, grid_height)

    for x in range(grid_width):
        set_guideline_cell(x, 0, grid, grid_width, grid_height)
        set_guideline_cell(x, grid_height - 1, grid, grid_width, grid_height)

def get_grass_tassel(grass_tassels, pos):
    """
    Retrieves a grass tassel at the specified position.

    :param grass_tassels: List - List of grass tassels.
    :param pos: Tuple (x, y) - Position to check.
    :return: Agent or None - Grass tassel at the given position or None.
    """
    for tassel_info in grass_tassels:
        if tassel_info.pos == pos:
            return tassel_info
    return None


def find_central_tassel(rows, cols):
    """
    Finds the central tassel coordinates in the grid.

    :param rows: int - Number of rows in the grid.
    :param cols: int - Number of columns in the grid.
    :return: Tuple (x, y) - Coordinates of the central tassel.
    """
    if rows % 2 == 1 and cols % 2 == 1:
        central_row = rows // 2
        central_col = cols // 2
    else:
        central_row = rows // 2 if rows % 2 == 1 else rows // 2 - 1
        central_col = cols // 2 if cols % 2 == 1 else cols // 2 - 1
    return central_row, central_col

def profile_code(func):
    """
    Profiles the execution time of a function.

    :param func: Callable - Function to profile.
    :return: Callable - Wrapped function with profiling.
    """
    def wrapper(*args, **kwargs):
        pr = cProfile.Profile()
        pr.enable()
        result = func(*args, **kwargs)
        pr.disable()
        s = StringIO()
        sortby = "cumulative"
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())
        return result
    return wrapper