# microservice-dashboard

This is a Dash-based web application for visualizing microservice call data. All visualizations are generated based on the input file `inputs.csv` which contains extracted service to service calls from software traces.

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

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the app:
   ```
   python app.py
   ```

## Notes

- The app expects data at `data/inputs.csv` by default.
- Default port is 8050.

## User Guide

1. Right side panel description:
- Total records: Total number of events in the dataset.
- Start timestamp: Time of first events.
- End timestamp: Time of the last event.
- Select time range: Slider to select spesific time frame for the visualizations(Overall Service to Callee Service graph, Service to Callee Service Graph and Heatmap).
- Select Trace ID: List of trace IDs based on the input data.

2. Graph description:

- Overall Service to Callee Service graph (All Data):
This graph visualizes service-to-service calls between the selected start and end timestamps. Each node represents a service, while each directed edge indicates a call from the caller service to the callee. The edge labels display the total number of calls across all methods between the two services.

Clicking on an edge opens a histogram showing the distribution of call counts over time between the selected services.

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
