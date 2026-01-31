import base64
import io
import json
import uuid
from typing import Dict, List, Optional, Any

import matplotlib
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
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
async def get_data_info(df_id: str) -> str:
    """
    Returns comprehensive information about the dataframe including data types, 
    memory usage, and non-null counts.
    """
    if not df_id:
        return "Error: df_id parameter is required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    
    try:
        df = data_store[df_id]
        # Capture info() output using StringIO buffer
        buffer = io.StringIO()
        df.info(buf=buffer, memory_usage='deep')
        info_str = buffer.getvalue()
        return f"DataFrame Info:\n{info_str}"
    except Exception as e:
        return f"Error getting dataframe info: {e}"

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

@mcp.tool()
async def filter_dataframe(df_id: str, condition: str) -> str:
    """
    Filters a dataframe using pandas query syntax and returns the filtered result as a string.
    Example condition: "age > 30 and city == 'New York'"
    """
    if not df_id or not condition:
        return "Error: df_id and condition parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    
    # Basic validation to prevent code injection
    dangerous_keywords = ['import', 'exec', 'eval', '__', 'open', 'file']
    if any(keyword in condition.lower() for keyword in dangerous_keywords):
        return "Error: Invalid condition contains potentially dangerous operations"
    
    try:
        filtered_df = data_store[df_id].query(condition)
        return f"Filtered DataFrame (showing first 100 rows):\n{filtered_df.head(100).to_string()}"
    except Exception as e:
        return f"Error filtering dataframe: {e}"

@mcp.tool()
async def group_and_aggregate(df_id: str, group_by: List[str], agg_functions: str) -> str:
    """
    Groups dataframe by specified columns and applies aggregation functions.
    agg_functions should be JSON string like: {"column1": "mean", "column2": ["sum", "count"]}
    """
    if not df_id or not group_by or not agg_functions:
        return "Error: df_id, group_by, and agg_functions parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    
    try:
        df = data_store[df_id]
        
        # Validate group_by columns exist
        missing_cols = [col for col in group_by if col not in df.columns]
        if missing_cols:
            return f"Error: Columns not found: {missing_cols}"
        
        # Parse aggregation functions safely
        agg_dict = json.loads(agg_functions)
        
        # Perform groupby and aggregation
        grouped = df.groupby(group_by).agg(agg_dict)
        return f"Grouped and aggregated data:\n{grouped.to_string()}"
    except json.JSONDecodeError:
        return "Error: agg_functions must be valid JSON"
    except Exception as e:
        return f"Error performing group and aggregate: {e}"

@mcp.tool()
async def detect_outliers(df_id: str, method: str = "iqr", columns: Optional[List[str]] = None) -> str:
    """
    Detects outliers using IQR or Z-score methods.
    method: 'iqr' (Interquartile Range) or 'zscore'
    columns: List of numeric columns to analyze (if None, uses all numeric columns)
    """
    if not df_id:
        return "Error: df_id parameter is required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    
    if method not in ['iqr', 'zscore']:
        return "Error: method must be 'iqr' or 'zscore'"
    
    try:
        df = data_store[df_id]
        
        # Select numeric columns
        if columns is None:
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        else:
            numeric_cols = [col for col in columns if col in df.columns and df[col].dtype in ['int64', 'float64']]
        
        if not numeric_cols:
            return "Error: No numeric columns found for outlier detection"
        
        outlier_summary = []
        
        for col in numeric_cols:
            if method == 'iqr':
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                outliers = df[(df[col] < lower_bound) | (df[col] > upper_bound)]
                outlier_summary.append(f"{col}: {len(outliers)} outliers (bounds: {lower_bound:.2f} - {upper_bound:.2f})")
            
            elif method == 'zscore':
                z_scores = np.abs(stats.zscore(df[col].dropna()))
                outliers = df[z_scores > 3]
                outlier_summary.append(f"{col}: {len(outliers)} outliers (|z-score| > 3)")
        
        return f"Outlier detection using {method} method:\n" + "\n".join(outlier_summary)
    except Exception as e:
        return f"Error detecting outliers: {e}"

