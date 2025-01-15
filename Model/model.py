""" Copyright 2024 Sara Grecu

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import math
import os
import stat
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import mesa
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

from Model.agents import (
    GrassTassel,
    Robot,
    SquaredBlockedArea,
    CircledBlockedArea,
)
from Utils.utils import get_contents_at_point

class Simulator(mesa.Model):
    def __init__(
            self,
            grid,
            cycles,
            base_station_pos,
            robot_plugin,
            speed,
            autonomy,
            i,
            j,
            cycle_data,
            filename,
            dim_tassel,
            recharge
    ):
        """
        Initialize the simulator for the grass cutting simulation.

        :param recharge: Recharge time in minutes.
        :param grid: The simulation grid.
        :param cycles: Number of cycles to run the simulation.
        :param base_station_pos: The position of the base station.
        :param robot_plugin: The robot plugin used for the simulation.
        :param speed: The speed of the robot.
        :param autonomy: The autonomy of the robot in terms of cycles it can run.
        :param i: The map number (identifier).
        :param j: The repetition number of the simulation run.
        :param cycle_data: Data collected during the simulation cycles.
        :param filename: The filename for saving the data.
        :param dim_tassel: The dimension of the grass tassel.
        """
        super().__init__()
        self.schedule = mesa.time.StagedActivation(self)  # Initialize a schedule for agents
        self.grid = grid  # Assign the simulation grid
        self.cycles = cycles  # Set the number of cycles
        self.speed = speed  # Set the speed of the robot
        self.base_station_pos = base_station_pos  # Define the base station position
        self.dim_tassel = dim_tassel  # Define the size of each grid cell
        self.i = i  # Map identifier
        self.j = j  # Simulation repetition identifier
        self.recharge = recharge  # Time needed for recharging
        self.running = True  # Simulation running status
        self.cycle_data = cycle_data  # Data structure to store cycle-related data
        self.filename = filename  # Output filename
        self.autonomy = autonomy  # Autonomy of the robot

        self.grass_tassels = defaultdict(list)  # List of grass tassel agents
        self.robot = None  # Placeholder for the robot agent

        self.initialize_grass_tassels()  # Initialize grass tassels on the grid
        self.initialize_robot(robot_plugin, autonomy, base_station_pos)  # Initialize the robot

    def initialize_grass_tassels(self):
        """Initialize the grass tassels and place them in the grid."""
        for x in range(self.grid.width):  # Loop through grid width
            for y in range(self.grid.height):  # Loop through grid height
                contents = get_contents_at_point(self.grid, x, y)  # Check contents at grid point

                # If no agents are present or if the cell is empty
                if not contents or all(
                        agent_type not in contents
                        for agent_type in [GrassTassel, SquaredBlockedArea, CircledBlockedArea]
                ):
                    new_grass = GrassTassel((x, y))  # Create a grass tassel agent
                    self.grass_tassels[(x, y)].append(new_grass)  # Add to the dictionary at (x, y)
                    self.grid.place_agent(new_grass, (x, y))  # Place the agent on the grid

    def initialize_robot(self, robot_plugin, autonomy, base_station_pos):
        """
        Initialize the robot and place it at the base station.

        :param robot_plugin: The robot plugin for movement and other functions.
        :param autonomy: The autonomy of the robot in terms of steps it can take before recharging.
        :param base_station_pos: The position of the base station where the robot starts.
        """
        self.robot = Robot(
            len(self.grass_tassels) + 1,  # Unique ID for the robot
            self,  # Reference to the simulator
            robot_plugin,  # Robot plugin for behavior
            self.grass_tassels,  # List of grass tassels to be cut
            autonomy,  # Autonomy value
            self.speed,  # Robot speed
            2,  # Movement precision parameter
            base_station_pos,  # Base station position
            self.cycles  # Number of simulation cycles
        )
        self.grid.place_agent(self.robot, self.base_station_pos)  # Place robot on the grid
        self.schedule.add(self.robot)  # Add robot to the schedule

    def step(self):
        """Perform a single step of the simulation."""
        self.schedule.step()  # Advance the schedule by one step
        cycle = 0  # Initialize cycle counter
        beginning = 0  # Start time of the simulation

        while self.robot.cycles > 0:  # Continue while robot has remaining cycles
            while math.floor(self.robot.aux_autonomy) > 0:  # While the robot has autonomy
                self.robot.step()  # Perform robot's step
            self.robot.cycles -= self.recharge  # Decrease cycles by recharge time

            cycle += 1  # Increment cycle counter
            stop = math.ceil(self.autonomy - self.robot.aux_autonomy) + beginning  # Calculate stop time
            recharge = (self.recharge * 60) + stop  # Calculate recharge completion time
            self._process_cycle_data(cycle, beginning, stop, recharge)  # Process cycle data
            beginning = recharge + 60  # Update the start time for next cycle
            self.robot.reset_autonomy()  # Reset robot autonomy

        self.running = False  # Stop the simulation when cycles are exhausted

    def _process_cycle_data(self, cycle, beginning, stop, recharge):
        """
        Process the data collected during each cycle and save it.

        :param cycle: The current cycle number.
        :param beginning: Start time of the cycle in seconds.
        :param stop: Stop time of the cycle in seconds.
        :param recharge: Recharge time in seconds.
        """
        counts = np.zeros((self.grid.width, self.grid.height), dtype=int)  # Initialize counts array

        for grass_tassel in self.grass_tassels:  # Loop through all grass tassels
            x, y = grass_tassel.pos  # Get position of the tassel
            if grass_tassel.counts > 0:  # Check if tassel was cut
                counts[x, y] = grass_tassel.counts  # Update count at the position

        df = self._create_dataframe(counts, cycle, beginning, stop, recharge)  # Create DataFrame
        output_dir = self._prepare_output_directory("../smarters/View/")  # Prepare output directory

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # Generate timestamp
        self._save_heatmap(counts, output_dir, timestamp, cycle)  # Save heatmap
        self._save_histogram(counts, output_dir, timestamp, cycle)  # Save histogram
        df.to_csv(
            os.path.join(output_dir, f"{self.filename}_cycle_{cycle}.csv"), index=False
        )  # Save DataFrame as CSV

    def _create_dataframe(self, counts, cycle, beginning, stop, recharge):
        """Create a DataFrame for the simulation cycle data."""
        df = pd.DataFrame(counts)  # Convert counts array to DataFrame
        df = df.rename(
            columns={j: j * self.dim_tassel for j in range(self.grid.height)}  # Rename columns by tassel size
        )
        df.insert(loc=0, column="num_mappa", value=self.i)  # Add map number column
        df.insert(loc=1, column="ripetizione", value=self.j)  # Add repetition number column
        df.insert(loc=2, column="cycle", value=cycle)  # Add cycle number column
        df.insert(loc=3, column="beginning time", value=math.ceil(beginning / 60))  # Add start time column
        df.insert(loc=4, column="stop time", value=math.ceil(stop / 60))  # Add stop time column
        df.insert(loc=5, column="after recharge time", value=math.ceil(recharge / 60))  # Add recharge time column
        df.insert(
            loc=6,
            column="x",
            value=[i * self.dim_tassel for i in range(self.grid.width)],  # Add x-axis column
        )
        return df

    @staticmethod
    def _prepare_output_directory(path):
        """Ensure the output directory exists."""
        output_dir = os.path.realpath(path)  # Get absolute path
        Path(output_dir).mkdir(parents=True, exist_ok=True)  # Create directory if not exists
        os.chmod(output_dir, stat.S_IRWXU)  # Set directory permissions
        return output_dir

    def _save_heatmap(self, counts, output_dir, timestamp, cycle):
        """
        Generate and save a heatmap of the counts.

        :param counts: 2D array representing the counts data to visualize.
        :param output_dir: Directory where the heatmap image will be saved.
        :param timestamp: Timestamp string to include in the saved file name.
        :param cycle: Cycle number to include in the saved file name.
        """

        def reduce_ticks(ticks, step):
            """
            Reduce tick labels by skipping elements based on the step size.

            :param ticks: List of tick labels to reduce.
            :param step: The step size to determine which tick labels to keep.
            :return: A list of reduced tick labels.
            """
            return [tick if i % step == 0 else "" for i, tick in enumerate(ticks)]  # Reduce tick labels

        # Calculate the x and y axis tick labels based on the grid dimensions and tassel size
        xtick = [int(j * self.dim_tassel) for j in range(self.grid.height)]
        ytick = [int(i * self.dim_tassel) for i in range(self.grid.width)]

        # Reduce the number of tick labels for better visibility
        reduced_xtick = reduce_ticks(xtick, 35)
        reduced_ytick = reduce_ticks(ytick, 35)

        # Create the figure and axis for plotting the heatmap
        fig, ax = plt.subplots()
        ax.xaxis.tick_top()  # Position x-axis ticks at the top
        maximum = np.max(counts)  # Get the maximum value in the counts for color scaling

        # Generate the heatmap using seaborn, with appropriate color mapping and labels
        sns.heatmap(
            data=counts,
            annot=False,  # No annotations of the values on the heatmap
            cmap="BuGn",  # Color map for the heatmap
            cbar_kws={"label": "Number of Robot Passes (Counts)"},
            robust=True,  # Use robust scaling to avoid outliers skewing the color scale
            vmin=0, vmax=maximum,  # Set min and max values for color scaling
            ax=ax,
            xticklabels=reduced_xtick,  # Reduced x-tick labels for better readability
            yticklabels=reduced_ytick,  # Reduced y-tick labels
        )

        # Save the generated heatmap as a PNG file with a timestamp and cycle number
        file_path = os.path.join(output_dir, f"heatmap_{timestamp}_cycle_{cycle}.png")
        plt.savefig(file_path)
        plt.close(fig)  # Close the plot to free memory

    @staticmethod
    def _save_histogram(counts, output_dir, timestamp, cycle):
        """
        Generate and save a histogram of the counts.

        :param counts: 2D array representing the counts data to visualize.
        :param output_dir: Directory where the histogram image will be saved.
        :param timestamp: Timestamp string to include in the saved file name.
        :param cycle: Cycle number to include in the saved file name.
        """
        # Flatten the counts and filter out zeros to focus on relevant data
        flattened_counts = counts[counts > 0].flatten()

        # Set up the histogram plot
        plt.figure(figsize=(10, 6))
        plt.hist(flattened_counts, bins=20, color='green', edgecolor='black')  # Plot the histogram with custom color
        plt.title(f"Histogram of Counts for Cycle {cycle}")  # Title for the plot
        plt.xlabel("Number of Robot Passes per Grid Cell")  # Label for the x-axis
        plt.ylabel("Frequency of Occurrence")  # Label for the y-axis

        # Save the histogram as a PNG file with a timestamp and cycle number
        file_path = os.path.join(output_dir, f"histogram_{timestamp}_cycle_{cycle}.png")
        plt.savefig(file_path)
        plt.close()  # Close the plot to free memory
