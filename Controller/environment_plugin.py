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
from mesa.space import ContinuousSpace
from scipy.spatial import KDTree
from Controller.random_grid import RandomGrid
from Model.agents import (
    SquaredBlockedArea,
    CircledBlockedArea,
    IsolatedArea,
    Opening,
    GuideLine,
)
from Utils.utils import (
    set_guideline_cell,
    draw_line,
    within_bounds,
    contains_any_resource,
    add_resource,
)


def build_squared_isolated_area(
        x_start,
        y_start,
        isolated_area_width,
        isolated_area_length,
        grid,
        dim_opening,
        grid_width,
        grid_height,
):
    """
    Create a squared isolated area in the grid with an optional opening.

    :param x_start: The x-coordinate of the starting point.
    :param y_start: The y-coordinate of the starting point.
    :param isolated_area_width: The width of the isolated area.
    :param isolated_area_length: The length of the isolated area.
    :param grid: The grid where the area will be created.
    :param dim_opening: The dimension of the opening to be created.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: A random point in the isolated area to be used as an opening.
    """
    enclosure_tassels = []

    def create_resources(x_range, y_range):
        """Create resources within specified ranges."""
        for x in x_range:
            for y in y_range:
                new_resource = IsolatedArea((x, y))
                res = add_resource(grid, new_resource, x, y, grid_width, grid_height)
                if res and x != 0 and (y != 0 and x != grid_height and y != grid_width):
                    enclosure_tassels.append((x, y))

    if x_start == 0:
        if y_start == 0:
            create_resources(
                range(x_start, x_start + isolated_area_width),
                range(y_start, y_start + isolated_area_length),
            )

        else:
            create_resources(
                range(x_start, x_start + isolated_area_width),
                range(y_start - isolated_area_length, y_start),
            )
    elif y_start == 0:
        create_resources(
            range(x_start - isolated_area_width, x_start),
            range(y_start, y_start + isolated_area_length),
        )
    else:
        create_resources(
            range(x_start - isolated_area_width, x_start),
            range(y_start - isolated_area_length, y_start),
        )

    e_tassel = []
    # Remove points in the corners from enclosure_tassels
    for point in enclosure_tassels:
        for neighbor in grid.get_neighbors(point, radius=1, include_center=False):
            if neighbor not in enclosure_tassels and dim_opening > 0:
                e_tassel.append(point)
                dim_opening -= 1

    if not e_tassel:
        return

    for opening in e_tassel:
        opening_new = Opening(opening)
        add_resource(
            grid, opening_new, opening[0], opening[1], grid_width, grid_height
        )

    return random.choice(e_tassel)


def circular_isolation(
        grid, radius, x_start, y_start, dim_opening, grid_width, grid_height
):
    """
    Create a circular isolated area in the grid with optional openings.

    :param grid: The grid where the area will be created.
    :param radius: The radius of the circular isolated area.
    :param x_start: The x-coordinate of the center of the circle.
    :param y_start: The y-coordinate of the center of the circle.
    :param dim_opening: The dimension of the openings to be created.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: A random point in the isolated area to be used as an opening.
    """
    enclosure_tassels = []
    for i in range(-radius, radius + 1):
        for j in range(-radius, radius + 1):
            if i ** 2 + j ** 2 <= radius ** 2:
                p = (x_start + i, y_start + j)
                if add_resource(grid, IsolatedArea(p), *p, grid_width, grid_height):
                    if any(
                            nb in enclosure_tassels
                            for nb in grid.get_neighbors(p, radius=1, include_center=False)
                    ):
                        enclosure_tassels.append(p)

    if enclosure_tassels:
        current_opening = random.choice(enclosure_tassels)
        while dim_opening > 0:
            index_current_opening = enclosure_tassels.index(current_opening)
            next_openings = [
                (index_current_opening + i) % len(enclosure_tassels) for i in [-1, 0, 1]
            ]
            current_opening = enclosure_tassels[random.choice(next_openings)]
            add_resource(
                grid,
                Opening(current_opening),
                *current_opening,
                grid_width,
                grid_height,
            )
            dim_opening -= 1

    return random.choice(enclosure_tassels)


