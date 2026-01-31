# Feature: Enhanced Python Data Analysis Tools

## Feature Description

Extend the existing Python MCP server with 6 essential data analysis tools that cover the most common analytical workflows missing from the current implementation. These tools will enable comprehensive data exploration, statistical analysis, and data quality assessment within the existing FastMCP framework.

## User Story

As a data analyst using the MCP chat interface
I want access to comprehensive data analysis tools (filtering, grouping, outlier detection, data type conversion, statistical testing, and data profiling)
So that I can perform complete analytical workflows without switching between multiple tools or platforms

## Problem Statement

The current Python MCP server provides basic data operations but lacks critical analytical capabilities that are standard in data science workflows. Users cannot perform advanced filtering, statistical analysis, data quality assessment, or proper data type management, limiting the analytical depth possible through the chat interface.

## Solution Statement

Add 6 new MCP tools to the existing `server_python.py` that integrate seamlessly with the current DataFrame storage system and follow established patterns for error handling, logging, and response formatting.

## Feature Metadata

**Feature Type**: Enhancement
**Estimated Complexity**: Medium
**Primary Systems Affected**: Python MCP Server (`server_python.py`)
**Dependencies**: pandas, scipy (for statistical tests), existing FastMCP framework

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `backend/server_python.py` (lines 1-40) - Why: FastMCP setup pattern and data_store structure
- `backend/server_python.py` (lines 57-101) - Why: Error handling pattern for DataFrame operations
- `backend/server_python.py` (lines 145-167) - Why: Tool implementation pattern with validation
- `backend/server_python.py` (lines 195-212) - Why: DataFrame querying pattern to mirror for filtering
- `backend/services/mcp_service.py` (lines 55-65) - Why: Required tools list update pattern

### New Files to Create

None - all additions go into existing `backend/server_python.py`

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Pandas DataFrame.query() Documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.query.html)
  - Specific section: Query syntax and examples
  - Why: Required for safe filtering implementation
- [Pandas GroupBy Documentation](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html)
  - Specific section: Aggregation functions
  - Why: Core functionality for group_and_aggregate tool
