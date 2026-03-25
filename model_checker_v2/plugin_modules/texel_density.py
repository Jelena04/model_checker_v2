import maya.cmds as cmds
import maya.api.OpenMaya as om
import math
from model_checker_v2 import base_check


class TexelDensity(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "UVs"

        self.check_cb = None

        self.arnold_shader_data = "vertex"
        self.turntable_render = True


    def run(self, mesh, *args) -> dict:
        try:
            texture_resolution = 1024
            dag_path = self.get_mesh_dag_path(mesh)
            fn_mesh = om.MFnMesh(dag_path)

            self.create_color_set(mesh, fn_mesh)

            # Iterate over faces once and compute texel densities
            texel_densities = []
            face_vertex_map = []  # store vertex indices per face

            it_poly = om.MItMeshPolygon(dag_path)
            while not it_poly.isDone():
                vtx_ids = it_poly.getVertices()
                face_vertex_map.append(vtx_ids)

                world_area = it_poly.getArea(space=om.MSpace.kWorld)
                uv_area = it_poly.getUVArea()

                if world_area > 0 and uv_area > 0:
                    density = math.sqrt((uv_area * (texture_resolution ** 2)) / world_area)
                else:
                    density = 0.0

                texel_densities.append(density)
                it_poly.next()

            # Normalize densities
            min_dens = min(texel_densities)
            max_dens = max(texel_densities)
            normalized = [(d - min_dens) / (max_dens - min_dens + 1e-6) for d in texel_densities]
            avg_density = sum(normalized) / len(normalized)

            # Prepare face-vertex color arrays
            colors = []
            face_ids = []
            vertex_ids = []

            for f_idx, norm_d in enumerate(normalized):
                # Red → high density, Blue → low density
                if norm_d >= avg_density:
                    red = 1.0
                    blue = 1.0 - ((norm_d - avg_density) / (1.0 - avg_density + 1e-6))
                else:
                    blue = 1.0
                    red = norm_d / (avg_density + 1e-6)

                color = om.MColor((red, 0.0, blue, 1.0))

                for v_id in face_vertex_map[f_idx]:
                    colors.append(color)
                    face_ids.append(f_idx)
                    vertex_ids.append(v_id)

            # Apply colors
            fn_mesh.setFaceVertexColors(colors, face_ids, vertex_ids)
            fn_mesh.updateSurface()

            cmds.setAttr(f"{mesh}.displayColors", 1)

            status = "Completed"
            details = "red = high density - purple = average density - blue = low density"
            self.update_result_message("-", self.BLUE)
            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except Exception as e:
            cmds.warning("Texel Density check failed to run")
            status = "Failed to check"
            details = "/"
            self.update_result_message("-", self.BLUE)
            self.update_status_message("Error", self.ORANGE)

        return_dict = {
            "name": "Texel Density check",
            "status": status,
            "details": details
        }
        return return_dict

    def build_ui(self, *args):
        super().build_ui()

        self.check_cb = cmds.checkBox("Texel density",  p=self.check_content)