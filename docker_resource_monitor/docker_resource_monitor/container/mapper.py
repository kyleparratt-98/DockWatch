"""
Container mapping module for Docker Resource Monitor.

This module provides the ContainerMapper class which maintains a mapping
between process IDs (PIDs) and Docker container information by parsing
cgroup files and mount information.
"""

import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, Optional, Set, Any, List

logger = logging.getLogger(__name__)


class ContainerMapper:
    """
    Maps PIDs to Docker container information by parsing cgroup files.
    
    This class maintains a cache of PID-to-container mappings and periodically
    refreshes it to handle PID recycling and container lifecycle changes.
    """
    
    def __init__(self, cache_ttl: int = 5):
        """
        Initialize the ContainerMapper.
        
        Args:
            cache_ttl: Cache time-to-live in seconds. The cache will be
                       refreshed if it's older than this value.
        """
        self.pid_to_container_cache: Dict[int, Dict[str, Any]] = {}
        self.last_refresh_time: float = 0.0
        self.cache_ttl: int = cache_ttl
        
        # Pre-compile regex patterns for performance
        self._docker_id_patterns = [
            re.compile(r'/([0-9a-f]{64})(?:/|$)', re.IGNORECASE),  # Full ID in path
            re.compile(r'/([0-9a-f]{12,64})(?:/|$)', re.IGNORECASE),  # Short or full ID
            re.compile(r'/(?:docker|containerd)[_-]([0-9a-f]{64})\.scope', re.IGNORECASE),  # Scope format
        ]
        self._cgroup_line_pattern = re.compile(r'^\d+:([^:]+):(.+)$')
        self._container_runtime_patterns = ['docker', 'containerd', 'crio', 'podman']
        
    def get_container_for_pid(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Get container information for a given PID.
        
        Args:
            pid: Process ID to look up.
            
        Returns:
            Dictionary with container information if found, None otherwise.
            The dictionary contains:
                - 'container_id': Docker container ID (64-character hex)
                - 'container_name': Container name (if available)
                - 'cgroup_path': Full cgroup path
                - 'pid': The original PID
        """
        # Check if cache needs refresh
        current_time = time.time()
        if (current_time - self.last_refresh_time) > self.cache_ttl:
            self.refresh_cache()
        
        # Return cached value if available
        if pid in self.pid_to_container_cache:
            return self.pid_to_container_cache[pid]
        
        # Try to parse cgroup for this specific PID
        try:
            container_info = self._parse_cgroup(pid)
        except (PermissionError, OSError) as e:
            logger.debug(f"Failed to parse cgroup for PID {pid}: {e}")
            return None
            
        if container_info:
            self.pid_to_container_cache[pid] = container_info
        
        return container_info
    
    def refresh_cache(self) -> None:
        """
        Refresh the entire PID-to-container cache.
        
        This method scans running processes and updates the cache with
        current PID-to-container mappings. It handles PID recycling by
        clearing stale entries.
        """
        # Only refresh if cache is stale
        current_time = time.time()
        if current_time - self.last_refresh_time < self.cache_ttl:
            return
            
        logger.debug("Refreshing container mapping cache")
        
        # Get all PIDs from /proc
        try:
            pids = self._get_all_pids()
        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to list PIDs: {e}")
            return
        
        new_cache: Dict[int, Dict[str, Any]] = {}
        processed_pids = 0
        batch_size = 100  # Process in batches to avoid memory spikes
        
        # Process PIDs in batches
        pid_batches = [list(pids)[i:i + batch_size] for i in range(0, len(pids), batch_size)]
        
        for batch in pid_batches:
            for pid in batch:
                processed_pids += 1
                
                # Skip if we already processed this PID in current refresh
                if pid in new_cache:
                    continue
                
                # Check if cached entry is still valid
                cached_info = self.pid_to_container_cache.get(pid)
                if cached_info:
                    try:
                        # Verify PID still exists and belongs to same container
                        if self._verify_pid_container(pid, cached_info.get('container_id')):
                            new_cache[pid] = cached_info
                            continue
                    except (PermissionError, OSError):
                        # PID might have been recycled or permission denied
                        pass
                
                # Parse cgroup for this PID
                try:
                    container_info = self._parse_cgroup(pid)
                    if container_info:
                        new_cache[pid] = container_info
                except (PermissionError, OSError) as e:
                    logger.debug(f"Failed to parse cgroup for PID {pid}: {e}")
                    continue
        
        # Update cache and refresh time
        self.pid_to_container_cache = new_cache
        self.last_refresh_time = current_time
        
        logger.debug(f"Cache refreshed with {len(self.pid_to_container_cache)} "
                    f"entries out of {processed_pids} PIDs processed")
    
    def _verify_pid_container(self, pid: int, expected_container_id: Optional[str]) -> bool:
        """
        Verify that a PID still belongs to the expected container.
        
        Args:
            pid: Process ID to verify.
            expected_container_id: Expected container ID.
            
        Returns:
            True if PID still belongs to the same container, False otherwise.
        """
        if not expected_container_id:
            return False
            
        try:
            current_info = self._parse_cgroup(pid)
            return current_info and current_info.get('container_id') == expected_container_id
        except (PermissionError, OSError):
            return False
    
    def _get_all_pids(self) -> Set[int]:
        """
        Get all PIDs from /proc directory.
        
        Returns:
            Set of all PIDs currently present in /proc.
            
        Raises:
            PermissionError: If unable to read /proc directory.
            OSError: If /proc directory doesn't exist or other OS error occurs.
        """
        pids = set()
        proc_path = Path('/proc')
        
        if not proc_path.exists():
            raise OSError("/proc directory does not exist")
        
        try:
            # Use listdir for better performance than iterdir
            for entry_name in os.listdir(proc_path):
                entry_path = proc_path / entry_name
                if entry_path.is_dir():
                    try:
                        pid = int(entry_name)
                        pids.add(pid)
                    except ValueError:
                        # Skip non-integer directory names like 'self', 'thread-self'
                        continue
        except PermissionError as e:
            raise PermissionError(f"Permission denied accessing /proc: {e}")
        
        return pids
    
    def _parse_cgroup(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Parse cgroup information for a specific PID.
        
        Args:
            pid: Process ID to parse.
            
        Returns:
            Dictionary with container information if found, None otherwise.
            
        Raises:
            PermissionError: If unable to read cgroup files for the PID.
            OSError: If cgroup files don't exist or other OS error occurs.
        """
        cgroup_path = Path(f'/proc/{pid}/cgroup')
        
        if not cgroup_path.exists():
            logger.debug(f"Cgroup file not found for PID {pid}: {cgroup_path}")
            return None
        
        try:
            # Read cgroup file
            with open(cgroup_path, 'r') as f:
                cgroup_content = f.read()
        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to read cgroup file for PID {pid}: {e}")
            raise
        
        container_id = None
        cgroup_line = None
        
        # Parse cgroup file lines
        for line in cgroup_content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            match = self._cgroup_line_pattern.match(line)
            if not match:
                continue
            
            subsystems, path = match.groups()
            cgroup_line = line
            
            # Check if this is a container cgroup path
            if any(runtime in path.lower() for runtime in self._container_runtime_patterns):
                container_id = self._extract_container_id_from_path(path)
                if container_id:
                    break
            
            # Check for cgroup v2 unified hierarchy (subsystems empty)
            if not subsystems and path:
                # For cgroup v2, check for container patterns in the path
                container_id = self._extract_container_id_from_path(path)
                if container_id:
                    break
        
        if not container_id:
            logger.debug(f"No container found for PID {pid} in cgroup: {cgroup_line}")
            return None
        
        # Get container name (simplified - just use short ID)
        container_name = container_id[:12] if len(container_id) >= 12 else container_id
        
        return {
            'container_id': container_id,
            'container_name': container_name,
            'cgroup_path': cgroup_line,
            'pid': pid
        }
    
    def _extract_container_id_from_path(self, path: str) -> Optional[str]:
        """
        Extract container ID from cgroup path using multiple patterns.
        
        Args:
            path: Cgroup path string.
            
        Returns:
            Container ID if found, None otherwise.
        """
        for pattern in self._docker_id_patterns:
            match = pattern.search(path)
            if match:
                container_id = match.group(1)
                # Validate it looks like a container ID (hex characters)
                if all(c in '0123456789abcdefABCDEF' for c in container_id):
                    # Ensure full length if we have a short ID
                    if len(container_id) == 64:
                        return container_id
                    elif len(container_id) >= 12:
                        # For short IDs, we need to find the full ID
                        # This is a simplified approach - in production,
                        # we might need to map short IDs to full IDs
                        return container_id
        
        return None
    
    def get_all_containers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information for all currently mapped containers.
        
        Returns:
            Dictionary mapping container IDs to container information.
        """
        containers: Dict[str, Dict[str, Any]] = {}
        
        for pid, info in self.pid_to_container_cache.items():
            container_id = info.get('container_id')
            if not container_id:
                continue
                
            if container_id not in containers:
                containers[container_id] = {
                    'container_id': container_id,
                    'container_name': info.get('container_name'),
                    'pids': set(),
                    'cgroup_path': info.get('cgroup_path')
                }
            containers[container_id]['pids'].add(pid)
        
        # Convert sets to lists for JSON serialization
        for container_info in containers.values():
            container_info['pids'] = list(container_info['pids'])
        
        return containers
    
    def clear_cache(self) -> None:
        """Clear the PID-to-container cache."""
        self.pid_to_container_cache.clear()
        self.last_refresh_time = 0.0
        logger.debug("Container mapping cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current cache.
        
        Returns:
            Dictionary with cache statistics.
        """
        containers = self.get_all_containers()
        current_time = time.time()
        
        return {
            'cache_size': len(self.pid_to_container_cache),
            'unique_containers': len(containers),
            'cache_age_seconds': current_time - self.last_refresh_time if self.last_refresh_time > 0 else 0,
            'cache_ttl': self.cache_ttl,
            'is_stale': current_time - self.last_refresh_time > self.cache_ttl
        }
    
    def _detect_cgroup_version(self) -> int:
        """
        Detect the cgroup version in use.
        
        Returns:
            1 for cgroup v1, 2 for cgroup v2.
        """
        # Check for cgroup v2 unified hierarchy
        cgroup2_path = Path('/sys/fs/cgroup/cgroup.controllers')
        if cgroup2_path.exists():
            return 2
        return 1
