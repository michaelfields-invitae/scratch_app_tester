import os
from datetime import datetime
from decimal import Decimal
from typing import List

from dateutil.relativedelta import relativedelta

from AMPPanelDesignLib.InventoryTracking import InventoryTracking, GLILotInfo
from AMPPanelDesignLib.PanelInfo import RawMaterialInfo, PanelInfo
from GeneratePanelFilesLib.Logger import Logger


def check_raw_material_inventory(logger: Logger, panel_info: PanelInfo, gsp1_raw_materials: List[RawMaterialInfo],
                                 gsp2_raw_materials: List[RawMaterialInfo], inventory_tracking: InventoryTracking,
                                 output_directory: str) -> None:
    logger.message("Checking GLI inventory levels...")
    if panel_info is None:
        logger.warning("No Panel Info config file provided, skipping raw material inventory check.")
        return
    elif inventory_tracking is None:
        logger.warning("No inventory tracking file provided, skipping raw material inventory check.")
        return

    min_expiration_date_delta_years = relativedelta(years=2)
    gli_inventory_check_output_file_path = os.path.join(output_directory, "gli_inventory_check.txt")
    logger.message(f"Writing raw materials with insufficient inventory volumes to {gli_inventory_check_output_file_path}")
    with open(gli_inventory_check_output_file_path, 'w') as output_file:
        output_file.write("\t".join(["Part_Number", "Additional_Volume_Required_uL"]) + "\n")
        for raw_material in gsp1_raw_materials + gsp2_raw_materials:
            if raw_material.spike_in_erp_description is not None or raw_material.is_catalog_panel:
                continue
            raw_material_volume_uL = raw_material.volume * Decimal(100) * panel_info.bulk_manufacturing_volume_ml
            if raw_material.part_number not in inventory_tracking:
                output_file.write("\t".join([raw_material.part_number, str(raw_material_volume_uL)]) + "\n")
            else:
                gli_lots = [gli_lot for gli_lot in inventory_tracking[raw_material.part_number]
                            if gli_lot.expiration_date >= datetime.today() + min_expiration_date_delta_years]
                gli_lots: List[GLILotInfo] = sorted(gli_lots, key=lambda lot: lot.expiration_date)
                gli_remaining_volume = sum(lot.volume_remaining for lot in gli_lots)
                if gli_remaining_volume < raw_material_volume_uL:
                    output_file.write("\t".join([raw_material.part_number, str(raw_material_volume_uL-gli_remaining_volume)]) + "\n")

