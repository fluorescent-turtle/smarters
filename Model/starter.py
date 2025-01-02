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

import copy
import importlib
import logging
import math
import os
import random
import stat
from datetime import datetime
from pathlib import Path

import pandas as pd

from Controller.environment_plugin import DefaultRandomGrid, DefaultCreatedGrid
from Controller.robot_plugin import DefaultMovementPlugin
from Model.model import Simulator
from Utils.utils import (
    load_data_from_file,
    PerimeterPairStrategy,
    populate_perimeter_guidelines, get_contents_at_point,
)


def _initialize_plugins(plugin_names):
    """
    Dynamically import and instantiate plugin classes.

    :param plugin_names: List of plugin class names to import and instantiate.
    :return: List of initialized plugin instances.
    """
    plugins = []
    for name in plugin_names:
        try:
            module = importlib.import_module(f"./Controller/{name}")
            plugin_class = getattr(module, name)
            plugins.append(plugin_class())
        except ImportError as e:
            logging.error(f"Error importing plugin '{name}': {e}")
    return plugins


class Starter:
    def __init__(self, env_plugin_names, robot_plugin_names, filename):
        self.env_plugins = _initialize_plugins(env_plugin_names)
        self.robot_plugins = _initialize_plugins(robot_plugin_names)
        self.filename = filename

    def run(self):
        """
        Execute the model with the initialized plugins.
        """
        run_model_with_parameters(self.env_plugins, self.robot_plugins[0] if self.robot_plugins else None,
                                  self.filename)


def execute_plugins(env_plugins, grid_width, grid_height):
    """
    Apply environment plugins to initialize the grid.

    :param env_plugins: List of environment plugins to execute.
    :param grid_width: Width of the grid.
    :param grid_height: Height of the grid.
    :return: Initialized grid and corner position.
    """
    grid, corner = None, None
    for plugin in env_plugins:
        try:
            grid, corner = plugin(grid_width, grid_height).begin()
        except Exception as e:
            logging.error(f"Error in environment plugin: {e}")
    return grid, corner


def create_grid(grid_type, data_e, grid_width, grid_height, dim_tassel, env_plugins):
    """
    Create and initialize the grid based on the specified type.

    :param grid_type: Type of the grid ("default" or "random").
    :param data_e: Environment data.
    :param grid_width: Width of the grid.
    :param grid_height: Height of the grid.
    :param dim_tassel: Dimension of each tassel.
    :param env_plugins: List of environment plugins.
    :return: Initialized grid and additional information.
    """
    if grid_type == "default":
        raw_shapes = data_e["circles"] + data_e["squares"] + data_e["isolated_area"]
        return DefaultCreatedGrid(
            grid_width=grid_width,
            grid_height=grid_height,
            data_e=data_e,
            raw_shapes=raw_shapes,
            dim_tassel=dim_tassel,
        ).begin()

    elif grid_type == "random":
        required_keys = [
            "min_width_square",
            "max_width_square",
            "min_height_square",
            "max_height_square",
            "min_ray",
            "max_ray",
            "isolated_area_min_length",
            "isolated_area_max_length",
            "min_radius",
            "max_radius",
            "isolated_area_min_width",
            "isolated_area_max_width",
            "num_blocked_squares",
            "num_blocked_circles",
        ]
        params = {key: int(data_e[key]) for key in required_keys if key in data_e}
        params.update(
            {
                "isolated_shape": data_e.get("isolated_area_shape"),
                "dim_tassel": dim_tassel,
            }
        )
        return DefaultRandomGrid(grid_width, grid_height, **params).begin()

    else:
        if env_plugins:
            return execute_plugins(env_plugins, grid_width, grid_height)


def split_at_first_hyphen(string):
    """
    Split a string at the first hyphen.

    :param string: The string to split.
    :return: Tuple containing the part before and after the hyphen.
    """
    parts = string.split("-", 1)
    return (parts[0].strip(), parts[1].strip()) if len(parts) > 1 else (parts[0], "")


def process_grid_data(
        grid_height, grid_width, map_index, repetition_index, filename, dim_tassel, grid
):
    """
    Save grid data to a CSV file.

    :param grid_height: Height of the grid.
    :param grid_width: Width of the grid.
    :param map_index: Index of the current map.
    :param repetition_index: Index of the current repetition.
    :param filename: Filename for the output CSV.
    :param dim_tassel: Dimension of each tassel.
    :param grid: The grid to process.
    """
    external_data = [["" for _ in range(grid_height)] for _ in range(grid_width)]

    for x in range(grid_width):
        for y in range(grid_height):
            external_data[x][y] = get_contents_at_point(grid, x, y)

    df = pd.DataFrame(external_data)
    df = df.rename(columns={j: j * dim_tassel for j in range(grid_height)})
    df.insert(0, "num_mappa", map_index)
    df.insert(1, "ripetizione", repetition_index)
    df.insert(2, "x", [dim_tassel * i for i in range(grid_width)])

    output_dir = os.path.realpath("../smarters/View/")

    # Use Path to check if the directory exists, and create it if it doesn't
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    os.chmod(output_dir, stat.S_IRWXU)

    df.to_csv(os.path.join(output_dir, filename), index=False)


