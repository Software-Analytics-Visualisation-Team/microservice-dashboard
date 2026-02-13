# Microservice Dash App

This is a Dash-based web application for visualizing microservice call data. All visualizations are generated based on the input file which prepared extracting service to service calls.

## Table of Contents

- [Requirements](#requirements)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development](#local-development)
- [CLI Commands](#cli-commands)
- [Notes](#notes)
- [Processed Data Format](#processed-data-format)
- [User Guide](#user-guide)

## Requirements

- Docker (recommended)
- Or: Python 3.13.3 and pip

## Quick Start (Docker)

1. Build the Docker image:
   ```
   docker build -t microservice_data .
   ```

2. Run the container:
   ```
   docker run -p 8050:8050 --name microservice_data microservice_data
   ```

3. Open the userr browser and go to [http://localhost:8050](http://localhost:8050)

## Local Development

1. Create and activate a virtual environment (PowerShell):
   ```
   cd src
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Show available CLI commands:
   ```
   python -m msviz --help
   ```

## CLI Commands

Run commands from `src/`.

1. Start dashboard only:
   ```
   python -m msviz serve
   ```

2. Run preprocessing only:
   ```
   python -m msviz preprocess
   ```

3. Run preprocessing and then start dashboard:
   ```
   python -m msviz run
   ```

4. Common options:
   ```
   python -m msviz serve --host 0.0.0.0 --port 8050 --debug
   python -m msviz preprocess --input-csv data/raw_data.csv --output-csv data/processed_data.csv
   python -m msviz run --input-csv data/raw_data.csv --output-csv data/processed_data.csv
   ```

5. Backward-compatible wrapper:
   ```
   python app.py
   ```
   This delegates to the same CLI entrypoint.

## Notes

- The app expects data at `data/processed_data.csv` by default.
- Default port is 8050.

## Processed Data Format
| Attribute | Description |
| --- | --- |
| `timestamp` | Event timestamp for the trace entry. |
| `service_name` | Name of the caller service. |
| `event_code` | Fully qualified method name. |
| `event_provider` | Source that emitted the event. |
| `trace_id` | Identifier for a full distributed trace. |
| `transaction_id` | Identifier for a transaction within a trace. |
| `message` | Method or operation call details. |
| `callee` | Name of the called service. |
| `parsed` | Parsed representation of the raw message. |
| `call_duration` | Duration of the call (latency). |

## User Guide

1. Right side panel description:
- Total records: Total number of events in the dataset.
- Start timestamp: Time of first events.
- End timestamp: Time of the last event.
- Select time range: Slider that provide user to select spesific time frame that generate visualizations(Overall Service to Callee Service graph, Service to Callee Service Graph and Heatmap).
- Select Trace ID: List of trace IDs are recognized based on the input data.

2. Graph description:

- Overall Service to Callee Service graph (All Data):
This graph visualizes service-to-service calls between the selected start and end timestamps. Each node represents a service, while each directed edge indicates a call from the caller service to the callee. The edge labels display the total number of calls across all methods between the two services.

Clicking an edge opens a histogram showing the distribution of call counts over time between the selected services.

In the full graph view, dark blue nodes and edges highlight the communication path for the currently selected trace ID. The user can switch the trace ID to explore different call paths.

Additionally, the user can filter the service calls by selecting a specific time range, with a minimum of 1 second.

- Service to Callee Service Graph (Selected Trace ID):
This graph is generated based on the selected trace ID and visualizes all service-to-service communications within that trace. Each edge represents a call and includes the fully qualified method name and its latency. Additionally, the user can filter the displayed calls by selecting a specific time range.

- Call Counts Histogram (All Data):
This histogram is generated from all input data. It shows call frequency for each method call.

- Heatmap:
This Heatmap provides average call duration per method call in a selected trace ID.

- Table:
This table provides service to service call details in a table view.
