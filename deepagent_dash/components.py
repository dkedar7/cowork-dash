"""UI components for rendering messages, canvas items, and other UI elements."""

from datetime import datetime
from typing import Dict, List
from dash import html, dcc


def format_message(role: str, content: str, colors: Dict, styles: Dict, is_new: bool = False):
    """Format a chat message."""
    is_user = role == "user"

    # Render content as markdown for assistant messages, plain text for user
    if is_user:
        content_element = html.Div(content, style={
            "fontSize": "14px", "lineHeight": "1.6", "whiteSpace": "pre-wrap",
        })
    else:
        content_element = dcc.Markdown(
            content,
            style={
                "fontSize": "14px",
                "lineHeight": "1.6",
                "marginLeft": "8px",
            }
        )

    return html.Div([
        html.Div([
            html.Span("You" if is_user else "Agent", style={
                "fontSize": "12px", "fontWeight": "500",
                "color": colors["accent"] if is_user else colors["text_muted"],
                "textTransform": "uppercase", "letterSpacing": "0.5px",
            }),
            html.Span(datetime.now().strftime("%H:%M"), style={
                "fontSize": "11px", "color": colors["text_muted"], "marginLeft": "8px",
            })
        ], style={"marginBottom": "8px"}),
        content_element
    ], className="message-enter" if is_new else "", style={
        "padding": "16px",
        "background": colors["accent_light"] if is_user else colors["bg_primary"],
        "borderLeft": f"3px solid {colors['accent'] if is_user else colors['border']}",
        "boxShadow": "none" if is_user else styles["shadow"],
    })


def format_loading(colors: Dict):
    """Format loading indicator."""
    return html.Div([
        html.Div([
            html.Span("Agent", style={
                "fontSize": "12px", "fontWeight": "500",
                "color": colors["text_muted"], "textTransform": "uppercase",
            }),
        ], style={"marginBottom": "8px"}),
        html.Span("Thinking", className="loading-dots thinking-pulse", style={
            "fontSize": "14px", "color": colors["thinking"], "fontWeight": "500",
        })
    ], style={
        "padding": "16px", "background": colors["bg_primary"],
        "borderLeft": f"3px solid {colors['thinking']}",
    })


def format_thinking(thinking_text: str, colors: Dict):
    """Format thinking as an inline subordinate message."""
    if not thinking_text:
        return None

    return html.Details([
        html.Summary("🧠 Thinking", style={
            "fontSize": "11px",
            "fontWeight": "500",
            "color": colors["thinking"],
            "cursor": "pointer",
            "padding": "8px 12px",
            "background": colors["bg_secondary"],
            "borderLeft": f"2px solid {colors['thinking']}",
            "userSelect": "none",
            "marginBottom": "4px",
        }),
        html.Div(thinking_text, style={
            "fontSize": "12px",
            "color": colors["text_secondary"],
            "padding": "8px 12px",
            "background": colors["bg_secondary"],
            "borderLeft": f"2px solid {colors['thinking']}",
            "whiteSpace": "pre-wrap",
        })
    ], style={
        "marginBottom": "8px",
    })


