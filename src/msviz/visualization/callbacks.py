"""Dash callback registrations."""

import base64
import io
import json
import re

import pandas as pd
from copy import deepcopy
from dash import Input, Output, State, no_update, html


def extract_function_name(name: str) -> str:
    """Extract simple function name from a string (text before '(')."""
    if not name:
        return ""
    paren_index = str(name).find("(")
    if paren_index > 0:
        return str(name)[:paren_index].strip()
    return str(name).strip()
from .graphs import (
    build_all_event_code_histogram,
    build_edge_event_code_histogram,
    build_event_table,
    build_overall_graph_elements,
    build_selected_edge_violinplot,
    build_service_heatmap_figure,
    build_span_elements,
    build_static_graph_elements,
    build_trace_comparison_table,
    build_trace_difference_elements,
    build_trace_elements,
    get_global_incoming_range,
)

def register_callbacks(app, runtime_data, static_elements, overall_stylesheet):
    global_min_count, global_max_count = get_global_incoming_range(runtime_data)

    def _is_empty_figure(figure):
        return isinstance(figure, dict) and not figure

    def _flow_stylesheet(base_stylesheet, offset):
        ss = deepcopy(base_stylesheet)
        for rule in ss:
            if rule.get("selector") == "edge.flow":
                rule["style"]["line-dash-offset"] = -(offset % 100)
        return ss

    def _runtime_data_from_store(store_data):
        if store_data:
            df = pd.read_json(store_data, orient="split")
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
            return df
        return runtime_data

    def _static_elements_from_store(store_data):
        if store_data:
            return build_static_graph_elements(store_data)
        return static_elements

    def _parse_static_csv_dataframe(df: pd.DataFrame) -> dict:
        static_services = {}
        packages = {}
        functions = {}

        for _, row in df.iterrows():
            entity_name = str(row.get("name", "")).strip()
            entity_type = str(row.get("type", "")).strip().lower()
            properties_raw = row.get("properties")

            if not entity_name:
                continue

            properties = {}
            if pd.notna(properties_raw):
                if isinstance(properties_raw, dict):
                    properties = properties_raw
                else:
                    try:
                        properties = json.loads(str(properties_raw))
                    except json.JSONDecodeError:
                        properties = {"raw": str(properties_raw)}

            if entity_type == "microservice":
                static_services[entity_name] = properties
            elif entity_type == "package":
                packages[entity_name] = properties
            elif entity_type == "function":
                functions[entity_name] = properties

        return {
            "static_services": static_services,
            "packages": packages,
            "functions": functions,
        }

    @app.callback(
        Output("overall-cytoscape-graph", "stylesheet"),
        [
            Input("edge-flow-interval", "n_intervals"),
            Input("static-edges-toggle", "value"),
        ],
    )
    def update_overall_stylesheet(n, show_static_dependencies):
        animated_stylesheet = _flow_stylesheet(overall_stylesheet, n * 2)
        ss = deepcopy(animated_stylesheet)

        for rule in ss:
            if rule.get("selector") == "edge.static-edge":
                rule["style"]["display"] = "element" if show_static_dependencies else "none"

        return ss

    @app.callback(
        Output("edge-flow-interval", "disabled"),
        Input("flow-animation-toggle", "value"),
    )
    def toggle_flow_interval(animate_enabled):
        return not animate_enabled

    @app.callback(
        [
            Output("runtime-data-store", "data"),
            Output("runtime-data-upload-status", "children"),
        ],
        [Input("runtime-data-upload", "contents")],
        [State("runtime-data-upload", "filename")],
    )
    def upload_runtime_data(contents, filename):
        if contents is None:
            return no_update, no_update

        content_type, content_string = contents.split(",", 1)
        try:
            decoded = base64.b64decode(content_string)
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S:%f", errors="coerce")
            return df.to_json(date_format="iso", orient="split"), f"Imported {filename}"
        except Exception as exc:
            return no_update, f"Unable to import runtime CSV: {exc}"

    @app.callback(
        [
            Output("static-data-store", "data"),
            Output("static-data-upload-status", "children"),
        ],
        [Input("static-data-upload", "contents")],
        [State("static-data-upload", "filename")],
    )
    def upload_static_data(contents, filename):
        if contents is None:
            return no_update, no_update

        content_type, content_string = contents.split(",", 1)
        try:
            decoded = base64.b64decode(content_string)
            df = pd.read_csv(io.StringIO(decoded.decode("utf-8")))
            static_payload = _parse_static_csv_dataframe(df)
            return static_payload, f"Imported {filename}"
        except Exception as exc:
            return no_update, f"Unable to import static CSV: {exc}"

    # @app.callback(
    #     Output("static-edges-toggle", "disabled"),
    #     Input("static-edges-toggle", "value"),
    # )
    # def update_static_edges_toggle(static_edges_enabled):
    #     return not static_edges_enabled

    @app.callback(
        [
            Output("cytoscape-graph", "elements"),
            Output("event-table", "children"),
        ],
        [
            Input("trace-id-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("main-tabs", "value"),
            Input("runtime-data-store", "data"),
        ],
    )
    def update_dashboard(selected_trace_id, time_range, _active_tab, runtime_store):
        runtime_df = _runtime_data_from_store(runtime_store)
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        filtered_data = runtime_df[
            (runtime_df["timestamp"] >= start_dt) & (runtime_df["timestamp"] <= end_dt)
        ]

        if not selected_trace_id:
            return [], "No trace_id selected."

        df = filtered_data[filtered_data["trace_id"] == selected_trace_id]

        elements = build_trace_elements(df)
        table_html = build_event_table(df)
        return elements, table_html

    @app.callback(
        Output("overall-cytoscape-graph", "elements"),
        [
            Input("trace-id-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("main-tabs", "value"),
            Input("runtime-data-store", "data"),
            Input("static-data-store", "data"),
        ],
    )
    def update_overall_graph(selected_trace_id, time_range, _active_tab, runtime_store, static_store):
        runtime_df = _runtime_data_from_store(runtime_store)
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        filtered_data = runtime_df[
            (runtime_df["timestamp"] >= start_dt) & (runtime_df["timestamp"] <= end_dt)
        ]
        current_static_elements = _static_elements_from_store(static_store)
        global_min_count, global_max_count = get_global_incoming_range(filtered_data)
        return build_overall_graph_elements(
            filtered_data,
            global_min_count,
            global_max_count,
            selected_trace_id,
            current_static_elements,
        )

    @app.callback(
        Output("slider-tooltip", "children"), Input("time-range-slider", "value")
    )
    def update_slider_tooltip(value):
        start = pd.to_datetime(value[0], unit="s").strftime("%Y-%m-%d %H:%M:%S")
        end = pd.to_datetime(value[1], unit="s").strftime("%Y-%m-%d %H:%M:%S")
        return f"{start}  to  {end}"

    @app.callback(
        [
            Output("edge-histogram-modal", "is_open"),
            Output("edge-eventcode-histogram", "figure"),
        ],
        [
            Input("overall-cytoscape-graph", "tapEdgeData"),
            Input("time-range-slider", "value"),
        ],
        [
            State("edge-histogram-modal", "is_open"),
            State("runtime-data-store", "data"),
        ],
    )
    def show_edge_event_code_histogram(edge_data, time_range, is_open, runtime_store):
        _ = is_open
        if edge_data:
            runtime_df = _runtime_data_from_store(runtime_store)
            start_dt = pd.to_datetime(time_range[0], unit="s")
            end_dt = pd.to_datetime(time_range[1], unit="s")
            runtime_df = runtime_df[
                (runtime_df["timestamp"] >= start_dt) &
                (runtime_df["timestamp"] <= end_dt)
            ]
            source = edge_data["source"]
            target = edge_data["target"]
            fig = build_edge_event_code_histogram(runtime_df, source, target)
            if not _is_empty_figure(fig):
                return True, fig
        return False, {}
    
    @app.callback(
        Output("event-code-histogram", "figure"),
        [
            Input("time-range-slider", "value"),
            Input("runtime-data-store", "data"),
        ],
    )
    def show_event_code_histogram(time_range, runtime_store):
        runtime_df = _runtime_data_from_store(runtime_store)
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        df = runtime_df[(runtime_df["timestamp"] >= start_dt) & (runtime_df["timestamp"] <= end_dt)]

        # optional: if you want histogram scoped to selected trace
        # if selected_trace_id:
        #     df = df[df["trace_id"] == selected_trace_id]

        return build_all_event_code_histogram(df)
    

    @app.callback(
        Output("span-id-dropdown", "options"),
        [Input("trace-id-dropdown", "value")],
        [State("runtime-data-store", "data")],
    )
    def update_span_id_dropdown(selected_trace_id, runtime_store):
        if not selected_trace_id:
            return []

        runtime_df = _runtime_data_from_store(runtime_store)
        filtered_df = runtime_df[runtime_df["trace_id"] == selected_trace_id]
        span_ids = filtered_df["transaction_id"].dropna().unique()
        return [
            {
                "label": (
                    f"{str(span_id)[:12]}..." if len(str(span_id)) > 12 else str(span_id)
                ),
                "value": span_id,
            }
            for span_id in span_ids
        ]

    @app.callback(
        [
            Output("trace-id-dropdown", "options"),
            Output("trace-id-dropdown", "value"),
            Output("trace-id-a-dropdown", "options"),
            Output("trace-id-a-dropdown", "value"),
            Output("trace-id-b-dropdown", "options"),
            Output("trace-id-b-dropdown", "value"),
            Output("service-name-dropdown", "options"),
            Output("service-name-dropdown", "value"),
            Output("callee-service-name-dropdown", "options"),
            Output("callee-service-name-dropdown", "value"),
        ],
        [
            Input("runtime-data-store", "data"),
        ],
    )
    def update_dropdown_options(runtime_store):
        runtime_df = _runtime_data_from_store(runtime_store)
        trace_ids = runtime_df["trace_id"].dropna().unique().tolist()
        service_names = sorted(runtime_df["service_name"].dropna().unique().tolist())
        callee_names = sorted(runtime_df["callee"].dropna().unique().tolist())

        trace_options = [
            {
                "label": (f"{str(tid)[:8]}..." if len(str(tid)) > 8 else str(tid)),
                "value": tid,
            }
            for tid in trace_ids
        ]
        service_options = [{"label": name, "value": name} for name in service_names]
        callee_options = [{"label": name, "value": name} for name in callee_names]

        default_trace = trace_ids[0] if trace_ids else None
        default_service = service_names[0] if service_names else None
        default_callee = callee_names[0] if callee_names else None

        return (
            trace_options,
            default_trace,
            trace_options,
            default_trace,
            trace_options,
            default_trace,
            service_options,
            default_service,
            callee_options,
            default_callee,
        )

    @app.callback(
        [
            Output("time-range-slider", "min"),
            Output("time-range-slider", "max"),
            Output("time-range-slider", "value"),
            Output("time-range-slider", "marks"),
            Output("record-count", "children"),
            Output("start-time", "children"),
            Output("end-time", "children"),
        ],
        [
            Input("runtime-data-store", "data"),
        ],
    )
    def update_runtime_metadata(runtime_store):
        runtime_df = _runtime_data_from_store(runtime_store)
        if runtime_df.empty:
            return no_update, no_update, no_update, no_update, no_update, no_update, no_update

        min_ts = runtime_df["timestamp"].min()
        max_ts = runtime_df["timestamp"].max()
        min_ts_int = int(min_ts.timestamp())
        max_ts_int = int(max_ts.timestamp())
        marks = {
            min_ts_int: min_ts.strftime("%Y-%m-%d %H:%M:%S"),
            max_ts_int: max_ts.strftime("%Y-%m-%d %H:%M:%S"),
        }
        return (
            min_ts_int,
            max_ts_int,
            [min_ts_int, max_ts_int],
            marks,
            f"Total records: {len(runtime_df)}",
            f"Start time: {min_ts.strftime('%Y-%m-%d %H:%M:%S')}",
            f"End time: {max_ts.strftime('%Y-%m-%d %H:%M:%S')}",
        )

    @app.callback(
        [
            Output("span-cytoscape-graph", "elements"),
            Output("span-event-table", "children"),
        ],
        [
            Input("span-id-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("main-tabs", "value"),
            Input("runtime-data-store", "data"),
        ],
    )
    def update_span_graph(selected_span_id, time_range, _active_tab, runtime_store):
        if not selected_span_id:
            return [], "No span_id selected."

        runtime_df = _runtime_data_from_store(runtime_store)
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        df = runtime_df[
            (runtime_df["transaction_id"] == selected_span_id)
            & (runtime_df["timestamp"] >= start_dt)
            & (runtime_df["timestamp"] <= end_dt)
        ].copy()

        if df.empty:
            return [], "No data for selected span."

        elements = build_span_elements(df)
        table_html = build_event_table(df)
        return elements, table_html

    @app.callback(
        [
            Output("trace-compare-graph", "elements"),
            Output("trace-compare-table", "children"),
        ],
        [
            Input("trace-id-a-dropdown", "value"),
            Input("trace-id-b-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("selected-edges-in-both-traces-toggle", "value"),
            Input("selected-edges-in-trace-A-toggle", "value"),
            Input("selected-edges-in-trace-B-toggle", "value"),
            Input("runtime-data-store", "data"),
        ],
    )
    def update_trace_compare(
        trace_a,
        trace_b,
        time_range,
        show_both,
        show_a,
        show_b,
        runtime_store,
    ):
        """Build full comparison graph and table when traces are selected."""
        if not trace_a or not trace_b:
            return [], "Select both Trace A and Trace B."

        if trace_a == trace_b:
            return [], "Please choose two different trace IDs to compare."

        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")

        runtime_df = _runtime_data_from_store(runtime_store)
        filtered_data = runtime_df[
            (runtime_df["timestamp"] >= start_dt) & (runtime_df["timestamp"] <= end_dt)
        ]
        df_a = filtered_data[filtered_data["trace_id"] == trace_a]
        df_b = filtered_data[filtered_data["trace_id"] == trace_b]

        # Generate full trace difference graph
        elements = build_trace_difference_elements(df_a, df_b)

        # apply toggle visibility filtering
        allowed_presence = set()
        if show_both:
            allowed_presence.add("both")
        if show_a:
            allowed_presence.add("only A")
        if show_b:
            allowed_presence.add("only B")

        if allowed_presence:
            filtered_edges = [
                e
                for e in elements
                if "data" in e
                and e["data"].get("source")
                and e["data"].get("target")
                and e["data"].get("presence") in allowed_presence
            ]
            node_elements = [e for e in elements if "position" in e]
            elements = node_elements + filtered_edges
        else:
            # no edge type selected -> hide all edges, keep nodes
            elements = [e for e in elements if "position" in e]

        compare_table = build_trace_comparison_table(df_a, df_b, trace_a, trace_b)

        return elements, compare_table

    @app.callback(
        Output("heatmap-graph", "figure"),
        [
            Input("service-name-dropdown", "value"),
            Input("callee-service-name-dropdown", "value"),
            Input("time-range-slider", "value"),
            Input("runtime-data-store", "data"),
        ],
    )
    def update_heatmap(selected_service, selected_callee, time_range, runtime_store):
        runtime_df = _runtime_data_from_store(runtime_store)
        start_dt = pd.to_datetime(time_range[0], unit="s")
        end_dt = pd.to_datetime(time_range[1], unit="s")
        filtered_data = runtime_df[
            (runtime_df["timestamp"] >= start_dt) & (runtime_df["timestamp"] <= end_dt)
        ]
        return build_service_heatmap_figure(filtered_data, selected_service, selected_callee)

    @app.callback(
        [Output("selected-edge-modal", "is_open"), Output("selected-edge-violinplot", "figure")],
        [Input("cytoscape-graph", "tapEdgeData")],
        [
            State("selected-edge-modal", "is_open"),
            State("trace-id-dropdown", "value"),
            State("time-range-slider", "value"),
            State("runtime-data-store", "data"),
        ],
    )
    def show_selected_edge_violinplot(
        edge_data, is_open, selected_trace_id, time_range, runtime_store
    ):
        _ = is_open
        if edge_data and selected_trace_id:
            runtime_df = _runtime_data_from_store(runtime_store)
            source = edge_data["source"]
            target = edge_data["target"]
            start_dt = pd.to_datetime(time_range[0], unit="s")
            end_dt = pd.to_datetime(time_range[1], unit="s")

            filtered_df = runtime_df[
                (runtime_df["trace_id"] == selected_trace_id)
                & (runtime_df["service_name"] == source)
                & (runtime_df["callee"] == target)
                & (runtime_df["timestamp"] >= start_dt)
                & (runtime_df["timestamp"] <= end_dt)
            ]
            fig = build_selected_edge_violinplot(filtered_df, source, target)
            if not _is_empty_figure(fig):
                return True, fig
        return False, {}


    @app.callback(
        Output("node-info", "children"),
        [
            Input("overall-cytoscape-graph", "tapNodeData"),
            Input("cytoscape-graph", "tapNodeData"),
            Input("runtime-data-store", "data"),
            Input("static-data-store", "data"),
        ],
    )
    def show_node_info(overall_node_data, selected_node_data, runtime_store, static_store):
        node_data = overall_node_data or selected_node_data
        if not node_data:
            return "Click a node to see functions."

        service_name = node_data.get("id") or node_data.get("label")

        # build static mappings
        static_payload = static_store or {}
        functions = static_payload.get("functions", {}) if isinstance(static_payload, dict) else {}
        packages = static_payload.get("packages", {}) if isinstance(static_payload, dict) else {}

        def _parse_properties(value):
            if isinstance(value, dict):
                return value
            if pd.isna(value):
                return {}
            try:
                return json.loads(str(value))
            except Exception:
                return {}

        def _detect_function_column(df):
            if df is None:
                return None
            for c in ("event_code", "event_provider", "message"):
                if c in df.columns:
                    return c
            return None

        runtime_df = None
        if runtime_store:
            try:
                runtime_df = pd.read_json(runtime_store, orient="split")
            except Exception:
                runtime_df = None

        func_col = _detect_function_column(runtime_df)

        # determine which package names map back to this service
        service_package_names = set()
        for pkg_name, pkg_props in packages.items():
            pkg_meta = _parse_properties(pkg_props)
            pkg_parent = pkg_meta.get("parent") if isinstance(pkg_meta, dict) else None
            if pkg_name == service_name or pkg_parent == service_name or pkg_name.startswith(f"{service_name}/"):
                service_package_names.add(pkg_name)

        # include service_name as a root group if functions point directly to it
        service_package_names.add(service_name)

        package_function_map: dict[str, list[tuple[str, str]]] = {}
        for fname, fprops in functions.items():
            func_meta = _parse_properties(fprops)
            parent_pkg = func_meta.get("parent") if isinstance(func_meta, dict) else None
            if parent_pkg in service_package_names:
                package_function_map.setdefault(parent_pkg or service_name, []).append(
                    (fname, extract_function_name(fname))
                )
            else:
                # if the package path belongs to a service package prefix, include it too
                for pkg_name in service_package_names:
                    if parent_pkg and parent_pkg.startswith(f"{pkg_name}/"):
                        package_function_map.setdefault(parent_pkg, []).append(
                            (fname, extract_function_name(fname))
                        )
                        break

        if not package_function_map:
            return f"No static functions found for {service_name}."

        total_functions = sum(len(funcs) for funcs in package_function_map.values())
        package_sections = []
        for pkg_name in sorted(package_function_map):
            funcs = sorted(package_function_map[pkg_name], key=lambda x: x[0])
            function_items = []
            for fname, base_fname in funcs:
                invoked = 0
                if runtime_df is not None and func_col is not None and base_fname:
                    try:
                        runtime_series = runtime_df.get(func_col).astype(str).fillna("")
                        pattern = re.escape(base_fname)
                        invoked = int(
                            runtime_df[
                                (runtime_df.get("callee") == service_name)
                                & runtime_series.str.contains(pattern, case=False, na=False)
                            ].shape[0]
                        )
                    except Exception:
                        invoked = 0
                # function_items.append(html.Li(f"{fname}: {invoked}:{total_functions}"))
                function_items.append(html.Li(f"{fname}: {invoked}"))

            package_sections.append(
                html.Details(
                    [
                        html.Summary(f"{pkg_name} ({len(funcs)} functions)"),
                        html.Ul(function_items),
                    ],
                    open=False,
                )
            )

        return html.Div(
            [
                html.H6(f"{service_name} : functions by package"),
                html.Div(f"Total functions found: {total_functions}"),
                *package_sections,
            ]
        )
