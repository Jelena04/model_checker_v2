import json
import maya.cmds as cmds
import maya.mel as mel

from PIL import Image, ImageDraw, ImageFont

import re
import sys
import os

import importlib
import importlib.util

from model_checker_v2 import ui_tool
importlib.reload(ui_tool)

from platformdirs import user_config_dir
import datetime

class ModelChecker:
    def __init__(self):
        self.ui = ui_tool.ModelCheckerUI(self)
        self.checks = {}
        self.load_checks_on_startup()

    def load_checks_on_startup(self):
        """
        Checks if the user has already got checks installed, if so, loads them in.
        """
        config_path = os.path.join(user_config_dir("MayaModelChecker"), "plugin_manifest.json")

        if not os.path.exists(config_path):
            return

        try:
            with open(config_path, "r") as read_file:
                plugin_dict = json.load(read_file)
        except json.JSONDecodeError:
            cmds.warning("Plugin register is corrupted or empty.")
            return

        for key,value in plugin_dict.items():
            if os.path.exists(value):
                self.load_plugin(value)
            else:
                cmds.warning(f"Plugin not found at: {value}")

    def create_new_directory(self, new_directory_name: str) -> str:
        """
        Runs the file setup function (creates an ModelChecker output folder if needed). Sets up a new folder if necessary.
        :param new_directory_name: Name of new directory that must be created.
        :return: Returns the newly created full directory
        """
        output_path = self.save_file_setup()
        if output_path == "":
            cmds.warning("Please select an output path.")
            return ""
        new_directory = os.path.join(output_path, new_directory_name)

        if not os.path.exists(new_directory):
            os.makedirs(new_directory, exist_ok=True)
        return new_directory

    def load_plugin(self, filepath):
        """
        Loads in a user-chosen check module, and initializes a check object that later gets used to run the checks.
        :param filepath: Filepath to the check module (.py file)
        :return:
        """
        config_dir = user_config_dir("MayaModelChecker")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "plugin_manifest.json")

        if os.path.exists(config_path):
            with open(config_path, "r") as read_file:
                try:
                    plugin_dict = json.load(read_file)
                except json.JSONDecodeError:
                    plugin_dict = {}
        else:
            plugin_dict = {}

        # get check's class name
        plugin_name = str(os.path.basename(filepath).replace(".py", ""))
        class_name = plugin_name.replace("_", " ").title().replace(" ", "")

        if class_name not in plugin_dict:
            plugin_dict[class_name] = filepath
            with open(config_path, "w") as f:
                json.dump(plugin_dict, f, indent=4)

        # Importing plugin with importlib
        spec = importlib.util.spec_from_file_location(plugin_name, filepath) # gives import mechanism details on how to load the file
        module = importlib.util.module_from_spec(spec)
        sys.modules[plugin_name] = module
        spec.loader.exec_module(module)

        # Getting instance of check class in module
        try:
            check_class = getattr(module, class_name)
            if class_name not in self.checks.keys():
                # Create instance
                check_instance = check_class(None)
                check_instance.manager = self

                category = getattr(check_instance, "category", "Misc")
                parent_layout = self.ui.category_tabs.get(category, self.ui.category_tabs["Misc"])
                check_instance.parent_layout = parent_layout

                # Load module's UI
                check_instance.build_ui()

                self.checks[class_name] = check_instance

                cmds.warning(f"{class_name} successfully added to {category} tab.")
            else:
                cmds.warning(f"{class_name} already included.")
                check_instance = self.checks[class_name]
                return
        except AttributeError as error:
            print(error)
            cmds.warning("Loading of check module failed.")

    def remove_plugin(self, instance):
        """
          Fully unloads a check plugin by removing it from the checks dictionary,
          the persistent plugin manifest, and the UI.

          :param instance: The check plugin instance to remove.
          :return: None
          """
        print(f"Instance: {instance}") # instance in memory

        check_name = instance.__class__.__name__
        print(f"Check class: {check_name}") # ex. LaminaFaces

        # remove from checks dictionary
        if check_name in self.checks:
            del self.checks[check_name]
        # remove from checks registry
        config_path = os.path.join(user_config_dir("MayaModelChecker"), "plugin_manifest.json")
        try:
            with open(config_path, "r") as read_file:
                data = json.load(read_file)
        except FileNotFoundError:
            cmds.warning("Plugin register is corrupted or empty.")
            return

        if check_name in data:
            del data[check_name]
            with open(config_path, "w") as f:
                json.dump(data, f, indent=4)
            print(f"Removed {check_name} from registry.")
        else:
            print(f"{check_name} not found in registry.")

        # remove from ui
        if instance.ui and cmds.layout(instance.ui, exists=True):
            cmds.deleteUI(instance.ui)
            print(f"Removed UI for {check_name}")

    @staticmethod
    def handle_mesh_path_input(path: str) -> None:
        """
        Loads in mesh if the selected file is a .fbx.
        :param path: File path of to-load mesh.
        :return: None
        """
        if path and path.endswith('.fbx') and os.path.exists(path):
            cmds.file(path, i=True)

    def run_checks_prep(self):
        """
           Resolves which mesh to check based on the UI selection mode, then
           duplicates it and hides the original in preparation for running checks.

           The mesh is either taken from the name typed in the text field (if
           'Specify target mesh' is checked), or from the current scene selection
           (if 'Use current selection as target mesh' is checked).

           :return: Tuple of (original_mesh, duplicated_mesh), or None if no valid
                    mesh could be resolved.
           """
        mesh_to_check = None
        if cmds.checkBox(self.ui.specify_mesh_cb, q=True, v=True):
            mesh_to_check = cmds.textField(self.ui.mesh_name_tf, q=True, tx=True)
            if mesh_to_check not in cmds.ls():
                cmds.warning(f"{mesh_to_check} not found. Please check the mesh name.")
                return None
        elif cmds.checkBox(self.ui.auto_select_cb, q=True, v=True):
            selected = cmds.ls(sl=True)
            if not selected:
                cmds.warning("Please select a mesh to run checks on.")
                return None
            mesh_to_check = selected
            if not mesh_to_check:
                return None

        duplicated_mesh = cmds.duplicate(mesh_to_check, n=f"{mesh_to_check}_duplicate")
        cmds.hide(mesh_to_check)
        return mesh_to_check, duplicated_mesh

    def run_all_checks(self, *args):
        """
        Runs all loaded checks.
        :param args:
        :return:
        """
        try:
            original_mesh, duplicated_mesh = self.run_checks_prep()

            if duplicated_mesh:
                results = []

                image_render_enabled = cmds.checkBox(self.ui.cb_image_render, q=True, v=True)
                turntable_render_enabled = cmds.checkBox(self.ui.cb_turntable_render, q=True, v=True)
                animation_length = 120
                turntable_camera = None
                image_camera = None
                turntable_path = None

                if image_render_enabled:
                    image_camera = self.image_render_setup(duplicated_mesh[0])
                if turntable_render_enabled:
                    turntable_camera = self.turntable_render_setup(duplicated_mesh[0], animation_length)

                for check_name, plugin in self.checks.items():
                    result = plugin.run(duplicated_mesh[0])
                    results.append(result)
                    if result["status"] != "PASS":
                        if image_render_enabled:
                            if plugin.arnold_shader_data:
                                self.make_image_render(original_mesh, duplicated_mesh[0], check_name, plugin.arnold_shader_data, result, image_camera)
                                plugin.cleanup()
                        if turntable_render_enabled:
                            if plugin.turntable_render:
                                turntable_path = self.make_turntable_render(original_mesh, duplicated_mesh[0], check_name, animation_length, turntable_camera, result)
                    plugin.cleanup()

                if image_render_enabled:
                    self.image_render_cleanup(image_camera)
                if turntable_render_enabled:
                    self.turntable_render_cleanup(turntable_camera, turntable_path)

                self.post_checks_process(duplicated_mesh, original_mesh, results)
        except Exception as e:
            cmds.warning(f"Something went wrong - {e}")
            return

    def run_selected_checks(self, *args):
        """
        Runs all selected checks.
        :param args:
        :return:
        """
        try:
            original_mesh, duplicated_mesh = self.run_checks_prep()

            if duplicated_mesh:
                results = []

                image_render_enabled = cmds.checkBox(self.ui.cb_image_render, q=True, v=True)
                turntable_render_enabled = cmds.checkBox(self.ui.cb_turntable_render, q=True, v=True)
                animation_length = 120
                turntable_camera = None
                image_camera = None
                turntable_path = None

                if image_render_enabled:
                    image_camera = self.image_render_setup(duplicated_mesh[0])
                if turntable_render_enabled:
                    turntable_camera = self.turntable_render_setup(duplicated_mesh[0], animation_length)

                for check_name, plugin in self.checks.items():
                    if cmds.checkBox(plugin.check_cb, q=True, v=True):
                        result = plugin.run(duplicated_mesh[0])
                        results.append(result)
                        if result["status"] != "PASS":
                            if image_render_enabled:
                                if plugin.arnold_shader_data:
                                    self.make_image_render(original_mesh, duplicated_mesh[0], check_name, plugin.arnold_shader_data, result, image_camera)
                            if turntable_render_enabled:
                                if plugin.turntable_render:
                                    if hasattr(plugin, "switch_to_turntable_view"):
                                        plugin. switch_to_turntable_view()
                                    turntable_path = self.make_turntable_render(original_mesh, duplicated_mesh[0], check_name, animation_length, turntable_camera, result)
                    plugin.cleanup()

                if image_render_enabled:
                    self.image_render_cleanup(image_camera)
                if turntable_render_enabled:
                    self.turntable_render_cleanup(turntable_camera, turntable_path)

                self.post_checks_process(duplicated_mesh, original_mesh, results)
        except Exception as e:
            cmds.warning(f"Something went wrong - {e}")
            return

    def post_checks_process(self, checked_mesh, original_mesh, results, *args):
        """
        Runs a post-checks process. The duplicated mesh gets deleted, the original one gets shown
        again, the output directory gets opened, and the reports get written.
        """
        cmds.delete(checked_mesh)

        cmds.showHidden(original_mesh)

        if (cmds.checkBox(self.ui.cb_output_file_txt, q=True, v=True) or
                cmds.checkBox(self.ui.cb_output_file_json, q=True, v=True) or
                cmds.checkBox(self.ui.cb_image_render, q=True, v=True) or
                cmds.checkBox(self.ui.cb_turntable_render, q=True, v=True)):
            output_path = self.save_file_setup()
            os.startfile(output_path)

        if cmds.checkBox(self.ui.cb_output_file_txt, q=True, v=True):
            self.generate_txt_report(original_mesh[0], results)
        if cmds.checkBox(self.ui.cb_output_file_json, q=True, v=True):
            self.generate_json_report(original_mesh[0], results)

    def save_file_setup(self) -> str:
        """
        Creates a ModelChecker_Output directory in the directory the user chose to save the output files.
        :return: Folder path where output files must be saved.
        """
        # get output path chosen by user
        output_path = cmds.textFieldButtonGrp(self.ui.output_path_field, q=True, tx=True)

        # create new directory to save data files in
        output_folder_path = os.path.join(output_path, "ModelChecker_Output")
        if not os.path.exists(output_folder_path):
            os.mkdir(output_folder_path)
        return output_folder_path

    def generate_txt_report(self, tested_mesh, results):
        """
        Generates a .txt report based on the results of the checks.
        :param tested_mesh: Mesh that was tested
        :param results: Dictionary of results of the checks
        """
        output_path = self.save_file_setup()
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.datetime.now().strftime("%H-%M-%S")
        file_name = f"{tested_mesh}_checks_report_{current_date}_{current_time}.txt"
        text_report_path = os.path.join(output_path, file_name)

        with open(text_report_path, "w") as write_file:
            write_file.write(f"Mesh checked: {tested_mesh}\n")
            write_file.write("========================================\n")
            write_file.write(f"Checked on {current_date} at {current_time.replace('-', ':')}\n")
            write_file.write(f"---------------------------------------\n")

            for result in results:
                write_file.write(f"{result['name']}\n")
                write_file.write(f"Status: {result['status']}\n")
                write_file.write(f"Details: {result['details']}\n")
                write_file.write("\n")

    def generate_json_report(self, tested_mesh, results):
        """
        Generates a .json report based on the results of the checks.
        :param tested_mesh: Mesh that was tested
        :param results: Dictionary of results of the checks
        """
        output_path = self.save_file_setup()
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.datetime.now().strftime("%H-%M-%S")
        file_name = f"{tested_mesh}_checks_report_{current_date}_{current_time}.json"
        json_report_path = os.path.join(output_path, file_name)

        report_data = {
            "mesh_checked": tested_mesh,
            "date": current_date,
            "time": current_time.replace("-", ":"),
            "results": results
        }

        with open(json_report_path, "w") as write_file:
            json.dump(report_data, write_file, indent=4)

    def image_render_setup(self, checked_mesh) -> None:
        """
        Checks if Maya to Arnold plugin is installed. Adds a SkyDomeLight if one is not present. Sets up render settings for Arnold renderer.
        :return: Rendercam that was created
        """
        if not cmds.pluginInfo("mtoa", query=True, loaded=True):
            cmds.loadPlugin("mtoa")

        # create skydomelight if it doesn't exist already
        sky_domes = cmds.ls(type="aiSkyDomeLight")
        if not sky_domes:
            mel.eval("cmdSkydomeLight;")

        if not cmds.objExists("defaultArnoldDriver"):
            cmds.createNode("aiAOVDriver", name="defaultArnoldDriver")

        cmds.setAttr("defaultArnoldDriver.ai_translator", "png", type="string")

        cmds.setAttr("defaultResolution.width", 1280)
        cmds.setAttr("defaultResolution.height", 720)

        render_cam = cmds.camera(name="RenderCam")[0]

        cmds.viewFit(render_cam, checked_mesh, f=0.75)

        return render_cam

    def make_image_render(self, original_mesh_name, checked_mesh, check_name, shader_type, text_result, camera):
        """
           Sets up the shader for if vertex colors were applied. Sets up the save path and render settings. Makes the
           render and adds text on top of it of what's being shown.

           Args:
               original_mesh_name (list): The name(s) of the original mesh, used to build the output image filename.
               checked_mesh (str): The name of the mesh being checked, used when building the vertex color shader.
               check_name (str): The name of the check being performed (e.g. "UVOverlap"), used in the shader name,
                                 image filename, and as the label rendered onto the image.
               shader_type (str): The type of shader to apply. If "vertex", a vertex color shader will be built
                                  before rendering.
               text_result (dict): A dictionary containing the check result to be overlaid on the image.
                                   Expected keys:
                                       - "status" (str): The result status (e.g. "Passed", "Failed").
                                       - "details" (str): A description of the result details.
               camera (str): The name of the camera to render from, passed to arnoldRender.

           Returns:
               str: The camera name that was used for the render.
           """
        if shader_type == "vertex":
            self.build_vert_color_shader(f"{check_name}_{checked_mesh}", checked_mesh, f"{check_name}Shader")

        cmds.refresh(force=True)

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.datetime.now().strftime("%H-%M-%S")

        save_path = self.create_new_directory("tests_images")
        cmds.workspace(os.path.abspath(save_path), openWorkspace=True)
        image_name = os.path.join(save_path,f"{original_mesh_name[0]}_{check_name}_{current_date}_{current_time}")
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", image_name, type="string")

        cmds.refresh(force=True)

        cmds.arnoldRender(cam=camera)

        words = re.findall('[A-Z][a-z]*', check_name)
        new_check_name = ' '.join(words)
        text_on_img = (f"{new_check_name}\n"
                       f"Result: {text_result['status'].lower()}\n"
                       f"Details: {text_result['details']}")
        self.add_text_to_image(f"{image_name}_1.png" ,text_on_img, 20)

        return camera

    def image_render_cleanup(self, camera):
        """
        Camera and skydome get deleted.
        """
        cmds.delete(camera)

        # delete skydome
        sky_domes = cmds.ls(type="aiSkyDomeLight")
        for dome in sky_domes:
            parent = cmds.listRelatives(dome, parent=True)
            if parent:
                cmds.delete(parent)

    def turntable_render_setup(self, mesh, anim_length):
        """
        Resolution and playblast settings get set. A camera gets created. The playback Sets the playback range
        and sets up the 360 degree rotation animation.
        param: mesh (str): The name of the mesh being checked, used when building the vertex color shader.
        param: anim_length (int): The length of the animation.
        """
        cmds.setAttr("defaultResolution.width", 1280)
        cmds.setAttr("defaultResolution.height", 720)
        cmds.optionVar(sv=("playblastFormat", "avi"))
        cmds.optionVar(iv=("playblastDisplaySize", 1))
        cmds.optionVar(iv=("playblastQuality", 100))
        cmds.optionVar(fv=("playblastScale", 1))

        # set up camera
        render_camera = cmds.camera()
        cam_shape = render_camera[1]
        cam_transform = render_camera[0]
        cmds.viewFit(render_camera, mesh, f=0.75)

        # set playback range
        cmds.playbackOptions(min=1, max=anim_length)

        start_frame = 1
        end_frame = anim_length
        cmds.setKeyframe(mesh, attribute="rotateY", value=0, t=start_frame)
        cmds.setKeyframe(mesh, attribute="rotateY", value=360, t=end_frame)
        cmds.selectKey(mesh, attribute="rotateY", k=True)
        cmds.keyTangent(inTangentType="linear", outTangentType="linear")

        return cam_transform

    def make_turntable_render(self, original_mesh, checked_mesh, check_name, anim_length, camera, text):
        """
           Sets up and renders a turntable playblast of a mesh check. Configures the save path, applies the
           correct vertex color set to the mesh if available, sets the active camera in the viewport, and
           exports the animation as an AVI file at 1280x720 resolution.

           Args:
               original_mesh (list): The name(s) of the original mesh, used to build the output video filename.
               checked_mesh (str): The name of the mesh being checked, used to look up and apply the correct
                                   color set and enable vertex color display.
               check_name (str): The name of the check being performed (e.g. "UVOverlap"), used to identify
                                 the target color set and build the output video filename.
               anim_length (int): The end frame of the playblast, defining how long the turntable animation is.
               camera (str): The name of the camera to use in the viewport for the playblast.
               text (str): Unused in the current implementation. Likely intended for overlaying text on the
                           turntable video.

           Returns:
               str: The path to the directory where the turntable video was saved.
           """
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.datetime.now().strftime("%H-%M-%S")

        save_path = self.create_new_directory("tests_turntables")
        cmds.workspace(os.path.abspath(save_path), openWorkspace=True)
        video_name = os.path.join(save_path, f"{original_mesh[0]}_{check_name}_{current_date}_{current_time}")
        cmds.setAttr("defaultRenderGlobals.imageFilePrefix", video_name, type="string")

        # set correct color set on mesh and enable vertex colors display
        color_set_name = f"{check_name}_{checked_mesh}"
        color_sets = cmds.polyColorSet(checked_mesh, query=True, allColorSets=True)
        if color_sets:
            if color_set_name in color_sets:
                cmds.polyColorSet(checked_mesh, currentColorSet=True, colorSet=color_set_name)
                cmds.setAttr(f"{checked_mesh}.displayColors", 1)
                cmds.sets(checked_mesh, e=True, forceElement="standardSurface1SG")

        panel = cmds.getPanel(withFocus=True)
        if not panel or cmds.getPanel(typeOf=panel) != "modelPanel":
            panels = cmds.getPanel(type="modelPanel")
            if panels:
                panel = panels[0]
        if panel:
            cmds.modelEditor(panel, e=True, camera=camera)

        cmds.playblast(cc=True,
                       et=anim_length,
                       f=video_name,
                       fo=True,
                       fmt="avi",
                       h=720,
                       p=100,
                       qlt=100,
                       sqt=False,
                       orn=False,
                       st=0,
                       w=1280,
                       v=False)

        return save_path

    def turntable_render_cleanup(self, camera, turntables_path):
        """
        Deletes the camera made for te turntable render.
        """
        cmds.delete(camera)

    # RENDER HELPER METHODS
    def build_vert_color_shader(self, color_set: str, mesh: str, shader_name:str):
        """
        Creates an aiStandardSurface shader to visualise the vertex colors on the mesh during rendering.
        :param color_set: Color set that holds the vertex colors of which to create the shaders.
        :param mesh: Mesh that holds vertex colors for which to create the shaders.
        :param shader_name: Name the shader should have.
        :return:
        """
        # create shader
        ai_shading_node = cmds.shadingNode("aiStandardSurface", asShader=True, name=f"{mesh}_ai{shader_name}")
        ai_vert_color_shader = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{mesh}_ai{shader_name}_SG")
        cmds.connectAttr(ai_shading_node + ".outColor", ai_vert_color_shader + ".surfaceShader", force=True)

        # create color data node -> will hold vertex color data of color set
        color_set_node = cmds.shadingNode("aiUserDataColor", asUtility=True, name=f"{mesh}_vert_colors_{shader_name}")
        cmds.setAttr(color_set_node + ".attribute", color_set, typ="string")
        cmds.setAttr(color_set_node + ".default", 1, 1, 1, typ="double3")

        # multiply this color with 1 so vertex always gets rendered
        multiply_node = cmds.shadingNode("aiMultiply", asUtility=True, name=f"{mesh}_vert_color_multiply")
        cmds.connectAttr(color_set_node + ".outColor", multiply_node + ".input1", f=True)

        # plug result into color of shader
        cmds.connectAttr(multiply_node + ".outColor", ai_shading_node + ".baseColor", f=True)

        # turn on export vertex colors on mesh
        cmds.setAttr(mesh + ".aiExportColors", 1)

        # apply shader to mesh
        cmds.sets(mesh, e=True, forceElement=ai_vert_color_shader)

        cmds.refresh(f=True)
        return ai_vert_color_shader

    def add_text_to_image(self, image_path: str, text: str, size: int) -> None:
        """
        Adds text to the left hand corner of an image.
        :param image_path: Path of image to put text on.
        :param text: Text to put on image.
        :param size: Text size to use.
        :return: None
        """
        img = Image.open(image_path)
        draw_img = ImageDraw.Draw(img)
        fnt = ImageFont.truetype("arial.ttf", size)
        draw_img.text((10,10), text, fill=(0,0,0), font=fnt)
        img.save(image_path)

my_checker = ModelChecker()

