import maya.cmds as cmds
from model_checker_v2 import base_check

class Polycount(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "Geometry"

        self.check_cb = None

        self.arnold_shader_data = None
        self.turntable_render = False

        self.min_field = None
        self.max_field = None

    def run(self, mesh, *args):
        """
        Checks polycount against set thresholds in UI.
        :param mesh: Mesh to check.
        :return: Result of check, amount of faces.
        """
        try:
            cmds.select(mesh)
            nr_faces = cmds.polyEvaluate(f=True)
            min_faces = cmds.intField(self.min_field, q=True, v=True)
            max_faces = cmds.intField(self.max_field, q=True, v=True)
            if nr_faces < min_faces:
                status = "FAIL"
                details = "Too little faces"
                self.update_result_message(status, self.RED)
            elif nr_faces > max_faces:
                status = "FAIL"
                details = "Too many faces"
                self.update_result_message(status, self.RED)
            else:
                status = "PASS"
                details = "Number of faces adequate"
                self.update_result_message(status, self.GREEN)
            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except:
            self.update_status_message("Error", self.ORANGE)

        return_dict = {
            "name": "Polycount check",
            "status": status,
            "details": details
        }

        return return_dict

    def build_ui(self, *args):
        super().build_ui()

        polycount_layout = cmds.rowLayout(nc=5, p=self.check_content, cw5=(140, 30, 40, 30, 40))
        self.check_cb = cmds.checkBox("Polycount", p=polycount_layout)

        cmds.text(label="Min:", p=polycount_layout)
        self.min_field = cmds.intField(v=0, p=polycount_layout, w=40)

        cmds.text(label="Max: ", p=polycount_layout)
        self.max_field = cmds.intField(p=polycount_layout, v=2000, w=40)