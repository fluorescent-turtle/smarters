## Description

SMARTER is an advanced simulator for managing robots in environments represented as tile grids. It uses the Mesa framework for detailed visualization of interactions between agents and the environment. The simulator allows testing and evaluating robot performance in complex scenarios with blocked areas, isolated areas, and different bounce and cutting modes.

## Environment Representation

### Tile Grid

The simulation environment is represented as a tile grid, managed using the Mesa framework with a MultiGrid object. Each tile can contain multiple agents and resources.
Agents and Resources

  - Agents: Mobile and interactive entities implemented as instances of the Agent class from Mesa. They interact with the environment and each other.
  - Resources: Static elements distributed across tiles, such as grass, guiding lines, isolated areas, and openings.

#### Tile Structure

Tiles are square and can contain various elements due to the multi-agent nature of MultiGrid. Resources include:

  - Grass tiles
  - Guiding lines
  - Isolated areas
  - Blocked Areas
  - Openings
    

#### Blocked Areas

Blocked areas are zones inaccessible to robots, represented by SquaredBlockedArea and CircledBlockedArea. These may include buildings, pools, or other obstructive structures. These areas can be set manually or distributed randomly.

#### Isolated Areas

Isolated areas are zones where robots can enter only through designated openings. Modeled with IsolatedArea and Opening, their size and position can be set manually or generated randomly.

# Customization

## Bounce Model

The bounce model manages robot collisions with obstacles:

  - Ping Pong: The robot reflects its movement in the opposite direction after hitting an obstacle.
  - Random: The robot always tries to move towards the upper-left tile. If blocked, it attempts other directions.

## Cutting Model

The robot simulates cutting by moving across tiles and incrementing a counter. In random mode, the robot chooses a random direction and moves in a straight line, affecting adjacent tiles.

## JSON Configuration
### JSON Preparation

To initialize SMARTER, a JSON file is required with one of two possible structures:

  - Structure 1: A full configuration file, including robot settings, environment parameters, and simulation variables. This structure defines robot specifications (type, speed, cutting mode, etc.), grid dimensions, and simulation details such as tile size and cycle duration.

  - Structure 2: Used to define the grid in Cartesian coordinates, listing the exact positions of blocked areas, isolated areas, and openings.

The simulator uses these files to configure:
  - Robot: Autonomous robot settings.
  - Environment: Grid and blocked area settings.
  - Simulation Variables: Cycle and repetition parameters.

### Example Commands
Run the simulator using the following command:

    python main.py --d data_file.json

Ensure the View folder has write permissions and dependencies such as pandas, matplotlib, seaborn, numpy, and mesa are installed.

## Plugins

SMARTER allows functionality extension through plugins, which must be Python files. Plugins are specified during runtime using the following flags:

    --e: Environment plugin.
    --r: Robot plugin.
    --d: JSON configuration file.

### Example:

    python main.py --e environment_plugin.py --r robot_plugin.py --d data_file.json


# Simulation and Output

## Simulation Cycle

The simulation proceeds as follows:

  - Generating maps and base station positions.
  - Exploring positions based on blocked areas.
  - Running the simulation for the duration specified in the JSON configuration.

The robot operates with limited autonomy per cycle, moving until exhausted, after which it recharges. The process repeats until the predefined number of cycles is completed.

## Output Files

The simulator generates multiple output files for analysis:

  - CSV Files:
        Grid Representation: Displays the grid as a matrix, with each cell representing a tile type (e.g., blocked area, grass, isolated area, or opening).
        Cycle Files: Contain the term cycle_i in the filename (i indicates the cycle number). These files track the number of robot passes over each tile.
  - Histograms:
        Show the distribution of tile crossings. The X-axis represents the number of crossings, and the Y-axis the number of tiles.
  - Heatmaps:
        Provide a visual representation of robot activity intensity across the grid, with colors indicating frequently and rarely traversed areas.

If the terminal outputs a warning about an agent already occupying a tile, it can be ignored.

By following these instructions, SMARTER can be properly configured and executed, producing detailed simulation results for analysis.
