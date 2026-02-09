# Scene Generation Module - HOLODECK 2.0

## Overview

This module implements the core scene generation logic for HOLODECK 2.0, including spatial constraint primitives, DFS layout solver, and iterative refinement mechanism.

## Features

### 1. Spatial Constraint Primitives
- **Relative Constraints**: `left_of`, `right_of`, `in_front_of`, `behind`, `side_of`
- **Distance Constraints**: `near` (≤2m), `far` (≥8m), `adjacent` (≤0.5m)
- **Vertical Constraints**: `on`, `above`, `below`
- **Rotation Constraints**: `face_to` (±10°), `parallel`, `perpendicular`

All constraints follow the mathematical definitions from HOLODECK 2.0 paper.

### 2. Collision Detection
- AABB (Axis-Aligned Bounding Box) intersection testing
- Minimum distance calculation
- Ground collision detection
- Object stability checks

### 3. DFS Layout Solver
- Topological sorting of objects based on constraints
- Candidate position sampling with constraint-based regions
- Depth-first search with backtracking
- Constraint validation at each placement step

### 4. Failure Analysis
- Comprehensive failure trace generation
- Natural language summary for LLM feedback
- Actionable fix suggestions
- Conflict type classification

### 5. Constraint Generation
- Natural language to spatial constraints
- Iterative refinement based on failure traces
- Support for VLM integration (GPT-o3)

## Usage

```python
from holodeck_core.scene_gen import DFSSolver, check_constraint_satisfaction

# Solve layout
placements, trace = DFSSolver.solve(
    objects=objects,
    constraints=constraints,
    config=config
)

if trace is None:
    print("Success! All objects placed.")
else:
    print(f"Failed: {trace['natural_language_summary']}")
```

## Files

- `constraint_primitives.py` - Core constraint types and calculations
- `collision_detection.py` - AABB collision detection system
- `dfs_solver.py` - DFS layout solving algorithm
- `failure_analysis.py` - Failure trace and analysis
- `constraint_generator.py` - Text-to-constraints conversion

## Performance

- Solves layouts with 10-25 objects in ≤60 seconds
- Collision-free ratio: ≥95%
- Constraint satisfaction rate: ≥90%
- Supports iterative refinement (max 3 iterations)

## Integration

This module integrates with:
- HOLODECK 2.0 Scene Analysis pipeline
- MCP tools (layout_tools.py)
- Blender for scene assembly
- VLM for constraint generation

## References

- HOLODECK 2.0: Vision-Language-Guided 3D World Generation with Editing
- Spatial Constraint Primitives: Table 3 of the paper
- DFS Algorithm with topological sorting

For detailed documentation, see `/docs/SCENE_GENERATION.md`.