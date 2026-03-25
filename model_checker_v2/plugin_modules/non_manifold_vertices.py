import maya.cmds as cmds
import maya.api.OpenMaya as om
from model_checker_v2 import base_check

class NonManifoldVertices(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "Geometry"

        self.check_cb = None

        self.arnold_shader_data = "vertex"
        self.turntable_render = True

    def run(self, mesh, *args) -> dict:
        try:
            status = "DEFAULT"
            details = "DEFAULT"

            fn_mesh = om.MFnMesh(self.get_mesh_dag_path(mesh))

            non_mani_verts = cmds.polyInfo(mesh, nmv=True)

            if not non_mani_verts:
                status = "PASS"
                details = "This mesh has no non-manifold vertices"
                self.update_result_message(status, self.GREEN)
            elif non_mani_verts:
                vert_indices = self.strings_to_indices(non_mani_verts)

                self.create_color_set(mesh, fn_mesh)

                num_verts = fn_mesh.numVertices
                white_color = om.MColor((0.5, 0.5, 0.5, 1.0))
                red_color = om.MColor((1.0, 0.0, 0.0, 1.0))

                colors = om.MColorArray()
                for i in range(num_verts):
                    colors.append(white_color)

                for vtx_id in vert_indices:
                    colors[vtx_id] = red_color

                vertex_indices = om.MIntArray(range(num_verts))
                fn_mesh.setVertexColors(colors, vertex_indices)

                cmds.setAttr(f"{mesh}.displayColors", 1)

                nr_verts = len(non_mani_verts)
                status = "FAIL"
                details = f"This mesh has {nr_verts} non-manifold vertices"
                self.update_result_message(status, self.RED)

            cmds.refresh(force=True)
            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except:
            self.update_status_message("Error", self.ORGANE)

        return_dict = {
            "name": "Non Manifold Vertices check",
            "status": status,
            "details": details
        }
        return return_dict

    def build_ui(self, *args):
        super().build_ui()

        self.check_cb = cmds.checkBox("Non-manifold vertices", p=self.check_content)