# test_server_direct.py
import asyncio
import base64
import json
import pytest
import sys
import os

# Clear data store before importing to avoid conflicts
import importlib.util

# Import the server module directly
spec = importlib.util.spec_from_file_location("server", "server_python.py")
server_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_module)

# Import functions and data store
load_csv = server_module.load_csv
get_head = server_module.get_head
get_descriptive_statistics = server_module.get_descriptive_statistics
check_missing_values = server_module.check_missing_values
handle_missing_values = server_module.handle_missing_values
rename_columns = server_module.rename_columns
drop_columns = server_module.drop_columns
get_value_counts = server_module.get_value_counts
get_correlation_matrix = server_module.get_correlation_matrix
query_dataframe = server_module.query_dataframe
create_plot = server_module.create_plot
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
    """Direct testing of server functions without MCP client overhead."""

    def setup_method(self):
        """Clear data store before each test."""
        data_store.clear()

    def create_csv_b64(self, csv_data: str) -> str:
        """Helper to create base64 encoded CSV data."""
        return base64.b64encode(csv_data.encode()).decode()

    async def load_test_data(self):
        """Helper to load test data and return df_id."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)
        result = await load_csv({"csv_b64": csv_b64})
        df_id = result[0].text.split("ID: ")[1].split(".")[0]
        return df_id

    async def test_load_csv(self):
        """Test loading CSV data."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_DATA)

        result = await load_csv({"csv_b64": csv_b64})

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

        result = await get_head({"df_id": df_id, "n": 3})

        assert len(result) == 1
        assert "John Doe" in result[0].text
        assert "Jane Smith" in result[0].text
        assert "Bob Johnson" in result[0].text

    async def test_get_descriptive_statistics(self):
        """Test getting descriptive statistics."""
        df_id = await self.load_test_data()

        result = await get_descriptive_statistics({"df_id": df_id})

        assert len(result) == 1
        assert "count" in result[0].text
        assert "mean" in result[0].text
        assert "std" in result[0].text

    async def test_get_value_counts(self):
        """Test getting value counts for a column."""
        df_id = await self.load_test_data()

        result = await get_value_counts({"df_id": df_id, "column_name": "department"})

        assert len(result) == 1
        assert "Engineering" in result[0].text
        assert "Marketing" in result[0].text

    async def test_check_missing_values(self):
        """Test checking for missing values."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_WITH_MISSING)

        # Load CSV with missing values
        result = await load_csv({"csv_b64": csv_b64})
        df_id = result[0].text.split("ID: ")[1].split(".")[0]

        # Check missing values
        result = await check_missing_values({"df_id": df_id})

        assert len(result) == 1
        assert "Missing value counts:" in result[0].text

    async def test_handle_missing_values_fill(self):
        """Test handling missing values by filling."""
        csv_b64 = self.create_csv_b64(SAMPLE_CSV_WITH_MISSING)

        # Load CSV with missing values
        result = await load_csv({"csv_b64": csv_b64})
        df_id = result[0].text.split("ID: ")[1].split(".")[0]

        # Handle missing values by filling
        result = await handle_missing_values({
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
        result = await rename_columns({
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

        result = await drop_columns({
            "df_id": df_id,
            "columns_to_drop": ["salary"]
        })

        assert len(result) == 1
        assert "Dropped columns: ['salary']" in result[0].text

    async def test_query_dataframe(self):
        """Test querying dataframe."""
        df_id = await self.load_test_data()

        result = await query_dataframe({
            "df_id": df_id,
            "query_string": "age > 30"
        })

        assert len(result) == 1
        assert "Query successful" in result[0].text
        assert "Created new dataframe with ID" in result[0].text

    async def test_create_histogram(self):
        """Test creating a histogram plot."""
        df_id = await self.load_test_data()

        result = await create_plot({
            "df_id": df_id,
            "plot_type": "histogram",
            "x_col": "age"
        })

        assert len(result) == 2
        assert "Generated histogram successfully" in result[0].text
        assert result[1].type == "image"
        assert result[1].mimeType == "image/png"

    async def test_error_handling_invalid_df_id(self):
        """Test error handling with invalid dataframe ID."""
        result = await get_head({"df_id": "invalid_id"})

        assert len(result) == 1
        assert "Error: Dataframe with ID invalid_id not found" in result[0].text

    async def test_error_handling_missing_parameters(self):
        """Test error handling with missing parameters."""
        result = await get_head({})

        assert len(result) == 1
        assert "Error: df_id parameter is required" in result[0].text

    async def test_error_handling_invalid_column(self):
        """Test error handling with invalid column name."""
        df_id = await self.load_test_data()

        result = await get_value_counts({
            "df_id": df_id,
            "column_name": "invalid_column"
        })

        assert len(result) == 1
        assert "Error: Column 'invalid_column' not found" in result[0].text


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
