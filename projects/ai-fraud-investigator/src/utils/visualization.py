"""Visualization utilities for transaction networks and risk charts."""

from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from ..models.transaction import Transaction


def build_transaction_network(transactions: list[Transaction]) -> nx.DiGraph:
    """Build a directed graph of transaction flows."""
    G = nx.DiGraph()
    for tx in transactions:
        if G.has_edge(tx.sender_id, tx.receiver_id):
            G[tx.sender_id][tx.receiver_id]["weight"] += tx.amount
            G[tx.sender_id][tx.receiver_id]["count"] += 1
        else:
            G.add_edge(
                tx.sender_id,
                tx.receiver_id,
                weight=tx.amount,
                count=1,
            )
    return G


def plot_transaction_network(G: nx.DiGraph, title: str = "Transaction Network") -> go.Figure:
    """Create an interactive Plotly visualization of the transaction network."""
    pos = nx.spring_layout(G, seed=42)

    # Edge traces
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color="#888"),
        hoverinfo="none",
        mode="lines",
    )

    # Node traces
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_text = [
        f"{n}<br>In: {G.in_degree(n, weight='weight'):,.0f}<br>"
        f"Out: {G.out_degree(n, weight='weight'):,.0f}"
        for n in G.nodes()
    ]

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=[n[:8] for n in G.nodes()],
        textposition="top center",
        hovertext=node_text,
        marker=dict(
            size=10,
            color=[G.degree(n) for n in G.nodes()],
            colorscale="YlOrRd",
            showscale=True,
            colorbar=dict(title="Connections"),
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=title,
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        ),
    )
    return fig
