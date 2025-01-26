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
from typing import Union, Tuple, Set, List

from mesa.space import ContinuousSpace

from Model.agents import (
    BaseStation,
    GuideLine,
    SquaredBlockedArea,
    CircledBlockedArea,
    IsolatedArea,
)



def validate_and_adjust_base_station(coords, grid_width, grid_height, grid):
    """
    Validates and adjusts the base station coordinates based on the grid dimensions
    and resource locations. If the coordinates are invalid, the function attempts to
    move the base station to an adjacent valid tile.

    :param coords: Coordinates of the base station (tuple of x, y).
    :param grid_width: Width of the grid.
    :param grid_height: Height of the grid.
    :param grid: The grid where the base station is being placed.
    :return: Valid coordinates of the base station (tuple of x, y) or adjusted coordinates.
    """
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

        def maybe_move_to_adjacent_valid_tile():
            if coords:
                x, y = coords
            else:
                x, y = (0, 0)
            offsets = (
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
            )
            for dx, dy in offsets:
                new_x, new_y = x + dx, y + dy
                if within_bounds(
                        grid_width, grid_height, (new_x, new_y)
                ) and not contains_any_resource(
                    grid,
                    coords,
                    [SquaredBlockedArea, CircledBlockedArea, IsolatedArea],
                    grid_width,
                    grid_height,
                ):
                    return new_x, new_y
            return coords

        return maybe_move_to_adjacent_valid_tile()

    return coords


def perimeter_try_generating_base_station(
        grid_width,
        grid_height,
        base_station,
        grid,
) -> Tuple[int, int]:
    """
    Attempts to generate a valid base station at the perimeter of the grid. It tries
    repeatedly until valid coordinates are found.

    :param grid_width: Width of the grid.
    :param grid_height: Height of the grid.
    :param base_station: Initial base station coordinates (None if not generated).
    :param grid: The grid where the base station is placed.
    :return: Coordinates of the base station (tuple of x, y).
    """
    def generate_perimeter_pair(width: int, length: int) -> Tuple[int, int]:
        return (
            (0, random.randint(0, width))
            if random.choice([0, 1]) == 0
            else (random.randint(0, length), 0)
        )

    while base_station is None:
        try:
            tmp_bs = generate_perimeter_pair(grid_width, grid_height)
            base_station = validate_and_adjust_base_station(
                tmp_bs, grid_width, grid_height, grid
            )
        except ValueError:
            base_station = None
    return base_station


def big_center_try_generating_base_station(
        center_tassel,
        grid_width,
        grid_height,
        base_station,
        biggest_blocked_area,
        grid,
):
    """
    Attempts to generate a base station near the center of the largest blocked area.

    :param center_tassel: Coordinates of the central tassel (tuple of x, y).
    :param grid_width: Width of the grid.
    :param grid_height: Height of the grid.
    :param base_station: Initial base station coordinates (None if not generated).
    :param biggest_blocked_area: Coordinates of the largest blocked area.
    :param grid: The grid where the base station is placed.
    :return: Coordinates of the base station (tuple of x, y) or None if not found.
    """
    if biggest_blocked_area:
        while base_station is None:
            try:
                tmp_bs = generate_biggest_center_pair(
                    center_tassel, biggest_blocked_area
                )
                base_station = validate_and_adjust_base_station(
                    tmp_bs, grid_width, grid_height, grid
                )
            except ValueError:
                base_station = None
        return base_station
    else:
        return None


class StationGuidelinesStrategy:
    """
    Base class for strategies to locate a base station within a grid.
    """

    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height):
        """
        Abstract method to locate a base station within the grid.

        :param grid: The grid where the base station will be placed.
        :param center_tassel: Coordinates of the central tassel (tuple of x, y).
        :param biggest_blocked_area: Coordinates of the largest blocked area.
        :param grid_width: Width of the grid.
        :param grid_height: Height of the grid.
        """
        pass


class PerimeterPairStrategy(StationGuidelinesStrategy):
    """
    Strategy to place a base station along the perimeter of the grid.
    """

    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height):
        """
        Attempts to place a base station on the perimeter of the grid by generating
        random perimeter coordinates.

        :param grid: The grid where the base station will be placed.
        :param center_tassel: Coordinates of the central tassel (tuple of x, y).
        :param biggest_blocked_area: Coordinates of the largest blocked area.
        :param grid_width: Width of the grid.
        :param grid_height: Height of the grid.
        :return: Coordinates of the base station (tuple of x, y) or None if not found.
        """
        base_station = None
        attempt_limit = 35

        for _ in range(attempt_limit):
            base_station = perimeter_try_generating_base_station(
                grid_width, grid_height, base_station, grid
            )
            if base_station is not None and add_base_station(
                    grid, base_station, grid_width, grid_height
            ):
                print(f"BASE STATION: {base_station}")
                return base_station
        return None


