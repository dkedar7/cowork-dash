"""UI components for rendering messages, canvas items, and other UI elements."""

import json
from datetime import datetime
from typing import Dict, List
from dash import html, dcc


def format_message(role: str, content: str, colors: Dict, styles: Dict, is_new: bool = False):
    """Format a chat message."""
    is_user = role == "user"

    # Render content as markdown for assistant messages, plain text for user
    if is_user:
        content_element = html.Div(content, style={
            "fontSize": "15px", "lineHeight": "1.5", "whiteSpace": "pre-wrap",
        })
    else:
        content_element = dcc.Markdown(
            content,
            style={
                "fontSize": "15px",
                "lineHeight": "1.5",
            }
        )

    # Use CSS classes for theme-aware styling
    message_class = "message-enter chat-message" if is_new else "chat-message"
    if is_user:
        message_class += " chat-message-user"
    else:
        message_class += " chat-message-agent"

    return html.Div([
        html.Div([
            html.Span("You" if is_user else "Agent", className="message-role-user" if is_user else "message-role-agent", style={
                "fontSize": "12px", "fontWeight": "500",
                "textTransform": "uppercase", "letterSpacing": "0.4px",
            }),
            html.Span(datetime.now().strftime("%H:%M"), className="message-time", style={
                "fontSize": "12px", "marginLeft": "8px",
            })
        ], style={"marginBottom": "5px"}),
        content_element
    ], className=message_class, style={
        "padding": "12px 15px",
    })


def format_loading(colors: Dict):
    """Format loading indicator."""
    return html.Div([
        html.Div([
            html.Span("Agent", className="message-role-agent", style={
                "fontSize": "12px", "fontWeight": "500",
                "textTransform": "uppercase",
            }),
        ], style={"marginBottom": "5px"}),
        html.Span("Thinking", className="loading-dots thinking-pulse thinking-text", style={
            "fontSize": "15px", "fontWeight": "500",
        })
    ], className="chat-message chat-message-loading", style={"padding": "12px 15px"})


def format_thinking(thinking_text: str, colors: Dict):
    """Format thinking as an inline subordinate message."""
    if not thinking_text:
        return None

    return html.Details([
        html.Summary("Thinking", className="details-summary details-summary-thinking"),
        html.Div(thinking_text, className="details-content details-content-thinking", style={
            "whiteSpace": "pre-wrap",
        })
    ], className="chat-details", style={
        "marginBottom": "4px",
    })


def format_todos(todos: Dict, colors: Dict):
    """Format todo list. Handles dict format where keys are task names and values are statuses."""
    if not todos:
        return html.Span("No tasks", style={"color": colors["text_muted"], "fontStyle": "italic", "fontSize": "14px"})

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
                    "fontSize": "14px",
                    "color": text_color,
                    "textDecoration": text_decoration,
                    "fontWeight": font_weight if status == "in_progress" else "normal",
                })
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "4px"}))

    return html.Div(items)


def format_todos_inline(todos: Dict, colors: Dict):
    """Format todos as an inline subordinate message."""
    if not todos:
        return None

    todo_items = format_todos(todos, colors)

    return html.Details([
        html.Summary("Tasks", className="details-summary details-summary-todo"),
        html.Div(todo_items, className="details-content details-content-todo")
    ], open=True, className="chat-details", style={
        "marginBottom": "4px",
    })


def format_tool_call(tool_call: Dict, colors: Dict, is_completed: bool = False):
    """Format a single tool call as a submessage.

    Args:
        tool_call: Dict with 'name', 'args', and optionally 'result', 'status'
        colors: Color scheme dict
        is_completed: Whether the tool call has completed
    """
    tool_name = tool_call.get("name", "unknown")
    tool_args = tool_call.get("args", {})
    tool_result = tool_call.get("result")
    tool_status = tool_call.get("status", "pending")

    # Status indicator - use CSS classes for theme awareness
    if tool_status == "success":
        status_icon = "✓"
        status_class = "tool-call-success"
        icon_class = "tool-call-icon-success"
    elif tool_status == "error":
        status_icon = "✗"
        status_class = "tool-call-error"
        icon_class = "tool-call-icon-error"
    elif tool_status == "running":
        status_icon = "◐"
        status_class = "tool-call-running"
        icon_class = "tool-call-icon-running"
    else:  # pending
        status_icon = "○"
        status_class = "tool-call-pending"
        icon_class = "tool-call-icon-pending"

    # Format args for display (truncate if too long)
    args_display = ""
    if tool_args:
        try:
            args_str = json.dumps(tool_args, indent=2)
            if len(args_str) > 500:
                args_str = args_str[:500] + "..."
            args_display = args_str
        except:
            args_display = str(tool_args)[:500]

    # Build the tool call display using CSS classes
    tool_header = html.Div([
        html.Span(status_icon, className=icon_class, style={
            "marginRight": "10px",
            "fontWeight": "bold",
        }),
        html.Span("Tool: ", className="tool-call-label"),
        html.Span(tool_name, className="tool-call-name"),
    ], style={"display": "flex", "alignItems": "center"})

    # Arguments section (collapsible)
    args_section = None
    if args_display:
        args_section = html.Details([
            html.Summary("Arguments", className="tool-call-summary"),
            html.Pre(args_display, className="tool-call-args")
        ], style={"marginTop": "5px"})

    # Result section (collapsible, only if completed)
    result_section = None
    if tool_result is not None and is_completed:
        result_display = str(tool_result)
        if len(result_display) > 500:
            result_display = result_display[:500] + "..."

        result_section = html.Details([
            html.Summary("Result", className="tool-call-summary"),
            html.Pre(result_display, className="tool-call-result")
        ], style={"marginTop": "5px"})

    children = [tool_header]
    if args_section:
        children.append(args_section)
    if result_section:
        children.append(result_section)

    return html.Div(children, className=f"tool-call {status_class}")


