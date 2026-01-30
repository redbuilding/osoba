# OhSee Tasks User Guide

## Overview

OhSee's Tasks feature enables you to create and manage long-running, autonomous tasks that can plan and execute multi-step workflows. Tasks run independently in the background and can operate overnight or for extended periods, making them perfect for complex data analysis, research projects, and multi-step automation.

## Key Features

- **Autonomous Planning**: Tasks automatically break down high-level goals into structured execution plans
- **Multi-Tool Integration**: Access to web search, SQL databases, YouTube transcripts, Python analysis, and direct LLM generation
- **Live Progress Monitoring**: Real-time streaming of task progress with step-by-step updates
- **Budget Controls**: Set limits on execution time and tool usage to prevent runaway tasks
- **Pause/Resume/Cancel**: Full control over task execution at any time
- **Rich Output Display**: View tables, images, and structured data directly in the UI
- **Template System**: Pre-built task templates for common workflows
- **Scheduled Execution**: Set up recurring tasks with cron-style scheduling

## Getting Started

### Opening the Tasks Panel

1. Click the **Tasks** button in the top-right header
2. The Tasks panel opens on the right side of the screen
3. The button shows active task count: `Tasks (2)` if you have running tasks

### Creating Your First Task

1. In the Tasks panel, enter a high-level goal in the text field:
   ```
   Analyze the latest trends in AI research by searching for recent papers and summarizing key findings
   ```

2. Click the **Play** button (▶️) to create the task

3. The system will automatically:
   - Generate a structured execution plan
   - Break down your goal into specific steps
   - Begin execution immediately

## Task Lifecycle

### Task Statuses

- **PLANNING**: System is creating the execution plan
- **PENDING**: Task is queued and waiting to start
- **RUNNING**: Task is actively executing steps
- **PAUSED**: Task execution is temporarily stopped
- **COMPLETED**: All steps finished successfully
- **FAILED**: Task encountered an error or exceeded budget limits
- **CANCELED**: Task was manually stopped

### Task Controls

Once a task is created, you can:

- **Pause** ⏸️: Temporarily stop execution
- **Resume** ▶️: Continue a paused task
- **Cancel** ⏹️: Permanently stop the task
- **Refresh** 🔄: Update the task list

## Available Tools

Tasks can use these tools automatically:

### Web Search
- **Tool**: `web_search`
- **Purpose**: Search the internet for current information
- **Example**: Research latest developments, find specific data

### Database Queries
- **Tool**: `execute_sql_query_tool`
- **Purpose**: Query MySQL databases (read-only)
- **Example**: Extract data for analysis, generate reports

### YouTube Analysis
- **Tool**: `get_youtube_transcript`
- **Purpose**: Extract and analyze video transcripts
- **Example**: Summarize educational content, analyze presentations

### Python Data Analysis
- **Tools**: `python.load_csv`, `python.get_head`, `python.get_descriptive_statistics`, `python.create_plot`, `python.query_dataframe`
- **Purpose**: Load, analyze, and visualize data
- **Example**: Statistical analysis, data cleaning, chart generation

### Direct LLM Generation
- **Tool**: `llm.generate`
- **Purpose**: Use the local LLM for reasoning, summarization, or text generation
- **Example**: Synthesize findings, create summaries, generate insights

## Example Tasks

### 1. Market Research Analysis
```
Goal: Research the current state of the electric vehicle market, including major players, market share, and recent developments, then create a comprehensive summary report
```

**Expected Plan**:
1. Search for recent EV market reports and statistics
2. Research major EV manufacturers and their market positions
3. Look up recent developments and news in the EV industry
4. Synthesize findings into a structured report
5. Generate key insights and recommendations

### 2. Data Analysis Workflow
```
Goal: Load the sales data CSV, clean and analyze it, identify trends, and create visualizations showing monthly performance
```

**Expected Plan**:
1. Load the provided CSV file
2. Examine data structure and identify any quality issues
3. Clean and prepare the data for analysis
4. Calculate monthly sales trends and statistics
5. Create visualizations (line charts, bar charts)
6. Generate summary insights about performance patterns

### 3. Research Synthesis
```
Goal: Find recent academic papers about machine learning interpretability, summarize the key methods, and identify emerging trends
```

**Expected Plan**:
1. Search for recent ML interpretability research papers
2. Extract key methodologies from top papers
3. Identify common themes and approaches
4. Research emerging trends and novel techniques
5. Create a comprehensive summary with categorized findings

### 4. YouTube Content Analysis
```
Goal: Analyze the transcript of this educational video about climate change, extract key points, and create a structured summary with main topics
```

**Expected Plan**:
1. Extract transcript from the provided YouTube URL
2. Identify main topics and themes in the content
3. Extract key facts, statistics, and arguments
4. Organize findings into logical categories
5. Generate a structured summary with bullet points

## Advanced Features

### Task Templates

Access pre-built templates for common workflows:

1. Click **Templates** button in the Tasks panel
2. Browse available templates:
   - **Data Analysis Pipeline**: Complete CSV analysis workflow
   - **Market Research Report**: Comprehensive market analysis
   - **Content Summarization**: Multi-source content synthesis
   - **Competitive Analysis**: Business intelligence gathering

3. Select a template and fill in required parameters
4. The system creates a customized task based on the template

### Scheduled Tasks

Set up recurring tasks that run automatically:

1. Click **Scheduled** button in the Tasks panel
2. Click **Create New Scheduled Task**
3. Configure the schedule:
   - **Name**: Descriptive name for the task
   - **Goal**: The task objective
   - **Cron Expression**: When to run (e.g., `0 9 * * 1` = every Monday at 9 AM)
   - **Timezone**: Your local timezone
   - **Enabled**: Whether the schedule is active

