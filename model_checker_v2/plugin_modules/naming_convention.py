import maya.cmds as cmds
from model_checker_v2 import base_check

class NamingConvention(base_check.BaseCheck):

    def __init__(self, layout):
        super().__init__(layout)
        self.category = "Misc"

        self.check_cb = None

        self.arnold_shader_data = None
        self.turntable_render = False

        self.prefix_field = None
        self.suffix_field = None

    def run(self, mesh, *args) -> dict:
        """
        Handles the logic to check if the selected mesh follows the set naming convention.
        :return: Boolean stating if prefix is correct, boolean stating if suffix is correct.
        """
        try:
            prefix = cmds.textField(self.prefix_field, q=True, text=True)
            suffix = cmds.textField(self.suffix_field, q=True, text=True)

            if prefix != "":
                if mesh.startswith(prefix):
                    status_prefix = "PASSED"
                    details_prefix = "Correct prefix"
                else:
                    status_prefix = "FAILED"
                    details_prefix = "Incorrect prefix"
            else:
                status_prefix = "PASSED"
                details_prefix = "Correct prefix"

            if suffix != "":
                if mesh.endswith(suffix):
                    status_suffix = "PASSED"
                    details_suffix = "correct suffix"
                else:
                    status_suffix = "FAILED"
                    details_suffix = "correct suffix"
            else:
                status_suffix = "PASSED"
                details_suffix = "correct suffix"

            status = "DEFAULT"
            if status_prefix == "FAILED" or status_suffix == "FAILED":
                status = "FAIL"
                self.update_result_message(status, self.RED)
            else:
                status = "PASS"
                self.update_result_message(status, self.GREEN)


            details = f"{details_prefix}, {details_suffix}"
            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except:
            self.update_status_message("Error", self.ORANGE)

        return_dict = {
            "name": "Naming Convention check",
            "status": status,
            "details": details
        }

        return return_dict

    def build_ui(self, *args):
        super().build_ui()

        naming_convention_layout = cmds.rowLayout(nc=5, p=self.check_content, cw5=(150, 30, 50, 30, 50))
        self.check_cb = cmds.checkBox("Naming Convention", p=naming_convention_layout)

        cmds.text(label="Prefix:", p=naming_convention_layout)
        self.prefix_field = cmds.textField(text="", p=naming_convention_layout, w=40)

        cmds.text(label="Suffix:", p=naming_convention_layout)
        self.suffix_field = cmds.textField(p=naming_convention_layout, text="", w=40)