- [SciPy Stats Documentation](https://docs.scipy.org/doc/scipy/reference/stats.html)
  - Specific section: Statistical tests (ttest_ind, chi2_contingency)
  - Why: Required for hypothesis testing implementation

### Patterns to Follow

**Tool Registration Pattern:**
```python
@mcp.tool()
async def tool_name(df_id: str, param: str) -> str:
    """Tool description"""
    if df_id not in data_store:
        return f"Error: DataFrame with ID '{df_id}' not found"
    # Implementation
    return result_string
```

**Error Handling Pattern:**
```python
try:
    # DataFrame operation
    result = data_store[df_id].operation()
    return result.to_string()
except Exception as e:
    return f"Error performing operation: {e}"
```

**Data Store Access Pattern:**
```python
if df_id not in data_store:
    return f"Error: DataFrame with ID '{df_id}' not found"
df = data_store[df_id]
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation
Add required imports and validate existing patterns work with new functionality.

### Phase 2: Core Implementation
Implement the 6 new tools following established patterns from existing codebase.

### Phase 3: Integration
Update MCP service configuration to include new tools in required_tools list.

### Phase 4: Testing & Validation
Test each tool individually and validate integration with existing workflow.

---

## STEP-BY-STEP TASKS

### ADD backend/server_python.py imports

- **IMPLEMENT**: Add scipy.stats import for statistical testing
- **PATTERN**: Follow existing import structure at top of file
- **IMPORTS**: `from scipy import stats`
- **VALIDATE**: `python -c "from scipy import stats; print('scipy available')"`

### ADD get_data_info tool

- **IMPLEMENT**: DataFrame info method with memory usage and dtypes
- **PATTERN**: Mirror `get_descriptive_statistics` pattern (lines 157-167)
- **IMPORTS**: Use existing pandas DataFrame.info()
- **GOTCHA**: Capture info() output using StringIO buffer
- **VALIDATE**: Test with sample DataFrame

### ADD filter_dataframe tool

- **IMPLEMENT**: Safe DataFrame filtering using pandas query syntax
- **PATTERN**: Mirror `query_dataframe` pattern (lines 195-212)
- **IMPORTS**: Use existing pandas DataFrame.query()
- **GOTCHA**: Validate query syntax before execution to prevent code injection
- **VALIDATE**: Test with simple filter condition

### ADD group_and_aggregate tool

- **IMPLEMENT**: GroupBy operations with multiple aggregation functions
- **PATTERN**: Follow error handling from `handle_missing_values` (lines 71-101)
- **IMPORTS**: Use pandas DataFrame.groupby() and agg()
- **GOTCHA**: Parse aggregation functions from JSON string safely
- **VALIDATE**: Test with sample grouping operation

### ADD detect_outliers tool

- **IMPLEMENT**: IQR and Z-score outlier detection methods
- **PATTERN**: Follow column validation from `get_value_counts` (lines 169-181)
- **IMPORTS**: Use pandas and numpy for statistical calculations
- **GOTCHA**: Handle non-numeric columns gracefully
- **VALIDATE**: Test with dataset containing outliers

### ADD convert_data_types tool

- **IMPLEMENT**: Safe data type conversion with validation
- **PATTERN**: Mirror `rename_columns` JSON parsing pattern (lines 107-123)
- **IMPORTS**: Use pandas astype() and to_datetime()
- **GOTCHA**: Handle conversion errors gracefully, validate type names
- **VALIDATE**: Test datetime and category conversions

### ADD perform_hypothesis_test tool

- **IMPLEMENT**: Common statistical tests (t-test, chi-square)
- **PATTERN**: Follow parameter validation from existing tools
- **IMPORTS**: Use scipy.stats for test implementations
- **GOTCHA**: Validate column types match test requirements
- **VALIDATE**: Test with sample data for each test type

### UPDATE backend/services/mcp_service.py

- **IMPLEMENT**: Add new tools to PYTHON_SERVICE_NAME required_tools list
- **PATTERN**: Follow existing required_tools pattern (lines 55-65)
- **IMPORTS**: No new imports needed
- **VALIDATE**: `python -c "from services.mcp_service import app_state; print(app_state.mcp_configs['python_service'].required_tools)"`

---

## TESTING STRATEGY

### Unit Tests

Create test cases for each new tool using existing test patterns from `test_server_python.py`:
- Valid input scenarios
- Invalid DataFrame ID handling
- Parameter validation
- Error condition handling

### Integration Tests

Test tools work together in analytical workflows:
- Load CSV → Convert types → Filter → Group → Detect outliers
- Validate data_store persistence across tool calls

### Edge Cases

- Empty DataFrames
- Non-numeric data for statistical operations
- Invalid query syntax for filtering
- Malformed JSON parameters

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
cd backend && python -m py_compile server_python.py
```

### Level 2: Import Validation

```bash
cd backend && python -c "
import server_python
print('All imports successful')
print(f'Available tools: {len([attr for attr in dir(server_python.mcp) if not attr.startswith(\"_\")])}')"
```

### Level 3: Tool Registration

```bash
cd backend && python -c "
from server_python import mcp
tools = [tool.name for tool in mcp.list_tools()]
expected = ['get_data_info', 'filter_dataframe', 'group_and_aggregate', 'detect_outliers', 'convert_data_types', 'perform_hypothesis_test']
print(f'New tools registered: {[t for t in expected if t in tools]}')"
```

### Level 4: Manual Validation

```bash
# Test with sample CSV through existing load_csv tool
cd backend && python -c "
import asyncio
from server_python import load_csv, get_data_info
import base64
import pandas as pd

# Create test CSV
df = pd.DataFrame({'A': [1,2,3,4,5], 'B': ['x','y','x','y','x']})
csv_str = df.to_csv(index=False)
csv_b64 = base64.b64encode(csv_str.encode()).decode()

async def test():
    df_id = await load_csv(csv_b64)
    info = await get_data_info(df_id.split()[-1])  # Extract ID from response
    print('Data info test passed')

asyncio.run(test())"
```

---

## ACCEPTANCE CRITERIA

- [ ] All 6 new tools are implemented and registered with FastMCP
- [ ] Tools follow existing error handling and response patterns
- [ ] Each tool validates DataFrame ID existence before operation
- [ ] Statistical tests handle non-numeric data appropriately
- [ ] Filtering tool prevents code injection through query validation
- [ ] All tools integrate with existing data_store system
- [ ] MCP service configuration updated with new required tools
- [ ] Tools work in combination for complete analytical workflows
- [ ] Error messages are informative and consistent with existing tools
- [ ] All validation commands pass without errors

---

## COMPLETION CHECKLIST

- [ ] scipy dependency added to imports
- [ ] get_data_info tool implemented with StringIO buffer
- [ ] filter_dataframe tool with query syntax validation
- [ ] group_and_aggregate tool with JSON parameter parsing
- [ ] detect_outliers tool with IQR and Z-score methods
- [ ] convert_data_types tool with safe type conversion
- [ ] perform_hypothesis_test tool with scipy.stats integration
- [ ] mcp_service.py updated with new required_tools
- [ ] All validation commands executed successfully
- [ ] Integration testing confirms workflow compatibility

---

## NOTES

**Design Decision**: Using existing data_store pattern maintains consistency and avoids architectural changes.

**Security Consideration**: DataFrame.query() method requires input validation to prevent code execution - implement whitelist approach for allowed operations.

**Performance**: Tools operate on in-memory DataFrames, suitable for typical analytical datasets but may need optimization for very large datasets.

**Extensibility**: Pattern established allows easy addition of more statistical tests and analysis methods in future.