def format_tool_calls_inline(tool_calls: List[Dict], colors: Dict):
    """Format multiple tool calls as an inline collapsible section.

    Args:
        tool_calls: List of tool call dicts with 'name', 'args', 'result', 'status'
        colors: Color scheme dict
    """
    if not tool_calls:
        return None

    # Count statuses
    completed = sum(1 for tc in tool_calls if tc.get("status") in ("success", "error"))
    total = len(tool_calls)
    running = sum(1 for tc in tool_calls if tc.get("status") == "running")

    # Summary text and class
    if running > 0:
        summary_text = f"Tools ({completed}/{total}, {running} running)"
        summary_class = "details-summary details-summary-warning"
    elif completed == total:
        summary_text = f"Tools ({total} done)"
        summary_class = "details-summary details-summary-success"
    else:
        summary_text = f"Tools ({completed}/{total})"
        summary_class = "details-summary details-summary-muted"

    tool_elements = [
        format_tool_call(tc, colors, is_completed=tc.get("status") in ("success", "error"))
        for tc in tool_calls
    ]

    return html.Details([
        html.Summary(summary_text, className=summary_class),
        html.Div(tool_elements, style={
            "paddingLeft": "10px",
        })
    ], open=False, className="chat-details", style={
        "marginBottom": "5px",
    })


def format_interrupt(interrupt_data: Dict, colors: Dict):
    """Format an interrupt request for human-in-the-loop interaction.

    Args:
        interrupt_data: Dict with 'action_requests' and/or 'message'
        colors: Color scheme dict
    """
    if not interrupt_data:
        return None

    message = interrupt_data.get("message", "The agent needs your input to continue.")
    action_requests = interrupt_data.get("action_requests", [])

    children = [
        html.Div([
            html.Span("Action Required", className="interrupt-title", style={
                "fontSize": "14px",
                "fontWeight": "600",
                "textTransform": "uppercase",
                "letterSpacing": "0.5px",
            })
        ], style={"marginBottom": "12px"}),
        html.P(message, className="interrupt-message", style={
            "fontSize": "15px",
            "marginBottom": "15px",
        })
    ]

    # Show action requests if any
    if action_requests:
        for i, action in enumerate(action_requests):
            action_type = action.get("type", "unknown")
            action_tool = action.get("tool", "")
            action_args = action.get("args", {})

            action_children = [
                html.Span("Tool: ", className="interrupt-tool-label", style={
                    "fontSize": "14px",
                }),
                html.Span(f"{action_tool}", className="interrupt-tool-name", style={
                    "fontSize": "15px",
                    "fontWeight": "600",
                    "fontFamily": "'IBM Plex Mono', monospace",
                }),
            ]

            children.append(html.Div(action_children, style={"marginBottom": "10px"}))

            # Show args for bash command specifically
            if action_tool == "bash" and action_args:
                command = action_args.get("command", "")
                if command:
                    children.append(html.Div([
                        html.Span("Command: ", className="interrupt-tool-label", style={
                            "fontSize": "14px",
                        }),
                        html.Pre(command, className="interrupt-command", style={
                            "fontSize": "15px",
                            "fontFamily": "'IBM Plex Mono', monospace",
                            "padding": "10px 15px",
                            "borderRadius": "5px",
                            "margin": "5px 0 15px 0",
                            "whiteSpace": "pre-wrap",
                            "wordBreak": "break-all",
                        })
                    ]))
            elif action_args:
                # Show other args in a compact format
                args_str = json.dumps(action_args, indent=2)
                if len(args_str) > 200:
                    args_str = args_str[:200] + "..."
                children.append(html.Pre(args_str, className="interrupt-args", style={
                    "fontSize": "14px",
                    "fontFamily": "'IBM Plex Mono', monospace",
                    "padding": "10px",
                    "borderRadius": "5px",
                    "margin": "5px 0 15px 0",
                    "maxHeight": "125px",
                    "overflow": "auto",
                }))

    # Input field for response
    children.append(html.Div([
        dcc.Input(
            id="interrupt-input",
            type="text",
            placeholder="Type your response...",
            className="interrupt-input",
            style={
                "width": "100%",
                "padding": "12px 15px",
                "borderRadius": "5px",
                "fontSize": "16px",
                "marginBottom": "10px",
            }
        ),
        html.Div([
            html.Button("Approve", id="interrupt-approve-btn", n_clicks=0,
                className="interrupt-btn interrupt-btn-approve",
                style={"marginRight": "10px"}
            ),
            html.Button("Reject", id="interrupt-reject-btn", n_clicks=0,
                className="interrupt-btn interrupt-btn-reject",
                style={"marginRight": "10px"}
            ),
            html.Button("Edit", id="interrupt-edit-btn", n_clicks=0,
                className="interrupt-btn interrupt-btn-edit"
            ),
        ], style={"display": "flex"})
    ]))

    return html.Div(children, className="interrupt-container")