def get_current_datetime():
    """
    Get the current date and time formatted as a string.

    :return: Current date and time in "YYYY-MM-DD_HH-MM-SS" format.
    """
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def runner(
        robot_plugin,
        grid,
        cycles,
        base_station_pos,
        data_r,
        grid_width,
        grid_height,
        i,
        j,
        cycle_data,
        filename,
        dim_tassel,
        recharge
):
    """
    Execute the simulation and process grid data.

    :param recharge: Recharge time.
    :param robot_plugin: Robot plugin to use.
    :param grid: The grid to simulate on.
    :param cycles: Number of simulation cycles.
    :param base_station_pos: Position of the base station.
    :param data_r: Robot data.
    :param grid_width: Width of the grid.
    :param grid_height: Height of the grid.
    :param i: Index of the current map.
    :param j: Index of the current repetition.
    :param cycle_data: List to collect cycle data.
    :param filename: Filename for saving the output CSV.
    :param dim_tassel: Dimension of each tassel.
    """
    movement_type, boing = split_at_first_hyphen(data_r["cutting_mode"])
    plugin = (
        robot_plugin(grid, base_station_pos)
        if robot_plugin
        else DefaultMovementPlugin(
            movement_type=movement_type,
            grid=grid,
            base_station_pos=base_station_pos,
            boing=boing,
            cut_diameter=data_r["cutting_diameter"],
            grid_width=grid_width,
            grid_height=grid_height,
            dim_tassel=dim_tassel,
        )
    )

    process_grid_data(grid_height, grid_width, i, j, filename, dim_tassel, grid)

    current_data = []
    simulator = Simulator(grid, cycles, base_station_pos, plugin, data_r["speed"],
                          (data_r["autonomy"] - (data_r["autonomy"] * (10 / 100))) * 60, i, j, current_data, filename,
                          dim_tassel, recharge)
    simulator.step()
    cycle_data.append(current_data)


def run_model_with_parameters(env_plugins, robot_plugin, filename):
    """
    Run the simulation model with the given plugins.

    :param filename: Data file name
    :param env_plugins: List of environment plugins.
    :param robot_plugin: Robot plugin to use.
    """

    try:
        data_r, data_e, data_s = load_data_from_file(Path(filename.strip()).resolve())
    except TypeError as e:
        print(f"Error: {e}")
        exit()
    repetitions = data_s["repetitions"]
    num_maps = data_s["num_maps"]
    cycles = data_s["cycle"] * 60  # Convert to seconds
    dim_tassel = data_s["dim_tassel"]
    created = False
    grid_width = math.ceil(data_e["width"] / dim_tassel)
    grid_height = math.ceil(data_e["length"] / dim_tassel)
    recharge = data_r["recharge"]

    # Set random seed for reproducibility
    random.seed(random.randint(0, grid_width * grid_height))

    for i in range(num_maps):
        cycle_data = []
        grid, random_corner, biggest_area_blocked = create_grid(
            "default"
            if data_e.get("circles") is not None and not created
            else "random",
            data_e,
            grid_width,
            grid_height,
            dim_tassel,
            env_plugins,
        )
        created = True

        # Save initial grid data
        process_grid_data(
            grid_height,
            grid_width,
            i,
            0,
            f"grid{get_current_datetime()}.csv",
            dim_tassel,
            grid,
        )

        # Populate perimeter guidelines
        populate_perimeter_guidelines(grid_width, grid_height, grid)

        # Create copies of the grid for different strategies
        grids = [copy.deepcopy(grid) for _ in range(3)]

        for j in range(repetitions):
            # Run the experiment with the specified strategy.
            runner(robot_plugin, grids[0], cycles, (int(grid_height / 3), 0), data_r, grid_width, grid_height, i, j,
                   cycle_data, f"perimeter_model{get_current_datetime()}.csv", dim_tassel, recharge)

            """
            # List of active strategies for base station placement.
            # Uncomment if needed.
            strategies = [
                (PerimeterPairStrategy, f"perimeter_model{get_current_datetime()}.csv"),
                (BiggestRandomPairStrategy, f"big_model{get_current_datetime()}.csv"),
                (BiggestCenterPairStrategy, f"bigcenter_model{get_current_datetime()}.csv")
            ]
            
            # Optionally add a base station according to the strategy.
            for strategy, filename in strategies:
                base_station_pos = put_station_guidelines(
                    strategy,
                    grids[strategies.index((strategy, filename))],
                    grid_width,
                    grid_height,
                    random_corner,
                    find_central_tassel(grid_width, grid_height) if strategy == BiggestCenterPairStrategy else None,
                    biggest_area_blocked
                )

                if base_station_pos:

                # Run the experiment with the specified strategy.
                runner(
                    robot_plugin,
                    grids[strategies.index((strategy, filename))],
                    cycles,
                    base_station_pos,
                    data_r,
                    grid_width,
                    grid_height,
                    i,
                    j,
                    cycle_data,
                    filename,
                    dim_tassel,
                )"""