def initialize_isolated_area(
        grid,
        isolated_shape,
        isolated_length,
        isolated_width,
        grid_width,
        grid_height,
        radius,
):
    """
    Initialize isolated areas in the grid based on the specified shape and dimensions.

    :param grid: The grid where the area will be created.
    :param isolated_shape: The shape of the isolated area ("Square" or "Circle").
    :param isolated_length: The length of the isolated area.
    :param isolated_width: The width of the isolated area.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param radius: The radius for circular isolated areas.
    :return: A random point in the isolated area to be used as an opening, if applicable.
    """
    def choose_random_corner():
        seed = random.random()
        if seed == 0:
            return 0, 0
        elif seed == (grid_width + grid_height):
            return grid_height, grid_width
        elif seed % 2 == 0:
            return 0, grid_width
        else:
            return grid_height, 0

    x_corner, y_corner = choose_random_corner()
    if isolated_width != 0:
        dim_opening = random.randint(1, isolated_width) % grid_width

        if isolated_shape == "Square":
            return build_squared_isolated_area(
                x_corner,
                y_corner,
                isolated_length,
                isolated_width,
                grid,
                dim_opening,
                grid_width,
                grid_height,
            )
        else:
            return circular_isolation(
                grid, radius, x_corner, y_corner, dim_opening, grid_width, grid_height
            )


def calculate_variance(value1, value2):
    """
    Calculate the variance between two values.

    :param value1: The first value.
    :param value2: The second value.
    :return: The variance between the two values.
    """
    mean = (value1 + value2) / 2
    sum_of_squares = abs((value1 - mean) ** 2 + (value2 - mean) ** 2)
    return int(sum_of_squares / 2)


def find_and_draw_lines(grid, neighbors, grid_width, grid_height):
    """
    Find and draw lines connecting neighboring cells to the perimeter.

    :param grid: The grid where the lines will be drawn.
    :param neighbors: A list of neighboring cells.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    """

    def find_perimeter_cells(width, height):
        return [
            (x, y)
            for x in range(height)
            for y in range(width)
            if x in {0, height} or y in {0, width}
        ]

    def neighbor_on_the_perimeter(n, perimeter_cells):
        perimeter_set = set(perimeter_cells)
        return any(neighbor in perimeter_set for neighbor in n)

    perimeter_guidelines = find_perimeter_cells(grid_width, grid_height)

    if neighbors and not neighbor_on_the_perimeter(neighbors, perimeter_guidelines):
        tree = KDTree(neighbors)
        closest_neighbor, nearest_perimeter, min_distance = None, None, float("inf")
        for pg_cell in perimeter_guidelines:
            distance, index = tree.query(pg_cell)
            if distance < min_distance:
                closest_neighbor = neighbors[index]
                min_distance = distance
                nearest_perimeter = pg_cell

        if closest_neighbor:
            draw_line(
                closest_neighbor[0],
                closest_neighbor[1],
                nearest_perimeter[0],
                nearest_perimeter[1],
                grid,
                grid_width,
                grid_height,
            )


def fill_circular_blocked_area(
        start_x,
        start_y,
        rad,
        grid,
        grid_width,
        grid_height,
        dim_tassel,
):
    """
    Fill a circular blocked area in the grid.

    :param grid: The grid where the area will be created.
    :param start_x: The x-coordinate of the center of the circle.
    :param start_y: The y-coordinate of the center of the circle.
    :param rad: The radius of the circular blocked area.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param dim_tassel: Dimension tassel.
    """
    blocked_tassels = []
    neighbors = grid.get_neighbors(pos=(start_x, start_y), include_center=True, radius=rad)
    for neighbor in neighbors:
        if not is_near_opening(
                grid, (start_x, start_y), grid_width, grid_height
        ):
            new_resource = CircledBlockedArea(
                neighbor
            )  # Creating a new blocked area resource.

            add_resource(
                grid,
                new_resource,
                neighbor[0],
                neighbor[1],
                grid_width,
                grid_height,
            )
            blocked_tassels.append(neighbor)

    for bt in blocked_tassels:
        aux_lines(bt, grid, grid_width, grid_height)