def render_canvas_items(canvas_items: List[Dict], colors: Dict) -> html.Div:
    """Render all canvas items using CSS classes for theme awareness."""
    if not canvas_items:
        return html.Div([
            html.P("Canvas empty", className="canvas-empty-text", style={
                "textAlign": "center",
                "fontSize": "14px"
            }),
            html.P("Visualizations and outputs appear here", className="canvas-empty-text", style={
                "textAlign": "center",
                "fontSize": "12px",
                "marginTop": "5px"
            })
        ], className="canvas-empty", style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "center",
            "height": "100%",
            "padding": "25px"
        })

    rendered_items = []

    for i, item in enumerate(canvas_items):
        item_type = item.get("type", "unknown")
        title = item.get("title")

        # Add title if present
        if title:
            rendered_items.append(
                html.H3(title, className="canvas-item-title", style={
                    "fontSize": "15px",
                    "fontWeight": "600",
                    "marginBottom": "8px",
                    "marginTop": "15px" if i > 0 else "0",
                })
            )

        # Render based on type
        if item_type == "markdown":
            rendered_items.append(
                html.Div([
                    dcc.Markdown(
                        item.get("data", ""),
                        className="canvas-markdown",
                        style={
                            "fontSize": "15px",
                            "lineHeight": "1.5",
                            "wordBreak": "break-word",
                            "overflowWrap": "break-word",
                        }
                    )
                ], className="canvas-item canvas-item-markdown")
            )

        elif item_type == "dataframe":
            rendered_items.append(
                html.Div([
                    html.Div(
                        dangerously_allow_html=True,
                        children=dcc.Markdown(
                            item.get("html", ""),
                            dangerously_allow_html=True,
                            style={"fontSize": "14px"}
                        )
                    )
                ], className="canvas-item canvas-item-dataframe", style={
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
                            "width": "100%",
                            "height": "auto",
                            "borderRadius": "5px",
                            "objectFit": "contain",
                        }
                    )
                ], className="canvas-item canvas-item-image", style={
                    "textAlign": "center",
                })
            )

        elif item_type == "plotly":
            fig_data = item.get("data", {})
            rendered_items.append(
                html.Div([
                    dcc.Graph(
                        figure=fig_data,
                        style={"height": "400px", "width": "100%"},
                        responsive=True,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                            "responsive": True,
                        }
                    )
                ], className="canvas-item canvas-item-plotly")
            )

        elif item_type == "mermaid":
            # Mermaid diagram
            mermaid_code = item.get("data", "")
            rendered_items.append(
                html.Div([
                    html.Div(
                        mermaid_code,
                        className="mermaid-diagram",
                        style={
                            "textAlign": "center",
                            "padding": "25px",
                            "width": "100%",
                            "overflow": "auto",
                            "whiteSpace": "pre",
                        }
                    )
                ], className="canvas-item canvas-item-mermaid", style={
                    "textAlign": "center",
                    "overflow": "auto",
                })
            )

        else:
            # Unknown type
            rendered_items.append(
                html.Div([
                    html.Code(
                        str(item),
                        className="canvas-code",
                        style={
                            "fontSize": "15px",
                            "display": "block",
                            "whiteSpace": "pre-wrap",
                            "wordBreak": "break-word",
                        }
                    )
                ], className="canvas-item canvas-item-code", style={
                    "overflow": "auto",
                })
            )

    return html.Div(rendered_items, style={
        "maxWidth": "100%",
        "overflow": "hidden",
    })