@mcp.tool()
async def convert_data_types(df_id: str, type_map_json: str) -> str:
    """
    Converts column data types safely.
    type_map_json: JSON string like {"column1": "int64", "column2": "datetime", "column3": "category"}
    Supported types: int64, float64, str, datetime, category
    """
    if not df_id or not type_map_json:
        return "Error: df_id and type_map_json parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    
    try:
        df = data_store[df_id]
        type_map = json.loads(type_map_json)
        
        # Validate columns exist
        missing_cols = [col for col in type_map.keys() if col not in df.columns]
        if missing_cols:
            return f"Error: Columns not found: {missing_cols}"
        
        # Validate type names
        valid_types = ['int64', 'float64', 'str', 'datetime', 'category']
        invalid_types = [t for t in type_map.values() if t not in valid_types]
        if invalid_types:
            return f"Error: Invalid types: {invalid_types}. Valid types: {valid_types}"
        
        conversion_results = []
        
        for col, new_type in type_map.items():
            try:
                if new_type == 'datetime':
                    df[col] = pd.to_datetime(df[col])
                elif new_type == 'category':
                    df[col] = df[col].astype('category')
                else:
                    df[col] = df[col].astype(new_type)
                conversion_results.append(f"{col}: converted to {new_type}")
            except Exception as e:
                conversion_results.append(f"{col}: conversion failed - {str(e)}")
        
        return f"Data type conversion results:\n" + "\n".join(conversion_results)
    except json.JSONDecodeError:
        return "Error: type_map_json must be valid JSON"
    except Exception as e:
        return f"Error converting data types: {e}"

@mcp.tool()
async def perform_hypothesis_test(df_id: str, test_type: str, col1: str, col2: Optional[str] = None) -> str:
    """
    Performs statistical hypothesis tests.
    test_type: 'ttest' (two-sample t-test), 'chi2' (chi-square test), 'correlation' (Pearson correlation)
    col1: First column name
    col2: Second column name (required for ttest and correlation, optional for chi2)
    """
    if not df_id or not test_type or not col1:
        return "Error: df_id, test_type, and col1 parameters are required"
    if df_id not in data_store:
        return f"Error: Dataframe with ID {df_id} not found."
    
    if test_type not in ['ttest', 'chi2', 'correlation']:
        return "Error: test_type must be 'ttest', 'chi2', or 'correlation'"
    
    try:
        df = data_store[df_id]
        
        # Validate columns exist
        if col1 not in df.columns:
            return f"Error: Column '{col1}' not found"
        if col2 and col2 not in df.columns:
            return f"Error: Column '{col2}' not found"
        
        if test_type == 'ttest':
            if not col2:
                return "Error: col2 is required for t-test"
            
            # Check if columns are numeric
            if not pd.api.types.is_numeric_dtype(df[col1]) or not pd.api.types.is_numeric_dtype(df[col2]):
                return "Error: Both columns must be numeric for t-test"
            
            statistic, p_value = stats.ttest_ind(df[col1].dropna(), df[col2].dropna())
            return f"Two-sample t-test results:\nStatistic: {statistic:.4f}\nP-value: {p_value:.4f}\nSignificant at α=0.05: {p_value < 0.05}"
        
        elif test_type == 'chi2':
            if col2:
                # Chi-square test of independence
                contingency_table = pd.crosstab(df[col1], df[col2])
                statistic, p_value, dof, expected = stats.chi2_contingency(contingency_table)
                return f"Chi-square test of independence:\nStatistic: {statistic:.4f}\nP-value: {p_value:.4f}\nDegrees of freedom: {dof}\nSignificant at α=0.05: {p_value < 0.05}"
            else:
                return "Error: col2 is required for chi-square test of independence"
        
        elif test_type == 'correlation':
            if not col2:
                return "Error: col2 is required for correlation test"
            
            # Check if columns are numeric
            if not pd.api.types.is_numeric_dtype(df[col1]) or not pd.api.types.is_numeric_dtype(df[col2]):
                return "Error: Both columns must be numeric for correlation test"
            
            correlation, p_value = stats.pearsonr(df[col1].dropna(), df[col2].dropna())
            return f"Pearson correlation test:\nCorrelation coefficient: {correlation:.4f}\nP-value: {p_value:.4f}\nSignificant at α=0.05: {p_value < 0.05}"
    
    except Exception as e:
        return f"Error performing hypothesis test: {e}"

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
