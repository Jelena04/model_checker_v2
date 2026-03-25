import maya.cmds as cmds
import maya.api.OpenMaya as om
from model_checker_v2 import base_check

class NonManifoldEdges(base_check.BaseCheck):
    def __init__(self, layout):
        super().__init__(layout)
        self.category = "Geometry"

        self.check_cb = None

        self.arnold_shader_data = "pass"
        self.turntable_render = True

        self.edge_indicators = []
        self.edges_group = None

    def run(self, mesh, *args) -> dict:
        try:
            status = "DEFAULT"
            details = "DEFAULT"

            fn_mesh = om.MFnMesh(self.get_mesh_dag_path(mesh))

            non_mani_edges = cmds.polyInfo(mesh, nme=True)

            if not non_mani_edges:
                status = "PASS"
                details = "This mesh has no non-manifold edge"
                self.update_result_message(status, self.GREEN)
            elif non_mani_edges:
                edge_indices = self.strings_to_indices(non_mani_edges)

                if cmds.objExists("nmEdgeShader"):
                    shader = "nmEdgeShader"
                else:
                    shader = cmds.shadingNode("aiStandardSurface", asShader=True, name="nmEdgeShader")
                    cmds.setAttr(shader + ".baseColor", 1, 0, 0, type="double3")

                self.edge_indicators = []
                for edge_id in edge_indices:
                    verts = fn_mesh.getEdgeVertices(edge_id)
                    points = [om.MPoint(fn_mesh.getPoint(v, om.MSpace.kWorld)) for v in verts]

                    # Create a temporary line between the two vertices
                    curve = cmds.curve(p=[(points[0].x, points[0].y, points[0].z),(points[1].x, points[1].y, points[1].z)],
                                       d=1, n=f"edgeIndicator_{edge_id}")
                    self.edge_indicators.append(curve)
                    cmds.setAttr(curve + ".overrideEnabled", 1)
                    cmds.setAttr(curve + ".overrideRGBColors", 1)
                    cmds.setAttr(curve + ".aiRenderCurve", 1)
                    cmds.setAttr(curve + ".aiCurveWidth", 1)
                    cmds.setAttr(curve + ".aiSampleRate", 10)
                    cmds.setAttr(curve + ".aiMode", 1)
                self.edges_group = cmds.group(self.edge_indicators, n="NonManifoldEdgesMarkers")
                cmds.parent(self.edges_group, mesh)

                for curve in self.edge_indicators:
                    shapes = cmds.listRelatives(curve, shapes=True, fullPath=True)
                    if shapes:
                        shape = shapes[0]
                        cmds.connectAttr(shader+".outColor", shape+".aiCurveShader", f=True)

                nr_edges = len(non_mani_edges)
                status = "FAIL"
                details = f"This mesh has {nr_edges} non-manifold edges"
                self.update_result_message(status, self.RED)

            self.update_status_message("Completed", self.BLUE_COMPLETED)
        except:
            self.update_status_message("Error", self.ORANGE)

        return_dict = {
            "name": "Non Manifold Edges check",
            "status": status,
            "details": details
        }
        return return_dict

    def build_ui(self, *args):
        super().build_ui()

        self.check_cb = cmds.checkBox("Non-manifold edges", p=self.check_content)

    def cleanup(self):
        cmds.delete(self.edge_indicators)
        cmds.delete(self.edges_group)

    def switch_to_turntable_view(self):
        # loop over all curves
        # in attribute editor > display > drawing overrides > turn on enable overrides > set color to RGC > enter red color
        if not self.edge_indicators:
            return

        for curve in self.edge_indicators:
            shapes = cmds.listRelatives(curve, shapes=True, fullPath=True)
            if not shapes:
                continue
            shape = shapes[0]

            # Enable drawing overrides
            cmds.setAttr(shape + ".overrideEnabled", 1)

            # Set color to red (using Maya's color index 13 for red in viewport)
            # If you want a custom RGB color, use overrideRGBColors instead
            cmds.setAttr(shape + ".overrideRGBColors", 1)
            cmds.setAttr(shape + ".overrideColorRGB", 1, 0, 0)  # RGB = Red

            # Optional: Make curves renderable in playblast
            # In your existing code you use aiRenderCurve for Arnold, but playblast uses viewport
            cmds.setAttr(shape + ".template", 0)  # make sure it’s not templated
            cmds.setAttr(shape + ".visibility", 1)

            cmds.select(clear=True)
