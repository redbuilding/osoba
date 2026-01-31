# test_server_python.py
import asyncio
import base64
import json
import pytest
import sys
import os

# Clear data store before importing to avoid conflicts
import importlib.util
from fastmcp import Client

# Import the server module directly
spec = importlib.util.spec_from_file_location("server", "server_python.py")
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)

# Import MCP server and data store
mcp_server = server_module.mcp
data_store = server_module.data_store

SAMPLE_CSV_DATA = """name,age,city,salary,department
John Doe,30,New York,50000,Engineering
Jane Smith,25,San Francisco,60000,Marketing
Bob Johnson,35,Chicago,55000,Engineering
Alice Brown,28,New York,52000,Marketing
Charlie Wilson,32,San Francisco,58000,Engineering
Diana Davis,29,Chicago,51000,Marketing
Eve Miller,31,,59000,Engineering
Frank Garcia,27,New York,53000,
"""

SAMPLE_CSV_WITH_MISSING = """name,age,city,salary,department
John Doe,30,New York,50000,Engineering
Jane Smith,,San Francisco,60000,Marketing
Bob Johnson,35,,55000,Engineering
Alice Brown,28,New York,,Marketing
Charlie Wilson,32,San Francisco,58000,
Diana Davis,,Chicago,51000,Marketing
Eve Miller,31,Boston,59000,Engineering
Frank Garcia,27,New York,53000,Sales
"""