def add_squared_area(
        coord_x,
        coord_y,
        min_width_blocked,
        max_height_blocked,
        max_width_blocked,
        min_height_blocked,
        grid,
        grid_width,
        grid_height,
        dim_tassel,
):
    """
    Add a squared blocked area to the grid based on specified dimensions and position.

    :param coord_x: The x-coordinate of the starting point of the squared area.
    :param coord_y: The y-coordinate of the starting point of the squared area.
    :param min_width_blocked: The minimum width of the blocked area.
    :param max_height_blocked: The maximum height of the blocked area.
    :param max_width_blocked: The maximum width of the blocked area.
    :param min_height_blocked: The minimum height of the blocked area.
    :param grid: The grid to which the blocked area will be added.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param dim_tassel: The dimension of each tassel.
    :return: A list of coordinates representing the blocked area.
    """
    columns = calculate_variance(min_width_blocked, max_width_blocked)
    rows = calculate_variance(min_height_blocked, max_height_blocked)
    num_rows = math.ceil((columns + min_width_blocked) / dim_tassel)
    num_columns = math.ceil((rows + min_height_blocked) / dim_tassel)
    blocked_area = []
    resources = set()

    for j in range(num_rows):
        tassel_x = coord_x + j
        for i in range(num_columns):
            tassel_y = coord_y + i
            if (
                    within_bounds(grid_width, grid_height, (tassel_x, tassel_y))
                    and not is_near_opening(
                grid, (tassel_x, tassel_y), grid_width, grid_height
            )
                    and (tassel_x, tassel_y) not in resources
            ):
                add_resource(
                    grid,
                    SquaredBlockedArea((tassel_x, tassel_y)),
                    tassel_x,
                    tassel_y,
                    grid_width,
                    grid_height,
                )
                resources.add((tassel_x, tassel_y))
                blocked_area.append((tassel_x, tassel_y))

    neighbors = []
    for tassel in blocked_area:
        for nb in grid.get_neighbors(tassel, include_center=False, radius=1):
            if nb not in blocked_area and not is_near_opening(
                    grid, tassel, grid_width, grid_height
            ):
                neighbors.append((nb[0], nb[1]))

    for neighbor in neighbors:
        set_guideline_cell(neighbor[0], neighbor[1], grid, grid_width, grid_height)

    find_and_draw_lines(grid, neighbors, grid_width, grid_height)

    return blocked_area


def aux_lines(blocked_area, grid, grid_width, grid_height):  # sourcery skip: use-named-expression
    """
    Add guideline lines around the blocked area based on its neighbors.

    :param blocked_area: List of coordinates representing the blocked area.
    :param grid: The grid to which the guidelines will be added.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    """

    def get_circular_neighbors(cell):
        """
        Get the circular neighbors of a given cell.

        :param cell: The coordinate of the cell.
        :return: A list of valid circular neighbors.
        """

        def _valid_coordinate(h, max_val):
            """Check if a coordinate value is inside grid bounds."""
            return -1 < h < max_val

        n = []  # Initialize empty list to store valid neighbor coordinates
        x, y = cell

        # Loop through possible relative offsets (-1, 0, 1) along both axes
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = x + dx, y + dy

                # Check if the potential neighbor is within grid boundaries and has no common tassel
                if (
                        _valid_coordinate(nx, grid_width)
                        and _valid_coordinate(ny, grid_height)
                ) and ((abs(dx) + abs(dy)) == 1):
                    n.append((nx, ny))

        return n

    neighbors = get_circular_neighbors(blocked_area)

    for neighbor in neighbors:
        set_guideline_cell(neighbor[0], neighbor[1], grid, grid_width, grid_height)

    find_and_draw_lines(grid, neighbors, grid_width, grid_height)


def is_near_opening(grid, point, grid_width, grid_height):
    """
    Check if a point is near an opening on the grid.

    :param grid: The grid to check.
    :param point: The coordinate of the point.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :return: True if the point is near an opening, False otherwise.
    """
    neighbors = grid.get_neighbors(point, include_center=False, radius=1)
    return any(
        contains_any_resource(grid, nb, [Opening], grid_width, grid_height)
        for nb in neighbors
    )


def generate_valid_agent_position(grid, grid_width, grid_height, max_attempts=35):
    """
    Generate a valid position for an agent that is not blocked or near an opening.

    :param grid: The grid where the position will be checked.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param max_attempts: The maximum number of attempts to find a valid position.
    :return: A tuple representing the valid position (x, y), or None if no valid position is found.
    """
    blocked_types = [
        IsolatedArea,
        SquaredBlockedArea,
        CircledBlockedArea,
        Opening,
        GuideLine,
    ]
    for _ in range(max_attempts):
        x, y = (random.uniform(0, grid_width), random.uniform(0, grid_height))

        if (
                within_bounds(grid_width, grid_height, (x, y))
                and not contains_any_resource(
            grid,
            (x, y),
            blocked_types,
            grid_width,
            grid_height,
        )
        ):
            return x, y
    return None


