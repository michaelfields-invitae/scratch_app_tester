from PyQt5 import uic, QtWidgets
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QModelIndex, Qt, QUrl, QObject, pyqtSignal
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QLineEdit, QListView
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import sys

from dataclasses import dataclass, asdict
import generate_panel_files
from datetime import datetime

from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.files.file import File

import os

@dataclass
class RecipeOptionsInterface:
    CTF_filepath: str = None
    GTF_filepath: str = None
    BED_filepath: str = None
    panel_info_filepath: str = None
    design_repo_folder: str = None
    spikein_folder: str = None
    disable_CTF_cleaning: bool = None
    disable_GTF_cleaning: bool = None
    disable_prod_insert_gen: bool = None
    disable_dbom_gen: bool = None
    disable_calc_vols_for_raw_mats: bool = None
    disable_odoo_bom_file_gen: bool = None
    disable_label_info_file_gen: bool = None
    verbose_logging: bool = None
    output_dir: str = None

@dataclass
class WIOptionsInterface:
    # Required Inputs
    # Bools
    scale_volume_radio: bool = None
    num_SA_radio: bool = None
    # Values
    scale_volume: float = None
    num_SA: int = None

    # Optional Inputs
    # Bools
    exclude_lots_bool: bool = None
    force_lots_bool: bool = None
    exclude_bc_bool: bool = None
    force_bc_bool: bool = None
    custom_ret_vol_bool: bool = None
    min_exp_bool: bool = None
    custom_overage_bool: bool = None
    # Bool Values
    pick_LIFO_bool: bool = None
    force_QC_tubes_only_bool: bool = None
    # Values
    exclude_lots: str = None
    force_lots: str = None
    exclude_bc: str = None
    force_bc: str = None
    custom_ret_vol: float = None
    min_exp: str = None
    custom_overage: float = None


# IDK WHAT TO DO WITH THIS YET:::::::::::
# ui_path = r'C:\Users\mfields\Desktop\amp-panel-toolkit-python3-20230127\RUO_AIO_Order_Proc_v1_ui_Test.ui'
# ui_path = r'C:\Users\mfields\Desktop\amp-panel-toolkit-python3-20230127\RUO_AIO_Order_Proc_v1_CUSTOM_WIDGET_TESTER.ui'
# ui_path = r'C:\Qt\6.4.2\mingw_64\bin\RUO_AIO_Order_Proc_v1.ui'

ui_path = r'C:\Users\mfields\Desktop\amp-panel-toolkit-python3-20230127\RUO_AIO_Order_Proc_v2.ui'
baseUIClass, baseUIWidget = uic.loadUiType(ui_path)


