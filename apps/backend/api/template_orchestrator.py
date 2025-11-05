"""
Template Orchestrator - Intelligent Multi-Template Workflow Engine
This demonstrates the true power of having 256 templates that work together
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime
import json
import logging

from template_library_full import get_full_template_library, TemplateCategory, SQLTemplate
from bigquery_engine import BigQueryAIEngine

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """A single step in a template workflow"""
    template_id: str
    parameters: Dict[str, str]
    depends_on: Optional[List[str]] = None
    output_name: str = None
    condition: Optional[str] = None


@dataclass
class TemplateWorkflow:
    """A complete workflow combining multiple templates"""
    name: str
    description: str
    steps: List[WorkflowStep]
    final_output: str


class TemplateOrchestrator:
    """
    Orchestrates complex workflows by intelligently chaining templates together.
    This is where the magic happens - templates become building blocks for 
    sophisticated e-commerce intelligence pipelines.
    """
    
    def __init__(self, engine: BigQueryAIEngine):
        self.engine = engine
        self.template_library = get_full_template_library()
        self.workflow_history = []
        
    def create_smart_catalog_enhancement_workflow(self) -> TemplateWorkflow:
        """
        Create an intelligent workflow that:
        1. Discovers schema
        2. Validates data quality
        3. Enriches products based on quality score
        4. Standardizes categories/brands
        5. Generates personalized content
        6. Forecasts demand
        
        This demonstrates templates working together intelligently
        """
        
        workflow = TemplateWorkflow(
            name="Smart Catalog Enhancement Pipeline",
            description="Intelligently enhances catalog based on data quality",
            steps=[
                # Step 1: Validate data quality first
                WorkflowStep(
                    template_id="VALID_186",
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "name_column": "product_name",
                        "price_column": "price",
                        "description_column": "description",
                        "category_column": "category"
                    },
                    output_name="quality_report"
                ),
                
                # Step 2: Extract attributes from existing text
                WorkflowStep(
                    template_id="EXTRACT_051",
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "text_column": "product_name",
                        "size_column": "size"
                    },
                    depends_on=["quality_report"],
                    output_name="extracted_sizes"
                ),
                
                # Step 3: Extract colors in parallel
                WorkflowStep(
                    template_id="EXTRACT_052",
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "text_column": "product_name",
                        "color_column": "color"
                    },
                    depends_on=["quality_report"],
                    output_name="extracted_colors"
                ),
                
                # Step 4: Standardize categories based on extraction results
                WorkflowStep(
                    template_id="CATEGORY_091",
                    parameters={
                        "table_name": "{input_table}",
                        "mapping_table": "{category_mapping}",
                        "sku_column": "sku",
                        "category_column": "category"
                    },
                    depends_on=["extracted_sizes", "extracted_colors"],
                    output_name="standardized_categories"
                ),
                
                # Step 5: Clean brand names
                WorkflowStep(
                    template_id="BRAND_121",
                    parameters={
                        "table_name": "{input_table}",
                        "brand_mapping_table": "{brand_mapping}",
                        "sku_column": "sku",
                        "brand_column": "brand_name"
                    },
                    depends_on=["standardized_categories"],
                    output_name="standardized_brands"
                ),
                
                # Step 6: Generate descriptions only for products that need them
                WorkflowStep(
                    template_id="ENRICH_001",
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "brand_column": "brand_name",
                        "name_column": "product_name",
                        "category_column": "category",
                        "attribute_column": "material",
                        "description_column": "description"
                    },
                    depends_on=["standardized_brands"],
                    condition="description IS NULL OR LENGTH(description) < 20",
                    output_name="enriched_descriptions"
                ),
                
                # Step 7: Generate SEO titles
                WorkflowStep(
                    template_id="ENRICH_003",
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "brand_column": "brand_name",
                        "name_column": "product_name",
                        "category_column": "category",
                        "key_attribute_column": "color",
                        "seo_title_column": "seo_title"
                    },
                    depends_on=["enriched_descriptions"],
                    output_name="seo_optimized"
                ),
                
                # Step 8: Price competitiveness analysis
                WorkflowStep(
                    template_id="PRICE_146",
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "price_column": "price",
                        "category_column": "category",
                        "brand_column": "brand_name"
                    },
                    depends_on=["standardized_brands"],
                    output_name="price_analysis"
                ),
                
                # Step 9: Generate personalized content for different segments
                WorkflowStep(
                    template_id="ENRICH_041",  # Budget conscious persona
                    parameters={
                        "table_name": "{input_table}",
                        "sku_column": "sku",
                        "product_column": "product_name",
                        "persona_column": "'budget_conscious'"
                    },
                    depends_on=["price_analysis"],
                    output_name="budget_content"
                ),
                
                # Step 10: Forecast demand
                WorkflowStep(
                    template_id="TREND_221",
                    parameters={
                        "sales_table": "{sales_history}",
                        "date_column": "date",
                        "sku_column": "sku",
                        "category_column": "category",
                        "quantity_column": "quantity",
                        "revenue_column": "revenue"
                    },
                    depends_on=["seo_optimized"],
                    output_name="demand_forecast"
                )
            ],
            final_output="enhanced_catalog"
        )
        
        return workflow
    
    async def execute_workflow(self, workflow: TemplateWorkflow, 
                             parameters: Dict[str, str]) -> Dict[str, Any]:
        """
        Execute a workflow with intelligent dependency resolution and parallel execution
        """
        logger.info(f"Starting workflow: {workflow.name}")
        start_time = datetime.now()
        
        # Track execution state
        completed_steps = {}
        results = {}
        
        # Group steps by dependencies for parallel execution
        execution_groups = self._group_steps_by_dependencies(workflow.steps)
        
        for group_index, group in enumerate(execution_groups):
            logger.info(f"Executing group {group_index + 1} with {len(group)} steps")
            
            # Execute all steps in this group in parallel
            tasks = []
            for step in group:
                # Check if dependencies are met
                if step.depends_on:
                    for dep in step.depends_on:
                        if dep not in completed_steps:
                            raise ValueError(f"Dependency {dep} not met for {step.template_id}")
                
                # Prepare parameters with results from previous steps
                step_params = self._resolve_parameters(
                    step.parameters, parameters, results
                )
                
                # Create execution task
                task = self._execute_step(step, step_params)
                tasks.append((step, task))
            
            # Wait for all tasks in group to complete
            for step, task in tasks:
                result = await task
                completed_steps[step.output_name] = True
                results[step.output_name] = result
                
                logger.info(f"Completed step: {step.template_id} -> {step.output_name}")
        
        # Create final unified result
        final_result = self._create_unified_result(results, workflow)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Workflow completed in {execution_time:.2f} seconds")
        
        # Store in history for analysis
        self.workflow_history.append({
            'workflow': workflow.name,
            'execution_time': execution_time,
            'steps_executed': len(completed_steps),
            'timestamp': datetime.now()
        })
        
        return final_result
    
    async def _execute_step(self, step: WorkflowStep, parameters: Dict[str, str]) -> Any:
        """Execute a single workflow step"""
        template = self.template_library.get_template(step.template_id)
        if not template:
            raise ValueError(f"Template {step.template_id} not found")
        
        # Render the SQL
        sql = self.template_library.render_template(step.template_id, parameters)
        
        # Add condition if specified
        if step.condition:
            sql = f"SELECT * FROM ({sql}) WHERE {step.condition}"
        
        # Execute asynchronously
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.engine._run_query, sql
            )
            return result
        except Exception as e:
            logger.error(f"Error executing step {step.template_id}: {str(e)}")
            raise
    
    def _group_steps_by_dependencies(self, steps: List[WorkflowStep]) -> List[List[WorkflowStep]]:
        """Group steps that can be executed in parallel"""
        groups = []
        remaining_steps = steps.copy()
        completed = set()
        
        while remaining_steps:
            current_group = []
            
            for step in remaining_steps[:]:
                # Check if all dependencies are completed
                deps_met = True
                if step.depends_on:
                    for dep in step.depends_on:
                        if dep not in completed:
                            deps_met = False
                            break
                
                if deps_met:
                    current_group.append(step)
                    remaining_steps.remove(step)
            
            if not current_group:
                raise ValueError("Circular dependency detected in workflow")
            
            groups.append(current_group)
            
            # Mark current group as completed
            for step in current_group:
                if step.output_name:
                    completed.add(step.output_name)
        
        return groups
    
    def _resolve_parameters(self, template_params: Dict[str, str], 
                          workflow_params: Dict[str, str],
                          results: Dict[str, Any]) -> Dict[str, str]:
        """Resolve parameters with values from workflow parameters and previous results"""
        resolved = {}
        
        for key, value in template_params.items():
            if value.startswith('{') and value.endswith('}'):
                # This is a parameter reference
                param_name = value[1:-1]
                
                # Check workflow parameters first
                if param_name in workflow_params:
                    resolved[key] = workflow_params[param_name]
                # Then check results from previous steps
                elif param_name in results:
                    # Use the table name from the result
                    resolved[key] = f"({results[param_name].to_sql()})"
                else:
                    raise ValueError(f"Parameter {param_name} not found")
            else:
                # Direct value
                resolved[key] = value
        
        return resolved
    
    def _create_unified_result(self, results: Dict[str, Any], 
                             workflow: TemplateWorkflow) -> Dict[str, Any]:
        """Create a unified result combining all workflow steps"""
        return {
            'workflow_name': workflow.name,
            'workflow_description': workflow.description,
            'steps_completed': len(results),
            'results': results,
            'summary': self._generate_workflow_summary(results)
        }
    
    def _generate_workflow_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the workflow execution"""
        summary = {
            'total_products_processed': 0,
            'quality_improvements': {},
            'enrichments_made': {},
            'forecasts_generated': 0
        }
        
        # Analyze results
        for step_name, result in results.items():
            if 'quality' in step_name and hasattr(result, 'shape'):
                summary['quality_improvements'][step_name] = result.shape[0]
            elif 'enriched' in step_name and hasattr(result, 'shape'):
                summary['enrichments_made'][step_name] = result.shape[0]
            elif 'forecast' in step_name and hasattr(result, 'shape'):
                summary['forecasts_generated'] = result.shape[0]
        
        return summary
    
    def create_intelligent_pricing_workflow(self) -> TemplateWorkflow:
        """
        Create a workflow that intelligently adjusts pricing based on multiple factors
        """
        return TemplateWorkflow(
            name="Intelligent Pricing Optimization",
            description="Multi-factor pricing optimization using competitor and demand data",
            steps=[
                # Analyze competitor prices
                WorkflowStep(
                    template_id="COMP_206",
                    parameters={
                        "our_table": "{products}",
                        "competitor_table": "{competitor_prices}",
                        "sku_column": "sku",
                        "name_column": "product_name",
                        "price_column": "price",
                        "brand_column": "brand"
                    },
                    output_name="competitor_analysis"
                ),
                
                # Analyze price elasticity
                WorkflowStep(
                    template_id="PRICE_149",
                    parameters={
                        "table_name": "{sales_history}",
                        "sku_column": "sku",
                        "price_column": "price",
                        "cost_column": "cost",
                        "category_column": "category"
                    },
                    depends_on=["competitor_analysis"],
                    output_name="elasticity_analysis"
                ),
                
                # Generate optimal prices
                WorkflowStep(
                    template_id="PRICE_156",
                    parameters={
                        "table_name": "{products}",
                        "sku_column": "sku",
                        "price_column": "current_price",
                        "sales_column": "monthly_sales",
                        "margin_column": "gross_margin"
                    },
                    depends_on=["elasticity_analysis"],
                    output_name="optimized_prices"
                )
            ],
            final_output="pricing_recommendations"
        )
    
    def create_customer_intelligence_workflow(self) -> TemplateWorkflow:
        """
        Create a workflow that builds comprehensive customer intelligence
        """
        return TemplateWorkflow(
            name="360-Degree Customer Intelligence",
            description="Build complete customer profiles using product affinity and behavior",
            steps=[
                # Product affinity analysis
                WorkflowStep(
                    template_id="SEG_236",
                    parameters={
                        "order_table": "{orders}",
                        "order_id": "order_id",
                        "sku_column": "sku"
                    },
                    output_name="product_affinity"
                ),
                
                # Customer segmentation
                WorkflowStep(
                    template_id="SEG_237",
                    parameters={
                        "table_name": "{customers}",
                        "customer_column": "customer_id",
                        "feature_columns": "recency, frequency, monetary_value"
                    },
                    depends_on=["product_affinity"],
                    output_name="customer_segments"
                ),
                
                # Behavior prediction
                WorkflowStep(
                    template_id="TREND_231",
                    parameters={
                        "table_name": "{customer_behavior}",
                        "id_column": "customer_id",
                        "feature1_column": "days_since_last_purchase",
                        "feature2_column": "average_order_value",
                        "feature3_column": "product_categories_purchased"
                    },
                    depends_on=["customer_segments"],
                    output_name="churn_predictions"
                )
            ],
            final_output="customer_intelligence"
        )


# Example usage demonstrating the power of template orchestration
if __name__ == "__main__":
    # This would be used in the demo notebook
    engine = BigQueryAIEngine('project-id', 'dataset-id')
    orchestrator = TemplateOrchestrator(engine)
    
    # Create and execute a smart workflow
    workflow = orchestrator.create_smart_catalog_enhancement_workflow()
    
    # Parameters for the workflow
    params = {
        'input_table': 'project.dataset.messy_catalog',
        'category_mapping': 'project.dataset.category_map',
        'brand_mapping': 'project.dataset.brand_map',
        'sales_history': 'project.dataset.sales_data'
    }
    
    # Execute asynchronously
    import asyncio
    results = asyncio.run(orchestrator.execute_workflow(workflow, params))
    
    print(f"Workflow completed: {results['summary']}")