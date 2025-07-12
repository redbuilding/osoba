import base64
import io
import json
import uuid
from typing import Dict, List, Optional, Any

import matplotlib
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from fastmcp import FastMCP
from pandas import DataFrame

# Set a non-interactive backend for Matplotlib to prevent it from trying to open a GUI
matplotlib.use('Agg')

# In-memory "database" to store dataframes between tool calls
data_store: Dict[str, DataFrame] = {}

# Initialize the MCP server using FastMCP
mcp = FastMCP(
    name="EnhancedDataAnalysisServer",
    version="1.0.0",
    display_name="Enhanced Data Analysis Server",
    description="Provides tools for CSV data loading, analysis, and visualization."
)

# --------------------------------------------------------------------------
# Data Loading Tool
# --------------------------------------------------------------------------

@mcp.tool()
async def load_csv(csv_b64: str) -> str:
    """
    Loads a CSV from a base64 encoded string into a new dataframe.
    Returns a unique ID for the loaded dataframe.
    """
    if not csv_b64:
        return "Error: csv_b64 parameter is required"

    try:
        csv_bytes = base64.b64decode(csv_b64)
        csv_file = io.BytesIO(csv_bytes)
        df = pd.read_csv(csv_file)

        df_id = str(uuid.uuid4())
        data_store[df_id] = df

        return f"Successfully loaded dataframe with ID: {df_id}. Columns: {df.columns.tolist()}, Shape: {df.shape}"
    except Exception as e:
        return f"Error loading CSV: {e}"

# --------------------------------------------------------------------------
# Data Cleaning and Inspection Tools 🧹
# --------------------------------------------------------------------------

@mcp.tool()
async def check_missing_values(df_id: str) -> str:
    """
    Checks for and returns the count of missing (NaN) values in each column.
    """
    if not df_id:
        return "Error: df_id parameter is required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    df = data_store[df_id]
    missing_values = df.isnull().sum()
    return f"Missing value counts:\n{missing_values[missing_values > 0].to_string()}"

@mcp.tool()
async def handle_missing_values(df_id: str, strategy: str, columns: Optional[List[str]] = None, value: Optional[Any] = None) -> str:
    """
    Handles missing values in specified columns of a dataframe.
    Strategy can be 'drop', 'fill', or 'interpolate'.
    For 'fill', a 'value' must be provided.
    """
    if not df_id or not strategy:
        return "Error: df_id and strategy parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    df = data_store[df_id]
    target_cols = columns if columns else df.columns

    try:
        if strategy == 'drop':
            df.dropna(subset=target_cols, inplace=True)
            return f"Dropped rows with missing values in columns: {target_cols}."
        elif strategy == 'fill':
            if value is None:
                return "Error: A 'value' must be provided for the 'fill' strategy."
            df[target_cols] = df[target_cols].fillna(value)
            return f"Filled missing values with '{value}' in columns: {target_cols}."
        elif strategy == 'interpolate':
            df[target_cols] = df[target_cols].interpolate()
            return f"Interpolated missing values in columns: {target_cols}."
        else:
            return "Error: Invalid strategy. Choose from 'drop', 'fill', or 'interpolate'."
    except Exception as e:
        return f"Error handling missing values: {e}"

# --------------------------------------------------------------------------
# Data Transformation Tools 🔄
# --------------------------------------------------------------------------

@mcp.tool()
async def rename_columns(df_id: str, rename_map_json: str) -> str:
    """
    Renames one or more columns in a dataframe.
    Expects a JSON string for the rename map, e.g., '{"old_name": "new_name"}'.
    """
    if not df_id or not rename_map_json:
        return "Error: df_id and rename_map_json parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    try:
        rename_map = json.loads(rename_map_json)
        data_store[df_id].rename(columns=rename_map, inplace=True)
        return f"Columns renamed. New columns: {data_store[df_id].columns.tolist()}"
    except Exception as e:
        return f"Error renaming columns: {e}"