class BiggestRandomPairStrategy(StationGuidelinesStrategy):
    """
    Strategy to place a base station randomly in the largest blocked area.
    """

    def locate_base_station(self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height) -> Union[
        Tuple[int, int], None]:
        """
        Attempts to place a base station in a randomly selected spot within the largest blocked area.

        :param grid: The grid where the base station will be placed.
        :param center_tassel: Coordinates of the central tassel (tuple of x, y).
        :param biggest_blocked_area: Coordinates of the largest blocked area.
        :param grid_width: Width of the grid.
        :param grid_height: Height of the grid.
        :return: Coordinates of the base station (tuple of x, y) or None if not found.
        """

        base_station = None
        attempt_limit = 35

        def generate_biggest_pair(bba):
            random_choice = random.choice(bba) if bba else None
            print(f"RANDOM CHOICE {random_choice}")
            return random_choice

        def big_random_try_generating_base_station(bs):
            while bs is None:
                try:
                    tmp_bs = generate_biggest_pair(biggest_blocked_area)
                    bs = validate_and_adjust_base_station(
                        tmp_bs, grid_width, grid_height, grid
                    )
                except ValueError:
                    bs = None
            return bs

        if biggest_blocked_area:
            for _ in range(attempt_limit):
                base_station = big_random_try_generating_base_station(base_station)
                if base_station is not None and add_base_station(
                        grid, base_station, grid_width, grid_height
                ):
                    return base_station
            return None
        else:
            return None


class BiggestCenterPairStrategy(StationGuidelinesStrategy):
    def locate_base_station(
            self, grid, center_tassel, biggest_blocked_area, grid_width, grid_height
    ) -> Union[Tuple[int, int], None]:
        base_station = None
        attempt_limit = 35

        for _ in range(attempt_limit):
            base_station = big_center_try_generating_base_station(
                center_tassel,
                grid_width,
                grid_height,
                base_station,
                biggest_blocked_area,
                grid,
            )
            if base_station is not None and add_base_station(
                    grid, base_station, grid_width, grid_height
            ):
                return base_station
        return None


def mowing_time(speed_robot, autonomy_robot_seconds, dim_tassel, k=1):
    """
    Estimates the time required for the robot to mow a given area based on the robot's
    speed, cutting diameter, and total area to mow.

    :param speed_robot: Speed of the robot (units per second).
    :param autonomy_robot_seconds: Robot's autonomy in seconds (battery life).
    :param dim_tassel: Total area to be mowed.
    :param k: Multiplier for the estimated time. Default is 1.
    :return: Estimated time in seconds for the mowing operation.
    """
    # Total time in seconds
    total_time_seconds = (dim_tassel / speed_robot) * k

    if total_time_seconds > autonomy_robot_seconds:
        print("Warning: The robot's autonomy might not be sufficient.")
        return 0

    return total_time_seconds


def get_contents_at_point(space, x, y, tol=1e-5):
    try:
        # Attempt to calculate neighbors from the given position
        neighbors = space.get_neighbors((float(x), float(y)), 0)
    except ValueError as e:
        # Handle expected error when there are no agents
        if "operands could not be broadcast together" in str(e):
            return []  # Return an empty list if there are no neighbors
        # For unexpected errors, re-raise the exception
        raise

    # Filter neighbors based on proximity (within the tolerance)
    contents = [agent for agent in neighbors if abs(agent.pos[0] - x) < tol and abs(agent.pos[1] - y) < tol]
    return contents

def euclidean_distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
    """
    Computes the Euclidean distance between two points.

    :param p1: First point (x, y).
    :param p2: Second point (x, y).
    :return: Euclidean distance between the two points.
    """
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)



def generate_biggest_center_pair(center_tassel, biggest_blocked_area):
    """
    Generates coordinates of the nearest point in the biggest blocked area relative to the center tassel.

    :param center_tassel: Coordinates of the central tassel (tuple of x, y).
    :param biggest_blocked_area: Coordinates of the largest blocked area.
    :return: Coordinates of the nearest point in the biggest blocked area (tuple of x, y).
    """
    if not biggest_blocked_area:
        return None

    nearest_tuple = min(
        biggest_blocked_area, key=lambda pos: euclidean_distance(pos, center_tassel)
    )

    return nearest_tuple


