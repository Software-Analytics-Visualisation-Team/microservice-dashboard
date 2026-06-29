"""Neo4j push/pull helpers for the knowledge graph."""

from neo4j import GraphDatabase


def push_graph(graph: dict, uri: str, auth: tuple) -> None:
    """Write all nodes and edges to Neo4j. Safe to re-run (uses MERGE)."""
    driver = GraphDatabase.driver(uri, auth=auth)
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


def load_graph_from_neo4j(uri: str, auth: tuple) -> dict:
    """Pull all nodes and edges from Neo4j as a knowledge graph dict."""
    driver = GraphDatabase.driver(uri, auth=auth)
    nodes = []
    edges = []
    with driver.session() as session:
        for record in session.run("MATCH (n) RETURN n"):
            node = dict(record["n"])
            node["label"] = list(record["n"].labels)[0]
            nodes.append(node)
        for record in session.run(
            "MATCH (a)-[r]->(b) RETURN r, a.id AS src, b.id AS tgt"
        ):
            edge = dict(record["r"])
            edge["type"] = record["r"].type
            edge["source"] = record["src"]
            edge["target"] = record["tgt"]
            edges.append(edge)
    driver.close()
    return {"nodes": nodes, "edges": edges}
