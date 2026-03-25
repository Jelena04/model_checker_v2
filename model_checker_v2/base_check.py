import maya.cmds as cmds
import maya.api.OpenMaya as om
import re
import os
_content_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "content")

class BaseCheck:

    def __init__(self, layout):
        self.parent_layout = layout

        check_name = self.__class__.__name__
        check_name = re.findall(r'[A-Z][^A-Z]*', check_name)
        self.check_name =" ".join(check_name)

        self.arnold_shader_data = None

        self.ui = None
        self.check_content = None
        self.category = "Misc"

        self.RED = (0.812, 0.412, 0.388)
        self.BLUE = (0.441, 0.642, 0.771)
        self.GREEN = (0.431, 0.741, 0.506)
        self.ORANGE = (1.0, 0.549, 0.259)
        self.BLUE_COMPLETED = (0.227, 0.525, 1.0)

    def run(self, mesh_name, original_mesh):
        """
        Executes the check on the given mesh. Intended to be overridden by subclasses — the
        base implementation does nothing.
        param: mesh_name (str): The name of the mesh to run the check on.
        param: original_mesh (str): The name of the original reference mesh, used for comparison where relevant.
        """
        pass

    def build_ui(self, *args):
        """
        Builds the UI row for this check within the parent layout. Creates a row containing a content area, a status
        box, a result box, and a remove button. The status and result boxes are initialised with a blue (pending) color.
        """

        self.ui = cmds.rowLayout(adj=True, p=self.parent_layout, nc=4, cw4=[300, 40, 20, 30])
        self.check_content = cmds.rowLayout(adj=True, p=self.ui)

        frame_status = cmds.frameLayout(labelVisible=False, marginWidth=2, marginHeight=2, bgc=(0.47, 0.87, 0.47), p=self.ui, w=70)
        self.status_box = cmds.text(label="Status", bgc=self.BLUE, p=frame_status)

        frame = cmds.frameLayout(labelVisible=False, marginWidth=2, marginHeight=2, bgc=(0.47, 0.87, 0.47), p=self.ui, w=50)
        self.result_box = cmds.text(label="Result", bgc=self.BLUE, p=frame)


        remove_btn = cmds.symbolButton(image=os.path.join(_content_dir, "remove_plugin_img.png"),
                                       p=self.ui,
                                       w=20, h=20,
                                       c=self._on_remove_pressed)

    def _on_remove_pressed(self, *args):
        """
        Triggered when the user clicks the remove (❌) button.
        Delegates removal logic to the manager (BaseTool).
        """
        if hasattr(self, "manager") and self.manager:
            self.manager.remove_plugin(self)
        else:
            cmds.warning("No manager found for this check — cannot remove.")

    def create_color_set(self, mesh_name, mesh_fn):
        """
        Creates a uniquely named color set on the given mesh, replacing any existing one with
        the same name. Sets the new color set as the active one on the mesh.
        param: mesh_name (str): The name of the mesh, used to construct the color set name.
        param: mesh_fn (om.MFnMesh): The MFnMesh function set instance for the mesh to operate on.
        """
        color_set_name = f"{self.__class__.__name__}_{mesh_name}"

        existing_sets = mesh_fn.getColorSetNames()

        if color_set_name in existing_sets:
            mesh_fn.deleteColorSet(color_set_name)
        mesh_fn.createColorSet(color_set_name, False)
        mesh_fn.setCurrentColorSetName(color_set_name)

    def get_mesh_dag_path(self, mesh_name):
        """
        Retrieves the DAG path of the given mesh by name using the Maya API selection list.
        """
        sel = om.MSelectionList()
        sel.add(mesh_name)
        dagPath = sel.getDagPath(0)
        return dagPath

    def update_result_message(self, new_text, new_color):
        """
        Updates the result message with the given text and color.
        param: new_text (str): The new text of the message.
        param: new_color (str): The new color of the message.
        """
        cmds.text(self.result_box, e=True, label=new_text, bgc=new_color)

    def update_status_message(self, new_text, new_color):
        """
        Updates the status message with the given text and color.
        param: new_text (str): The new text of the message.
        param: new_color (str): The new color of the message.
        """
        cmds.text(self.status_box, e=True, label=new_text, bgc=new_color)

    def strings_to_indices(self, string_list):
        """
        Converts a list of Maya vertex component strings into a flat list of integer indices.
        Handles both single vertex notation (e.g. "vtx[5]") and range notation (e.g. "vtx[3:7]"),
        expanding ranges into individual indices.
        """
        indices_list = []
        for vtx_name in string_list:
            # Match both single and range vertex notations
            match = re.search(r"\[(\d+)(?::(\d+))?\]", vtx_name)
            if match:
                start = int(match.group(1))
                end = match.group(2)
                if end:
                    end = int(end)
                    indices_list.extend(range(start, end + 1))
                else:
                    indices_list.append(start)
        return indices_list

    def cleanup(self):
        pass