def load_data_from_file(file_path) -> Union[Tuple[dict, dict, dict], None]:
    """
    Loads data from a JSON file and returns robot, environment, and simulator data.

    :param file_path: Path to the JSON file.
    :return: Tuple containing robot, environment, and simulator data or None if the file does not exist.
    """
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r") as json_file:
        data = json.load(json_file)

    return data.get("robot", {}), data.get("env", {}), data.get("simulator", {})


def put_station_guidelines(
        strategy,
        grid,
        grid_width: int,
        grid_height: int,
        random_corner_perimeter: Tuple[int, int],
        central_tassel: Tuple[int, int],
        biggest_area_blocked
):
    """
    Places station guidelines on the grid, connecting the base station to a random corner or farthest point.

    :param strategy: The strategy object that locates the base station.
    :param grid: The grid object where cells are placed.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param random_corner_perimeter: A tuple representing a random corner on the grid perimeter.
    :param central_tassel: The central tassel coordinates.
    :param biggest_area_blocked: The area where the base station cannot be placed.
    :return: The position of the base station, or None if not found.
    """
    base_station_pos = strategy.locate_base_station(
        strategy, grid, central_tassel, biggest_area_blocked, grid_width, grid_height
    )

    if base_station_pos:
        if random_corner_perimeter:
            draw_line(
                base_station_pos[0],
                base_station_pos[1],
                random_corner_perimeter[0],
                random_corner_perimeter[1],
                grid,
                grid_width,
                grid_height,
            )

        # Find the farthest point from the base station
        farthest_point = find_farthest_point(
            grid_width, grid_height, base_station_pos[0], base_station_pos[1]
        )

        # If the farthest point is found, draw a line to it
        if farthest_point is not None:
            draw_line(
                base_station_pos[0],
                base_station_pos[1],
                farthest_point[0],
                farthest_point[1],
                grid,
                grid_width,
                grid_height,
            )

    return base_station_pos


def contains_any_resource(
        grid: ContinuousSpace, pos: Tuple[float, float], resource_types: List, grid_width: float, grid_height: float
) -> bool:
    """
    Checks if a position contains any resources from a specified list of resource types.

    :param grid: The grid object where cells are placed.
    :param pos: The (x, y) position to check.
    :param resource_types: A list of resource types to check for.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: True if any resource type is present, False otherwise.
    """
    for rtype in resource_types:
        if contains_resource(grid, pos, rtype, grid_width, grid_height):
            return True
    return False


