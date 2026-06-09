<p align="center">
  <img src="https://img.shields.io/badge/status-active-success?style=for-the-badge" alt="Status">
  <img src="https://img.shields.io/badge/license-MIT-blue?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/stars-potential-gold?style=for-the-badge" alt="Stars">
</p>

<h1 align="center">⚡ DockWatch ⚡</h1>
<p align="center"><i>Real-time Docker container resource contention heatmaps in your terminal</i></p>

---

## ✨ Why This Exists

You're running a swarm of containers on your dev machine or shared server. CPU throttling silently spikes, memory pressure builds, I/O waits balloon—and you're left guessing which container is the culprit. `docker stats` gives you raw numbers, ctop gives you a list, and Prometheus+Grafana requires a PhD in YAML. **DockWatch** scrapes `/sys/fs/cgroup` and `/proc` directly, extracts per-container CPU throttling counts, memory OOM scores, and I/O wait percentages, and paints them onto a real-time, color-coded ASCII heatmap grid with sparkline trends—all in your terminal. No setup. No web dashboard. Just instant, visceral insight into resource contention.

## 🎯 Features

- **Real-time Heatmap Grid**: Every container gets a row; CPU, Memory, and I/O metrics are color-coded cells (green→yellow→red) for instant bottleneck identification
- **Sparkline Trends**: Each cell includes a mini sparkline showing the last N data points, so you see direction not just snapshots
- **Cgroup v1/v2 Auto-Detection**: Works out of the box on both legacy and unified cgroup hierarchies without manual configuration
- **Ephemeral Container Handling**: PID recycling and container restarts are handled transparently with automatic cache invalidation
- **Graceful Fallback**: If filesystem access fails (permissions, missing paths), falls back to `docker stats` API with a clear warning banner
- **Rich Terminal UI**: Built with `rich` library's Layout, Panel, and Live widgets for a polished, full-screen real-time display
- **TOML Configuration**: Customize refresh interval, color themes, and container filters via `config.toml`
- **Lightweight**: Pure Python with minimal dependencies—no daemons, no web servers, no database

## 📦 Installation

### Prerequisites

- Python 3.8+
- Docker Engine (running containers to monitor)
- Read access to `/sys/fs/cgroup` and `/proc` (default on most systems)

### Quick Install

```bash
pip install dockwatch
```

### From Source

```bash
git clone https://github.com/yourusername/dockwatch.git
cd dockwatch
pip install -e .
```

## 🚀 Quick Start

```bash
# Monitor all running containers with default settings
dockwatch
```

Press `Ctrl+C` to exit.

## 📖 Usage

```bash
# Monitor with a 1-second refresh interval
dockwatch --refresh-interval 1

# Use the 'dark' color theme
dockwatch --color-theme dark

# Filter to specific containers by name or ID prefix
dockwatch --filter my-app,redis

# Load configuration from a custom TOML file
dockwatch --config /path/to/config.toml

# Force fallback to Docker API (bypass filesystem scraping)
dockwatch --use-docker-api
```

**Keyboard shortcuts:**
- `q` or `Ctrl+C`: Quit
- `r`: Force refresh container list

## 🏗️ Architecture

DockWatch is structured around four core modules:

- **`container/mapper.py`**: Parses `/proc/<pid>/cgroup` and `/proc/<pid>/mountinfo` to map PIDs to Docker container IDs. Maintains a TTL-based cache to handle PID recycling and ephemeral containers. Supports both cgroup v1 and v2 path formats.

- **`metrics/collector.py`**: The primary metric scraper. Attempts to read CPU throttling (`cpu.stat`), memory pressure (`memory.current`, `memory.events`), and I/O pressure (`io.stat`) from cgroup v2 paths, falling back to v1 paths (`cpuacct`, `memory`, `blkio`). If filesystem access fails, delegates to the fallback collector.

- **`metrics/fallback.py`**: Uses the Docker Engine SDK (`docker-py`) to call `docker stats` as a fallback. Provides the same metric schema but sourced from the Docker API instead of the kernel's cgroup filesystem.

- **`visualization/`**: Contains `ui.py` (sets up `rich.Layout` with a top warning banner and main live area) and `heatmap.py` (renders the color-coded grid with sparklines via `rich.table.Table` and `rich.sparkline.Sparkline`).

The main loop in `main.py` orchestrates: refresh container mapping → collect metrics (with fallback) → update visualization → sleep for refresh interval → repeat.

## 📚 API Reference

### `Config` (config.py)

| Method / Attribute | Description |
|---|---|
| `load_from_file(path: str) -> None` | Load TOML configuration from file. Validates all values. |
| `refresh_interval: int` | Seconds between metric collection cycles (default: 2) |
| `color_theme: str` | One of `default`, `dark`, `light`, `monochrome` |
| `container_filter: List[str]` | List of container name/ID prefixes to monitor (empty = all) |
| `use_docker_api: bool` | Force fallback to Docker API |
| `warning_banner: str` | Set automatically when fallback is active |

### `ContainerMapper` (container/mapper.py)

| Method | Description |
|---|---|
| `get_container_for_pid(pid: int) -> Optional[Dict]` | Look up container info for a PID. Returns `{container_id, container_name, cgroup_path, pid}` or `None`. |
| `refresh_cache() -> None` | Force refresh of PID-to-container mapping. |
| `get_all_containers() -> Dict[str, Dict]` | Return all currently mapped containers by container ID. |
| `get_cache_stats() -> Dict` | Return cache size, unique container count, age, and staleness status. |

### `MetricCollector` (metrics/collector.py)

| Method | Description |
|---|---|
| `collect_metrics() -> Dict[str, Dict]` | Collect metrics for all discovered containers. Returns dict keyed by container ID with CPU throttling count, memory OOM score, I/O wait %, and sparkline data. |

### `VisualizationEngine` (visualization/ui.py)

| Method | Description |
|---|---|
| `start() -> None` | Initialize rich Layout and enter live display mode. |
| `update(data: Dict) -> None` | Update the display with new metric data. |
| `stop() -> None` | Cleanly exit live display and restore terminal. |

## 🤝 Contributing

Contributions are welcome! Please check out our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Setting up a development environment
- Running tests (`pytest`)
- Code style (Black + isort)
- Submitting pull requests

**Bug reports and feature requests** are encouraged—open an issue on GitHub.

## 📄 License

MIT © 2026

---

<p align="center">
  <sub>Built with ❤️ by an autonomous AI software factory</sub>
</p>