def populate_blocked_areas(
        grid,
        num_squares,
        num_circles,
        min_width_blocked,
        max_width_blocked,
        min_height_blocked,
        max_height_blocked,
        ray,
        grid_width,
        grid_height,
        dim_tassel,
):
    """
    Populate the grid with blocked areas, including squares and circles.

    :param grid: The grid to populate.
    :param num_squares: The number of square blocked areas to add.
    :param num_circles: The number of circular blocked areas to add.
    :param min_width_blocked: The minimum width for square blocked areas.
    :param max_width_blocked: The maximum width for square blocked areas.
    :param min_height_blocked: The minimum height for square blocked areas.
    :param max_height_blocked: The maximum height for square blocked areas.
    :param ray: The radius for circular blocked areas.
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param dim_tassel: The dimension of each tassel.
    :return: A list of coordinates representing the blocked areas.
    """
    blocked_tassels = []
    max_size = 0

    for _ in range(num_squares):
        pos = generate_valid_agent_position(grid, grid_width, grid_height)
        if pos:
            blocked_tassels = add_squared_area(
                pos[0],
                pos[1],
                min_width_blocked,
                max_height_blocked,
                max_width_blocked,
                min_height_blocked,
                grid,
                grid_width,
                grid_height,
                dim_tassel,
            )
            if len(blocked_tassels) > max_size:
                max_size = len(blocked_tassels)

    for _ in range(num_circles):
        pos = generate_valid_agent_position(grid, grid_width, grid_height)
        if pos:
            fill_circular_blocked_area(
                pos[0], pos[1], ray, grid, grid_width, grid_height, dim_tassel
            )

    if len(blocked_tassels) > 0:
        return blocked_tassels


class DefaultRandomGrid(RandomGrid):
    """
    A default grid initialized with random isolated and blocked areas.

    :param width: The width of the grid.
    :param length: The length of the grid.
    :param isolated_shape: The shape of isolated areas.
    :param num_blocked_squares: The number of square blocked areas.
    :param min_width_square: The minimum width of square blocked areas.
    :param max_width_square: The maximum width of square blocked areas.
    :param min_height_square: The minimum height of square blocked areas.
    :param max_height_square: The maximum height of square blocked areas.
    :param num_blocked_circles: The number of circular blocked areas.
    :param min_ray: The minimum radius for circular blocked areas.
    :param max_ray: The maximum radius for circular blocked areas.
    :param isolated_area_min_length: The minimum length of isolated areas.
    :param isolated_area_max_length: The maximum length of isolated areas.
    :param min_radius: The minimum radius for isolated areas.
    :param max_radius: The maximum radius for isolated areas.
    :param isolated_area_min_width: The minimum width of isolated areas.
    :param isolated_area_max_width: The maximum width of isolated areas.
    :param dim_tassel: The dimension of each tassel.
    """

    def __init__(
            self,
            width,
            length,
            isolated_shape,
            num_blocked_squares,
            min_width_square,
            max_width_square,
            min_height_square,
            max_height_square,
            num_blocked_circles,
            min_ray,
            max_ray,
            isolated_area_min_length,
            isolated_area_max_length,
            min_radius,
            max_radius,
            isolated_area_min_width,
            isolated_area_max_width,
            dim_tassel,
    ):
        super().__init__(width, length)
        self._isolated_width = int(
            (
                    isolated_area_min_width
                    + random.randint(
                0,
                calculate_variance(
                    isolated_area_min_width, isolated_area_max_width
                ),
            )
            )
            / dim_tassel
        )
        self._isolated_length = int(
            (
                    isolated_area_min_length
                    + random.randint(
                0,
                calculate_variance(
                    isolated_area_min_length, isolated_area_max_length
                ),
            )
            )
            / dim_tassel
        )
        self._ray = min_ray + (calculate_variance(min_ray, max_ray))

        self._isolated_shape = isolated_shape
        self._min_height_blocked = min_height_square
        self._max_height_blocked = max_height_square

        self._min_width_blocked = min_width_square
        self._max_width_blocked = max_width_square
        self._radius = int(
            (min_radius + random.randint(0, calculate_variance(min_radius, max_radius)))
            / dim_tassel
        )

        self._num_blocked_squares = num_blocked_squares
        self._num_blocked_circles = num_blocked_circles
        self._dim_tassel = dim_tassel

        self._grid = ContinuousSpace(width, length, torus=False)

    def begin(self):
        """
        Begin populating the grid with isolated areas and blocked areas.

        :return: A tuple containing the grid, a random corner, and a list of blocked tassels.
        """
        random_corner = initialize_isolated_area(
            self._grid,
            self._isolated_shape,
            self._isolated_length,
            self._isolated_width,
            self._width,
            self._length,
            self._radius,
        )

        blocked_tassels = populate_blocked_areas(
            self._grid,
            self._num_blocked_squares,
            self._num_blocked_circles,
            self._min_width_blocked,
            self._max_width_blocked,
            self._min_height_blocked,
            self._max_height_blocked,
            self._ray,
            self._width,
            self._length,
            self._dim_tassel,
        )

        return self._grid, random_corner, blocked_tassels


