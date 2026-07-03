
import os
from neo4j import GraphDatabase
from requests import session

class Neo4jClient:
    _driver = None

    @classmethod
    def connect(cls):
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))
            )
        return cls._driver

    @classmethod
    def _get_driver(cls):
        """Always returns a live driver, reconnecting if a previous
        close() left a stale reference."""
        if cls._driver is None:
            cls.connect()
        else:
            try:
                cls._driver.verify_connectivity()
            except Exception:
                cls._driver = None
                cls.connect()
        return cls._driver
    
    @classmethod
    def close(cls):
        driver = cls._get_driver()
        if driver:
            driver.close()
            cls._driver = None
        
    @classmethod 
    def push_graph(cls, graph: dict) -> None:
        """Write all nodes and edges to Neo4j. Safe to re-run (uses MERGE)."""
        driver = cls._get_driver()
        
        with driver.session() as session:
            for node in graph["nodes"]:
                label = node["label"]
                props = {k: v for k, v in node.items() if k != "label"}
                session.run(
                    f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                    id=props["id"], props=props,
                )
            for edge in graph["edges"]:
                edge_type = edge["type"]
                props = {k: v for k, v in edge.items()
                        if k not in ("source", "target", "type")}
                session.run(
                    f"MATCH (a {{id: $src}}), (b {{id: $tgt}}) "
                    f"MERGE (a)-[r:{edge_type}]->(b) SET r += $props",
                    src=edge["source"], tgt=edge["target"], props=props,
                )
        driver.close()

    @classmethod
    def load_graph_from_neo4j(cls) -> dict:
        """Pull all nodes and edges from Neo4j as a knowledge graph dict."""
        driver = cls._get_driver()

        nodes = []
        edges = []
        with driver.session() as session:
            for record in session.run("MATCH (n) RETURN n"):
                node = dict(record["n"])
                node["label"] = list(record["n"].labels)[0]
                nodes.append(node)

            for record in session.run("MATCH (a)-[r]->(b) RETURN r, a.id AS src, b.id AS tgt"):
                edge = dict(record["r"])
                edge["type"] = record["r"].type
                edge["source"] = record["src"]
                edge["target"] = record["tgt"]
                edges.append(edge)
        driver.close()
        return {"nodes": nodes, "edges": edges}
    
    @classmethod
    def query(cls, cypher, parameters=None):
        driver = cls._get_driver()
        with driver.session() as session:
            return list(session.run(cypher, parameters or {}))
        
    @classmethod
    def retrieve_trace_ids(cls, start_time, end_time) -> list:
        """Retrieve all trace IDs from Neo4j within the specified time range."""
        cypher = """
            MATCH (et:ExecutionTrace)-[:CONTAINS]->(ri:RuntimeInvocation)
            WHERE datetime(ri.timestamp) >= datetime($start_time) AND datetime(ri.timestamp) <= datetime($end_time)
            RETURN DISTINCT et.name AS trace_id
        """
        records = cls.query(cypher, {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()})
        return [record["trace_id"] for record in records]

    @classmethod
    def retrieve_full_dependency_graph(cls, start_time, end_time) -> dict:
        """Retrieve the full dependency graph from Neo4j as a knowledge graph dict."""
        cypher = """
            MATCH (s:Service)
            OPTIONAL MATCH (s)-[:CONTAINS]->(m:Module)
            WITH s, count(m) AS moduleCount

            OPTIONAL MATCH (s)-[r:DEPENDS_ON]->(dep:Service)
            OPTIONAL MATCH (s)-[:CONTAINS]->(:Module)-[:CONTAINS]->(:Structure)-[:CONTAINS]->(op1:Operation)
            OPTIONAL MATCH (ri:RuntimeInvocation)-[:EXECUTES]->(op1)
            OPTIONAL MATCH (et:ExecutionTrace)-[:CONTAINS]->(ri)

            WITH
                s,
                moduleCount,
                r,
                dep,
                collect(DISTINCT et.name) AS trace_ids

            RETURN
                s.id AS id,
                s.name AS service,
                moduleCount,
                [
                    d IN collect(
                        CASE WHEN r.source_type = "static"
                        THEN {
                            service_id: dep.id,
                            call_count: r.call_count
                        }
                        END
                    )
                    WHERE d IS NOT NULL
                ] AS staticDependsOn,
                [
                    d IN collect(
                        CASE WHEN r.source_type = "dynamic"
                            AND ANY(ts IN r.timestamps WHERE datetime(ts) >= datetime($start_time) AND datetime(ts) <= datetime($end_time))
                        THEN {
                            service_id: dep.id,
                            call_count: size([
                                ts IN r.timestamps
                                WHERE datetime(ts) >= datetime($start_time)
                                AND datetime(ts) <= datetime($end_time)
                            ]),
                            trace_ids: trace_ids
                        }
                        END
                    )
                    WHERE d IS NOT NULL
                ] AS dynamicDependsOn
            ORDER BY moduleCount DESC
        """
        records = cls.query(cypher, {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()})

        nodes = {}
        edges = []

        total_deps = set()
        for record in records:
            if (not record["staticDependsOn"] and not record["dynamicDependsOn"]):
                # Skip services with no dependencies for now; we'll add them later
                continue

            service_id = record["id"]
            total_deps.update([service_id])
            total_deps.update(dep["service_id"] for dep in record["staticDependsOn"])
            total_deps.update(dep["service_id"] for dep in record["dynamicDependsOn"])

        for record in records:
            service_id = record["id"]
            if service_id not in total_deps:
                # Include services with no dependencies as isolated nodes
                continue


            service_name = record["service"]
            nodes[service_name] = {
                "id": service_id, 
                "label": "Service", 
                "name": service_name,
                "properties": {
                    "moduleCount": record["moduleCount"]
                }
            }

            for dep_object in record["staticDependsOn"]:
                dep_id = dep_object["service_id"]
                dep_call_count = dep_object.get("call_count", 0)

                edges.append({
                    "source": service_id,
                    "target": dep_id,
                    "type": "DEPENDS_ON",
                    "source_type": "static",
                    "properties": {
                        "call_count": dep_call_count
                    }
                })

            for dep_object in record["dynamicDependsOn"]:
                dep_id = dep_object["service_id"]
                dep_call_count = dep_object.get("call_count", 0)

                edges.append({
                    "source": service_id,
                    "target": dep_id,
                    "type": "DEPENDS_ON",
                    "source_type": "dynamic",
                    "properties": {
                        "call_count": dep_call_count,
                        "trace_ids": dep_object.get("trace_ids", [])
                    }
                })

        return {"nodes": list(nodes.values()), "edges": edges}
    
    @classmethod
    def retrieve_call_graph_for_trace(cls, trace_id: str) -> dict:
        """Retrieve the call graph for a specific trace ID"""
        cypher = """
            MATCH (et:ExecutionTrace {name: $trace_id})
                -[:CONTAINS]->
                (ri:RuntimeInvocation)
                -[e:EXECUTES]->
                (op:Operation)

            OPTIONAL MATCH (caller:Service {id: ri.caller})
            OPTIONAL MATCH (callee:Service {id: ri.callee})

            RETURN
                ri.timestamp AS timestamp,
                e.duration AS duration,
                caller.id as caller_service_id,
                caller.name as caller_service_name,
                op.name AS operation_name,
                callee.id AS service_id,
                callee.name AS service_name
            ORDER BY timestamp
        """
        records = cls.query(cypher, {"trace_id": trace_id})

        nodes = {}
        edges = []

        for record in records:
            service_id = record["service_id"]
            service_name = record["service_name"]
            nodes[service_id] = {
                "id": service_id,
                "label": "Service",
                "name": service_name
            }

            caller_service_id = record["caller_service_id"]
            caller_service_name = record["caller_service_name"]
            nodes[caller_service_id] = {
                "id": caller_service_id,
                "label": "Service",
                "name": caller_service_name
            }

            operation_name = record["operation_name"]

            if caller_service_id and caller_service_name:
                edges.append({
                    "source": caller_service_id,
                    "target": service_id,
                    "label": operation_name,
                    "properties": {
                        "trace_id": trace_id,
                        "duration": record["duration"],
                        "timestamp": record["timestamp"]
                    }
                })

        return {"nodes": list(nodes.values()), "edges": edges}

    @classmethod
    def _retrieve_invocations(cls, extra_filter: str, parameters: dict) -> list:
        """Retrieve flat RuntimeInvocation rows shaped like the legacy runtime DataFrame."""
        cypher = f"""
            MATCH (et:ExecutionTrace)-[:CONTAINS]->(ri:RuntimeInvocation)-[e:EXECUTES]->(op:Operation)
            OPTIONAL MATCH (caller:Service {{id: ri.caller}})
            OPTIONAL MATCH (callee:Service {{id: ri.callee}})
            WITH et, ri, e, op, caller, callee
            WHERE {extra_filter}
            RETURN
                ri.timestamp AS timestamp,
                caller.name AS service_name,
                callee.name AS callee,
                op.name AS event_code,
                et.name AS trace_id,
                ri.transaction_id AS transaction_id,
                e.duration AS call_duration
            ORDER BY timestamp
        """
        return [dict(record) for record in cls.query(cypher, parameters)]

    @classmethod
    def retrieve_trace_invocations(cls, trace_id: str, start_time, end_time) -> list:
        """Retrieve all RuntimeInvocation rows for a trace within a time range."""
        return cls._retrieve_invocations(
            "et.name = $trace_id AND datetime(ri.timestamp) >= datetime($start_time) "
            "AND datetime(ri.timestamp) <= datetime($end_time)",
            {
                "trace_id": trace_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

    @classmethod
    def retrieve_span_ids(cls, trace_id: str) -> list:
        """Retrieve all transaction (span) IDs recorded for a trace."""
        cypher = """
            MATCH (et:ExecutionTrace {name: $trace_id})-[:CONTAINS]->(ri:RuntimeInvocation)
            RETURN DISTINCT ri.transaction_id AS transaction_id
        """
        records = cls.query(cypher, {"trace_id": trace_id})
        return [record["transaction_id"] for record in records]

    @classmethod
    def retrieve_span_invocations(cls, transaction_id: str, start_time, end_time) -> list:
        """Retrieve all RuntimeInvocation rows for a span (transaction) within a time range."""
        return cls._retrieve_invocations(
            "ri.transaction_id = $transaction_id AND datetime(ri.timestamp) >= datetime($start_time) "
            "AND datetime(ri.timestamp) <= datetime($end_time)",
            {
                "transaction_id": transaction_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

    @classmethod
    def retrieve_service_names(cls, start_time, end_time) -> list:
        """Retrieve distinct caller service names with invocations in a time range."""
        cypher = """
            MATCH (ri:RuntimeInvocation)
            MATCH (caller:Service {id: ri.caller})
            WHERE datetime(ri.timestamp) >= datetime($start_time) AND datetime(ri.timestamp) <= datetime($end_time)
            RETURN DISTINCT caller.name AS service_name ORDER BY service_name
        """
        records = cls.query(cypher, {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()})
        return [record["service_name"] for record in records]

    @classmethod
    def retrieve_service_invocations(cls, service_name: str, start_time, end_time) -> list:
        """Retrieve all RuntimeInvocation rows made by a service within a time range."""
        return cls._retrieve_invocations(
            "caller.name = $service_name AND datetime(ri.timestamp) >= datetime($start_time) "
            "AND datetime(ri.timestamp) <= datetime($end_time)",
            {
                "service_name": service_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

    @classmethod
    def retrieve_all_invocations(cls, start_time, end_time) -> list:
        """Retrieve all RuntimeInvocation rows within a time range."""
        return cls._retrieve_invocations(
            "datetime(ri.timestamp) >= datetime($start_time) AND datetime(ri.timestamp) <= datetime($end_time)",
            {"start_time": start_time.isoformat(), "end_time": end_time.isoformat()},
        )

    @classmethod
    def retrieve_invocations_between_services(cls, source_id: str, target_id: str, start_time, end_time) -> list:
        """Retrieve all RuntimeInvocation rows between two services (by Service id) within a time range."""
        return cls._retrieve_invocations(
            "caller.id = $source_id AND callee.id = $target_id AND datetime(ri.timestamp) >= datetime($start_time) "
            "AND datetime(ri.timestamp) <= datetime($end_time)",
            {
                "source_id": source_id,
                "target_id": target_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

    @classmethod
    def retrieve_trace_edge_invocations(cls, trace_id: str, source_name: str, target_name: str, start_time, end_time) -> list:
        """Retrieve all RuntimeInvocation rows for one call edge within a trace and time range."""
        return cls._retrieve_invocations(
            "et.name = $trace_id AND caller.name = $source_name AND callee.name = $target_name "
            "AND datetime(ri.timestamp) >= datetime($start_time) AND datetime(ri.timestamp) <= datetime($end_time)",
            {
                "trace_id": trace_id,
                "source_name": source_name,
                "target_name": target_name,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

    @classmethod
    def retrieve_service_detail(cls, service_id: str, start_time, end_time) -> dict:
        """Retrieve call counts, static dependencies, and package hierarchy for a service."""
        params = {
            "service_id": service_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        counts_cypher = """
            MATCH (ri:RuntimeInvocation)
            WHERE datetime(ri.timestamp) >= datetime($start_time) AND datetime(ri.timestamp) <= datetime($end_time)
            RETURN
                count(CASE WHEN ri.caller = $service_id THEN 1 END) AS outgoing,
                count(CASE WHEN ri.callee = $service_id THEN 1 END) AS incoming
        """
        counts = cls.query(counts_cypher, params)[0]

        deps_cypher = """
            MATCH (s:Service {id: $service_id})-[r:DEPENDS_ON {source_type: 'static'}]->(dep:Service)
            RETURN dep.name AS name
        """
        dependencies = [record["name"] for record in cls.query(deps_cypher, params)]

        hierarchy_cypher = """
            MATCH (s:Service {id: $service_id})-[:CONTAINS]->(m:Module)
            OPTIONAL MATCH (m)-[:CONTAINS]->(st:Structure)-[:CONTAINS]->(op:Operation)
            RETURN m.name AS module, st.name AS structure, op.name AS operation
        """
        hierarchy = {}
        for record in cls.query(hierarchy_cypher, params):
            module = hierarchy.setdefault(record["module"], {})
            if record["structure"]:
                structure_ops = module.setdefault(record["structure"], [])
                if record["operation"]:
                    structure_ops.append(record["operation"])

        return {
            "outgoing": counts["outgoing"],
            "incoming": counts["incoming"],
            "dependencies": dependencies,
            "hierarchy": hierarchy,
        }

    @classmethod
    def retrieve_time_bounds(cls) -> dict:
        """Retrieve the total invocation count and timestamp range across all data."""
        cypher = """
            MATCH (ri:RuntimeInvocation)
            RETURN count(ri) AS count, min(ri.timestamp) AS min_timestamp, max(ri.timestamp) AS max_timestamp
        """
        record = cls.query(cypher)[0]
        return {
            "count": record["count"],
            "min_timestamp": record["min_timestamp"],
            "max_timestamp": record["max_timestamp"],
        }