# -*- coding: utf-8 -*-
"""Stage 5: Layout Solving."""

import json
from ..base_stage import BaseStage
from ..stage_data import StageData


class LayoutStage(BaseStage):
    """Solve object layout with collision detection."""

    name = "layout"

    def __init__(self, layout_solver):
        self.solver = layout_solver

    async def execute(self, data: StageData) -> StageData:
        # Create a mock session object for LayoutSolver
        class MockSession:
            def __init__(self, session_dir, objects):
                self.session_dir = session_dir
                self._objects = objects

            def load_objects(self):
                return {"objects": self._objects}

            def get_assets_dir(self):
                return self.session_dir / "assets"

        session = MockSession(data.session_dir, data.objects)
        constraints_path = str(data.session_dir / "constraints.json")

        solution = self.solver.solve_dfs(session, constraints_path)
        data.layout = solution

        # Save to file
        layout_path = data.session_dir / "layout_solution.json"
        with open(layout_path, 'w', encoding='utf-8') as f:
            json.dump(solution, f, indent=2, ensure_ascii=False)

        return data
