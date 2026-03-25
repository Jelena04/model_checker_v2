import maya.cmds as cmds
import maya.api.OpenMaya as om
import statistics
from model_checker_v2 import base_check


class PolygonDensity(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "Geometry"

        self.check_cb = None

        self.arnold_shader_data = "vertex"
        self.turntable_render = True

    def run(self, mesh, *args) -> dict:
        status = "DEFAULT"
        details = "DEFAULT"
        try:
            dag_path = self.get_mesh_dag_path(mesh)

            iterator = om.MItMeshPolygon(dag_path)
            fn_mesh = om.MFnMesh(dag_path)

            # compute world-space face area
            areas = []
            for i in range(iterator.count()):
                area = iterator.getArea(space=om.MSpace.kWorld)
                areas.append(area)
                iterator.next()

            # color faces based on density (yellow-orange-red)
            yellow = om.MColor((1.0, 1.0, 0.0))
            orange = om.MColor((1.0, 0.5, 0.0))
            red = om.MColor((1.0, 0.0, 0.0))

            def lerp_color(c1, c2, t):
                """Linearly interpolate between two MColors."""
                return om.MColor((
                    c1.r + (c2.r - c1.r) * t,
                    c1.g + (c2.g - c1.g) * t,
                    c1.b + (c2.b - c1.b) * t
                ))

            iterator.reset()
            colors = []
            face_ids = []
            vertex_ids = []

            self.create_color_set(mesh, fn_mesh)

            # calculate normalized area accoarding to median and assign color based on this value
            median_area = statistics.median(areas)
            max_area = max(areas)
            min_area = min(areas)
            for face_index, area in enumerate(areas):
                if area <= median_area:
                    t = (area - min_area) / (median_area - min_area) if median_area != min_area else 0.0
                    color = lerp_color(red, orange, t)
                else:
                    t = (area - median_area) / (max_area - median_area) if max_area != median_area else 0.0
                    color = lerp_color(orange, yellow, t)

                vertex_indices = iterator.getVertices()
                for vtx_id in vertex_indices:
                    colors.append(color)
                    face_ids.append(face_index)
                    vertex_ids.append(vtx_id)
                iterator.next()

            # assign color to faces
            fn_mesh.setFaceVertexColors(colors, face_ids, vertex_ids)
            fn_mesh.updateSurface()
            # make sure vertex colors are displayed in viewport
            cmds.setAttr(f"{mesh}.displayColors", 1)

            status = "Completed"
            details = "red = high density - orange = average density - yellow = low density"
            self.update_result_message("-", self.BLUE)
            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except Exception as e:
            cmds.warning(f"Polygon Density check failed to run - {e}")
            status = "Error"
            details = "/"
            self.update_result_message("-", self.BLUE)
            self.update_status_message("Error", self.ORANGE)

        return_dict = {
            "name": "Polygon Density check",
            "status": status,
            "details": details
        }
        return return_dict

    def build_ui(self, *args):
        super().build_ui()

        self.check_cb = cmds.checkBox("Polygon Density", p=self.check_content)