import asyncio
import base64
import io
import json
import uuid
from typing import Dict, List, Optional, Any

import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    NotificationOptions,
)
from pandas import DataFrame

# Set a non-interactive backend for Matplotlib to prevent it from trying to open a GUI
matplotlib.use('Agg')

# In-memory "database" to store dataframes between tool calls
data_store: Dict[str, DataFrame] = {}

# Initialize the MCP server
server = Server("EnhancedDataAnalysisServer")

# --------------------------------------------------------------------------
# Data Loading Tool
# --------------------------------------------------------------------------

@server.call_tool()
async def load_csv(arguments: dict) -> list[TextContent]:
    """
    Loads a CSV from a base64 encoded string into a new dataframe.
    Returns a unique ID for the loaded dataframe.
    """
    csv_b64 = arguments.get("csv_b64")
    if not csv_b64:
        return [TextContent(type="text", text="Error: csv_b64 parameter is required")]

    try:
        csv_bytes = base64.b64decode(csv_b64)
        csv_file = io.BytesIO(csv_bytes)
        df = pd.read_csv(csv_file)

        df_id = str(uuid.uuid4())
        data_store[df_id] = df

        result = f"Successfully loaded dataframe with ID: {df_id}. Columns: {df.columns.tolist()}, Shape: {df.shape}"
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error loading CSV: {e}")]

# --------------------------------------------------------------------------
# Data Cleaning and Inspection Tools 🧹
# --------------------------------------------------------------------------