**Common Cron Patterns**:
- `0 9 * * *` - Daily at 9 AM
- `0 9 * * 1` - Every Monday at 9 AM
- `0 9 1 * *` - First day of every month at 9 AM
- `0 */6 * * *` - Every 6 hours

### Budget Controls

Control task resource usage by setting budgets when creating tasks:

```json
{
  "goal": "Your task goal here",
  "budget": {
    "max_seconds": 3600,        // 1 hour maximum
    "max_tool_calls": 50        // Maximum 50 tool invocations
  }
}
```

**Default Limits**:
- **Time**: 30 minutes maximum execution
- **Tool Calls**: 100 maximum tool invocations
- **Step Timeout**: 5 minutes per individual step

## Monitoring Task Progress

### Live Progress Stream

Tasks provide real-time updates through Server-Sent Events (SSE):

1. Click on any task in the list to view details
2. Watch live progress as steps execute
3. See step-by-step outputs including:
   - Text results and summaries
   - Data tables with sortable columns
   - Generated images and charts
   - Error messages and debugging info

### Step Output Types

Tasks can produce various output formats:

- **Text**: Plain text results, summaries, and analysis
- **Tables**: Structured data with columns and rows
- **Images**: Charts, graphs, and visualizations (displayed inline)
- **JSON**: Structured data objects
- **Errors**: Detailed error messages for debugging

### Progress Events

Monitor these event types in the live stream:

- `TASK_STATUS`: Overall task status changes
- `STEP_START`: Individual step begins execution
- `STEP_COMPLETE`: Step finishes with results
- `STEP_ERROR`: Step encounters an error
- `TOOL_CALL`: Tool invocation details
- `BUDGET_WARNING`: Approaching resource limits

## Best Practices

### Writing Effective Goals

**Good Goals** (Specific and Actionable):
```
✅ Analyze the Q3 sales data CSV to identify top-performing products and create a summary report with visualizations

✅ Research the top 5 project management tools, compare their features and pricing, and create a recommendation matrix

✅ Extract insights from the latest 3 TED talks about artificial intelligence and summarize key themes and predictions
```

**Poor Goals** (Too Vague):
```
❌ Analyze some data
❌ Do research about AI
❌ Help me with my project
```

### Task Optimization Tips

1. **Be Specific**: Include details about what you want analyzed, researched, or created
2. **Mention Data Sources**: Specify if you have files to upload or URLs to analyze
3. **Define Output Format**: Mention if you want reports, visualizations, summaries, etc.
4. **Set Context**: Provide background information that helps the task planner
5. **Use Constraints**: Mention time periods, data ranges, or specific focus areas

### Resource Management

1. **Monitor Active Tasks**: Keep track of running tasks to avoid resource conflicts
2. **Use Budgets**: Set appropriate limits for long-running or experimental tasks
3. **Pause When Needed**: Pause tasks if you need to free up resources
4. **Clean Up**: Cancel failed or unnecessary tasks to keep the list manageable

## Troubleshooting

### Common Issues

**Task Stuck in PLANNING**:
- The goal might be too vague or complex
- Try rephrasing with more specific requirements
- Check if required tools are available

**Task Fails Immediately**:
- Review the error message in the task details
- Ensure required data sources are accessible
- Check if budget limits are too restrictive

**No Progress Updates**:
- Refresh the task list
- Close and reopen the task details
- Check browser console for connection issues

**Tool Errors**:
- Web search: Check internet connectivity
- Database: Verify database is accessible
- Python: Ensure CSV data is properly formatted
- YouTube: Confirm video URL is valid and accessible

### Getting Help

1. **Check Task Details**: Expand failed steps to see specific error messages
2. **Review Logs**: Look at the Events section for detailed execution logs
3. **Simplify Goals**: Break complex goals into smaller, more focused tasks
4. **Use Templates**: Start with proven templates and modify as needed

## Integration with Conversations

### Promoting Messages to Tasks

Convert any chat message into a long-running task:

1. In any conversation, type a complex request
2. Look for the **"Promote to Task"** option
3. The message content becomes the task goal
4. The task is linked to the current conversation
5. Results are posted back to the conversation when complete

### Task-Conversation Linking

When creating tasks from the Tasks panel:
- Tasks created while viewing a conversation are automatically linked
- Completion summaries are posted to the linked conversation
- Task progress can be monitored without leaving the chat context

## API Reference

For developers integrating with the Tasks API:

### Endpoints

- `POST /api/tasks` - Create a new task
- `GET /api/tasks` - List all tasks
- `GET /api/tasks/{id}` - Get task details
- `GET /api/tasks/{id}/stream` - Stream task progress (SSE)
- `POST /api/tasks/{id}/pause` - Pause task execution
- `POST /api/tasks/{id}/resume` - Resume paused task
- `POST /api/tasks/{id}/cancel` - Cancel task execution

### Task Creation Payload

```json
{
  "goal": "Your task objective",
  "conversation_id": "optional-conversation-link",
  "ollama_model_name": "optional-model-override",
  "budget": {
    "max_seconds": 1800,
    "max_tool_calls": 50
  },
  "dry_run": false
}
```

---

## Conclusion

The Tasks system in OhSee provides powerful autonomous execution capabilities that extend far beyond simple chat interactions. By leveraging structured planning, multi-tool integration, and robust monitoring, you can accomplish complex, multi-step workflows that would be time-consuming to execute manually.

Start with simple goals, experiment with different task types, and gradually build up to more complex autonomous workflows. Each task is planned independently based on your specific goal and the available tools.
