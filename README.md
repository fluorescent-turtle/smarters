# SMARTERS - Simulation of Mowing Agents in a Tile-based Environments with Realistic Space

## Description

**SMARTERS** is a customizable simulator for testing autonomous robot performance in complex environments. Built on the Mesa framework, it combines a **continuous space** with a **discrete tile grid**, allowing for both fine-grained motion tracking and statistical analysis of robot behavior. The simulator supports blocked zones, isolated areas, different movement and cutting models, and JSON-based environment configuration.

## Environment Representation

### Dual-Space Model

SMARTERS uses two parallel representations of space:

- **Continuous Space** (`ContinuousSpace`): The robot moves using real coordinates, allowing smooth transitions and directional flexibility. This is the space where motion logic is computed.
- **Discrete Grid** (`MultiGrid`): A tiled representation of the environment used for tracking visits and displaying features (e.g., grass, lines, obstacles). Each tile logs how many times the robot has passed over it.

This dual-layer model allows for accurate simulation of robot behavior and robust analysis of area coverage.

### Tile Grid

Tiles represent discrete areas of the environment, each capable of holding multiple agents or resources:

- **Agents**: Dynamic entities (e.g., robots), implemented using Mesa’s `Agent` class.
- **Resources**: Static objects such as grass, guiding lines, isolated areas, blocked areas, and entry points.

#### Key Resources

- **Grass Tiles**
- **Guiding Lines**
- **Isolated Areas**
- **Blocked Areas** (Square or Circular)
- **Openings** (for controlled access to isolated areas)

## Obstacle and Area Types

### Blocked Areas

Inaccessible zones for the robot. Defined as:

- `SquaredBlockedArea`
- `CircledBlockedArea`

They represent real-world obstructions like buildings or pools and can be placed manually or generated randomly.

### Isolated Areas

Zones that the robot can enter only through predefined `Opening` tiles. Managed with the `IsolatedArea` class. Their size, shape, and placement can be manually configured or randomized.

## Robot Behavior Models

### Bounce Model

Determines how the robot reacts upon hitting an obstacle:

- **Ping Pong**: Reflects the direction (bounces back).
- **Random**: Attempts upper-left movement first, falling back on other directions if blocked.

### Cutting Model

Represents the robot's grass-cutting logic:

- The robot "cuts" by traversing tiles and incrementing a counter.
- In **random cutting mode**, it selects a random direction and proceeds until blocked, potentially crossing multiple tiles diagonally.

## Configuration

### JSON Input

SMARTERS uses a configuration file in JSON format. Two formats are supported:

- **Structure 1**: Full configuration with:
  - Robot specs (type, speed, cutting mode, etc.)
  - Environment settings (dimensions, blocked area counts, etc.)
  - Simulation parameters (tile size, number of cycles, etc.)

- **Structure 2**: Grid definition using Cartesian coordinates, manually specifying:
  - Blocked areas
  - Isolated areas
  - Openings

### Example Command

```bash
python main.py --d data_file.json
```

Ensure the `View/` folder is writable and the following libraries are installed: `mesa`, `pandas`, `numpy`, `matplotlib`, `seaborn`.

## Plugin Support

SMARTERS supports modular extensions through Python-based plugins.

### Runtime Options

- `--e`: Environment plugin (e.g., `environment_plugin.py`)
- `--r`: Robot plugin (e.g., `robot_plugin.py`)
- `--d`: JSON configuration file

### Example:

```bash
python main.py --e environment_plugin.py --r robot_plugin.py --d data_file.json
```

## Simulation Cycle

Each simulation follows these steps:

1. Map generation and base station placement
2. Placement of blocked and isolated areas
3. Continuous robot motion across the space
4. Tile-based logging of robot presence
5. Repeat across multiple cycles until completion

The robot has limited **autonomy** per cycle. Once exhausted, it recharges before resuming activity.

## Output

### CSV Exports

- **Grid Representation**: Shows tile types across the grid.
- **Cycle Files** (`cycle_i.csv`): Record how many times the robot passed over each tile in cycle *i*.

### Visual Analysis

- **Histograms**: Distribution of tile traversals (X = number of crossings, Y = number of tiles).
- **Heatmaps**: Color-coded views of high and low traversal zones.

> Note: Warnings in the terminal about agents occupying the same tile can be ignored.

## Summary

SMARTERS offers a flexible, powerful framework for simulating autonomous mowing robots in rich, user-defined environments. With support for continuous motion, discrete logging, customizable behaviors, and plugin-based extension, it enables detailed performance evaluation for research or development purposes.
