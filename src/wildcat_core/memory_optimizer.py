"""
Memory optimization utilities for WILDCAT processing
"""

import gc
import psutil
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class MemoryOptimizer:
    """
    Memory optimization utilities for large fire processing
    """
    
    @staticmethod
    def get_memory_info() -> Dict:
        """Get current memory information"""
        mem = psutil.virtual_memory()
        return {
            'total_gb': mem.total / (1024**3),
            'available_gb': mem.available / (1024**3),
            'percent_used': mem.percent,
            'used_gb': mem.used / (1024**3)
        }
    
    @staticmethod
    def check_memory_availability(required_gb: float = 2.0) -> bool:
        """
        Check if sufficient memory is available
        
        Args:
            required_gb: Required memory in GB
            
        Returns:
            True if sufficient memory available
        """
        mem_info = MemoryOptimizer.get_memory_info()
        available = mem_info['available_gb'] >= required_gb
        
        if not available:
            logger.warning(f"⚠️  Low memory: {mem_info['available_gb']:.1f} GB available, "
                          f"{required_gb:.1f} GB required")
        
        return available
    
    @staticmethod
    def optimize_memory(aggressive: bool = False):
        """
        Optimize memory usage
        
        Args:
            aggressive: Use aggressive optimization
        """
        logger.info("🧹 Optimizing memory...")
        
        # Basic garbage collection
        gc.collect()
        
        if aggressive:
            # Force full collection
            gc.collect(2)
            
            # Clear caches if available
            try:
                import numpy as np
                # Clear numpy cache
                np.fft.fftpack._fft_cache.clear()
            except:
                pass
            
            try:
                import rasterio
                # Clear rasterio env
                rasterio.env.delenv()
            except:
                pass
        
        mem_after = MemoryOptimizer.get_memory_info()
        logger.info(f"   Available memory: {mem_after['available_gb']:.1f} GB")
    
    @staticmethod
    def get_optimization_config(fire_size_mb: float, 
                                available_memory_gb: float) -> Dict:
        """
        Get optimization configuration based on fire size and available memory
        
        Args:
            fire_size_mb: Fire data size in MB
            available_memory_gb: Available memory in GB
            
        Returns:
            Optimization configuration
        """
        config = {
            'chunk_size': 1024,
            'use_multiprocessing': False,
            'n_workers': 1,
            'optimize_rasters': False,
            'clear_cache_frequency': 10
        }
        
        # Adjust based on fire size
        if fire_size_mb > 100:
            config['chunk_size'] = 256
            config['optimize_rasters'] = True
            config['clear_cache_frequency'] = 5
        elif fire_size_mb > 50:
            config['chunk_size'] = 512
            config['optimize_rasters'] = True
        
        # Adjust based on available memory
        if available_memory_gb > 8:
            config['use_multiprocessing'] = True
            config['n_workers'] = min(4, psutil.cpu_count() - 1)
        elif available_memory_gb > 4:
            config['use_multiprocessing'] = True
            config['n_workers'] = 2
        
        return config
    
    @staticmethod
    def monitor_memory_usage(func):
        """
        Decorator to monitor memory usage of a function
        
        Args:
            func: Function to monitor
            
        Returns:
            Wrapped function
        """
        def wrapper(*args, **kwargs):
            # Memory before
            mem_before = MemoryOptimizer.get_memory_info()
            
            try:
                # Run function
                result = func(*args, **kwargs)
                
                # Memory after
                mem_after = MemoryOptimizer.get_memory_info()
                
                # Calculate usage
                used_gb = mem_before['available_gb'] - mem_after['available_gb']
                
                logger.info(f"💾 Memory used by {func.__name__}: {used_gb:.2f} GB")
                
                return result
                
            except MemoryError as e:
                logger.error(f"❌ Memory error in {func.__name__}: {e}")
                # Try to recover
                MemoryOptimizer.optimize_memory(aggressive=True)
                raise
                
        return wrapper