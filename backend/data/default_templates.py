from datetime import datetime, timezone

DEFAULT_TEMPLATES = [
    {
        "name": "Code Review",
        "description": "Comprehensive code review for a project",
        "goal_template": "Review the codebase in {project_path} and provide detailed feedback on code quality, security, and best practices. Focus on {focus_areas}.",
        "default_parameters": {
            "focus_areas": "security, performance, maintainability"
        },
        "category": "development",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "name": "Data Analysis",
        "description": "Analyze CSV data and generate insights",
        "goal_template": "Load and analyze the CSV file {csv_path}, generate descriptive statistics, identify patterns, and create visualizations. Focus on {analysis_type} analysis.",
        "default_parameters": {
            "analysis_type": "exploratory"
        },
        "category": "analysis",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "name": "Documentation Generation",
        "description": "Generate comprehensive documentation for a project",
        "goal_template": "Generate comprehensive documentation for the project in {project_path}. Include {doc_types} and ensure it covers {coverage_areas}.",
        "default_parameters": {
            "doc_types": "API documentation, user guides, and setup instructions",
            "coverage_areas": "installation, usage, and troubleshooting"
        },
        "category": "documentation",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "name": "Test Suite Creation",
        "description": "Create comprehensive test suite for a project",
        "goal_template": "Create a comprehensive test suite for the project in {project_path}. Include {test_types} and aim for {coverage_target}% code coverage.",
        "default_parameters": {
            "test_types": "unit tests, integration tests, and end-to-end tests",
            "coverage_target": "80"
        },
        "category": "testing",
        "created_at": datetime.now(timezone.utc)
    },
    {
        "name": "Performance Optimization",
        "description": "Analyze and optimize application performance",
        "goal_template": "Analyze the performance of the application in {project_path} and provide optimization recommendations. Focus on {performance_areas}.",
        "default_parameters": {
            "performance_areas": "database queries, API response times, and memory usage"
        },
        "category": "optimization",
        "created_at": datetime.now(timezone.utc)
    }
]

def get_default_templates():
    """Get the list of default templates."""
    return DEFAULT_TEMPLATES
