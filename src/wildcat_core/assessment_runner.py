"""
WILDCAT assessment runner module
Handles running debris flow assessments
"""

import os
import time
import psutil
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class AssessmentRunner:
    """
    Run WILDCAT debris flow assessments
    """
    
    def __init__(self):
        """Initialize assessment runner"""
        try:
            import wildcat
            self.wildcat = wildcat
        except ImportError:
            logger.error("WILDCAT not installed")
            raise
    
    def preprocess_project(self, project_dir: str) -> Dict:
        """
        Run preprocessing for a project
        
        Args:
            project_dir: Project directory
            
        Returns:
            Preprocessing results
        """
        results = {
            'success': False,
            'time_seconds': 0,
            'outputs': []
        }
        
        try:
            start_time = time.time()
            
            # Run preprocessing
            self.wildcat.preprocess(project_dir)
            
            results['time_seconds'] = time.time() - start_time
            
            # Check outputs
            preprocessed_dir = Path(project_dir) / "preprocessed"
            if preprocessed_dir.exists():
                results['outputs'] = [f.name for f in preprocessed_dir.iterdir()]
                results['success'] = len(results['outputs']) > 0
            
            logger.info(f"✅ Preprocessing complete in {results['time_seconds']:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ Preprocessing failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def run_assessment(self, project_dir: str) -> Dict:
        """
        Run debris flow assessment
        
        Args:
            project_dir: Project directory
            
        Returns:
            Assessment results
        """
        results = {
            'success': False,
            'time_seconds': 0,
            'memory_used_gb': 0,
            'outputs': []
        }
        
        try:
            # Check memory before
            mem_before = psutil.virtual_memory()
            start_time = time.time()
            
            # Run assessment
            self.wildcat.assess(project_dir)
            
            results['time_seconds'] = time.time() - start_time
            
            # Calculate memory usage
            mem_after = psutil.virtual_memory()
            results['memory_used_gb'] = (mem_before.available - mem_after.available) / (1024**3)
            
            # Check outputs
            outputs_dir = Path(project_dir) / "outputs"
            if outputs_dir.exists():
                results['outputs'] = [f.name for f in outputs_dir.iterdir()]
                results['success'] = len(results['outputs']) > 0
            
            logger.info(f"✅ Assessment complete in {results['time_seconds']:.1f}s")
            logger.info(f"   Memory used: {results['memory_used_gb']:.1f} GB")
            
        except MemoryError as e:
            logger.error(f"❌ Memory error during assessment: {e}")
            results['error'] = 'MemoryError'
            results['error_message'] = str(e)
            
        except Exception as e:
            logger.error(f"❌ Assessment failed: {e}")
            results['error'] = type(e).__name__
            results['error_message'] = str(e)
        
        return results
    
    def export_results(self, project_dir: str, formats: list = None) -> Dict:
        """
        Export assessment results
        
        Args:
            project_dir: Project directory
            formats: List of export formats
            
        Returns:
            Export results
        """
        if formats is None:
            formats = ['Shapefile', 'GeoJSON']
        
        results = {
            'success': False,
            'formats': {},
            'files': []
        }
        
        try:
            for format_type in formats:
                try:
                    self.wildcat.export(project_dir, format=format_type)
                    results['formats'][format_type] = True
                    logger.info(f"✅ Exported {format_type}")
                except Exception as e:
                    results['formats'][format_type] = False
                    logger.error(f"❌ Failed to export {format_type}: {e}")
            
            # Check exported files
            export_dir = Path(project_dir) / "exports"
            if export_dir.exists():
                results['files'] = [f.name for f in export_dir.iterdir()]
                results['success'] = len(results['files']) > 0
            
        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            results['error'] = str(e)
        
        return results
    
    def run_complete_workflow(self, project_dir: str, 
                              skip_preprocessing: bool = False) -> Dict:
        """
        Run complete WILDCAT workflow
        
        Args:
            project_dir: Project directory
            skip_preprocessing: Skip preprocessing if already done
            
        Returns:
            Complete workflow results
        """
        results = {
            'project_dir': project_dir,
            'preprocessing': {},
            'assessment': {},
            'export': {},
            'total_time': 0,
            'success': False
        }
        
        start_time = time.time()
        
        # Preprocessing
        if not skip_preprocessing:
            results['preprocessing'] = self.preprocess_project(project_dir)
            if not results['preprocessing']['success']:
                results['total_time'] = time.time() - start_time
                return results
        
        # Assessment
        results['assessment'] = self.run_assessment(project_dir)
        if not results['assessment']['success']:
            results['total_time'] = time.time() - start_time
            return results
        
        # Export
        results['export'] = self.export_results(project_dir)
        
        results['total_time'] = time.time() - start_time
        results['success'] = results['export']['success']
        
        return results