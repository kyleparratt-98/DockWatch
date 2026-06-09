# ⚡ Docker Resource Monitor ⚡
<p align="center"><i>Real-time, color-coded container contention heatmaps for your terminal</i></p>

---

## ✨ Why This Exists

You've got 15 microservices running locally, one of them is thrashing CPU, another is leaking memory, and `docker stats` is just a wall of scrolling numbers that tell you nothing about *trends* or *severity*. Meanwhile, your dev environment feels like molasses and you have no idea which container is the culprit. **Docker Resource Monitor** scrapes `/sys/fs/cgroup` and `/proc` at the kernel level, maps every PID to its container, and renders a live, color-coded ASCII heatmap with sparkline trends — so you can spot resource contention at a glance, even when containers are ephemeral and PID recycling is rampant.

## 🎯 Features

- **Live Heatmap Grid** — Color-coded cells (green → yellow → red) for CPU throttling, memory OOM scores, and I/O wait percentages per container
- **Sparkline Trends** — Embedded mini line charts showing metric history over the last N data points
- **Ephemeral Container Handling** — Automatically detects PID recycling and refreshes container mappings every 5 seconds
- **Dual cgroup Support** — Works with both cgroup v1 and v2, automatically detecting the correct filesystem paths
- **Graceful Degradation** — Falls back to `docker stats` API with a prominent warning banner when direct filesystem access fails
- **Configurable via TOML** — Set refresh intervals, color themes, and container filters in a simple config file
- **Rich Terminal UI** — Uses `rich` Layout, Panel, and Live widgets for a polished, professional display

## 📦 Installation

### Prerequisites

- Python 3.8+
- Docker (for fallback mode)
- Access to `/sys/fs/cgroup` and `/proc` (Linux only; macOS via Docker Desktop requires fallback mode)

### Quick Install

```bash
pip install docker-resource-monitor
```

### From Source

```bash
git clone https://github.com/yourusername/docker_resource_monitor.git
cd docker_resource_monitor
pip install -e .
```

## 🚀 Quick Start

```bash
# Run with default settings - watch your containers live!
docker-resource-monitor
```

## 📖 Usage

```bash
# Run with a custom refresh interval (seconds)
docker-resource-monitor --refresh 3

# Specify a configuration file
docker-resource-monitor --config ~/.docker-monitor/config.toml

# Force Docker API fallback mode (bypass direct filesystem access)
docker-resource-monitor --use-docker-api

# Filter to specific containers by name or ID prefix
docker-resource-monitor --filter my-service,redis
```

## 🏗️ Architecture

The tool is organized into four core modules, each with a single responsibility:

- **`container/mapper.py`** — Parses `/proc/<pid>/cgroup` and mountinfo to build a PID-to-container-ID mapping. Handles PID recycling via a TTL-based cache (default 5s) and supports both cgroup v1 and v2 paths.
- **`metrics/collector.py`** — The primary metric scraper. Reads CPU throttling from `cpu.stat`, memory OOM scores from `memory.current`/`memory.stat`, and I/O pressure from `io.stat` (v2) or `blkio.throttle.io_service_bytes` (v1). If direct access fails, delegates to the fallback collector.
- **`metrics/fallback.py`** — Uses the `docker` Python SDK to call `docker stats` when filesystem access is unavailable. Returns metrics in the same format as the direct collector for seamless swapping.
- **`visualization/ui.py`** — Orchestrates the `rich` Live display with a `Layout` split into a warning banner `Panel` and a main heatmap `Table`. The `HeatmapRenderer` applies color thresholds and embeds `rich.sparkline.Sparkline` objects in each cell.

## 📚 API Reference

### `ContainerMapper`

| Method | Description |
|--------|-------------|
| `get_container_for_pid(pid)` | Returns container info dict for a PID, or `None` |
| `refresh_cache()` | Forces a full cache refresh across all `/proc` entries |
| `get_all_containers()` | Returns a dict of `{container_id: container_info}` |
| `get_cache_stats()` | Returns cache size, unique containers, age, and staleness |

### `MetricCollector`

| Method | Description |
|--------|-------------|
| `collect_metrics()` | Returns a dict of `{container_id: {cpu_throttling, memory_oom, io_wait, sparklines}}` |

### `Config`

| Method | Description |
|--------|-------------|
| `load_from_file(path)` | Loads and validates a TOML config file |
| `get_refresh_interval()` | Returns the refresh interval in seconds |
| `get_color_theme()` | Returns the active color theme name |
| `set_use_docker_api(value)` | Toggles fallback mode |
| `set_warning_banner(text)` | Sets the warning banner text |

### `VisualizationEngine`

| Method | Description |
|--------|-------------|
| `start()` | Begins the live rich display |
| `update(metrics_dict)` | Renders new data into the heatmap grid |
| `stop()` | Stops the live display cleanly |

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Setting up a development environment
- Running tests
- Submitting pull requests

We especially appreciate contributions around:
- Additional color themes
- Support for more container runtimes (Podman, containerd)
- Performance optimizations for large-scale deployments

## 📄 License

MIT © 2026

---

<p align="center">
  <sub>Built with ❤️ by an autonomous AI software factory</sub>
</p>