def add_area(grid, t, tassels, opening_tassels, grid_width, grid_height):
    """
    Add areas to the grid based on the type specified.

    :param grid: The grid to which areas will be added.
    :param t: The type of area ("circles", "squares", or "is_area").
    :param tassels: The list of coordinates for the area.
    :param opening_tassels: The list of coordinates for openings (used for "is_area").
    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    """
    if t == "circles":
        for tassel in tassels:
            add_resource(
                grid,
                CircledBlockedArea((tassel[0], tassel[1])),
                tassel[0],
                tassel[1],
                grid_width,
                grid_height,
            )
        for t in tassels:
            aux_lines(t, grid, grid_width, grid_height)
    elif t == "squares":
        for tassel in tassels:
            add_resource(
                grid,
                SquaredBlockedArea((tassel[0], tassel[1])),
                tassel[0],
                tassel[1],
                grid_width,
                grid_height,
            )
        for t in tassels:
            aux_lines(t, grid, grid_width, grid_height)
    elif t == "is_area":
        for tassel in tassels:
            add_resource(
                grid,
                IsolatedArea((tassel[0], tassel[1])),
                tassel[0],
                tassel[1],
                grid_width,
                grid_height,
            )
        for tassel in opening_tassels:
            add_resource(
                grid,
                Opening((tassel[0], tassel[1])),
                tassel[0],
                tassel[1],
                grid_width,
                grid_height,
            )


class DefaultCreatedGrid(RandomGrid):
    """
    A default grid created from raw shape data.

    :param grid_width: The width of the grid.
    :param grid_height: The height of the grid.
    :param data_e: The raw shape data.
    :param raw_shapes: The raw shapes used for grid creation.
    :param dim_tassel: The dimension of each tassel.
    """

    def __init__(self, grid_width, grid_height, data_e, raw_shapes, dim_tassel):
        super().__init__(grid_width, grid_height)
        self.data_e = data_e
        self.grid = ContinuousSpace(grid_width, grid_height, torus=False)
        self.random_corner = (-1, -1)
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.raw_shapes = raw_shapes
        self.dim_tassel = dim_tassel

    def begin(self):
        """
        Populate the grid based on raw shape data.

        :return: A tuple containing the grid, a random corner, and a list of squares.
        """
        circles = self.data_e["circles"]
        circles_rounded = set()
        squares_rounded = []
        t = None

        if circles:
            for t in circles:
                x, y = (int(t[0]), int(t[1]))
                circles_rounded.add((x, y))

            add_area(self.grid, "circles", circles_rounded, [], self.grid_width, self.grid_height)

        squares = self.data_e["squares"]

        if squares:
            for t in squares:
                x, y = (int(t[0]), int(t[1]))
                squares_rounded.append((x, y))
            add_area(self.grid, "squares", squares_rounded, [], self.grid_width, self.grid_height)

        opening = self.data_e["opening"]
        isolated_area = self.data_e["isolated_area"]
        if opening and isolated_area:
            opening_rounded = []
            for t in opening:
                x, y = (math.ceil(t[0]), math.ceil(t[1]))
                opening_rounded.append((x, y))

            isolated_area_rounded = set()
            for tassel in isolated_area:
                x, y = (math.ceil(tassel[0]), math.ceil(tassel[1]))
                isolated_area_rounded.add((x, y))
            add_area(self.grid, "is_area", isolated_area_rounded, opening_rounded, self.grid_width, self.grid_height)
            self.random_corner = random.choice(opening)
            t = (math.ceil(self.random_corner[0]), math.ceil(self.random_corner[1]))

        return self.grid, t, squares_rounded