def draw_line(
        x1: float, y1: float, x2: float, y2: float, grid: ContinuousSpace, grid_width, grid_height
) -> Set[Tuple[float, float]]:
    """
    Draws a line from one point to another on the grid, placing guidelines along the path.

    :param x1: The starting x-coordinate.
    :param y1: The starting y-coordinate.
    :param x2: The ending x-coordinate.
    :param y2: The ending y-coordinate.
    :param grid: The grid object where cells are placed.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: A set of cells that have been modified with guidelines.
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
            if not contains_any_resource(
                grid,
                (x, y),
                [
                    CircledBlockedArea,
                    SquaredBlockedArea,
                    IsolatedArea,
                    BaseStation,
                    GuideLine,
                ],
                grid_width,
                grid_height,
            ):
                cells_to_add.add((x, y))
                add_resource(grid, GuideLine((x, y)), x, y, grid_width, grid_height)

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
        else:
            break

    if within_bounds(grid_width, grid_height, (x2, y2)):
        cells_to_add.add((x2, y2))
        add_resource(grid, GuideLine((x2, y2)), x2, y2, grid_width, grid_height)

    return cells_to_add

def contains_resource(
        grid: ContinuousSpace, cell: Tuple[float, float], resource, grid_width: float, grid_height: float
) -> bool:
    """
    Checks if a specific resource is present in the specified cell on the grid.

    :param grid: The grid object where cells are placed.
    :param cell: The (x, y) coordinates of the cell.
    :param resource: The type of resource to check for.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: True if the resource is present, False otherwise.
    """
    x, y = cell

    # Ensure x and y are within bounds
    if 0 <= x < grid_width and 0 <= y < grid_height:
        cell_contents = get_contents_at_point(grid, x, y)

        specific_agent = next(
            (agent for agent in cell_contents if isinstance(agent, resource)), None
        )

        if specific_agent:
            return True
        else:
            return False
    else:
        return False

def add_base_station(
        grid, position: Tuple[int, int], grid_width: int, grid_height: int
) -> bool:
    """
    Adds a base station to the grid at the specified position.

    :param grid: The grid object where the base station will be placed.
    :param position: The (x, y) coordinates where the base station should be placed.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: True if the base station is added successfully, False if the position is out of bounds.
    """
    base_station = BaseStation((position[0], position[1]))

    return add_resource(
        grid, base_station, position[0], position[1], grid_width, grid_height
    )


def set_guideline_cell(x: int, y: int, grid, grid_width: int, grid_height: int) -> bool:
    """
    Sets a guideline cell in the grid if the position is valid and not blocked by other resources.

    :param x: The x-coordinate of the cell.
    :param y: The y-coordinate of the cell.
    :param grid: The grid object where cells are placed.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: True if the guideline cell is successfully set, False if out of bounds.
    """
    # Check if the cell is within the grid boundaries (after wrapping)
    if not within_bounds(grid_width, grid_height, (x, y)):
        return False

    blocked_areas = [
        CircledBlockedArea,
        SquaredBlockedArea,
        IsolatedArea,
        BaseStation,
        GuideLine,
    ]

    # Check for existing resources at the wrapped cell
    if not contains_any_resource(
            grid,
            (x, y),
            blocked_areas,
            grid_width,
            grid_height,
    ):
        add_resource(grid, GuideLine((x, y)), x, y, grid_width, grid_height)


def add_resource(grid: ContinuousSpace, resource, x: float, y: float, grid_width, grid_height) -> bool:
    """
    Adds a resource to the grid at the specified position.

    :param grid: The grid object where the resource will be placed.
    :param resource: The resource to be added.
    :param x: The x-coordinate of the position.
    :param y: The y-coordinate of the position.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: True if the resource is added successfully, False if the position is out of bounds.
    """
    if within_bounds(grid_width, grid_height, (x, y)):
        grid.place_agent(resource, (x, y))
        return True
    else:
        return False


def within_bounds(grid_width: int, grid_height: int, pos) -> bool:
    """
    Checks if a position is within the bounds of the grid.

    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param pos: The (x, y) position to check.
    :return: True if the position is within bounds, False otherwise.
    """
    return 0 <= pos[0] < grid_width and 0 <= pos[1] < grid_height


def find_farthest_point(grid_width: int, grid_height: int, fx: int, fy: int) -> Tuple[int, int]:
    """
    Finds the farthest eligible point from the given position in the grid.

    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param fx: The x-coordinate of the reference point.
    :param fy: The y-coordinate of the reference point.
    :return: The coordinates of the farthest point from (fx, fy).
    """
    max_dist = 0
    result = (-1, -1)

    eligible_points = [
        (0, grid_height),
        (grid_width, 0),
        (0, 0),
        (grid_width, grid_height),
    ]

    for point in eligible_points:
        dist = euclidean_distance((fx, fy), point)
        if dist > max_dist:
            max_dist = dist
            result = point
            if dist > grid_width or dist > grid_height:  # Early return if very far
                return result

    return result


def populate_perimeter_guidelines(grid_width: int, grid_height: int, grid):
    """
    Populates the perimeter of the grid with guideline cells.

    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param grid: The grid object where cells are placed.
    """
    for x in range(0, grid_height):
        set_guideline_cell(x, 0, grid, grid_width, grid_height)

    for x in range(0, grid_height):
        set_guideline_cell(x, grid_width, grid, grid_width, grid_height)

    for y in range(0, grid_width):
        set_guideline_cell(0, y, grid, grid_width, grid_height)

    for y in range(0, grid_width):
        set_guideline_cell(grid_height, y, grid, grid_width, grid_height)


def get_grass_tassel(grass_tassels, pos):
    """
    Retrieves a grass tassel at the specified position.

    :param grass_tassels: A list of tuples, where each tuple is (x, y, tassel).
    :param pos: The (x, y) position to search for the tassel.
    :return: The first grass tassel at the given position, or None if not found.
    """
    for tassel_info in grass_tassels:
        if tassel_info.pos == pos:
            return tassel_info
    return None

def find_central_tassel(rows: int, cols: int) -> Tuple[int, int]:
    """
    Finds the central tassel of a grid with the given rows and columns.

    :param rows: The number of rows in the grid.
    :param cols: The number of columns in the grid.
    :return: The coordinates of the central tassel.
    """
    if rows % 2 == 1 and cols % 2 == 1:
        central_row = rows // 2
        central_col = cols // 2
        return central_row, central_col
    else:
        central_row = rows // 2 if rows % 2 == 1 else rows // 2 - 1
        central_col = cols // 2 if cols % 2 == 1 else cols // 2 - 1
        return central_row, central_col


def profile_code(func):
    """
    Profiles the execution time of a function.

    :param func: The function to be profiled.
    :return: A wrapped function with profiling enabled.
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
