"""
Route planning service with A* pathfinding algorithm

Implements custom A* pathfinding with security status weighting,
avoid lists, and support for custom waypoints.
"""
import heapq
import math
from dataclasses import dataclass
from typing import Optional, List, Dict, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.universe import System, SystemJump

logger = logging.getLogger(__name__)


@dataclass
class RouteNode:
    """Node in the pathfinding graph"""
    system_id: int
    g_cost: float  # Actual cost from start
    h_cost: float  # Heuristic cost to goal
    parent: Optional['RouteNode'] = None
    
    @property
    def f_cost(self) -> float:
        """Total cost (g + h)"""
        return self.g_cost + self.h_cost
    
    def __lt__(self, other):
        """For heapq comparison"""
        return self.f_cost < other.f_cost


class RoutePlanner:
    """
    Route planner using A* pathfinding algorithm
    
    Features:
    - Security status weighting (prefer high-sec or avoid low-sec)
    - Custom avoid lists (systems/regions to exclude)
    - Waypoint support
    - Fastest route (shortest jumps)
    - Safest route (prefer high security)
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._system_cache: Dict[int, System] = {}
        self._jump_graph: Dict[int, List[int]] = {}
    
    def _get_system(self, system_id: int) -> Optional[System]:
        """Get system from cache or database"""
        if system_id in self._system_cache:
            return self._system_cache[system_id]
        
        system = self.db.query(System).filter(
            System.system_id == system_id
        ).first()
        
        if system:
            self._system_cache[system_id] = system
        
        return system
    
    def _get_connected_systems(self, system_id: int) -> List[int]:
        """Get list of connected system IDs"""
        if system_id in self._jump_graph:
            return self._jump_graph[system_id]
        
        # Query both directions (from and to)
        jumps = self.db.query(SystemJump).filter(
            (SystemJump.from_system_id == system_id) |
            (SystemJump.to_system_id == system_id)
        ).all()
        
        connected = set()
        for jump in jumps:
            if jump.from_system_id == system_id:
                connected.add(jump.to_system_id)
            else:
                connected.add(jump.from_system_id)
        
        connected_list = list(connected)
        self._jump_graph[system_id] = connected_list
        return connected_list
    
    def _heuristic_distance(self, system_id1: int, system_id2: int) -> float:
        """
        Calculate heuristic distance between two systems
        
        Uses Euclidean distance in 3D space if coordinates are available,
        otherwise falls back to simple hop count estimate.
        """
        system1 = self._get_system(system_id1)
        system2 = self._get_system(system_id2)
        
        if system1 and system2 and system1.x is not None and system2.x is not None:
            # Use 3D Euclidean distance
            dx = system1.x - system2.x
            dy = system1.y - system2.y
            dz = system1.z - system2.z
            return math.sqrt(dx*dx + dy*dy + dz*dz) / 9460730472580800  # Convert to approximate jumps (1 AU ≈ 9460730472580800 meters)
        
        # Fallback: estimate based on region/constellation
        if system1 and system2:
            if system1.region_id == system2.region_id:
                if system1.constellation_id == system2.constellation_id:
                    return 1.0  # Same constellation
                return 5.0  # Same region, different constellation
            return 20.0  # Different regions
        
        return 10.0  # Default estimate
    
    def calculate_route(
        self,
        start_system_id: int,
        end_system_id: int,
        avoid_systems: Optional[List[int]] = None,
        avoid_regions: Optional[List[int]] = None,
        prefer_safer: bool = True,
        security_penalty: float = 2.0,
        max_jumps: Optional[int] = None,
    ) -> Tuple[List[int], Dict[str, any]]:
        """
        Calculate route between two systems using A* pathfinding
        
        Args:
            start_system_id: Starting system ID
            end_system_id: Destination system ID
            avoid_systems: List of system IDs to avoid
            avoid_regions: List of region IDs to avoid
            prefer_safer: If True, prefer high-security systems
            security_penalty: Penalty multiplier for low-security systems
            max_jumps: Maximum number of jumps allowed (None for unlimited)
            
        Returns:
            Tuple of (route_list, metadata_dict)
            route_list: List of system IDs from start to end
            metadata_dict: Route metadata (total_jumps, estimated_time, etc.)
        """
        if avoid_systems is None:
            avoid_systems = []
        if avoid_regions is None:
            avoid_regions = []
        
        # Convert to sets for faster lookup
        avoid_systems_set = set(avoid_systems)
        avoid_regions_set = set(avoid_regions)
        
        # Verify start and end systems exist
        start_system = self._get_system(start_system_id)
        end_system = self._get_system(end_system_id)
        
        if not start_system:
            raise ValueError(f"Start system {start_system_id} not found")
        if not end_system:
            raise ValueError(f"End system {end_system_id} not found")
        
        # Check if start or end is in avoid list
        if start_system_id in avoid_systems_set:
            raise ValueError(f"Start system {start_system_id} is in avoid list")
        if end_system_id in avoid_systems_set:
            raise ValueError(f"End system {end_system_id} is in avoid list")
        
        if start_system.region_id in avoid_regions_set:
            raise ValueError(f"Start system region {start_system.region_id} is in avoid list")
        if end_system.region_id in avoid_regions_set:
            raise ValueError(f"End system region {end_system.region_id} is in avoid list")
        
        # A* algorithm
        open_set: List[Tuple[float, int, RouteNode]] = []  # (f_cost, tiebreaker, node)
        closed_set: Set[int] = set()
        node_map: Dict[int, RouteNode] = {}  # Track best node for each system
        
        # Initialize start node
        h_cost = self._heuristic_distance(start_system_id, end_system_id)
        start_node = RouteNode(
            system_id=start_system_id,
            g_cost=0.0,
            h_cost=h_cost,
            parent=None
        )
        node_map[start_system_id] = start_node
        heapq.heappush(open_set, (start_node.f_cost, 0, start_node))
        
        tiebreaker = 1
        
        while open_set:
            # Get node with lowest f_cost
            current_f_cost, _, current = heapq.heappop(open_set)
            
            # Skip if we've already found a better path to this node
            if current.system_id in closed_set:
                continue
            
            # Check if we've reached the destination
            if current.system_id == end_system_id:
                # Reconstruct path
                route = []
                node = current
                while node:
                    route.append(node.system_id)
                    node = node.parent
                route.reverse()
                
                # Calculate metadata
                total_jumps = len(route) - 1
                estimated_time = total_jumps * 3  # 3 seconds per jump (approximate)
                
                # Calculate route statistics
                route_systems = [self._get_system(sid) for sid in route]
                avg_security = sum(
                    (s.security_status if s else 0.0) for s in route_systems
                ) / len(route_systems) if route_systems else 0.0
                
                metadata = {
                    "total_jumps": total_jumps,
                    "estimated_time_seconds": estimated_time,
                    "average_security": avg_security,
                    "route_length": len(route),
                }
                
                return route, metadata
            
            # Mark as closed
            closed_set.add(current.system_id)
            
            # Check max jumps limit
            if max_jumps and current.g_cost >= max_jumps:
                continue
            
            # Explore neighbors
            neighbors = self._get_connected_systems(current.system_id)
            
            for neighbor_id in neighbors:
                # Skip if in closed set
                if neighbor_id in closed_set:
                    continue
                
                # Skip if in avoid list
                if neighbor_id in avoid_systems_set:
                    continue
                
                # Check if neighbor's region is in avoid list
                neighbor_system = self._get_system(neighbor_id)
                if neighbor_system and neighbor_system.region_id in avoid_regions_set:
                    continue
                
                # Calculate cost to reach neighbor
                jump_cost = 1.0  # Base cost per jump
                
                # Apply security penalty if prefer_safer
                if prefer_safer and neighbor_system:
                    security = neighbor_system.security_status
                    if security < 0.5:  # Low-sec or null-sec
                        jump_cost += (0.5 - max(security, -1.0)) * security_penalty
                
                g_cost = current.g_cost + jump_cost
                h_cost = self._heuristic_distance(neighbor_id, end_system_id)
                
                # Check if we've seen this neighbor before
                if neighbor_id in node_map:
                    existing_node = node_map[neighbor_id]
                    # If we found a better path, update it
                    if g_cost < existing_node.g_cost:
                        existing_node.g_cost = g_cost
                        existing_node.parent = current
                        heapq.heappush(open_set, (existing_node.f_cost, tiebreaker, existing_node))
                        tiebreaker += 1
                else:
                    # New node
                    neighbor_node = RouteNode(
                        system_id=neighbor_id,
                        g_cost=g_cost,
                        h_cost=h_cost,
                        parent=current
                    )
                    node_map[neighbor_id] = neighbor_node
                    heapq.heappush(open_set, (neighbor_node.f_cost, tiebreaker, neighbor_node))
                    tiebreaker += 1
        
        # No route found
        return [], {
            "total_jumps": 0,
            "estimated_time_seconds": 0,
            "average_security": 0.0,
            "route_length": 0,
            "error": "No route found"
        }
    
    def calculate_route_with_waypoints(
        self,
        waypoints: List[int],
        avoid_systems: Optional[List[int]] = None,
        avoid_regions: Optional[List[int]] = None,
        prefer_safer: bool = True,
        security_penalty: float = 2.0,
    ) -> Tuple[List[int], Dict[str, any]]:
        """
        Calculate route through multiple waypoints
        
        Args:
            waypoints: List of system IDs to visit in order
            avoid_systems: List of system IDs to avoid
            avoid_regions: List of region IDs to avoid
            prefer_safer: If True, prefer high-security systems
            security_penalty: Penalty multiplier for low-security systems
            
        Returns:
            Tuple of (full_route_list, metadata_dict)
        """
        if len(waypoints) < 2:
            raise ValueError("At least 2 waypoints required")
        
        full_route = [waypoints[0]]
        total_metadata = {
            "total_jumps": 0,
            "estimated_time_seconds": 0,
            "average_security": 0.0,
            "route_length": 0,
            "segments": []
        }
        
        for i in range(len(waypoints) - 1):
            start = waypoints[i]
            end = waypoints[i + 1]
            
            segment_route, segment_metadata = self.calculate_route(
                start_system_id=start,
                end_system_id=end,
                avoid_systems=avoid_systems,
                avoid_regions=avoid_regions,
                prefer_safer=prefer_safer,
                security_penalty=security_penalty,
            )
            
            if not segment_route:
                return [], {
                    "error": f"No route found between waypoint {i} and {i+1}",
                    **total_metadata
                }
            
            # Append segment (skip first system as it's already in full_route)
            full_route.extend(segment_route[1:])
            
            total_metadata["total_jumps"] += segment_metadata.get("total_jumps", 0)
            total_metadata["estimated_time_seconds"] += segment_metadata.get("estimated_time_seconds", 0)
            total_metadata["segments"].append({
                "from": start,
                "to": end,
                "jumps": segment_metadata.get("total_jumps", 0),
                "route": segment_route
            })
        
        total_metadata["route_length"] = len(full_route)
        
        # Calculate average security for full route
        route_systems = [self._get_system(sid) for sid in full_route]
        total_security = sum(
            (s.security_status if s else 0.0) for s in route_systems
        )
        total_metadata["average_security"] = total_security / len(route_systems) if route_systems else 0.0
        
        return full_route, total_metadata

