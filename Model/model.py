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
import os
import stat
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

        :param recharge: Recharge time
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
        self.schedule = mesa.time.StagedActivation(self)
        self.grid = grid
        self.cycles = cycles
        self.speed = speed
        self.base_station_pos = base_station_pos
        self.grass_tassels = []
        self.robot = None
        self.dim_tassel = dim_tassel
        self.initialize_grass_tassels()
        self.initialize_robot(robot_plugin, autonomy, base_station_pos)
        self.i = i
        self.j = j
        self.recharge = recharge

        self.running = True
        self.cycle_data = cycle_data
        self.filename = filename
        self.autonomy = autonomy

    def initialize_grass_tassels(self):
        """Initialize the grass tassels and place them in the grid."""
        for x in range(self.grid.width):
            for y in range(self.grid.height):
                contents = get_contents_at_point(self.grid, x, y)

                if (contents == []
                        or (GrassTassel not in contents
                            and SquaredBlockedArea not in contents
                            and CircledBlockedArea not in contents)
                ):
                    new_grass = GrassTassel((x, y))
                    self.grass_tassels.append(new_grass)
                    self.grid.place_agent(new_grass, (x, y))

    def initialize_robot(self, robot_plugin, autonomy, base_station_pos):
        """
        Initialize the robot and place it at the base station.

        :param robot_plugin: The robot plugin for movement and other functions.
        :param autonomy: The autonomy of the robot in terms of steps it can take before recharging.
        :param base_station_pos: The position of the base station where the robot starts.
        """

        # Create the robot with all necessary attributes
        self.robot = Robot(
            len(self.grass_tassels) + 1,
            self,
            robot_plugin,
            self.grass_tassels,
            autonomy,
            self.speed,
            2,
            base_station_pos,
            self.cycles
        )

        # Place the robot at the base station and add it to the schedule
        self.grid.place_agent(self.robot, self.base_station_pos)
        self.schedule.add(self.robot)

    def step(self):
        """Perform a single step of the simulation."""
        self.schedule.step()  # Progress the simulation schedule by one step
        cycle = 0
        beginning = 0

        # Main simulation loop
        while self.robot.cycles > 0:
            while math.floor(self.robot.aux_autonomy) > 0:  # and self.robot.cycles > 0:
                self.robot.step()  # Move the robot until it runs out of autonomy
            self.robot.cycles -= self.recharge

            cycle += 1
            stop = math.ceil(self.autonomy - self.robot.aux_autonomy) + beginning
            recharge = (self.recharge * 60) + stop
            self._process_cycle_data(cycle, beginning, stop, recharge)  # Process the data for the current cycle
            beginning = recharge + 60  # plus 1 minute
            self.robot.reset_autonomy()  # Reset the robot's autonomy for the next cycle

        self.running = False  # Mark the simulation as not running

    def _process_cycle_data(self, cycle, beginning, stop, recharge):
        """
        Process the data collected during each cycle and save it.

        :param cycle: The current cycle number.
        """
        counts = [[0 for _ in range(self.grid.height)] for _ in range(self.grid.width)]

        for grass_tassel in self.grass_tassels:
            x, y = grass_tassel.get()
            if grass_tassel.get_counts() > 0:
                counts[x][y] = grass_tassel.get_counts()

        # Create a DataFrame to store the counts
        df = pd.DataFrame(counts)
        df = df.rename(
            columns={j: j * self.dim_tassel for j in range(self.grid.height)}
        )
        df.insert(loc=0, column="num_mappa", value=self.i)
        df.insert(loc=1, column="ripetizione", value=self.j)
        df.insert(loc=2, column="cycle", value=cycle)
        df.insert(loc=3, column="beginning time", value=math.ceil(beginning / 60))
        df.insert(loc=4, column="stop time", value=math.ceil(stop / 60))
        df.insert(loc=5, column="after recharge time", value=math.ceil(recharge / 60))
        df.insert(
            loc=6,
            column="x",
            value=[i * self.dim_tassel for i in range(self.grid.width)],
        )

        output_dir = os.path.realpath("../smarters/View/")  # Define the output directory
        # Use Path to check if the directory exists, and create it if it doesn't
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        os.chmod(output_dir, stat.S_IRWXU)

        def reduce_ticks(ticks, step):
            return [tick if i % step == 0 else "" for i, tick in enumerate(ticks)]

        # Generate ticks for x and y axes
        xtick = [int(j * self.dim_tassel) for j in range(self.grid.height)]
        ytick = [int(i * self.dim_tassel) for i in range(self.grid.width)]

        tick_step = 35  # Define the step for tick reduction
        reduced_xtick = reduce_ticks(xtick, tick_step)
        reduced_ytick = reduce_ticks(ytick, tick_step)

        # Create a heatmap of the counts
        fig, ax = plt.subplots()
        ax.xaxis.tick_top()  # Place x-axis ticks at the top
        maximum = max(max(sublist) for sublist in counts)

        sns.heatmap(
            data=counts,
            annot=False,
            cmap="BuGn",
            cbar_kws={"label": "Counts"},
            robust=True,
            vmin=0,
            vmax=maximum,
            ax=ax,
            xticklabels=reduced_xtick,
            yticklabels=reduced_ytick,
        )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )  # Generate a timestamp for the filename
        file_path = os.path.join(
            output_dir, f"heatmap_{timestamp}_cycle_{cycle}.png"
        )  # Define the file path

        plt.savefig(file_path)  # Save the heatmap as a PNG file
        plt.close(fig)  # Close the figure

        # Flatten the array (in case of multidimensional data)
        flattened_counts = np.array(counts).flatten()

        # Create the figure and axis objects
        fig, ax = plt.subplots()

        # Create the histogram plot with uniform bins
        bins = np.linspace(min(flattened_counts), max(flattened_counts), 20)
        sns.histplot(flattened_counts, bins=bins, discrete=True, edgecolor='black')

        # Set axis limits to ensure consistent scaling
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 10 ** 6)  # Fixed upper limit for y-axis

        ax.set_xticks([1, 5, 10, 50, 100, 120])

        # Define y-axis ticks for uniform scaling
        # Adjust ticks according to desired scale; here set for log scaling
        ax.set_yticks([1, 10, 100, 10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6])
        ax.get_yaxis().set_major_formatter(plt.ScalarFormatter())  # Use normal number formatting

        # Set axis scales
        plt.xscale('linear')
        plt.yscale('symlog', linthresh=1)  # 'linthresh' avoids over-compression of linear part near zero

        # Set x and y axis labels
        plt.xlabel("Number of tassels")
        plt.ylabel("Number of passes")

        # Adjust layout to prevent overlapping labels
        plt.tight_layout()

        # Save the plot as a PNG file (uncomment and modify path to use)
        plt.savefig(os.path.join(output_dir, f"hist_{timestamp}_cycle_{cycle}.png"))

        # Display the plot
        # plt.show()

        # Close the figure to free memory
        plt.close(fig)

        # Save the DataFrame as a CSV file
        df.to_csv(
            os.path.join(output_dir, f"{self.filename}_cycle_{cycle}.csv"), index=False
        )