"""Application stylesheet definitions."""

overall_stylesheet = [
    {
        "selector": "edge",
        "style": {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#888",
            "arrow-scale": 2,
            "line-color": "#888",
            "width": 3,
            "label": "data(label)",
            "font-size": 12,
            "text-background-color": "#fff",
            "text-background-opacity": 1,
            "text-background-padding": "2px",
        },
    },
    {
        "selector": "node",
        "style": {
            "content": "data(label)",
            "text-valign": "center",
            "text-halign": "center",
            "background-color": "#5bc0de",
            "color": "#222",
            "font-size": 16,
            "width": 60,
            "height": 60,
        },
    },
    {
        "selector": 'edge.flow',
        "style": {
        'line-style': 'dashed',
        'line-dash-pattern': [10, 5],
        'line-dash-offset': 0
        }
    },
    {
        "selector": ".selected",
        "style": {
            "background-color": "#0074D9",
            "line-color": "#0074D9",
            "target-arrow-color": "#0074D9",
            "color": "#000",
        },
    },
    {
        "selector": "node.static-microservice",
        "style": {
            "shape": "round-rectangle",
            "border-width": 2,
            "border-color": "#495057",
        },
    },
    {
        "selector": "edge.static-edge",
        "style": {
            "line-style": "solid",
            "line-color": "#767676",
            "target-arrow-color": "#767676",
            "opacity": 0.7,
        },
    },
    {
        "selector": ".static-hidden",
        "style": {
            "display": "none",
        },
    },
]
