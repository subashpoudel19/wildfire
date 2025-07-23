"""
WILDCAT project initialization module
Handles project setup and configuration
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ProjectInitializer:
    """
    Initialize and configure WILDCAT projects
    """
    
    def __init__(self):
        """Initialize project initializer"""
        try:
            import wildcat
            self.wildcat = wildcat
        except ImportError:
            logger.error("WILDCAT not installed")
            raise
    
    def create_project(self, project_name: str, project_dir: str) -> bool:
        """
        Create a new WILDCAT project
        
        Args:
            project_name: Name of the project
            project_dir: Directory for the project
            
        Returns:
            Success status
        """
        try:
            # Create project directory
            os.makedirs(project_dir, exist_ok=True)
            
            # Initialize WILDCAT project
            self.wildcat.initialize(project_dir)
            
            logger.info(f"✅ Created project: {project_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create project: {e}")
            return False
    
    def configure_project(self, project_dir: str, config_dict: Dict) -> bool:
        """
        Configure a WILDCAT project
        
        Args:
            project_dir: Project directory
            config_dict: Configuration dictionary
            
        Returns:
            Success status
        """
        try:
            config_path = Path(project_dir) / "config.py"
            
            if not config_path.exists():
                logger.error("Config file not found")
                return False
            
            # Read current config
            with open(config_path, 'r') as f:
                config_lines = f.readlines()
            
            # Build custom configuration
            custom_config = "\n# Custom configuration\n"
            for key, value in config_dict.items():
                if isinstance(value, str):
                    custom_config += f'{key} = r"{value}"\n'
                else:
                    custom_config += f'{key} = {value}\n'
            
            # Find insertion point
            inputs_index = next(
                (i for i, line in enumerate(config_lines) if "# Inputs" in line),
                len(config_lines)
            )
            
            # Insert custom config
            config_lines.insert(inputs_index + 1, custom_config)
            
            # Write updated config
            with open(config_path, 'w') as f:
                f.writelines(config_lines)
            
            logger.info("✅ Project configured")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to configure project: {e}")
            return False
    
    def get_optimization_settings(self, fire_size_mb: float) -> Dict:
        """
        Get optimization settings based on fire size
        
        Args:
            fire_size_mb: Fire data size in MB
            
        Returns:
            Optimization settings dictionary
        """
        if fire_size_mb < 10:
            return {
                'chunk_size': 1024,
                'max_memory_gb': 2,
                'multiprocessing': False
            }
        elif fire_size_mb < 50:
            return {
                'chunk_size': 512,
                'max_memory_gb': 4,
                'multiprocessing': True,
                'n_workers': 2
            }
        elif fire_size_mb < 100:
            return {
                'chunk_size': 256,
                'max_memory_gb': 6,
                'multiprocessing': True,
                'n_workers': 4
            }
        else:
            return {
                'chunk_size': 128,
                'max_memory_gb': 8,
                'multiprocessing': True,
                'n_workers': 6,
                'use_dask': True
            }
    
    def validate_project(self, project_dir: str) -> Tuple[bool, List[str]]:
        """
        Validate a WILDCAT project setup
        
        Args:
            project_dir: Project directory
            
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        project_path = Path(project_dir)
        
        # Check directory exists
        if not project_path.exists():
            issues.append("Project directory does not exist")
            return False, issues
        
        # Check required files
        required_files = ['config.py']
        for file in required_files:
            if not (project_path / file).exists():
                issues.append(f"Missing required file: {file}")
        
        # Check required directories
        required_dirs = ['preprocessed', 'outputs', 'exports']
        for dir_name in required_dirs:
            dir_path = project_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(exist_ok=True)
                logger.info(f"Created missing directory: {dir_name}")
        
        is_valid = len(issues) == 0
        return is_valid, issues