@mcp.tool()
async def drop_columns(df_id: str, columns_to_drop: List[str]) -> str:
    """
    Drops one or more specified columns from a dataframe.
    """
    if not df_id or not columns_to_drop:
        return "Error: df_id and columns_to_drop parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    try:
        data_store[df_id].drop(columns=columns_to_drop, inplace=True)
        return f"Dropped columns: {columns_to_drop}. Remaining columns: {data_store[df_id].columns.tolist()}"
    except Exception as e:
        return f"Error dropping columns: {e}"

# --------------------------------------------------------------------------
# Deeper Analysis and Querying Tools 🔎
# --------------------------------------------------------------------------

@mcp.tool()
async def get_head(df_id: str, n: int = 5) -> str:
    """
    Returns the first n rows of the dataframe.
    """
    if not df_id:
        return "Error: df_id parameter is required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    return data_store[df_id].head(n).to_string()

@mcp.tool()
async def get_descriptive_statistics(df_id: str) -> str:
    """
    Returns descriptive statistics for the numerical columns of a loaded dataframe.
    """
    if not df_id:
        return "Error: df_id parameter is required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    return data_store[df_id].describe().to_string()

@mcp.tool()
async def get_value_counts(df_id: str, column_name: str) -> str:
    """
    Returns the unique values and their frequencies for a specified categorical column.
    """
    if not df_id or not column_name:
        return "Error: df_id and column_name parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    if column_name not in data_store[df_id].columns:
        return f"Error: Column '{column_name}' not found."

    return data_store[df_id][column_name].value_counts().to_string()

@mcp.tool()
async def get_correlation_matrix(df_id: str) -> str:
    """
    Computes and returns the correlation matrix for numerical columns.
    """
    if not df_id:
        return "Error: df_id parameter is required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    return data_store[df_id].corr(numeric_only=True).to_string()

@mcp.tool()
async def query_dataframe(df_id: str, query_string: str) -> str:
    """
    Filters a dataframe using a query string, stores it as a new dataframe, and returns its ID.
    Example query_string: "age > 30 and city == 'New York'"
    """
    if not df_id or not query_string:
        return "Error: df_id and query_string parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."

    try:
        filtered_df = data_store[df_id].query(query_string)
        new_df_id = str(uuid.uuid4())
        data_store[new_df_id] = filtered_df
        return f"Query successful. Created new dataframe with ID {new_df_id}. Shape: {filtered_df.shape}"
    except Exception as e:
        return f"Error executing query: {e}"

# --------------------------------------------------------------------------
# Enhanced Data Visualization Tool 📈
# --------------------------------------------------------------------------

@mcp.tool()
async def create_plot(df_id: str, plot_type: str, x_col: str, y_col: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Generates a plot from the dataframe and returns it as a base64 encoded image.
    Supported plot_types: 'histogram', 'scatterplot', 'barplot', 'boxplot', 'heatmap'
    """
    if not df_id or not plot_type or not x_col:
        return [{"type": "text", "content": "Error: df_id, plot_type, and x_col parameters are required"}]
    if df_id not in data_store:
        return [{"type": "text", "content": f"Error: Dataframe with ID {df_id} not found."}]

    df = data_store[df_id]
    fig, ax = plt.subplots(figsize=(10, 6))

    try:
        if plot_type == 'histogram':
            sns.histplot(data=df, x=x_col, ax=ax, kde=True)
            ax.set_title(f'Histogram of {x_col}')
        elif plot_type == 'scatterplot':
            if y_col is None:
                return [{"type": "text", "content": "Error: y_col is required for scatterplot."}]
            sns.scatterplot(data=df, x=x_col, y=y_col, ax=ax)
            ax.set_title(f'Scatterplot of {x_col} vs {y_col}')
        elif plot_type == 'barplot':
            if y_col is None:
                return [{"type": "text", "content": "Error: y_col is required for barplot."}]
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
            return [{"type": "text", "content": f"Error: Plot type '{plot_type}' is not supported."}]

        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

        return [
            {"type": "text", "content": f"Generated {plot_type} successfully."},
            {"type": "image", "data": img_b64, "mimeType": "image/png"}
        ]

    except Exception as e:
        return [{"type": "text", "content": f"An error occurred while creating the plot: {e}"}]
    finally:
        plt.close(fig)
