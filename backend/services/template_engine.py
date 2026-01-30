import re
from typing import Dict, List
from core.models import TaskTemplate

class TaskTemplateEngine:
    def render_template(self, template: TaskTemplate, parameters: Dict[str, str]) -> str:
        """Render a template with provided parameters."""
        goal = template.goal_template
        
        # Replace placeholders with parameter values
        for key, value in parameters.items():
            placeholder = f"{{{key}}}"
            goal = goal.replace(placeholder, value)
        
        # Fill in any remaining placeholders with default values
        for key, default_value in template.default_parameters.items():
            placeholder = f"{{{key}}}"
            if placeholder in goal:
                goal = goal.replace(placeholder, str(default_value))
        
        return goal
    
    def get_template_parameters(self, template_text: str) -> List[str]:
        """Extract parameter names from template text."""
        return re.findall(r'\{(\w+)\}', template_text)
    
    def validate_parameters(self, template: TaskTemplate, parameters: Dict[str, str]) -> List[str]:
        """Validate that all required parameters are provided."""
        required_params = self.get_template_parameters(template.goal_template)
        missing_params = []
        
        for param in required_params:
            if param not in parameters and param not in template.default_parameters:
                missing_params.append(param)
        
        return missing_params

# Global template engine instance
template_engine = TaskTemplateEngine()
