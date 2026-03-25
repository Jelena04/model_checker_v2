import maya.cmds as cmds
import maya.api.OpenMaya as om
from model_checker_v2 import base_check

class OverlappingUvs(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "UVs"

        self.check_cb = None

        self.arnold_shader_data = "vertex"
        self.turntable_render = True

    def run(self, mesh, *args) -> dict:
        try:
            status = "DEFAULT"
            details = "DEFAULT"

            faces = cmds.ls(f"{mesh}.f[*]", flatten=True)
            overlapping_uvs = cmds.polyUVOverlap(faces, oc=True) or []

            # convert overlapping uv strings to face indices
            overlapping_indices = self.strings_to_indices(overlapping_uvs)

            # create mesh function set
            dag_path = self.get_mesh_dag_path(mesh)
            fn_mesh = om.MFnMesh(dag_path)

            # get individual face and vertex ids
            self.create_color_set(mesh, fn_mesh)

            # prepare face-vertex color arrays
            colors = []
            face_ids = []
            vertex_ids = []

            num_faces = fn_mesh.numPolygons
            red = om.MColor((1,0,0))
            white = om.MColor((0.5,0.5,0.5))

            for f_id in range(num_faces):
                vtx_ids = fn_mesh.getPolygonVertices(f_id)
                face_color = red if f_id in overlapping_indices else white

                for v_id in vtx_ids:
                    colors.append(face_color)
                    face_ids.append(f_id)
                    vertex_ids.append(v_id)

            # assign color to faces
            fn_mesh.setFaceVertexColors(colors, face_ids, vertex_ids)
            fn_mesh.updateSurface()
            # make sure vertex colors are displayed in viewport
            cmds.setAttr(f"{mesh}.displayColors", 1)

            if not overlapping_uvs:
                status = "PASS"
                details = "This mesh has no overlapping UVs"
                self.update_result_message(status, self.GREEN)
            elif overlapping_uvs:
                nr_overlapping_uvs = len(overlapping_uvs)
                status = "FAIL"
                details = f"This mesh has {nr_overlapping_uvs} overlapping UVs"
                self.update_result_message(status, self.RED)
            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except:
            self.update_status_message("Error", self.ORANGE)

        return_dict = {
            "name": "Overlapping UVs check",
            "status": status,
            "details": details
        }
        return return_dict



    def build_ui(self, *args):
        super().build_ui()

        self.check_cb = cmds.checkBox("Overlapping UV shells", p=self.check_content)