class FormLogic(baseUIWidget, baseUIClass):
    def __init__(self, parent=None):
        super(FormLogic, self).__init__(parent)
        self.setupUi(self)
        self.ctx = self.connect_to_sharepoint()
        self.open_orders_url = "/sites/IDTArcherEngineering/Shared Documents/2_Open_Orders_Test"

        # Recipe Gen Inputs
        self.recipe_gen_line_edits = [
            self.line_edit_CTF_filepath,
            self.line_edit_GTF_filepath,
            self.line_edit_BED_filepath,
            self.line_edit_panel_info_filepath,
            self.line_edit_design_repo_folder,
            self.line_edit_spikein_folder,
            self.line_edit_recipe_gen_output_folder]

        self.recipe_gen_check_boxes = [
            self.check_box_disable_CTF_cleaning,
            self.check_box_disable_GTF_cleaning,
            self.check_box_disable_prod_insert_gen,
            self.check_box_disable_dbom_xml_file_gen,
            self.check_box_disable_calc_vols_for_raw_mats,
            self.check_box_disable_oddo_bom_file_gen,
            self.check_box_disable_label_info_file_gen,
            self.check_box_verbose_logging
        ]

        self.recipe_gen_list_views = [
            self.list_view_custom_pick_CTFS,
            self.list_view_CTFS_to_ignore
        ]

        # Work Ins Gen Inputs
        self.wi_gen_req_line_edits = [self.line_edit_build_volume,
                                      self.line_edit_num_sa]

        self.wi_gen_req_rad_btns = [self.radio_btn_volume,
                                    self.radio_btn_num_sa]

        self.wi_gen_opt_line_edits = [self.line_edit_exclude_lots,
                                      self.line_edit_force_lots,
                                      self.line_edit_exclude_bc,
                                      self.line_edit_force_bc,
                                      self.line_edit_custom_retain_vol,
                                      self.line_edit_min_exp,
                                      self.line_edit_custom_overage]

        self.wi_gen_opt_check_boxes = [self.check_box_exclude_lots,
                                       self.check_box_force_lots,
                                       self.check_box_exclude_bc,
                                       self.check_box_force_bc,
                                       self.check_box_custom_retain_vol,
                                       self.check_box_min_exp,
                                       self.check_box_custom_overage,
                                       self.check_box_force_qc_only,
                                       self.check_box_pick_lifo]

        # Recipe Generation Tab Logic
        self.btn_gen_recipe.clicked.connect(self.generate_recipe)
        self.btn_clr_all_custom_pick_CTFS.clicked.connect(lambda: self.list_view_custom_pick_CTFS.model.removeRows(0, self.list_view_custom_pick_CTFS.model.rowCount()))
        self.btn_clr_all_CTFS_to_ignore.clicked.connect(lambda: self.list_view_CTFS_to_ignore.model.removeRows(0, self.list_view_CTFS_to_ignore.model.rowCount()))
        self.btn_remove_custom_pick_CTF.clicked.connect(lambda: self.remove_selected_item_from_list_view(self.list_view_custom_pick_CTFS))
        self.btn_remove_CTF_to_ignore.clicked.connect(lambda: self.remove_selected_item_from_list_view(self.list_view_CTFS_to_ignore))
        self.btn_clr_all_ins_recipe_gen.clicked.connect(self.clr_all_ins_recipe_gen)

        # Work Instruction Generation / Inventory Assessment Tab Logic
        self.btn_gen_work_ins.clicked.connect(self.generate_work_instructions)
        self.btn_refresh_open_orders.clicked.connect(self.refresh_open_orders)
        self.btn_clear_req_ins_wi_gen.clicked.connect(self.clr_req_ins_wi_gen)

        # Req Ins Checking
        self.line_edit_build_volume.setReadOnly(True)
        self.line_edit_num_sa.setReadOnly(True)
        self.radio_btn_volume.toggled.connect(self.radio_btn_volume_clicked)
        self.radio_btn_num_sa.toggled.connect(self.radio_btn_num_sa_clicked)

        # Opt Ins Checking
        for line_edit in self.wi_gen_opt_line_edits:
            line_edit.setReadOnly(True)

        self.check_box_exclude_lots.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_exclude_lots))
        self.check_box_force_lots.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_force_lots))
        self.check_box_exclude_bc.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_exclude_bc))
        self.check_box_force_bc.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_force_bc))
        self.check_box_custom_retain_vol.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_custom_retain_vol))
        self.check_box_min_exp.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_min_exp))
        self.check_box_custom_overage.stateChanged.connect(lambda state: self.check_box_toggled(state, self.line_edit_custom_overage))



    def check_box_toggled(self, state, line_edit):
        line_edit.setReadOnly(state != Qt.Checked)
        if state != Qt.Checked:
            line_edit.clear()

    def radio_btn_volume_clicked(self):
        self.line_edit_build_volume.setReadOnly(False)
        self.line_edit_num_sa.setReadOnly(True)
        self.line_edit_num_sa.clear()

    def radio_btn_num_sa_clicked(self):
        self.line_edit_build_volume.setReadOnly(True)
        self.line_edit_build_volume.clear()
        self.line_edit_num_sa.setReadOnly(False)

    # ------ Recipe Generation Tab Functions ---------------------------------------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    def generate_recipe(self):
        # Data Extration From Line Edits and Check Boxes <- Redundant
        # Line Edits
        CTF_filepath_val = self.line_edit_CTF_filepath.text() if self.line_edit_CTF_filepath.text() else None
        GTF_filepath_val = self.line_edit_GTF_filepath.text() if self.line_edit_GTF_filepath.text() else None
        BED_filepath_val = self.line_edit_BED_filepath.text() if self.line_edit_BED_filepath.text() else None
        panel_info_filepath_val = self.line_edit_panel_info_filepath.text() if self.line_edit_panel_info_filepath.text() else None
        design_repo_folder_val = self.line_edit_design_repo_folder.text() if self.line_edit_design_repo_folder.text() else None
        spikein_folder_val = self.line_edit_spikein_folder.text() if self.line_edit_spikein_folder.text() else None
        output_dir_val = self.line_edit_recipe_gen_output_folder.text() if self.line_edit_recipe_gen_output_folder.text() else None

        # Check Boxes
        disable_CTF_cleaning_val = self.check_box_disable_CTF_cleaning.isChecked()
        disable_GTF_cleaning_val = self.check_box_disable_GTF_cleaning.isChecked()
        disable_prod_insert_gen_val = self.check_box_disable_prod_insert_gen.isChecked()
        disable_dbom_gen_val = self.check_box_disable_dbom_xml_file_gen.isChecked()
        disable_calc_vols_for_raw_mats_val = self.check_box_disable_calc_vols_for_raw_mats.isChecked()
        disable_odoo_bom_file_gen_val = self.check_box_disable_oddo_bom_file_gen.isChecked()
        disable_label_info_file_gen_val = self.check_box_disable_label_info_file_gen.isChecked()
        verbose_logging_val = self.check_box_verbose_logging.isChecked()

        recipe_options = RecipeOptionsInterface(CTF_filepath=CTF_filepath_val,
                                                GTF_filepath=GTF_filepath_val,
                                                BED_filepath=BED_filepath_val,
                                                panel_info_filepath=panel_info_filepath_val,
                                                design_repo_folder=design_repo_folder_val,
                                                spikein_folder=spikein_folder_val,
                                                disable_CTF_cleaning=disable_CTF_cleaning_val,
                                                disable_GTF_cleaning=disable_GTF_cleaning_val,
                                                disable_prod_insert_gen=disable_prod_insert_gen_val,
                                                disable_dbom_gen=disable_dbom_gen_val,
                                                disable_calc_vols_for_raw_mats=disable_calc_vols_for_raw_mats_val,
                                                disable_odoo_bom_file_gen=disable_odoo_bom_file_gen_val,
                                                disable_label_info_file_gen=disable_label_info_file_gen_val,
                                                verbose_logging=verbose_logging_val,
                                                output_dir=output_dir_val)

        generate_panel_files.load_arg_dict(recipe_options)
        # upload_file_to_sharepoint(file_to_upload = "C:\\Users\\mfields\\Desktop\\amp-panel-toolkit-python3-20230127\\requirements.txt", url = self.open_orders_url)

    # Converted to lambda
    # def clr_list_view(self, list_view):
    #     list_view.model.removeRows(0, list_view.model.rowCount())

    # Consider turning this into lambda or turning the lambda for clear all back into a function
    def remove_selected_item_from_list_view(self, list_view):
        print(list_view.selected_item)
        print(list_view.selected_item_index)
        list_view.model.removeRow(list_view.selected_item_index)

    def clr_all_ins_recipe_gen(self):
        for input_field in self.recipe_gen_line_edits:
            input_field.clear()

        for input_field in self.recipe_gen_check_boxes:
            input_field.setChecked(False)

        for input_field in self.recipe_gen_list_views:
            input_field.model.removeRows(0, input_field.model.rowCount())

    # END RECIPE GEN ----------------------------------------------------------------

    # ------ Work Instruction Generation / Inventory Assessment Tab Functions ------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    def generate_work_instructions(self):
        work_ins_options = WIOptionsInterface(scale_volume_radio=self.radio_btn_volume.isChecked(),
                                              num_SA_radio=self.radio_btn_num_sa.isChecked(),
                                              scale_volume=self.line_edit_build_volume.text() if self.line_edit_build_volume.text() else None,
                                              num_SA=self.line_edit_num_sa.text() if self.line_edit_num_sa.text() else None,
                                              exclude_lots_bool=self.check_box_exclude_lots.isChecked(),
                                              force_lots_bool=self.check_box_force_lots.isChecked(),
                                              exclude_bc_bool=self.check_box_exclude_bc.isChecked(),
                                              force_bc_bool=self.check_box_force_bc.isChecked(),
                                              custom_ret_vol_bool=self.check_box_custom_retain_vol.isChecked(),
                                              min_exp_bool=self.check_box_min_exp.isChecked(),
                                              custom_overage_bool=self.check_box_custom_overage.isChecked(),
                                              pick_LIFO_bool=self.check_box_pick_lifo.isChecked(),
                                              force_QC_tubes_only_bool=self.check_box_force_qc_only.isChecked(),
                                              exclude_lots=self.line_edit_exclude_lots.text() if self.line_edit_exclude_lots.text() else None,
                                              force_lots=self.line_edit_force_lots.text() if self.line_edit_force_lots.text() else None,
                                              exclude_bc=self.line_edit_exclude_bc.text() if self.line_edit_exclude_bc.text() else None,
                                              force_bc=self.line_edit_force_bc.text() if self.line_edit_force_bc.text() else None,
                                              custom_ret_vol=self.line_edit_custom_retain_vol.text() if self.line_edit_custom_retain_vol.text() else None,
                                              min_exp=self.line_edit_min_exp.text() if self.line_edit_min_exp.text() else None,
                                              custom_overage=self.line_edit_custom_overage.text() if self.line_edit_custom_overage.text() else None)
        print(self.list_view_open_orders.selected_item)
        # print(asdict(work_ins_options))

    def refresh_open_orders(self):
        self.list_view_open_orders.model.removeRows(0, self.list_view_open_orders.model.rowCount())
        open_orders = self.list_all_files_in_folder(
            "/sites/IDTArcherEngineering/Shared Documents/Script Dev Testing/2_Open_Orders_Test", self.ctx)
        for order in open_orders:
            self.list_view_open_orders.model.appendRow(QStandardItem(order))

        self.log_console_message(
            f'The latest completed orders were successfully fetched from IDT Archer Engineering on Sharepoint.')

    def clr_req_ins_wi_gen(self):
        # This doesn't work
        # for input_field in self.wi_gen_req_rad_btns:
        #     input_field.setChecked(True)

        for input_field in self.wi_gen_req_line_edits:
            input_field.clear()

    def clr_opt_ins_wi_gen(self):
        for input_field in self.wi_gen_opt_line_edits:
            input_field.clear()

        for input_field in wi_gen_opts_check_boxes:
            input_field.setChecked(False)

    # END WORK INSTRUCTION GEN ------------------------------------------------------

    # General helper functions -----------------------------------------------------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------
    def connect_to_sharepoint(self):
        # PUT IN TRY HERE AND ERROR HANDLING
        site_url = 'https://danaher.sharepoint.com/sites/IDTArcherEngineering'
        app_principal = {
            'client_id': 'ce0a0b4d-72fc-4801-8113-1f5d5d0470b6',
            'client_secret': 'AnsM0UdsBFp+ULYVzSPKdlSpeRYy746RZKPMVpaCy3k=',
        }

        context_auth = AuthenticationContext(url=site_url)
        context_auth.acquire_token_for_app(client_id=app_principal['client_id'],
                                           client_secret=app_principal['client_secret'])

        ctx = ClientContext(site_url, context_auth)
        return ctx

    def upload_file_to_sharepoint(self, file_to_upload, url):
        file_name = os.path.basename(file_to_upload)

        with open(file_to_upload, 'rb') as content_file:
            file_content = content_file.read()

        self.ctx.web.get_folder_by_server_relative_url(url).upload_file(file_name, file_content).execute_query()

    def list_all_files_in_folder(self, relative_url, ctx):
        libraryRoot = ctx.web.get_folder_by_server_relative_path(relative_url)
        ctx.load(libraryRoot)
        ctx.execute_query()

        files = libraryRoot.files
        ctx.load(files)
        ctx.execute_query()

        open_orders_names = []

        for myfile in files:
            split_file_name = myfile.properties["ServerRelativeUrl"].split("/")
            order_name = split_file_name[-1]
            file_url = myfile.properties["ServerRelativeUrl"]

            open_orders_names.append(order_name)

        return open_orders_names

    def log_console_message(self, text_to_log):
        current_dateTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamped_text_to_log = str(current_dateTime) + ": " + text_to_log
        self.text_browser_console_log.append(timestamped_text_to_log)

def main():
    app = QtWidgets.QApplication(sys.argv)
    ui = FormLogic(None)
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()