def format_todos(todos: Dict, colors: Dict):
    """Format todo list. Handles dict format where keys are task names and values are statuses."""
    if not todos:
        return html.Span("No tasks", style={"color": colors["text_muted"], "fontStyle": "italic", "fontSize": "13px"})

    items = []

    # Handle dictionary format: {task_name: status}
    if isinstance(todos, dict):
        for task_name, status in todos.items():
            # Determine checkbox symbol and styling based on status
            if status == "completed":
                checkbox_symbol = "✓"
                checkbox_color = colors["todo"]
                text_color = colors["text_muted"]
                text_decoration = "line-through"
                font_weight = "bold"
            elif status == "in_progress":
                checkbox_symbol = "◐"
                checkbox_color = colors["warning"]
                text_color = colors["text_primary"]
                text_decoration = "none"
                font_weight = "bold"
            else:  # pending
                checkbox_symbol = "○"
                checkbox_color = colors["text_muted"]
                text_color = colors["text_primary"]
                text_decoration = "none"
                font_weight = "normal"

            checkbox = html.Span(
                checkbox_symbol,
                style={
                    "fontSize": "14px",
                    "color": checkbox_color,
                    "marginRight": "8px",
                    "fontWeight": font_weight,
                }
            )

            items.append(html.Div([
                checkbox,
                html.Span(task_name, style={
                    "fontSize": "13px",
                    "color": text_color,
                    "textDecoration": text_decoration,
                    "fontWeight": font_weight if status == "in_progress" else "normal",
                })
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px"}))

    return html.Div(items)


def format_todos_inline(todos: Dict, colors: Dict):
    """Format todos as an inline subordinate message."""
    if not todos:
        return None

    todo_items = format_todos(todos, colors)

    return html.Details([
        html.Summary("📋 Task Progress", style={
            "fontSize": "11px",
            "fontWeight": "500",
            "color": colors["todo"],
            "cursor": "pointer",
            "padding": "8px 12px",
            "background": colors["bg_secondary"],
            "borderLeft": f"2px solid {colors['todo']}",
            "userSelect": "none",
            "marginBottom": "4px",
        }),
        html.Div(todo_items, style={
            "padding": "8px 12px",
            "background": colors["bg_secondary"],
            "borderLeft": f"2px solid {colors['todo']}",
        })
    ], open=True, style={
        "marginBottom": "8px",
    })


def render_canvas_items(canvas_items: List[Dict], colors: Dict) -> html.Div:
    """Render all canvas items."""
    if not canvas_items:
        return html.Div([
            html.Div("🎨", style={
                "fontSize": "48px",
                "textAlign": "center",
                "marginBottom": "16px",
                "opacity": "0.3"
            }),
            html.P("Canvas is empty", style={
                "textAlign": "center",
                "color": colors["text_muted"],
                "fontSize": "14px"
            }),
            html.P("The agent will add visualizations, charts, and notes here", style={
                "textAlign": "center",
                "color": colors["text_muted"],
                "fontSize": "12px",
                "marginTop": "8px"
            })
        ], style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
            "height": "100%",
            "padding": "40px"
        })

    rendered_items = []

    for i, item in enumerate(canvas_items):
        item_type = item.get("type", "unknown")
        title = item.get("title")

        # Add title if present
        if title:
            rendered_items.append(
                html.H3(title, style={
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "marginBottom": "12px",
                    "marginTop": "24px" if i > 0 else "0",
                    "color": colors["text_primary"]
                })
            )

        # Render based on type
        if item_type == "markdown":
            rendered_items.append(
                html.Div([
                    dcc.Markdown(
                        item.get("data", ""),
                        style={
                            "fontSize": "14px",
                            "lineHeight": "1.6",
                            "color": colors["text_primary"],
                        }
                    )
                ], style={
                    "marginBottom": "20px",
                    "padding": "16px",
                    "background": "#ffffff",
                    "borderRadius": "6px",
                    "border": f"1px solid {colors['border_light']}",
                })
            )

        elif item_type == "dataframe":
            rendered_items.append(
                html.Div([
                    html.Div(
                        dangerously_allow_html=True,
                        children=dcc.Markdown(
                            item.get("html", ""),
                            dangerously_allow_html=True,
                            style={"fontSize": "13px"}
                        )
                    )
                ], style={
                    "marginBottom": "20px",
                    "padding": "16px",
                    "background": "#ffffff",
                    "borderRadius": "6px",
                    "border": f"1px solid {colors['border_light']}",
                    "overflowX": "auto",
                })
            )

        elif item_type == "matplotlib" or item_type == "image":
            img_data = item.get("data", "")
            rendered_items.append(
                html.Div([
                    html.Img(
                        src=f"data:image/png;base64,{img_data}",
                        style={
                            "maxWidth": "100%",
                            "height": "auto",
                            "borderRadius": "4px",
                        }
                    )
                ], style={
                    "marginBottom": "20px",
                    "padding": "16px",
                    "background": "#ffffff",
                    "borderRadius": "6px",
                    "border": f"1px solid {colors['border_light']}",
                    "textAlign": "center",
                })
            )

        elif item_type == "plotly":
            fig_data = item.get("data", {})
            rendered_items.append(
                html.Div([
                    dcc.Graph(
                        figure=fig_data,
                        style={"height": "500px"},
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        }
                    )
                ], style={
                    "marginBottom": "20px",
                    "padding": "16px",
                    "background": "#ffffff",
                    "borderRadius": "6px",
                    "border": f"1px solid {colors['border_light']}",
                })
            )

        elif item_type == "mermaid":
            # Mermaid diagram
            mermaid_code = item.get("data", "")
            rendered_items.append(
                html.Div([
                    html.Div(
                        mermaid_code,
                        className="mermaid-diagram mermaid",
                        style={
                            "textAlign": "center",
                            "padding": "20px",
                            "width": "100%",
                            "overflow": "auto",
                        }
                    )
                ], style={
                    "marginBottom": "20px",
                    "padding": "16px",
                    "background": "#ffffff",
                    "borderRadius": "6px",
                    "border": f"1px solid {colors['border_light']}",
                    "textAlign": "center",
                    "width": "100%",
                })
            )

        else:
            # Unknown type
            rendered_items.append(
                html.Div([
                    html.Code(
                        str(item),
                        style={
                            "fontSize": "12px",
                            "color": colors["text_secondary"],
                            "display": "block",
                            "whiteSpace": "pre-wrap",
                        }
                    )
                ], style={
                    "marginBottom": "20px",
                    "padding": "16px",
                    "background": "#ffffff",
                    "borderRadius": "6px",
                    "border": f"1px solid {colors['border_light']}",
                })
            )

    return html.Div(rendered_items)
