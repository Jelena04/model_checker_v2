import maya.cmds as cmds
from functools import partial

class ModelCheckerUI:
    def __init__(self, model_checker):
        self.model_checker = model_checker
        self.window = None
        self.layout = None
        self.specify_mesh_cb = None
        self.mesh_name_tf = None
        self.auto_select_cb = None

        self.tab_layout = None
        self.tab_content = None
        self.category_tabs = {}


        self.output_path_field = None
        self.cb_image_render = None
        self.cb_turntable_render = None
        self.cb_output_file_json = None
        self.cb_output_file_txt = None

        self.build_ui()


    def build_ui(self):
        """
           Builds and displays the main Model Checker UI window. Creates the top-level window and column
           layout, then delegates to the three section builders for Input, Checks Overview, and Output.
        """
        self.window = cmds.window(title='ModelCheckerV2.0', width=400, height=300)
        self.layout = cmds.columnLayout(adjustableColumn=True)

        self.build_section_1()
        self.build_section_2()
        self.build_section_3()

        cmds.showWindow(self.window)

    def build_section_1(self):
        """
            Builds the Input section of the UI (Section 1). Creates a collapsible frame containing options
            for importing a mesh via file browser, using the current scene selection as the target mesh,
            or specifying a target mesh by name via a text field.
        """
        # 1 MESH SELECTION
        sec_1_frame_layout = cmds.frameLayout("1. Input",
                                              bgc=[0.321, 0.522, 0.651],
                                              p=self.layout,
                                              cll=True,
                                              mh=5,
                                              mw=5)

        sec_1_col_layout = cmds.columnLayout(adj=True, bgc=(0.3, 0.3, 0.3), p=sec_1_frame_layout)
        cmds.separator(h=3, st="none", p=sec_1_col_layout)

        sec_1_import_row = cmds.rowLayout(nc=2, p=sec_1_col_layout, adjustableColumn=2)
        cmds.text(label="Import a mesh: ", align="left", p=sec_1_import_row)
        cmds.button(label="Browse...", c=self.fbx_file_select, p=sec_1_import_row, bgc=(0.2, 0.2, 0.2))
        cmds.separator(h=3, st="none", p=sec_1_col_layout)

        sec_1_mesh_input = cmds.columnLayout(adj=True, bgc=(0.3, 0.3, 0.3), p=sec_1_col_layout)
        auto_select_row = cmds.rowLayout(nc=2, p=sec_1_mesh_input)
        self.auto_select_cb = cmds.checkBox("Use current selection as target mesh", p=sec_1_mesh_input,v=True ,cc=partial(self.update_checkbox_states, "auto"))

        target_mesh_row = cmds.rowLayout(nc=2, p=sec_1_mesh_input)
        self.specify_mesh_cb = cmds.checkBox("Specify target mesh", p=target_mesh_row,cc=partial(self.update_checkbox_states, "specify"))
        self.mesh_name_tf = cmds.textField(p=target_mesh_row, en=False)

    def build_section_2(self):
        """
        Builds the Checks Overview section of the UI (Section 2). Creates a collapsible frame with a
        tab layout containing three categories: Geometry, UVs, and Misc. Each as its own column
        layout stored in self.category_tabs. Also provides a button for loading plugin checks.
        """
        sec_2_frame_layout = cmds.frameLayout("2. Checks overview", bgc=[0.321, 0.522, 0.651],p=self.layout,
                                              cll=True, mh=5, mw=5)

        cmds.button(label="Add Plugin", c=self.load_plugins, p=sec_2_frame_layout)
        cmds.separator(h=5, st="none", p=sec_2_frame_layout)

        self.tab_layout = cmds.tabLayout(p=sec_2_frame_layout, imh=5, imw=5, bgc=(0.3, 0.3, 0.3))
        for category in ["Geometry", "UVs", "Misc"]:
            self.tab_content = cmds.columnLayout(f"{category}_tablayout",adj=True, p=self.tab_layout)
            col = cmds.columnLayout()
            cmds.tabLayout(self.tab_layout, edit=True, tabLabel=(self.tab_content, category))
            self.category_tabs[category] = col

    def build_section_3(self):
        """
        Builds the Output section of the UI (Section 3). Creates a collapsible frame containing an
        output directory path field, per-check output options (image render, turntable render), data
        export format options (JSON report, TXT report), and buttons to run selected or all checks.
        """
        # 3 OUTPUT OPTIONS
        sec_3_frame_layout = cmds.frameLayout(
            "3. Output",
            bgc=[0.321, 0.522, 0.651],
            p=self.layout,
            cll=True,
            mh=5,
            mw=5)

        sec_3_col_layout = cmds.columnLayout(adj=True, bgc=(0.3, 0.3, 0.3), p=sec_3_frame_layout)

        self.output_path_field = cmds.textFieldButtonGrp(
            label='Output path:',
            text=r'None',
            buttonLabel='Browse',
            buttonCommand=self.output_file_select,
            p=sec_3_col_layout,
            columnAlign3=("left", "left", "left"),
            cw=(1, 100)
        )

        sec_3_separator = cmds.rowLayout(nc=2, p=sec_3_col_layout, adj=2, h=30)
        cmds.text(label="Per check ", p=sec_3_separator, fn="smallObliqueLabelFont")
        cmds.separator(h=5, st="in", p=sec_3_separator)

        sec_3_outputs = cmds.rowLayout(nc=2, cw2=(90, 100), p=sec_3_col_layout)
        self.cb_image_render = cmds.checkBox(label="Image render", p=sec_3_outputs)
        self.cb_turntable_render = cmds.checkBox(label="Turntable render", p=sec_3_outputs)

        sec_3_separator = cmds.rowLayout(nc=2, p=sec_3_col_layout, adj=2, h=30)
        cmds.text(label="Data ", p=sec_3_separator, fn="smallObliqueLabelFont")
        cmds.separator(h=5, st="in", p=sec_3_separator)

        sec_3_output_formats = cmds.rowLayout(nc=4, cw4=(90, 80, 110, 90), p=sec_3_col_layout)
        self.cb_output_file_json = cmds.checkBox(label="JSON report", p=sec_3_output_formats)
        self.cb_output_file_txt = cmds.checkBox(label="TXT report", p=sec_3_output_formats)

        sec_3_separator = cmds.rowLayout(nc=2, p=sec_3_frame_layout, adj=2, h=30)
        cmds.button("Run selected checks", p=sec_3_separator, c=self.model_checker.run_selected_checks, w=200)
        cmds.button("Run all checks", p=sec_3_separator, c=self.model_checker.run_all_checks, w=200)
        # cmds.button("Close", p=sec_3_separator, c=self.helper_on_close_clicked)

    def load_plugins(self, *args):
        """
        Opens up a dialog for the user to select plugin(s) to load.
        :return:
        """
        files = cmds.fileDialog2(fm=4, ds=1, cap="Please select plugin(s) to load", ff="*.py")
        print(files)
        if not files:
            return

        for filepath in files:
            self.model_checker.load_plugin(filepath)

    def fbx_file_select(self, *args):
        """
        Opens a file dialog for the user to select an FBX file to import. If a file is selected,
        passes the filepath to the model checker for processing.
        """

        file_directory = cmds.fileDialog2(cap="Please select a fbx file", fm=1)
        if file_directory:
            self.model_checker.handle_mesh_path_input(file_directory[0])

    def output_file_select(self, *_args):
        """
        Allows the user to enter a directory to save the output files in through a pop-up window.
        :return: None
        """
        output_directory = cmds.fileDialog2(cap="Please select directory to save output in", fm=3)
        if not output_directory:
            return
        cmds.textFieldButtonGrp(self.output_path_field, e=True, text=output_directory[0])

    def update_checkbox_states(self, source, *args):
        """
        Keeps the 'auto select' and 'specify mesh' checkboxes mutually exclusive. When one is enabled,
        the other is disabled. Also enables or disables the mesh name text field depending on whether
        'specify mesh' is active.
        param: source: Indicates which checkbox triggered the update.
        """
        if source == "specify":
            if cmds.checkBox(self.specify_mesh_cb, q=True, v=True):
                cmds.textField(self.mesh_name_tf, e=True, en=True)
                cmds.checkBox(self.auto_select_cb, e=True, v=False)
        elif source == "auto":
            if cmds.checkBox(self.auto_select_cb, q=True, v=True):
                cmds.textField(self.mesh_name_tf, e=True, en=False)
                cmds.checkBox(self.specify_mesh_cb, e=True, v=False)