@server.call_tool()
async def check_missing_values(arguments: dict) -> list[TextContent]:
    """
    Checks for and returns the count of missing (NaN) values in each column.
    """
    df_id = arguments.get("df_id")
    if not df_id:
        return [TextContent(type="text", text="Error: df_id parameter is required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    df = data_store[df_id]
    missing_values = df.isnull().sum()
    result = f"Missing value counts:\n{missing_values[missing_values > 0].to_string()}"
    return [TextContent(type="text", text=result)]

@server.call_tool()
async def handle_missing_values(arguments: dict) -> list[TextContent]:
    """
    Handles missing values in specified columns of a dataframe.
    Strategy can be 'drop', 'fill', or 'interpolate'.
    For 'fill', a 'value' must be provided.
    """
    df_id = arguments.get("df_id")
    strategy = arguments.get("strategy")
    columns = arguments.get("columns")
    value = arguments.get("value")

    if not df_id or not strategy:
        return [TextContent(type="text", text="Error: df_id and strategy parameters are required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    df = data_store[df_id]
    target_cols = columns if columns else df.columns

    try:
        if strategy == 'drop':
            df.dropna(subset=target_cols, inplace=True)
            result = f"Dropped rows with missing values in columns: {target_cols}."
        elif strategy == 'fill':
            if value is None:
                return [TextContent(type="text", text="Error: A 'value' must be provided for the 'fill' strategy.")]
            df[target_cols] = df[target_cols].fillna(value)
            result = f"Filled missing values with '{value}' in columns: {target_cols}."
        elif strategy == 'interpolate':
            df[target_cols] = df[target_cols].interpolate()
            result = f"Interpolated missing values in columns: {target_cols}."
        else:
            return [TextContent(type="text", text="Error: Invalid strategy. Choose from 'drop', 'fill', or 'interpolate'.")]

        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error handling missing values: {e}")]

# --------------------------------------------------------------------------
# Data Transformation Tools 🔄
# --------------------------------------------------------------------------

@server.call_tool()
async def rename_columns(arguments: dict) -> list[TextContent]:
    """
    Renames one or more columns in a dataframe.
    Expects a JSON string for the rename map, e.g., '{"old_name": "new_name"}'.
    """
    df_id = arguments.get("df_id")
    rename_map_json = arguments.get("rename_map_json")

    if not df_id or not rename_map_json:
        return [TextContent(type="text", text="Error: df_id and rename_map_json parameters are required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    try:
        rename_map = json.loads(rename_map_json)
        data_store[df_id].rename(columns=rename_map, inplace=True)
        result = f"Columns renamed. New columns: {data_store[df_id].columns.tolist()}"
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error renaming columns: {e}")]

@server.call_tool()
async def drop_columns(arguments: dict) -> list[TextContent]:
    """
    Drops one or more specified columns from a dataframe.
    """
    df_id = arguments.get("df_id")
    columns_to_drop = arguments.get("columns_to_drop")

    if not df_id or not columns_to_drop:
        return [TextContent(type="text", text="Error: df_id and columns_to_drop parameters are required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    try:
        data_store[df_id].drop(columns=columns_to_drop, inplace=True)
        result = f"Dropped columns: {columns_to_drop}. Remaining columns: {data_store[df_id].columns.tolist()}"
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error dropping columns: {e}")]

# --------------------------------------------------------------------------
# Deeper Analysis and Querying Tools 🔎
# --------------------------------------------------------------------------

@server.call_tool()
async def get_head(arguments: dict) -> list[TextContent]:
    """
    Returns the first n rows of the dataframe.
    """
    df_id = arguments.get("df_id")
    n = arguments.get("n", 5)

    if not df_id:
        return [TextContent(type="text", text="Error: df_id parameter is required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    result = data_store[df_id].head(n).to_string()
    return [TextContent(type="text", text=result)]

@server.call_tool()
async def get_descriptive_statistics(arguments: dict) -> list[TextContent]:
    """
    Returns descriptive statistics for the numerical columns of a loaded dataframe.
    """
    df_id = arguments.get("df_id")

    if not df_id:
        return [TextContent(type="text", text="Error: df_id parameter is required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    result = data_store[df_id].describe().to_string()
    return [TextContent(type="text", text=result)]

@server.call_tool()
async def get_value_counts(arguments: dict) -> list[TextContent]:
    """
    Returns the unique values and their frequencies for a specified categorical column.
    """
    df_id = arguments.get("df_id")
    column_name = arguments.get("column_name")

    if not df_id or not column_name:
        return [TextContent(type="text", text="Error: df_id and column_name parameters are required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    if column_name not in data_store[df_id].columns:
        return [TextContent(type="text", text=f"Error: Column '{column_name}' not found.")]

    result = data_store[df_id][column_name].value_counts().to_string()
    return [TextContent(type="text", text=result)]

@server.call_tool()
async def get_correlation_matrix(arguments: dict) -> list[TextContent]:
    """
    Computes and returns the correlation matrix for numerical columns.
    """
    df_id = arguments.get("df_id")

    if not df_id:
        return [TextContent(type="text", text="Error: df_id parameter is required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    result = data_store[df_id].corr(numeric_only=True).to_string()
    return [TextContent(type="text", text=result)]

@server.call_tool()
async def query_dataframe(arguments: dict) -> list[TextContent]:
    """
    Filters a dataframe using a query string, stores it as a new dataframe, and returns its ID.
    Example query_string: "age > 30 and city == 'New York'"
    """
    df_id = arguments.get("df_id")
    query_string = arguments.get("query_string")

    if not df_id or not query_string:
        return [TextContent(type="text", text="Error: df_id and query_string parameters are required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    try:
        filtered_df = data_store[df_id].query(query_string)
        new_df_id = str(uuid.uuid4())
        data_store[new_df_id] = filtered_df
        result = f"Query successful. Created new dataframe with ID {new_df_id}. Shape: {filtered_df.shape}"
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing query: {e}")]

# --------------------------------------------------------------------------
# Enhanced Data Visualization Tool 📈
# --------------------------------------------------------------------------

@server.call_tool()
async def create_plot(arguments: dict) -> list[TextContent | ImageContent]:
    """
    Generates a plot from the dataframe and returns it as a base64 encoded image.
    Supported plot_types: 'histogram', 'scatterplot', 'barplot', 'boxplot', 'heatmap'
    """
    df_id = arguments.get("df_id")
    plot_type = arguments.get("plot_type")
    x_col = arguments.get("x_col")
    y_col = arguments.get("y_col")

    if not df_id or not plot_type or not x_col:
        return [TextContent(type="text", text="Error: df_id, plot_type, and x_col parameters are required")]

    if df_id not in data_store:
        return [TextContent(type="text", text=f"Error: Dataframe with ID {df_id} not found.")]

    df = data_store[df_id]
    fig, ax = plt.subplots(figsize=(10, 6))

    try:
        if plot_type == 'histogram':
            sns.histplot(data=df, x=x_col, ax=ax, kde=True)
            ax.set_title(f'Histogram of {x_col}')
        elif plot_type == 'scatterplot':
            if y_col is None:
                return [TextContent(type="text", text="Error: y_col is required for scatterplot.")]
            sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax)
            ax.set_title(f'Scatterplot of {x_col} vs {y_col}')
        elif plot_type == 'barplot':
            if y_col is None:
                return [TextContent(type="text", text="Error: y_col is required for barplot.")]
            sns.barplot(data=df, x=x_col, y=y_col, ax=ax)
            ax.set_title(f'Bar Plot of {y_col} by {x_col}')
        elif plot_type == 'boxplot':
            sns.boxplot(data=df, x=x_col, y=y_col, ax=ax) # y_col is optional here
            title = f'Boxplot of {x_col}' + (f' by {y_col}' if y_col else '')
            ax.set_title(title)
        elif plot_type == 'heatmap':
            sns.heatmap(df.corr(numeric_only=True), annot=True, cmap='viridis', ax=ax)
            ax.set_title('Correlation Heatmap')
        else:
            return [TextContent(type="text", text=f"Error: Plot type '{plot_type}' is not supported.")]

        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        return [
            TextContent(type="text", text=f"Generated {plot_type} successfully."),
            ImageContent(type="image", data=img_b64, mimeType="image/png")
        ]

    except Exception as e:
        return [TextContent(type="text", text=f"An error occurred while creating the plot: {e}")]
    finally:
        plt.close(fig)

# --------------------------------------------------------------------------
# Tool Definitions
# --------------------------------------------------------------------------

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="load_csv",
            description="Loads a CSV from a base64 encoded string into a new dataframe",
            inputSchema={
                "type": "object",
                "properties": {
                    "csv_b64": {"type": "string", "description": "Base64 encoded CSV data"}
                },
                "required": ["csv_b64"]
            }
        ),
        Tool(
            name="check_missing_values",
            description="Checks for and returns the count of missing (NaN) values in each column",
            inputSchema={
                "type": "object",
                "properties": {
                    "df_id": {"type": "string", "description": "Dataframe ID"}
                },
                "required": ["df_id"]
            }
        ),
        Tool(
            name="handle_missing_values",
            description="Handles missing values in specified columns of a dataframe",
            inputSchema={
                "type": "object",
                "properties": {
                    "df_id": {"type": "string", "description": "Dataframe ID"},
                    "strategy": {"type": "string", "enum": ["drop", "fill", "interpolate"], "description": "Strategy for handling missing values"},
                    "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns to process (optional)"},
                    "value": {"description": "Value to fill with (required for 'fill' strategy)"}
                },
                "required": ["df_id", "strategy"]
            }
        ),
        Tool(
            name="rename_columns",
            description="Renames one or more columns in a dataframe",
            inputSchema={
                "type": "object",
                "properties": {
                    "df_id": {"type": "string", "description": "Dataframe ID"},
                    "rename_map_json": {"type": "string", "description": "JSON string mapping old names to new names"}
                },
                "required": ["df_id", "rename_map_json"]
            }
        ),
        Tool(
            name="drop_columns",
            description="Drops one or more specified columns from a dataframe",
            inputSchema={
                "type": "object",
                "properties": {
                    "df_id": {"type": "string", "description": "Dataframe ID"},
                    "columns_to_drop": {"type": "array", "items": {"type": "string"}, "description": "List of column names to drop"}
                },
                "required": ["df_id", "columns_to_drop"]
            }
        ),
        Tool(
            name="get_head",
            description="Returns the first n rows of the dataframe",
            inputSchema={
                "type": "object",
                "properties": {
                    "df_id": {"type": "string", "description": "Dataframe ID"},
                    "n": {"type": "integer", "default": 5, "description": "Number of rows to return"}
                },
                "required": ["df_id"]
            }
        ),
        Tool(
            name="get_descriptive_statistics",
            description="Returns descriptive statistics for the numerical columns of a loaded dataframe",
            inputSchema={
                "type": "object",
                "properties": {
                    "df_id": {"type": "string", "description": "Dataframe ID"}
                },
                "required": ["df_id"]
            }
        ),
        Tool(
             name="get_value_counts",
             description="Returns the unique values and their frequencies for a specified categorical column",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "df_id": {"type": "string", "description": "Dataframe ID"},
                     "column_name": {"type": "string", "description": "Name of the column to analyze"}
                 },
                 "required": ["df_id", "column_name"]
             }
         ),
         Tool(
             name="get_correlation_matrix",
             description="Computes and returns the correlation matrix for numerical columns",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "df_id": {"type": "string", "description": "Dataframe ID"}
                 },
                 "required": ["df_id"]
             }
         ),
         Tool(
             name="query_dataframe",
             description="Filters a dataframe using a query string, stores it as a new dataframe, and returns its ID",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "df_id": {"type": "string", "description": "Dataframe ID"},
                     "query_string": {"type": "string", "description": "Query string for filtering (e.g., 'age > 30 and city == \"New York\"')"}
                 },
                 "required": ["df_id", "query_string"]
             }
         ),
         Tool(
             name="create_plot",
             description="Generates a plot from the dataframe and returns it as a base64 encoded image",
             inputSchema={
                 "type": "object",
                 "properties": {
                     "df_id": {"type": "string", "description": "Dataframe ID"},
                     "plot_type": {"type": "string", "enum": ["histogram", "scatterplot", "barplot", "boxplot", "heatmap"], "description": "Type of plot to create"},
                     "x_col": {"type": "string", "description": "Column name for x-axis"},
                     "y_col": {"type": "string", "description": "Column name for y-axis (optional for some plot types)"}
                 },
                 "required": ["df_id", "plot_type", "x_col"]
             }
         )
     ]

 # --------------------------------------------------------------------------
 # Server Entry Point
 # --------------------------------------------------------------------------

async def main():
    """Main entry point for the MCP server."""
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="EnhancedDataAnalysisServer",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(tools_changed=False),
                    experimental_capabilities=None,
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
