"""Layout components for DeepAgent Dash."""

from dash import html, dcc
import dash_mantine_components as dmc

from .file_utils import build_file_tree, render_file_tree


def create_layout(workspace_root, app_title, app_subtitle, colors, styles, agent):
    """
    Create the app layout with current configuration.

    Args:
        workspace_root: Path to workspace directory
        app_title: Application title
        app_subtitle: Application subtitle
        colors: Color scheme dictionary
        styles: Styles dictionary
        agent: Agent instance (or None)

    Returns:
        Dash layout component
    """
    return dmc.MantineProvider([
        # State stores
        dcc.Store(id="chat-history", data=[{
            "role": "assistant",
            "content": f"""This is your AI-powered workspace. I can help you write code, analyze files, create visualizations, and more.

**Getting Started:**
- Type a message below to chat with me
- Browse files on the right (click to view, ↓ to download)
- Switch to **Canvas** tab to see charts and diagrams I create

Let's get started!"""
        }]),
        dcc.Store(id="pending-message", data=None),
        dcc.Store(id="expanded-folders", data=[]),
        dcc.Store(id="file-to-view", data=None),
        dcc.Download(id="file-download"),

        # Interval for polling agent updates (disabled by default)
        dcc.Interval(id="poll-interval", interval=250, disabled=True),

        # File viewer modal
        dmc.Modal(
            id="file-modal",
            title="",
            size="xl",
            children=[
                html.Div(id="modal-content"),
                html.Div([
                    dmc.Button(
                        "Download",
                        id="modal-download-btn",
                        variant="outline",
                        color="blue",
                        style={"marginTop": "16px"}
                    )
                ], style={"textAlign": "right"})
            ],
            opened=False,
        ),

        html.Div([
            # Header
            html.Header([
                html.Div([
                    html.Div([
                        html.H1(app_title or "DeepAgent Dash", style={
                            "fontSize": "18px", "fontWeight": "600", "margin": "0",
                        }),
                        html.Span(app_subtitle or "AI-Powered Workspace", style={
                            "fontSize": "12px", "color": colors["text_muted"], "marginLeft": "12px",
                        })
                    ], style={"display": "flex", "alignItems": "baseline"}),
                    html.Div([
                        html.Div(style={
                            "width": "8px", "height": "8px",
                            "background": colors["success"] if agent else colors["error"],
                            "marginRight": "8px",
                        }),
                        html.Span("Ready" if agent else "No Agent", style={
                            "fontSize": "13px", "color": colors["text_secondary"],
                        })
                    ], style={"display": "flex", "alignItems": "center"})
                ], style={
                    "display": "flex", "justifyContent": "space-between",
                    "alignItems": "center", "maxWidth": "1600px",
                    "margin": "0 auto", "padding": "0 24px",
                })
            ], style={
                "background": colors["bg_primary"],
                "borderBottom": f"1px solid {colors['border']}",
                "padding": "16px 0",
            }),

            # Main content
            html.Main([
                # Chat panel
                html.Div([
                    html.Div([
                        html.H2("Chat", style={"fontSize": "14px", "fontWeight": "600", "margin": "0"}),
                    ], style={
                        "padding": "16px 20px",
                        "borderBottom": f"1px solid {colors['border']}",
                        "background": colors["bg_primary"],
                    }),

                    # Messages
                    html.Div(id="chat-messages", style={
                        "flex": "1", "overflowY": "auto", "padding": "20px",
                        "display": "flex", "flexDirection": "column", "gap": "16px",
                    }),

                    # Input
                    html.Div([
                        dcc.Upload(
                            id="file-upload",
                            children=html.Div("+", style={"fontSize": "20px", "color": colors["text_muted"]}),
                            style={
                                "width": "40px", "height": "40px",
                                "display": "flex", "alignItems": "center", "justifyContent": "center",
                                "cursor": "pointer", "border": f"1px solid {colors['border']}",
                                "background": colors["bg_primary"],
                            },
                            multiple=True
                        ),
                        dcc.Input(
                            id="chat-input",
                            type="text",
                            placeholder="Type a message...",
                            className="chat-input",
                            debounce=False,
                            style={
                                "flex": "1", "padding": "10px 16px", "height": "40px",
                                "border": f"1px solid {colors['border']}",
                                "background": colors["bg_primary"], "fontSize": "14px",
                            },
                        ),
                        html.Button("Send", id="send-btn", className="send-btn", style={
                            "padding": "0 24px", "height": "40px",
                            "background": colors["accent"], "color": "#ffffff",
                            "border": "none", "fontSize": "14px", "fontWeight": "500",
                            "cursor": "pointer",
                        }),
                    ], style={
                        "display": "flex", "gap": "8px", "padding": "16px 20px",
                        "borderTop": f"1px solid {colors['border']}",
                        "background": colors["bg_primary"],
                    }),
                    html.Div(id="upload-status", style={
                        "padding": "0 20px 12px", "fontSize": "12px", "color": colors["text_muted"],
                    }),
                ], id="chat-panel", style={
                    "flex": "1", "display": "flex", "flexDirection": "column",
                    "background": colors["bg_secondary"], "minWidth": "0",
                }),

                # Resize handle
                html.Div(id="resize-handle", className="resize-handle", style={
                    "width": "4px",
                    "cursor": "col-resize",
                    "background": "transparent",
                    "flexShrink": "0",
                }),

                # Sidebar (Files/Canvas toggle)
                html.Div([
                    # Header with toggle
                    html.Div([
                        html.Div([
                            html.Button("Files", id="view-files-btn", style={
                                "background": colors["accent"],
                                "color": "#ffffff",
                                "border": "none",
                                "fontSize": "13px",
                                "fontWeight": "500",
                                "cursor": "pointer",
                                "padding": "6px 12px",
                                "borderRadius": "4px 0 0 4px",
                            }),
                            html.Button("Canvas", id="view-canvas-btn", style={
                                "background": colors["bg_secondary"],
                                "color": colors["text_secondary"],
                                "border": "none",
                                "fontSize": "13px",
                                "fontWeight": "500",
                                "cursor": "pointer",
                                "padding": "6px 12px",
                                "borderRadius": "0 4px 4px 0",
                            }),
                        ], style={"display": "flex"}),
                        html.Div([
                            html.Button(">_", id="open-terminal-btn", title="Open in Terminal", style={
                                "background": "transparent", "border": "none",
                                "fontSize": "13px", "cursor": "pointer", "padding": "4px 8px",
                                "color": colors["text_secondary"], "fontFamily": "'IBM Plex Mono', monospace",
                                "fontWeight": "600",
                            }),
                            html.Button("↻", id="refresh-btn", title="Refresh", style={
                                "background": "transparent", "border": "none",
                                "fontSize": "16px", "cursor": "pointer", "padding": "4px 8px",
                            }),
                        ], id="files-actions", style={"display": "flex", "alignItems": "center"})
                    ], style={
                        "display": "flex", "justifyContent": "space-between",
                        "alignItems": "center", "padding": "16px",
                        "borderBottom": f"1px solid {colors['border']}",
                    }),

                    # Files view
                    html.Div([
                        html.Div(
                            id="file-tree",
                            children=render_file_tree(build_file_tree(workspace_root, workspace_root), colors, styles),
                            style={
                                "flex": "1",
                                "overflowY": "auto",
                                "minHeight": "0",  # Critical for flex overflow
                                "padding-bottom": "15px"  # Bottom margin for spacing
                            }
                        ),
                    ], id="files-view", style={
                        "flex": "1",
                        "minHeight": "0",  # Critical for flex overflow
                        "display": "flex",
                        "flexDirection": "column",
                        "padding-bottom": "5%"
                    }),

                    # Canvas view (hidden by default)
                    html.Div([
                        html.Div(id="canvas-content", style={
                            "flex": "1",
                            "minHeight": "0",  # Critical for flex overflow
                            "overflowY": "auto",
                            "padding": "20px",
                            "background": "#ffffff",  # White background like a note
                        }),
                        # Clear canvas button (floating at bottom)
                        html.Div([
                            html.Button("Clear Canvas", id="clear-canvas-btn", style={
                                "background": colors["error"],
                                "color": "#ffffff",
                                "border": "none",
                                "fontSize": "13px",
                                "fontWeight": "500",
                                "cursor": "pointer",
                                "padding": "8px 16px",
                                "borderRadius": "4px",
                            })
                        ], style={
                            "padding": "12px 20px",
                            "borderTop": f"1px solid {colors['border']}",
                            "background": colors["bg_primary"],
                            "display": "flex",
                            "justifyContent": "center"
                        })
                    ], id="canvas-view", style={
                        "flex": "1",
                        "minHeight": "0",  # Critical for flex overflow
                        "display": "none",
                        "flexDirection": "column",
                        "overflow": "hidden"  # Prevent overflow from this container
                    }),
                ], id="sidebar-panel", style={
                    "flex": "1",
                    "minWidth": "0",
                    "minHeight": "0",  # Critical for flex overflow
                    "display": "flex",
                    "flexDirection": "column",
                    "background": colors["bg_primary"],
                    "borderLeft": f"1px solid {colors['border']}",
                }),
            ], id="main-container", style={"display": "flex", "flex": "1", "overflow": "hidden"}),
        ], style={"display": "flex", "flexDirection": "column", "height": "100vh"})
    ])