@pytest.mark.asyncio
class TestServerFunctionsDirect:
    """Direct testing of server functions using FastMCP Client."""

    def setup_method(self):
        """Clear data store before each test."""
        data_store.clear()

    async def test_get_data_info(self):
        """Test get_data_info function."""
        # Load test data
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await server_module.load_csv(csv_b64)
        df_id = result.split("ID: ")[1].split(".")[0]
        
        # Test get_data_info
        info_result = await server_module.get_data_info(df_id)
        assert "DataFrame Info:" in info_result
        assert "dtypes:" in info_result or "Data columns" in info_result
        
        # Test with invalid ID
        invalid_result = await server_module.get_data_info("invalid_id")
        assert "Error: Dataframe with ID invalid_id not found" in invalid_result

    async def test_filter_dataframe(self):
        """Test filter_dataframe function."""
        # Load test data
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await server_module.load_csv(csv_b64)
        df_id = result.split("ID: ")[1].split(".")[0]
        
        # Test valid filter
        filter_result = await server_module.filter_dataframe(df_id, "age > 30")
        assert "Filtered DataFrame" in filter_result
        
        # Test invalid condition (security check)
        dangerous_result = await server_module.filter_dataframe(df_id, "import os")
        assert "Error: Invalid condition contains potentially dangerous operations" in dangerous_result
        
        # Test with invalid ID
        invalid_result = await server_module.filter_dataframe("invalid_id", "age > 30")
        assert "Error: Dataframe with ID invalid_id not found" in invalid_result

    async def test_group_and_aggregate(self):
        """Test group_and_aggregate function."""
        # Load test data
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await server_module.load_csv(csv_b64)
        df_id = result.split("ID: ")[1].split(".")[0]
        
        # Test valid grouping
        agg_json = json.dumps({"salary": "mean"})
        group_result = await server_module.group_and_aggregate(df_id, ["department"], agg_json)
        assert "Grouped and aggregated data:" in group_result
        
        # Test invalid JSON
        invalid_json_result = await server_module.group_and_aggregate(df_id, ["department"], "invalid json")
        assert "Error: agg_functions must be valid JSON" in invalid_json_result
        
        # Test missing column
        missing_col_result = await server_module.group_and_aggregate(df_id, ["nonexistent"], agg_json)
        assert "Error: Columns not found:" in missing_col_result

    async def test_detect_outliers(self):
        """Test detect_outliers function."""
        # Load test data
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await server_module.load_csv(csv_b64)
        df_id = result.split("ID: ")[1].split(".")[0]
        
        # Test IQR method
        iqr_result = await server_module.detect_outliers(df_id, "iqr", ["salary"])
        assert "Outlier detection using iqr method:" in iqr_result
        
        # Test Z-score method
        zscore_result = await server_module.detect_outliers(df_id, "zscore", ["salary"])
        assert "Outlier detection using zscore method:" in zscore_result
        
        # Test invalid method
        invalid_method_result = await server_module.detect_outliers(df_id, "invalid", ["salary"])
        assert "Error: method must be 'iqr' or 'zscore'" in invalid_method_result

    async def test_convert_data_types(self):
        """Test convert_data_types function."""
        # Load test data
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await server_module.load_csv(csv_b64)
        df_id = result.split("ID: ")[1].split(".")[0]
        
        # Test valid conversion
        type_json = json.dumps({"age": "float64"})
        convert_result = await server_module.convert_data_types(df_id, type_json)
        assert "Data type conversion results:" in convert_result
        
        # Test invalid type
        invalid_type_json = json.dumps({"age": "invalid_type"})
        invalid_type_result = await server_module.convert_data_types(df_id, invalid_type_json)
        assert "Error: Invalid types:" in invalid_type_result
        
        # Test invalid JSON
        invalid_json_result = await server_module.convert_data_types(df_id, "invalid json")
        assert "Error: type_map_json must be valid JSON" in invalid_json_result

    async def test_perform_hypothesis_test(self):
        """Test perform_hypothesis_test function."""
        # Load test data
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await server_module.load_csv(csv_b64)
        df_id = result.split("ID: ")[1].split(".")[0]
        
        # Test correlation test
        corr_result = await server_module.perform_hypothesis_test(df_id, "correlation", "age", "salary")
        assert "Pearson correlation test:" in corr_result
        
        # Test t-test
        ttest_result = await server_module.perform_hypothesis_test(df_id, "ttest", "age", "salary")
        assert "Two-sample t-test results:" in ttest_result
        
        # Test invalid test type
        invalid_test_result = await server_module.perform_hypothesis_test(df_id, "invalid", "age", "salary")
        assert "Error: test_type must be 'ttest', 'chi2', or 'correlation'" in invalid_test_result
        
        # Test missing column
        missing_col_result = await server_module.perform_hypothesis_test(df_id, "correlation", "nonexistent", "salary")
        assert "Error: Column 'nonexistent' not found" in missing_col_result

    def create_csv_b64(self, csv_data: str) -> str:
        """Helper to create base64 encoded CSV data."""
        return base64.b64encode(csv_data.encode()).decode()

    async def load_test_data(self):
        """Helper to load test data and return df_id."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        async with Client(mcp_server) as client:
            result = await client.call_tool("load_csv", {"csv_b64": csv_b64})
            df_id = result[0].text.split("ID: ")[1].split(".")[0]
            return df_id

    async def test_load_csv(self):
        """Test loading CSV data."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)

        async with Client(mcp_server) as client:
            result = await client.call_tool("load_csv", {"csv_b64": csv_b64})

        assert len(result) == 1
        assert "Successfully loaded dataframe with ID:" in result[0].text
        assert "Columns: ['name', 'age', 'city', 'salary', 'department']" in result[0].text
        assert "Shape: (8, 5)" in result[0].text

        # Verify dataframe is in store
        df_id = result[0].text.split("ID: ")[1].split(".")[0]
        assert df_id in data_store
        assert data_store[df_id].shape == (8, 5)

    async def test_get_head(self):
        """Test getting first n rows of dataframe."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("get_head", {"df_id": df_id, "n": 3})

        assert len(result) == 1
        assert "John Doe" in result[0].text
        assert "Jane Smith" in result[0].text
        assert "Bob Johnson" in result[0].text

    async def test_get_descriptive_statistics(self):
        """Test getting descriptive statistics."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("get_descriptive_statistics", {"df_id": df_id})

        assert len(result) == 1
        assert "count" in result[0].text
        assert "mean" in result[0].text
        assert "std" in result[0].text

    async def test_get_value_counts(self):
        """Test getting value counts for a column."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("get_value_counts", {"df_id": df_id, "column_name": "department"})

        assert len(result) == 1
        assert "Engineering" in result[0].text
        assert "Marketing" in result[0].text

    async def test_check_missing_values(self):
        """Test checking for missing values."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_WITH_MISSING)

        # Load CSV with missing values
        async with Client(mcp_server) as client:
            result = await client.call_tool("load_csv", {"csv_b64": csv_b64})
            df_id = result[0].text.split("ID: ")[1].split(".")[0]

            # Check missing values
            result = await client.call_tool("check_missing_values", {"df_id": df_id})

        assert len(result) == 1
        assert "Missing value counts:" in result[0].text

    async def test_handle_missing_values_fill(self):
        """Test handling missing values by filling."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_WITH_MISSING)

        # Load CSV with missing values
        async with Client(mcp_server) as client:
            result = await client.call_tool("load_csv", {"csv_b64": csv_b64})
            df_id = result[0].text.split("ID: ")[1].split(".")[0]

            # Handle missing values by filling
            result = await client.call_tool("handle_missing_values", {
                "df_id": df_id,
                "strategy": "fill",
                "columns": ["age"],
                "value": 30
            })

        assert len(result) == 1
        assert "Filled missing values with '30'" in result[0].text

    async def test_rename_columns(self):
        """Test renaming columns."""
        df_id = await self.load_test_data()

        rename_map = {"name": "employee_name", "age": "employee_age"}
        async with Client(mcp_server) as client:
            result = await client.call_tool("rename_columns", {
                "df_id": df_id,
                "rename_map_json": json.dumps(rename_map)
            })

        assert len(result) == 1
        assert "Columns renamed" in result[0].text
        assert "employee_name" in result[0].text
        assert "employee_age" in result[0].text

    async def test_drop_columns(self):
        """Test dropping columns."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("drop_columns", {
                "df_id": df_id,
                "columns_to_drop": ["salary"]
            })

        assert len(result) == 1
        assert "Dropped columns: ['salary']" in result[0].text

    async def test_query_dataframe(self):
        """Test querying dataframe."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("query_dataframe", {
                "df_id": df_id,
                "query_string": "age > 30"
            })

        assert len(result) == 1
        assert "Query successful" in result[0].text
        assert "Created new dataframe with ID" in result[0].text

    async def test_create_histogram(self):
        """Test creating a histogram plot."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("create_plot", {
                "df_id": df_id,
                "plot_type": "histogram",
                "x_col": "age"
            })

        # The result is a JSON string containing the plot data
        assert len(result) == 1
        result_text = result[0].text
        assert "Generated histogram successfully" in result_text
        assert "image/png" in result_text
        assert "iVBORw0KGgoAAAANSUhEUgAA" in result_text  # Base64 PNG header

    async def test_error_handling_invalid_df_id(self):
        """Test error handling with invalid dataframe ID."""
        async with Client(mcp_server) as client:
            result = await client.call_tool("get_head", {"df_id": "invalid_id"})

        assert len(result) == 1
        assert "Error: Dataframe with ID invalid_id not found" in result[0].text

    async def test_error_handling_missing_parameters(self):
        """Test error handling with missing parameters."""
        async with Client(mcp_server) as client:
            try:
                result = await client.call_tool("get_head", {})
                # If no exception, check the error message in result
                assert len(result) == 1
                assert "Error: df_id parameter is required" in result[0].text
            except Exception as e:
                # FastMCP may raise validation errors for missing required parameters
                assert "df_id" in str(e)
                assert "Missing required argument" in str(e)

    async def test_error_handling_invalid_column(self):
        """Test error handling with invalid column name."""
        df_id = await self.load_test_data()

        async with Client(mcp_server) as client:
            result = await client.call_tool("get_value_counts", {
                "df_id": df_id,
                "column_name": "invalid_column"
            })

        assert len(result) == 1
        assert "Error: Column 'invalid_column' not found" in result[0].text


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
